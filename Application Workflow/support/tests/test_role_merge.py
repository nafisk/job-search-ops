"""Cross-run identity and source-owned referral restrictions, on both trackers."""
import copy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from job_search_ops import local_excel, queue, sheets
from test_pipeline import NativeConnector, STAMP, WORKBOOK, packet, policies
from test_local_excel import MODULES, NODE, RUNTIME


def alias(key="alternate:req-9", url=None):
    result = {"job_key": key, "evidence_url": "https://careers.example.com/jobs/req-1", "quote": "This official requisition also uses alternate job ID req-9."}
    if url is not None:
        result["url"] = url
    return result


class RoleMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        queue.configure_policies(self.root, WORKBOOK, policies())
        self.native = NativeConnector()

    def save(self, proposal):
        queue.enqueue(self.root, proposal)
        journal = sheets.prepare(self.root, WORKBOOK, self.native.snapshot(), "central")
        request = sheets.authorize_write(self.root, journal["journal_id"], self.native.snapshot())
        self.native.apply(request["requests"])
        receipt = sheets.verify_and_commit(self.root, journal["journal_id"], self.native.snapshot())
        return journal, receipt

    def test_later_portal_hold_and_contact_survive_manual_fields_and_weaker_sightings(self):
        self.save(packet("email"))
        for field, value in {"Notes": "Keep personal note", "Referral Contact": "My chosen contact", "Application Status": "Saved"}.items():
            self.native.set("Jobs", 4, field, value)
        portal = packet("portal", "portal-new", event="portal-sighting")
        portal["jobs"][0].update(referral_hold=True, referral_contact="Private portal referrer")
        journal, receipt = self.save(portal)
        self.assertEqual(receipt["new_jobs"], [])
        row = sheets.Snapshot(self.native.snapshot(), WORKBOOK).rows("Jobs")[0][1]
        self.assertEqual(row["Notes"], "Keep personal note")
        self.assertEqual(row["Referral Contact"], "My chosen contact")
        self.assertEqual(row["Application Status"], "Saved")
        restriction = receipt["referral_restrictions"][0]
        self.assertTrue(restriction["referral_hold"])
        self.assertEqual(restriction["contacts"], ["Private portal referrer"])
        self.assertEqual(sheets.verify_and_commit(self.root, journal["journal_id"], self.native.snapshot()), receipt)
        replay = copy.deepcopy(portal)
        replay["packet_id"] = "same-source-replay"
        self.assertEqual(self.save(replay)[1]["referral_updates"], [])
        self.save(packet("email", "weaker", event="weaker-event"))
        self.assertTrue(sheets.role_state(self.root, WORKBOOK)["referral_restrictions"][0]["referral_hold"])
        brief = queue.prepare_brief(self.root, "holds-brief")
        self.assertEqual(len(brief["referral_summary"]), 1)
        self.assertIn("Referral hold:", brief["referral_summary"][0]["change"])
        self.assertNotIn("Private portal referrer", json.dumps(brief["referral_summary"]))
        public = self.root / "public.json"
        body = self.root / "report.md"
        body.write_text("Example Company Software Engineer https://careers.example.com/jobs/req-1")
        queue.atomic(public, {})
        delivery = {"channel": "chat", "thread_id": "test-thread", "snapshot_path": str(public), "chat_body_path": str(body)}
        with self.assertRaisesRegex(queue.ProtocolError, "referral_updates"):
            queue.mark_brief_sending(self.root, "holds-brief", delivery)
        queue.atomic(public, {"referral_updates": brief["referral_summary"]})
        with self.assertRaisesRegex(queue.ProtocolError, "referral restriction"):
            queue.mark_brief_sending(self.root, "holds-brief", delivery)
        body.write_text(body.read_text() + "\n" + brief["referral_summary"][0]["change"])
        self.assertEqual(queue.mark_brief_sending(self.root, "holds-brief", delivery)["status"], "sending")
        raw = {"thread": {"id": "test-thread"}, "turns": [{"status": "completed", "completedAt": int(time.time()), "items": [{"type": "agentMessage", "phase": "final_answer", "id": "hold-delivery", "text": body.read_text()}]}]}
        queue.confirm_brief_delivery(self.root, "holds-brief", {"native_chat_readback": raw, "verified_at": queue.now()})
        self.assertEqual(queue.prepare_brief(self.root, "next-brief")["referral_summary"], [])

    def test_same_batch_overlap_retains_stricter_hold_in_new_role_receipt(self):
        email = packet("email", "email-first")
        portal = packet("portal", "portal-second", event="portal-event")
        portal["jobs"][0].update(referral_hold=True, referral_contact="Private contact")
        queue.enqueue(self.root, email)
        _, receipt = self.save(portal)
        self.assertEqual(len(receipt["new_jobs"]), 1)
        self.assertTrue(receipt["new_jobs"][0]["referral_hold"])
        self.assertTrue(receipt["referral_restrictions"][0]["referral_hold"])
        self.assertEqual(len(sheets.Snapshot(self.native.snapshot(), WORKBOOK).rows("Jobs")), 1)

    def test_alias_id_and_url_persist_across_independent_runs_without_new_role(self):
        original = packet("email")
        original["jobs"][0]["aliases"] = [alias()]
        _, first = self.save(original)
        self.assertTrue(any(a["job_key"] == "alternate:req-9" for a in first["role_aliases"]))
        alternate = packet("portal", "alternate-run", "alternate:req-9", "alternate-event")
        _, second = self.save(alternate)
        self.assertEqual(second["new_jobs"], [])
        self.assertEqual(second["new_source_events"], 1)
        rows = sheets.Snapshot(self.native.snapshot(), WORKBOOK).state()["Jobs"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], original["jobs"][0]["url"])
        self.assertEqual(rows[0]["values"]["Seen Count"], 2)
        same_url = packet("portal", "same-url-run", "another:req-10", "third-event")
        same_url["jobs"][0]["url"] = alternate["jobs"][0]["url"]
        self.assertEqual(self.save(same_url)[1]["new_jobs"], [])
        self.assertEqual(sheets.role_state(self.root, WORKBOOK)["aliases"]["another:req-10"], "example:req-1")
        brief = queue.prepare_brief(self.root, "alias-report")
        self.assertEqual(sum(len(r["new_jobs"]) for r in brief["receipts"]), 1)

    def test_declared_alias_url_is_reused_without_alias_id(self):
        original = packet()
        original["jobs"][0]["aliases"] = [alias(url="https://alternate.example/jobs/9")]
        self.save(original)
        later = packet("email", "different-id", "different:id", "later-event")
        later["jobs"][0]["url"] = "https://alternate.example/jobs/9"
        self.assertEqual(self.save(later)[1]["new_jobs"], [])

    def test_uncommitted_alias_and_hold_are_not_accepted_history(self):
        self.save(packet("email"))
        proposed = packet("portal", "not-saved", event="not-saved-event")
        proposed["jobs"][0].update(aliases=[alias()], referral_hold=True)
        queue.enqueue(self.root, proposed)
        journal = sheets.prepare(self.root, WORKBOOK, self.native.snapshot(), "central")
        self.assertTrue(journal["referral_restrictions"][0]["referral_hold"])
        state = sheets.role_state(self.root, WORKBOOK)
        self.assertNotIn("alternate:req-9", state["aliases"])
        self.assertEqual(state["referral_restrictions"], [])
        sheets.cancel_unattempted(self.root, journal["journal_id"], "central")
        self.assertNotIn("alternate:req-9", sheets.role_state(self.root, WORKBOOK)["aliases"])

    def test_conflicting_or_unevidenced_aliases_are_rejected(self):
        self.save(packet())
        self.save(packet("email", "second", "example:req-2", "second-event"))
        conflict = packet("portal", "conflict", event="conflict-event")
        conflict["jobs"][0]["aliases"] = [alias("example:req-2")]
        queue.enqueue(self.root, conflict)
        with self.assertRaisesRegex(queue.ProtocolError, "Conflicting cross-source"):
            sheets.prepare(self.root, WORKBOOK, self.native.snapshot(), "central")
        unverified = packet("email", "unverified")
        unverified["jobs"][0]["aliases"] = [{"job_key": "not-evidenced:id"}]
        with self.assertRaises(queue.ProtocolError):
            queue.enqueue(self.root, unverified)

    def test_conflicting_saved_alias_mapping_is_rejected(self):
        original = packet()
        original["jobs"][0]["aliases"] = [alias()]
        self.save(original)
        journal, _ = self.save(packet("email", "second", "example:req-2", "second-event"))
        path = self.root / "state/writer/receipts" / (journal["journal_id"] + ".json")
        receipt = queue.read(path)
        receipt["role_aliases"].append(dict(alias(), canonical_key="example:req-2", verified_at=STAMP))
        queue.atomic(path, receipt)
        with self.assertRaisesRegex(queue.ProtocolError, "Conflicting accepted alias"):
            sheets.role_state(self.root, WORKBOOK)

    def test_pre_upgrade_receipt_recovers_evidence_from_accepted_packet(self):
        original = packet()
        original["jobs"][0].update(aliases=[alias()], referral_hold=True, referral_contact="Legacy private contact")
        journal, receipt = self.save(original)
        for key in ("role_aliases", "referral_restrictions", "referral_updates"):
            receipt.pop(key)
        queue.atomic(self.root / "state/writer/receipts" / (journal["journal_id"] + ".json"), receipt)
        later = packet("email", "alternate", "alternate:req-9", "next-event")
        self.assertEqual(self.save(later)[1]["new_jobs"], [])
        state = sheets.role_state(self.root, WORKBOOK)
        self.assertTrue(state["referral_restrictions"][0]["referral_hold"])
        self.assertEqual(state["referral_restrictions"][0]["contacts"], ["Legacy private contact"])


