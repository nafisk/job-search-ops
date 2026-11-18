import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from job_search_ops import bootstrap, host_evidence, snapshots
from job_search_ops.doctor import HostReceipt
from job_search_ops.config import ConfigError
from test_pipeline import NativeConnector, WORKBOOK, packet


def captured_read():
    connector = NativeConnector()
    raw = connector.snapshot()
    ranges, mask = raw.pop("_read_ranges"), raw.pop("_cell_fields")
    metadata = {"spreadsheetId": raw["spreadsheetId"], "properties": raw["properties"],
                "sheets": [{"properties": s["properties"]} for s in raw["sheets"]]}
    reads = [{"request": {"spreadsheet_id": WORKBOOK, "ranges": ranges, "cell_fields": mask}, "response": raw}]
    return metadata, reads


def check(operation, tool, response, assertions, request=None):
    return {"operation": operation, "tool": tool, "request": request or {},
            "response": response, "assertions": assertions}


def bootstrap_response():
    from job_search_ops.sheets import SCHEMAS, STATUSES
    native = NativeConnector()
    for name, headers in SCHEMAS.items():
        tab = native.tab(name)
        tab["properties"]["gridProperties"]["frozenRowCount"] = 4
        if name not in ("Daily Summary", "How to Use"):
            tab["basicFilter"] = {"range": {"sheetId": tab["properties"]["sheetId"], "startRowIndex": 3, "endColumnIndex": len(headers)}}
    native.tab("Jobs")["data"][0]["columnMetadata"] = [{} for _ in range(14)] + [{"hiddenByUser": True}]
    for field in ("First Seen", "Last Seen"):
        native.cell("Jobs", 4, field)["userEnteredFormat"] = {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}
    native.cell("Jobs", 4, "Application Status")["dataValidation"] = {"strict": True, "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in STATUSES]}}
    formulas = ["=COUNTA(Jobs!C5:C)"] + [f'=COUNTIF(Jobs!F5:F,"{status}")' for status in ("New", "Saved", "Asked for referral", "Applied", "Interviewing")] + ["=COUNTA('Rated Companies'!A5:A)", "=COUNTA('Job Sources'!A5:A)"]
    for row, formula in enumerate(formulas, 4):
        native.cell("Daily Summary", row, "Value")["userEnteredValue"] = {"formulaValue": formula}
    raw = native.snapshot()
    raw.pop("_read_ranges"); raw.pop("_cell_fields")
    return {"spreadsheetId": WORKBOOK, "updatedSpreadsheet": raw, "replies": []}


class NativeBridgeTests(unittest.TestCase):
    def test_public_http_evidence_can_use_native_web_without_curl(self):
        native = check("bounded_http", "web__run", {"text": "Fictional public job page"},
                       [{"path": "/text", "contains": "public job"}], {"open": [{"ref_id": "https://example.invalid/job"}]})
        receipt = HostReceipt("public_research", "operation_verified", "fictional-public-http", "2026-10-18T12:00:00Z",
                              None, None, "bounded_http", {"operations": ["bounded_http"], "native_checks": [native]})
        self.assertTrue(host_evidence.verify(receipt))

    def test_assemble_preserves_observed_bounds_and_rejects_mixed_workbooks(self):
        metadata, reads = captured_read()
        snapshot = snapshots.assemble({"structuredContent": metadata}, reads)
        self.assertEqual(snapshot["_read_ranges"], reads[0]["request"]["ranges"])
        self.assertEqual(bootstrap.plan(snapshot)["spreadsheet_id"], WORKBOOK)
        reads[0]["response"]["spreadsheetId"] = "another-account-workbook"
        with self.assertRaises(ConfigError): snapshots.assemble(metadata, reads)

    def test_bootstrap_rejects_missing_header_or_existing_history(self):
        metadata, reads = captured_read()
        snapshot = snapshots.assemble(metadata, reads)
        snapshot["sheets"][3]["data"][0]["rowData"][3]["values"][0]["userEnteredValue"] = {"stringValue": "Wrong"}
        with self.assertRaises(ConfigError): bootstrap.plan(snapshot)
        connector = NativeConnector()
        connector.set("Rated Companies", 4, "Company", "Existing private row")
        with self.assertRaises(ConfigError): bootstrap.plan(connector.snapshot())

    def test_bootstrap_summary_is_unbounded_and_key_hidden(self):
        metadata, reads = captured_read()
        plan = bootstrap.plan(snapshots.assemble(metadata, reads))
        formulas = plan["requests"][-1]["updateCells"]["rows"]
        self.assertIn("C5:C)", formulas[0]["values"][1]["userEnteredValue"]["formulaValue"])
        self.assertTrue(any(r.get("updateDimensionProperties", {}).get("properties", {}).get("hiddenByUser") for r in plan["requests"]))

    def tracker_receipt(self):
        metadata, reads = captured_read()
        checks = [
            check("get_profile", "mcp__codex_apps__google_drive_get_profile", {"emailAddress": "alex@example.invalid"}, [{"path": "/emailAddress", "equals": "alex@example.invalid"}]),
            check("get_spreadsheet_metadata", "mcp__codex_apps__google_drive_get_spreadsheet_metadata", metadata, [{"path": "/spreadsheetId", "equals": WORKBOOK}]),
            check("get_spreadsheet_cells", "mcp__codex_apps__google_drive_get_spreadsheet_cells", reads[0]["response"], [{"path": "/spreadsheetId", "equals": WORKBOOK}], reads[0]["request"]),
            check("bootstrap_readback", "mcp__codex_apps__google_drive_batch_update_spreadsheet", bootstrap_response(), [{"path": "/spreadsheetId", "equals": WORKBOOK}]),
        ]
        return HostReceipt("resource.tracker", "operation_verified", "fictional-observation", "2026-10-18T12:00:00Z", "alex@example.invalid", WORKBOOK, "schema-readback", {"installation_id": "alex", "operations": [c["operation"] for c in checks], "native_checks": checks, "snapshot": snapshots.assemble(metadata, reads)})

    def test_native_tracker_requires_actual_captured_snapshot_and_identity(self):
        receipt = self.tracker_receipt()
        self.assertTrue(host_evidence.verify(receipt))
        self.assertFalse(host_evidence.verify(replace(receipt, identity="someone@example.invalid")))
        forged = copy.deepcopy(receipt.evidence)
        forged["snapshot"]["properties"]["timeZone"] = "Europe/London"
        self.assertFalse(host_evidence.verify(replace(receipt, evidence=forged)))
        wrong_structure = copy.deepcopy(receipt.evidence)
        wrong_structure["native_checks"][-1]["response"]["updatedSpreadsheet"]["sheets"][0]["data"][0]["columnMetadata"][14]["hiddenByUser"] = False
        self.assertFalse(host_evidence.verify(replace(receipt, evidence=wrong_structure)))

    def test_error_results_unchecked_flags_and_wrong_provider_are_not_evidence(self):
        receipt = self.tracker_receipt()
        self.assertFalse(host_evidence.verify(replace(receipt, evidence={"verified": True})))
        bad = copy.deepcopy(receipt.evidence)
        bad["native_checks"][0]["tool"] = "arbitrary_tool"
        self.assertFalse(host_evidence.verify(replace(receipt, evidence=bad)))
        bad = copy.deepcopy(receipt.evidence)
        bad["native_checks"][0]["tool"] = "mcp__codex_apps__google_drive_get_spreadsheet_cells"
        self.assertFalse(host_evidence.verify(replace(receipt, evidence=bad)))
        bad = copy.deepcopy(receipt.evidence)
        bad["native_checks"][0]["response"] = {"isError": True, "emailAddress": "alex@example.invalid"}
        self.assertFalse(host_evidence.verify(replace(receipt, evidence=bad)))

    def test_first_pass_cannot_attach_an_uncaptured_expected_manifest(self):
        manifest = {"workflow": "blind", "run_id": "example-run", "status": "complete", "unsynced_count": 0, "workbook_id": WORKBOOK, "delivery": "chat_verified"}
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        checks = [check("accepted_manifest_readback", "exec_command", {"exit_code": 0, "output": json.dumps(manifest)}, [{"path": "/exit_code", "equals": 0}]), check("delivery_readback", "mcp__codex_app__read_thread", {"threadId": "example-chat", "text": "saved"}, [{"path": "/text", "equals": "saved"}])]
        receipt = HostReceipt("first_live_pass", "operation_verified", "fictional-run-observation", "2026-10-18T12:00:00Z", None, "example-run", "run-readback", {**manifest, "accepted_manifest": manifest, "accepted_manifest_sha256": digest, "operations": [c["operation"] for c in checks], "native_checks": checks})
        self.assertTrue(host_evidence.verify(receipt))
        checks[0]["response"]["output"] = "unrelated output"
        self.assertFalse(host_evidence.verify(receipt))

    def test_local_first_pass_hash_is_bound_to_the_captured_manifest(self):
        manifest = {"workflow": "main", "run_id": "local-run", "status": "complete", "unsynced_count": 0,
                    "workbook_id": "local:fictional", "delivery": "chat_verified", "tracker_file_sha256": "a" * 64}
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        checks = [check("accepted_manifest_readback", "exec_command", {"exit_code": 0, "output": json.dumps(manifest)}, [{"path": "/exit_code", "equals": 0}]),
                  check("delivery_readback", "mcp__codex_app__read_thread", {"threadId": "fictional-chat", "text": "saved"}, [{"path": "/text", "equals": "saved"}])]
        evidence = {**manifest, "accepted_manifest": manifest, "accepted_manifest_sha256": digest, "operations": [x["operation"] for x in checks], "native_checks": checks}
        receipt = HostReceipt("first_live_pass", "operation_verified", "local-readback", "2026-10-18T12:00:00Z", None, "local-run", "run-readback", evidence)
        self.assertTrue(host_evidence.verify(receipt))
        self.assertFalse(host_evidence.verify(replace(receipt, evidence={**evidence, "tracker_file_sha256": "b" * 64})))

    def test_fresh_install_native_binding_blind_save_and_runtime_profile_agree(self):
        from job_search_ops import config, queue, setup, sheets
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            private = base / "instance"
            settings = json.loads((config.SUPPORT_ROOT / "config/legacy/installation.json").read_text())
            profile = json.loads((config.SUPPORT_ROOT / "config/legacy/profile.json").read_text())
            settings.update(instance_root=str(private), profile_path=str(base / "profile.json"))
            profile["private"] = {"state_root": str(private / "state"), "refs": {}}
            (base / "profile.json").write_text(json.dumps(profile))
            (base / "config.json").write_text(json.dumps(settings))
            cfg = config.load_config(base / "config.json")
            setup.init_instance(cfg)
            intent = setup.prepare_resource(cfg, "tracker", "tracker", {"title": "Fictional test tracker"})
            receipt = self.tracker_receipt()
            evidence = dict(receipt.evidence, installation_id=cfg["installation_id"], intent_id=intent["intent_id"], request_digest=intent["request_digest"])
            receipt = replace(receipt, evidence=evidence)
            setup.record_resource(cfg, "tracker", "tracker", receipt, host_evidence.verify, now=receipt.checked_at)
            runtime = setup.runtime_profile(cfg)
            self.assertEqual(runtime["trackers"]["jobs"]["workbook_id"], WORKBOOK)
            approved = json.loads((private / "state/approved-policies.json").read_text())
            proposal = packet("blind")
            proposal["policy"].update(id=approved["sources"]["blind"]["id"], version=approved["sources"]["blind"]["version"])
            queue.enqueue(private, proposal)
            connector = NativeConnector()
            journal = sheets.prepare(private, WORKBOOK, connector.snapshot(), "central")
            connector.apply(sheets.authorize_write(private, journal["journal_id"], connector.snapshot())["requests"])
            saved = sheets.verify_and_commit(private, journal["journal_id"], connector.snapshot())
            self.assertEqual(saved["new_jobs"][0]["tier"], "stretch")
            self.assertEqual(queue.pending(private), [])
            self.assertEqual(setup.init_instance(cfg)["resources"]["tracker:tracker"]["resource_id"], WORKBOOK)


if __name__ == "__main__": unittest.main()
