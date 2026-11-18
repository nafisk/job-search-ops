"""Offline protocol regression tests; NativeConnector is not a live pilot."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from job_search_ops import google_tracking as tracking, queue, sheets
from test_pipeline import NativeConnector, WORKBOOK, STAMP, packet, policies


def application(key="example:req-1"):
    return {"job_key": key, "company": "Example Company", "title": "Software Engineer", "url": "https://careers.example.com/jobs/" + key.split(":")[-1], "status": "Applied", "observed_at": STAMP, "evidence_ref": "private application confirmation", "role_evidence_ref": "private official role readback"}


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.connector = NativeConnector()
        # A tracking-only installation has no discovery source policies.
        queue.atomic(queue.storage(self.root) / "approved-policies.json", {"schema_version": 1, "workbook_id": WORKBOOK, "timezone": "UTC", "sources": {}})

    def plan(self, updates=None, additions=None):
        return {"workbook_id": WORKBOOK, "expected_state_sha256": tracking.review(self.connector.snapshot(), WORKBOOK)["expected_state_sha256"], "updates": updates or [], "new_records": additions or []}

    def prepare(self, plan):
        return tracking.prepare(self.root, WORKBOOK, self.connector.snapshot(), plan)

    def save(self, plan):
        journal = self.prepare(plan)
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.connector.apply(payload["requests"])
        return sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())

    def update(self, old="Applied", new="Interviewing", field="Application Status"):
        return {"job_key": "example:req-1", "field": field, "old_value": old, "new_value": new, "evidence_ref": "private tracking review"}

    def test_tracking_only_application_then_update_replay_and_no_discovery_claim(self):
        plan = self.plan(additions=[application()])
        receipt = self.save(plan)
        self.assertEqual(receipt["new_records"], [application()])
        self.assertEqual(receipt["new_jobs"], [])
        self.assertEqual(receipt["operation"], "tracking")
        self.assertEqual(self.prepare(plan)["status"], "committed")
        self.assertEqual(sheets.reconcile(self.root, receipt["receipt_id"], self.connector.snapshot()), receipt)
        state = sheets.Snapshot(self.connector.snapshot(), WORKBOOK).state()
        self.assertEqual(state["Jobs"]["rows"][0]["values"]["Source"], "Tracking evidence")
        self.assertEqual(state["Job Sources"]["rows"][0]["values"]["Qualification Tier"], "not_screened")
        self.connector.set("Jobs", 4, "Notes", "Keep a private manual note")
        result = self.save(self.plan(updates=[self.update()]))
        self.assertEqual(result["tracking_changes"][0]["company"], "Example Company")
        row = sheets.Snapshot(self.connector.snapshot(), WORKBOOK).rows("Jobs")[0][1]
        self.assertEqual(row["Application Status"], "Interviewing")
        self.assertEqual(row["Notes"], "Keep a private manual note")
        self.assertEqual(row["Seen Count"], 1)

    def test_plan_rejects_stale_workbook_value_identity_and_noop(self):
        self.save(self.plan(additions=[application()]))
        plan = self.plan(updates=[self.update()])
        self.connector.set("Jobs", 4, "Notes", "Later manual edit")
        with self.assertRaisesRegex(queue.ProtocolError, "changed since tracking review"):
            self.prepare(plan)
        for item in (self.update("Saved"), self.update("Applied", "Applied"), self.update("Applied", "unknown")):
            with self.assertRaises(queue.ProtocolError):
                self.prepare(self.plan(updates=[item]))
        with self.assertRaisesRegex(queue.ProtocolError, "Duplicate tracking"):
            self.prepare(self.plan(updates=[self.update(), self.update()]))
        with self.assertRaisesRegex(queue.ProtocolError, "already exists"):
            self.prepare(self.plan(additions=[application()]))
        with self.assertRaises(queue.ProtocolError):
            tracking.prepare(self.root, "wrong-workbook", self.connector.snapshot(), self.plan(updates=[self.update()]))
        self.connector.update(self.connector.cell("Jobs", 4, "Job Link"), {"userEnteredValue": sheets.hyperlink("https://careers.example.com/jobs/wrong")})
        with self.assertRaisesRegex(queue.ProtocolError, "independent accepted"):
            self.prepare(self.plan(updates=[self.update()]))

    def test_manual_edit_before_authorization_cannot_be_overwritten(self):
        self.save(self.plan(additions=[application()]))
        journal = self.prepare(self.plan(updates=[self.update()]))
        self.connector.set("Jobs", 4, "Application Status", "Rejected")
        with self.assertRaisesRegex(queue.ProtocolError, "User edit"):
            sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        sheets.cancel_unattempted(self.root, journal["journal_id"], "central")
        changed = self.save(self.plan(updates=[self.update("Rejected", "Closed")]))
        self.assertEqual(changed["updates"][0]["old_value"], "Rejected")

    def test_uncertain_write_waits_then_reconciles_without_duplicate(self):
        journal = self.prepare(self.plan(additions=[application()]))
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())["status"], "awaiting_settlement")
        with self.assertRaises(queue.ProtocolError):
            sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        with self.assertRaisesRegex(queue.ProtocolError, "Reconcile"):
            queue.release_claim(self.root, WORKBOOK, "central")
        self.connector.apply(payload["requests"])
        receipt = sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(receipt["status"], "saved")
        self.assertEqual(sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot()), receipt)
        self.assertEqual(len(sheets.Snapshot(self.connector.snapshot(), WORKBOOK).rows("Jobs")), 1)
        self.assertEqual(len(queue.prepare_brief(self.root, "once")["receipt_ids"]), 1)

    def test_settled_failure_can_retry_but_mixed_effect_is_conflict(self):
        journal = self.prepare(self.plan(additions=[application()]))
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        settlement = {"journal_id": journal["journal_id"], "attempt_id": payload["attempt_id"], "verified_at": queue.now(), "kind": "native_terminal_failure", "response": {"error": {"code": 403}}}
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot(), settlement)["status"], "retryable")
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.connector.apply(payload["requests"])
        self.connector.set("Jobs", 4, "Notes", "Concurrent user note")
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())["status"], "conflict")
        with self.assertRaises(queue.ProtocolError):
            sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(queue.prepare_brief(self.root, "no-unverified")["receipt_ids"], [])

    def test_partial_insertion_cannot_repeat_geometry_change(self):
        self.connector = NativeConnector(rows=5)
        self.save(self.plan(additions=[application()]))
        journal = self.prepare(self.plan(additions=[application("example:req-2")]))
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.connector.apply([request for request in payload["requests"] if "insertDimension" in request])
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())["status"], "conflict")

    def test_concurrent_human_append_is_preserved_and_receipt_withheld(self):
        self.save(self.plan(additions=[application()]))
        journal = self.prepare(self.plan(additions=[application("example:req-2")]))
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        # A human enters an unrelated complete row after authorization but
        # before the connector processes the insert. Never overwrite this row.
        self.connector.set("Jobs", 5, "Company", "Human Company")
        self.connector.set("Jobs", 5, "Title", "Human Engineer")
        self.connector.set("Jobs", 5, "Job Key", "human:req-3")
        self.connector.update(self.connector.cell("Jobs", 5, "Job Link"), {"userEnteredValue": sheets.hyperlink("https://careers.example.com/jobs/human-3")})
        self.connector.set("Jobs", 5, "Notes", "Keep this human note")
        self.connector.apply(payload["requests"])
        self.assertEqual(sheets.cellvalue(self.connector.cell("Jobs", 6, "Notes")), "Keep this human note")
        with self.assertRaisesRegex(queue.ProtocolError, "Readback differs"):
            sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())["status"], "conflict")

    def test_discovery_waits_for_tracking_and_preserves_accepted_application(self):
        journal = self.prepare(self.plan(additions=[application()]))
        with self.assertRaisesRegex(queue.ProtocolError, "tracking journal"):
            sheets.prepare(self.root, WORKBOOK, self.connector.snapshot(), "central")
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.connector.apply(payload["requests"])
        sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())
        queue.configure_policies(self.root, WORKBOOK, policies())
        queue.enqueue(self.root, packet())
        discovery = sheets.prepare(self.root, WORKBOOK, self.connector.snapshot(), "central")
        payload = sheets.authorize_write(self.root, discovery["journal_id"], self.connector.snapshot())
        self.connector.apply(payload["requests"])
        receipt = sheets.verify_and_commit(self.root, discovery["journal_id"], self.connector.snapshot())
        row = sheets.Snapshot(self.connector.snapshot(), WORKBOOK).rows("Jobs")[0][1]
        self.assertEqual(row["Application Status"], "Applied")
        self.assertEqual(row["Seen Count"], 2)
        self.assertEqual(receipt["new_jobs"], [])

    def render(self, brief, body=None, tracking_updates=None):
        snapshot = self.root / "public.json"
        snapshot.write_text(json.dumps({"tracking_updates": brief["tracking_summary"] if tracking_updates is None else tracking_updates}))
        path = self.root / "body.md"
        if body is None:
            body = "\n".join(" | ".join(item.values()) for item in brief["tracking_summary"])
            body += "\n" + "\n".join(" | ".join(job[key] for key in ("company", "title", "url")) for receipt in brief["receipts"] for job in receipt.get("new_jobs", []))
        path.write_text(body)
        return {"channel": "chat", "thread_id": "central", "snapshot_path": str(snapshot), "chat_body_path": str(path)}, body

    def delivered(self, brief, intent, body):
        queue.mark_brief_sending(self.root, brief["brief_id"], intent)
        native = {"thread": {"id": "central"}, "turns": [{"status": "completed", "completedAt": int(time.time()), "items": [{"type": "agentMessage", "phase": "final_answer", "id": brief["brief_id"], "text": body}]}]}
        return queue.confirm_brief_delivery(self.root, brief["brief_id"], {"verified_at": queue.now(), "native_chat_readback": native})

    def test_mixed_report_freezes_tracking_and_late_receipt_is_next(self):
        queue.configure_policies(self.root, WORKBOOK, policies())
        queue.enqueue(self.root, packet())
        discovery = sheets.prepare(self.root, WORKBOOK, self.connector.snapshot(), "central")
        payload = sheets.authorize_write(self.root, discovery["journal_id"], self.connector.snapshot())
        self.connector.apply(payload["requests"])
        discovered = sheets.verify_and_commit(self.root, discovery["journal_id"], self.connector.snapshot())
        tracked = self.save(self.plan(updates=[self.update("New", "Applied")]))
        brief = queue.prepare_brief(self.root, "mixed")
        self.assertEqual(set(brief["receipt_ids"]), {discovered["receipt_id"], tracked["receipt_id"]})
        late = self.save(self.plan(updates=[self.update()]))
        self.assertEqual(queue.prepare_brief(self.root, "mixed"), brief)
        intent, body = self.render(brief, tracking_updates=[])
        with self.assertRaisesRegex(queue.ProtocolError, "tracking_updates"):
            queue.mark_brief_sending(self.root, "mixed", intent)
        intent, body = self.render(brief, body="Example Company Software Engineer https://careers.example.com/jobs/req-1")
        with self.assertRaisesRegex(queue.ProtocolError, "omits a saved tracking"):
            queue.mark_brief_sending(self.root, "mixed", intent)
        intent, body = self.render(brief)
        self.delivered(brief, intent, body)
        next_brief = queue.prepare_brief(self.root, "later")
        self.assertEqual(next_brief["receipt_ids"], [late["receipt_id"]])
        intent, body = self.render(next_brief)
        self.delivered(next_brief, intent, body)
        self.assertEqual(queue.prepare_brief(self.root, "empty")["receipt_ids"], [])

    def test_private_notes_and_contacts_are_not_required_in_report(self):
        self.save(self.plan(additions=[application()]))
        old = sheets.Snapshot(self.connector.snapshot(), WORKBOOK).rows("Jobs")[0][1]["Notes"]
        self.save(self.plan(updates=[self.update(old, "personal confidential detail", "Notes"), self.update("", "someone@example.com", "Referral Contact")]))
        brief = queue.prepare_brief(self.root, "private")
        public = json.dumps(brief["tracking_summary"])
        self.assertNotIn("personal confidential", public)
        self.assertNotIn("someone@example.com", public)
        self.assertNotIn("private application", public)
        intent, body = self.render(brief)
        self.delivered(brief, intent, body)

    def test_legacy_local_receipts_are_selected_once(self):
        item = application()
        receipt = {"status": "saved", "operation": "tracking", "provider": "local_xlsx", "receipt_id": "legacy-local", "workbook_id": WORKBOOK, "updates": [], "new_records": [item]}
        record = {"status": "committed", "workbook_id": WORKBOOK, "receipt": receipt}
        base = queue.storage(self.root)
        queue.atomic(base / "writer/local-tracking/legacy.json", record)
        queue.atomic(base / "writer/receipts/legacy.json", receipt)
        brief = queue.prepare_brief(self.root, "legacy")
        self.assertEqual(brief["receipt_ids"], ["legacy-local"])
        intent, body = self.render(brief)
        self.delivered(brief, intent, body)
        self.assertEqual(queue.prepare_brief(self.root, "next")["receipt_ids"], [])

    def test_wrong_root_and_applying_preferences_do_not_create_state(self):
        wrong = self.root / "state"
        with self.assertRaisesRegex(queue.ProtocolError, "installation folder"):
            queue.prepare_brief(wrong, "wrong")
        self.assertFalse((wrong / "state").exists())
        queue.atomic(wrong / "preferences-update.json", {"status": "applying"})
        with self.assertRaisesRegex(queue.ProtocolError, "preferences-apply"):
            queue.pending(self.root)
        queue.atomic(wrong / "preferences-update.json", {"status": "applied"})
        self.assertEqual(queue.pending(self.root), [])


if __name__ == "__main__":
    unittest.main()
