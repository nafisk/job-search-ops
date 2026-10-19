"""Local tracker contract; real artifact-tool smoke runs when its runtime exists."""
import copy
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from job_search_ops import local_excel as local, queue, sheets, setup
from job_search_ops.config import ConfigError
from test_pipeline import packet, policies

DEPENDENCIES = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
NODE = Path(os.environ.get("JOB_SEARCH_TEST_NODE", DEPENDENCIES / "node/bin/node"))
MODULES = Path(os.environ.get("JOB_SEARCH_TEST_NODE_MODULES", DEPENDENCIES / "node/node_modules"))
RUNTIME = NODE.is_file() and (MODULES / "@oai/artifact-tool").is_dir()
WORKBOOK = "local:fictional-installation"


class LocalReadTests(unittest.TestCase):
    def test_template_is_explicit_local_evidence(self):
        snapshot = local.inspect_workbook(local.TEMPLATE, WORKBOOK)
        self.assertEqual(snapshot.provider, "local_xlsx")
        self.assertNotIn("spreadsheetId", snapshot.raw)
        self.assertEqual(len(snapshot.raw["file_sha256"]), 64)
        self.assertFalse(snapshot.rows("Jobs"))
        self.assertIn("1000", snapshot.rows("Daily Summary")[0][1]["Value"])

    def test_google_identity_and_symlink_rejected(self):
        with self.assertRaises(queue.ProtocolError):
            local.inspect_workbook(local.TEMPLATE, "google-example")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "tracker.xlsx"
            path.symlink_to(local.TEMPLATE)
            with self.assertRaisesRegex(queue.ProtocolError, "symlink"):
                local.inspect_workbook(path, WORKBOOK)

    def test_conflicting_actual_hyperlink_is_rejected(self):
        cell = {"userEnteredValue": sheets.hyperlink("https://example.com/jobs/1"), "xlsx_relationship_target": "https://example.com/jobs/2"}
        with self.assertRaisesRegex(queue.ProtocolError, "conflicts"):
            local.LocalSnapshot.link_target(cell)

    def test_open_excel_lock_prevents_read_and_sync(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "tracker.xlsx"
            shutil.copyfile(local.TEMPLATE, path)
            path.with_name("~$tracker.xlsx").touch()
            with self.assertRaisesRegex(queue.ProtocolError, "close it"):
                local.inspect_workbook(path, WORKBOOK)

    def test_claim_cannot_release_unresolved_tracking_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with queue.locked(root) as base:
                queue.acquire_claim(base, WORKBOOK, "central")
                queue.atomic(base / "writer/local-tracking/fixture.json", {"workbook_id": WORKBOOK, "status": "write_pending"})
            with self.assertRaisesRegex(queue.ProtocolError, "Reconcile"):
                queue.release_claim(root, WORKBOOK, "central")

    def test_literal_cache_repair_preserves_formula_and_other_cells(self):
        text = '2026-10-18T08:00:00+00:00'
        original = '<x:worksheet xmlns:x="' + local.NS["m"] + '"><x:sheetData><x:row r="5"><x:c r="J5" s="21" t="n"><x:f>"' + text + '"</x:f><x:v>46313.333333333336</x:v></x:c><x:c r="K5" t="n"><x:f>1+1</x:f><x:v>2</x:v></x:c></x:row></x:sheetData></x:worksheet>'
        original = original.replace('<x:c r="J5"', '<x:c r="I5" s="2" /><x:c r="J5"')
        repaired = local._repair_literal_caches(original)
        cells = ET.fromstring(repaired).findall(".//m:c", local.NS)
        literal = cells[1]
        self.assertEqual(literal.get("t"), "str")
        self.assertEqual(literal.findtext("m:f", namespaces=local.NS), '"' + text + '"')
        self.assertEqual(literal.findtext("m:v", namespaces=local.NS), text)
        self.assertIn('<x:c r="K5" t="n"><x:f>1+1</x:f><x:v>2</x:v></x:c>', repaired)
        self.assertEqual(local._entered(literal, []), {"formulaValue": '="' + text + '"'})
        literal.find("m:v", local.NS).text = "conflicting cached value"
        with self.assertRaisesRegex(queue.ProtocolError, "cache differs"):
            local._entered(literal, [])


@unittest.skipUnless(RUNTIME, "Codex bundled artifact-tool runtime is unavailable; local XLSX integration remains unverified")
class LocalArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "tracker.xlsx"
        self.config = {"instance_root": str(self.root), "installation_id": "fictional-installation", "tracker": {"provider": "local_xlsx", "path": str(self.path)}}
        self.intent = {"intent_id": "fictional-intent", "request_digest": "fixture-request", "request": self.config["tracker"]}
        queue.atomic(self.root / "installation.json", {"resources": {"tracker:tracker": self.intent}})
        queue.configure_policies(self.root, WORKBOOK, policies())

    def pilot_hold(self, enabled=True):
        manifest = queue.read(self.root / "installation.json")
        if enabled:
            manifest["preferences_update"] = {"update_id": "manual-pilot", "pilot_required": ["main"]}
        else:
            manifest.pop("preferences_update", None)
        queue.atomic(self.root / "installation.json", manifest)

    def initialize(self):
        return local.initialize(self.config, NODE, MODULES)

    def sync(self):
        return local.merge(self.root, WORKBOOK, self.path, NODE, MODULES)

    def enqueue(self, source="portal", packet_id="one", event="event-1"):
        value = packet(source, packet_id, event=event)
        value["workbook_id"] = WORKBOOK
        value["jobs"][0]["notes"] = "=Literal note, never a formula"
        queue.enqueue(self.root, value)
        return value

    def test_real_roundtrip_dedup_manual_fields_blind_and_literal_text(self):
        evidence = self.initialize()
        self.assertTrue(local.verify_binding(self.config, evidence))
        self.assertEqual(self.initialize(), evidence)
        original = self.enqueue()
        receipt = self.sync()
        self.assertEqual(receipt["provider"], "local_xlsx")
        self.assertEqual(receipt["file_sha256"], local.file_hash(self.path))
        snapshot = local.inspect_workbook(self.path, WORKBOOK)
        row = snapshot.state()["Jobs"]["rows"][0]
        self.assertEqual(row["values"]["Notes"], "=Literal note, never a formula")
        self.assertEqual(row["url"], original["jobs"][0]["url"])
        self.assertIsInstance(row["values"]["First Seen"], int)
        self.assertEqual(snapshot.rows("Job Sources")[0][1]["Observed At"], original["observed_at"])
        self.assertEqual(queue.enqueue(self.root, original)["status"], "done")
        self.assertEqual(self.sync()["status"], "empty")
        changes = [{"tab": "Jobs", "row": 4, "column": col, "after": sheets.native(value)} for col, value in ((5, "Applied"), (9, "My referrer"), (13, "=My literal note"))]
        changes.append({"tab": "How to Use", "row": 20, "column": 1, "after": sheets.native("My unrelated cell")})
        exact_text = '2026-10-18T08:00:00.123456+00:00 "quoted"'
        changes.append({"tab": "How to Use", "row": 21, "column": 1, "after": sheets.native(exact_text)})
        manual = self.root / "manual.xlsx"
        local._artifact(self.path, manual, changes, NODE, MODULES)
        os.replace(manual, self.path)
        self.enqueue("blind", "blind-one", "blind-event")
        receipt2 = self.sync()
        final = local.inspect_workbook(self.path, WORKBOOK)
        rows = final.state()["Jobs"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["values"]["Seen Count"], 2)
        for name, value in {"Application Status": "Applied", "Referral Contact": "My referrer", "Notes": "=My literal note"}.items():
            self.assertEqual(rows[0]["values"][name], value)
        self.assertEqual(final.all_cells["How to Use"]["20:1"]["userEnteredValue"], sheets.native("My unrelated cell"))
        self.assertEqual(final.all_cells["How to Use"]["21:1"]["userEnteredValue"], {"formulaValue": '="' + exact_text.replace('"', '""') + '"'})
        self.assertEqual(final.state()["Job Sources"]["rows"][-1]["values"]["Qualification Tier"], "stretch")
        self.assertEqual(receipt2["new_jobs"], [])

    def test_publish_before_receipt_failure_recovers_without_second_edit(self):
        self.initialize()
        self.enqueue()
        self.pilot_hold()
        with setup.execution_context(pilot_update_id="manual-pilot"), patch.object(sheets, "verify_and_commit", side_effect=OSError("simulated receipt failure")):
            with self.assertRaisesRegex(OSError, "receipt failure"):
                self.sync()
        after_hash = local.file_hash(self.path)
        with patch.object(local, "_artifact", side_effect=AssertionError("must not export twice")), patch.object(sheets, "authorize_write", side_effect=AssertionError("must not authorize a second write")):
            receipt = self.sync()
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            self.sync()
        self.assertEqual(receipt["status"], "saved")
        self.assertEqual(local.file_hash(self.path), after_hash)
        self.assertEqual(len(local.inspect_workbook(self.path, WORKBOOK).rows("Jobs")), 1)
        self.assertFalse(queue.pending(self.root))

    def test_interruption_before_publish_retries_only_unchanged_local_file(self):
        self.initialize()
        self.enqueue()
        before_hash = local.file_hash(self.path)
        original_sync = local._sync_file

        def interrupted(path):
            if path.name.endswith(".candidate.xlsx"):
                raise OSError("simulated interruption before publication")
            return original_sync(path)

        with patch.object(local, "_sync_file", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "before publication"):
                self.sync()
        self.assertEqual(local.file_hash(self.path), before_hash)
        journals = list((self.root / "state/writer/journals").glob("*.json"))
        self.assertEqual(len(journals), 1)
        interrupted_journal = queue.read(journals[0])
        self.assertEqual(interrupted_journal["status"], "write_pending")
        # No connector call exists locally: the exclusive lock and unchanged
        # original hash establish that this file replacement can be retried.
        receipt = self.sync()
        self.assertEqual(receipt["status"], "saved")
        self.assertEqual(queue.read(journals[0])["attempts"], 2)
        self.assertNotEqual(queue.read(journals[0])["attempt_id"], interrupted_journal["attempt_id"])
        self.assertEqual(len(local.inspect_workbook(self.path, WORKBOOK).rows("Jobs")), 1)
        self.assertFalse(queue.pending(self.root))

    def test_external_change_before_publish_preserves_changed_original(self):
        self.initialize()
        self.enqueue()
        original_artifact = local._artifact
        def changed(*args, **kwargs):
            result = original_artifact(*args, **kwargs)
            # ZIP permits trailing bytes: an outside save changes the full hash.
            with self.path.open("ab") as stream:
                stream.write(b"outside change")
            return result
        with patch.object(local, "_artifact", side_effect=changed):
            with self.assertRaisesRegex(queue.ProtocolError, "changed while preparing"):
                self.sync()
        self.assertTrue(self.path.read_bytes().endswith(b"outside change"))
        self.assertFalse(local.inspect_workbook(self.path, WORKBOOK).rows("Jobs"))
        self.assertTrue(queue.pending(self.root))

    def test_unknown_existing_workbook_not_overwritten(self):
        shutil.copyfile(local.TEMPLATE, self.path)
        before = local.file_hash(self.path)
        with self.assertRaisesRegex(queue.ProtocolError, "explicit adoption"):
            self.initialize()
        self.assertEqual(local.file_hash(self.path), before)

    def test_tracking_only_add_update_recovery_and_later_discovery(self):
        self.initialize()
        record = {"job_key": "example:req-1", "company": "Example Company", "title": "Software Engineer", "url": "https://careers.example.com/jobs/req-1", "status": "Applied", "observed_at": "2026-10-18T08:00:00+00:00", "evidence_ref": "fictional application confirmation", "role_evidence_ref": "fictional verified official role page"}
        plan = {"workbook_id": WORKBOOK, "expected_file_sha256": local.file_hash(self.path), "updates": [], "new_records": [record]}
        receipt = local.update_tracking(self.root, WORKBOOK, self.path, plan, NODE, MODULES)
        self.assertEqual(receipt["new_records"], [record])
        self.assertEqual(queue.read(queue.storage(self.root) / "writer/receipts" / (receipt["receipt_id"] + ".json")), receipt)
        snapshot = local.inspect_workbook(self.path, WORKBOOK)
        self.assertEqual(snapshot.rows("Jobs")[0][1]["Source"], "Tracking evidence")
        self.assertEqual(snapshot.rows("Job Sources")[0][1]["Qualification Tier"], "not_screened")
        update = {"workbook_id": WORKBOOK, "expected_file_sha256": local.file_hash(self.path), "updates": [{"job_key": record["job_key"], "field": "Application Status", "old_value": "Applied", "new_value": "Interviewing", "evidence_ref": "fictional interview invitation"}]}
        self.pilot_hold()
        with setup.execution_context(pilot_update_id="manual-pilot"), patch.object(local, "_tracking_receipt", side_effect=OSError("receipt interrupted")):
            with self.assertRaisesRegex(OSError, "receipt interrupted"):
                local.update_tracking(self.root, WORKBOOK, self.path, update, NODE, MODULES)
        with self.assertRaisesRegex(queue.ProtocolError, "interrupted local tracking"):
            self.sync()
        after_hash = local.file_hash(self.path)
        with patch.object(local, "_artifact", side_effect=AssertionError("must not repeat tracking export")):
            self.assertEqual(local.update_tracking(self.root, WORKBOOK, self.path, update, NODE, MODULES)["status"], "saved")
        self.assertEqual(local.file_hash(self.path), after_hash)
        blocked = {"workbook_id": WORKBOOK, "expected_file_sha256": after_hash, "updates": [{"job_key": record["job_key"], "field": "Notes", "old_value": "", "new_value": "held", "evidence_ref": "fictional manual review"}]}
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            local.update_tracking(self.root, WORKBOOK, self.path, blocked, NODE, MODULES)
        self.pilot_hold(False)
        self.enqueue()
        self.sync()
        final = local.inspect_workbook(self.path, WORKBOOK)
        self.assertEqual(len(final.rows("Jobs")), 1)
        self.assertEqual(final.rows("Jobs")[0][1]["Application Status"], "Interviewing")
        self.assertEqual(final.rows("Jobs")[0][1]["Seen Count"], 2)
        brief = queue.prepare_brief(self.root, "local-tracking-report")
        tracked = [entry for entry in brief["receipts"] if entry.get("operation") == "tracking"]
        self.assertEqual(len(tracked), 2)
        self.assertEqual({entry["change"] for entry in brief["tracking_summary"]}, {"Tracked application: Applied", "Application Status: Applied → Interviewing"})
        altered = self.root / "altered.xlsx"
        change = {"tab": "Jobs", "row": 4, "column": 4, "after": sheets.hyperlink("https://careers.example.com/jobs/wrong-role")}
        local._artifact(self.path, altered, [change], NODE, MODULES)
        os.replace(altered, self.path)
        wrong = {"workbook_id": WORKBOOK, "expected_file_sha256": local.file_hash(self.path), "updates": [{"job_key": record["job_key"], "field": "Notes", "old_value": final.rows("Jobs")[0][1]["Notes"], "new_value": "changed", "evidence_ref": "fictional review"}]}
        with self.assertRaisesRegex(queue.ProtocolError, "independent accepted"):
            local.update_tracking(self.root, WORKBOOK, self.path, wrong, NODE, MODULES)


if __name__ == "__main__":
    unittest.main()