@unittest.skipUnless(RUNTIME, "Bundled XLSX runtime unavailable")
class LocalRoleMergeTests(unittest.TestCase):
    def test_actual_excel_alias_merge_keeps_manual_cells_and_records_portal_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "tracker.xlsx"
            workbook = "local:fictional-installation"
            config = {"instance_root": str(root), "installation_id": "fictional-installation", "tracker": {"provider": "local_xlsx", "path": str(path)}}
            intent = {"intent_id": "fictional-intent", "request_digest": "fixture-request", "request": config["tracker"]}
            queue.atomic(root / "installation.json", {"resources": {"tracker:tracker": intent}})
            queue.configure_policies(root, workbook, policies())
            local_excel.initialize(config, NODE, MODULES)
            initial = packet("email")
            initial["workbook_id"] = workbook
            initial["jobs"][0]["aliases"] = [alias()]
            queue.enqueue(root, initial)
            local_excel.merge(root, workbook, path, NODE, MODULES)
            manual = root / "manual.xlsx"
            edits = [{"tab": "Jobs", "row": 4, "column": col, "after": sheets.native(value)} for col, value in ((5, "Saved"), (9, "My referrer"), (13, "Personal note"))]
            local_excel._artifact(path, manual, edits, NODE, MODULES)
            os.replace(manual, path)
            later = packet("portal", "later", "alternate:req-9", "portal-event")
            later["workbook_id"] = workbook
            later["jobs"][0].update(referral_hold=True, referral_contact="Private portal referrer")
            queue.enqueue(root, later)
            receipt = local_excel.merge(root, workbook, path, NODE, MODULES)
            self.assertEqual(receipt["new_jobs"], [])
            self.assertTrue(receipt["referral_restrictions"][0]["referral_hold"])
            rows = local_excel.inspect_workbook(path, workbook).rows("Jobs")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1]["Seen Count"], 2)
            self.assertEqual(rows[0][1]["Notes"], "Personal note")
            self.assertEqual(rows[0][1]["Referral Contact"], "My referrer")
            self.assertEqual(rows[0][1]["Application Status"], "Saved")
            self.assertTrue(sheets.role_state(root, workbook)["referral_restrictions"][0]["referral_hold"])
            self.assertEqual(len(queue.prepare_brief(root, "local-brief")["referral_summary"]), 1)
