"""Offline regressions for per-attempt native write settlement."""
import copy
import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_search_ops import queue, sheets
from test_pipeline import NativeConnector, WORKBOOK, packet, policies


class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        queue.configure_policies(self.root, WORKBOOK, policies())
        queue.enqueue(self.root, packet())
        self.connector = NativeConnector()
        self.plan = sheets.prepare(self.root, WORKBOOK, self.connector.snapshot(), "central")
        self.journal_id = self.plan["journal_id"]
        self.journal_path = self.root / "state/writer/journals" / f"{self.journal_id}.json"

    def authorize(self):
        return sheets.authorize_write(self.root, self.journal_id, self.connector.snapshot())

    def reconcile(self, evidence=None):
        return sheets.reconcile(self.root, self.journal_id, self.connector.snapshot(), evidence)

    def evidence(self, payload, **changes):
        result = {"journal_id": self.journal_id, "attempt_id": payload["attempt_id"], "kind": "native_terminal_failure", "verified_at": queue.now(), "response": {"error": {"code": 400, "message": "Request rejected before execution"}}}
        result.update(changes)
        return result

    def test_old_failure_cannot_rearm_new_uncertain_attempt(self):
        first = self.authorize()
        failure = self.evidence(first)
        self.assertEqual(self.reconcile(failure)["status"], "retryable")
        second = self.authorize()
        self.assertNotEqual(second["attempt_id"], first["attempt_id"])
        self.assertEqual(second["attempts"], 2)
        self.assertNotIn("settlement_evidence", queue.read(self.journal_path))
        current = self.reconcile()
        self.assertEqual(current["status"], "awaiting_settlement")
        self.assertEqual(current["attempt_id"], second["attempt_id"])
        saved_journal = self.journal_path.read_bytes()
        with self.assertRaisesRegex(queue.ProtocolError, "current attempt_id"):
            self.reconcile(failure)
        self.assertEqual(self.journal_path.read_bytes(), saved_journal)
        with self.assertRaisesRegex(queue.ProtocolError, "already attempted"):
            self.authorize()
        self.assertEqual(list((self.root / "state/writer/receipts").glob("*.json")), [])
        self.assertEqual(len(queue.pending(self.root)), 1)
        # The timed-out second call can still finish. Exact readback saves once.
        self.connector.apply(second["requests"])
        receipt = self.reconcile()
        self.assertEqual(receipt["status"], "saved")
        self.assertEqual(self.reconcile(), receipt)
        self.assertEqual(len(sheets.Snapshot(self.connector.snapshot(), WORKBOOK).rows("Jobs")), 1)

    def test_current_failure_replay_preserves_one_audit_entry_and_retries(self):
        first = self.authorize()
        failure = self.evidence(first)
        self.assertEqual(self.reconcile(failure)["status"], "retryable")
        self.assertEqual(self.reconcile(failure)["status"], "retryable")
        self.assertEqual(self.reconcile()["status"], "retryable")
        self.assertEqual(queue.read(self.journal_path)["settled_attempts"], [failure])
        second = self.authorize()
        second_failure = self.evidence(second)
        self.assertEqual(self.reconcile(second_failure)["status"], "retryable")
        self.assertEqual(queue.read(self.journal_path)["settled_attempts"], [failure, second_failure])
        third = self.authorize()
        self.assertEqual(len({first["attempt_id"], second["attempt_id"], third["attempt_id"]}), 3)
        self.connector.apply(third["requests"])
        receipt = sheets.verify_and_commit(self.root, self.journal_id, self.connector.snapshot())
        self.assertEqual(self.reconcile(), receipt)

    def test_missing_foreign_or_stale_identity_and_time_are_rejected(self):
        payload = self.authorize()
        attempted = queue.timestamp(payload["attempt_recorded_at"])
        invalid = [
            {"journal_id": "another-journal"},
            {"attempt_id": "another-attempt"},
            {"attempt_id": None},
            {"verified_at": (attempted - dt.timedelta(microseconds=1)).isoformat()},
            {"verified_at": (queue.timestamp(queue.now()) + dt.timedelta(days=1)).isoformat()},
            {"verified_at": "not-a-timestamp"},
        ]
        saved = self.journal_path.read_bytes()
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(queue.ProtocolError):
                self.reconcile(self.evidence(payload, **changes))
            self.assertEqual(self.journal_path.read_bytes(), saved)
        missing = self.evidence(payload)
        del missing["attempt_id"]
        with self.assertRaisesRegex(queue.ProtocolError, "current attempt_id"):
            self.reconcile(missing)
        self.assertEqual(self.reconcile()["status"], "awaiting_settlement")

    def test_nonterminal_errors_never_allow_retry(self):
        payload = self.authorize()
        for response in ({"error": {"code": 504}}, {"isError": True}, {"error": {"code": "400"}}, {"error": {"code": 400.0}}, {"error": {"code": 429}}):
            with self.subTest(response=response), self.assertRaisesRegex(queue.ProtocolError, "do not prove"):
                self.reconcile(self.evidence(payload, response=response))
        with self.assertRaises(queue.ProtocolError):
            self.authorize()

    def test_human_confirmation_is_bound_to_current_attempt(self):
        first = self.authorize()
        evidence = self.evidence(first, kind="human_reconciled", human_turn_ref="private user turn 1", confirmation="The previous connector operation has ended; no pending call can still apply this batch.")
        evidence.pop("response")
        self.assertEqual(self.reconcile(evidence)["status"], "retryable")
        second = self.authorize()
        with self.assertRaisesRegex(queue.ProtocolError, "current attempt_id"):
            self.reconcile(evidence)
        current = copy.deepcopy(evidence)
        current.update(attempt_id=second["attempt_id"], verified_at=queue.now())
        self.assertEqual(self.reconcile(current)["status"], "retryable")

    def test_old_journal_without_attempt_id_cannot_rearm_but_success_recovers(self):
        payload = self.authorize()
        old_journal = queue.read(self.journal_path)
        old_journal.pop("attempt_id")
        queue.atomic(self.journal_path, old_journal)
        with self.assertRaisesRegex(queue.ProtocolError, "current attempt_id"):
            self.reconcile(self.evidence(payload, attempt_id=None))
        self.assertEqual(self.reconcile()["status"], "awaiting_settlement")
        self.connector.apply(payload["requests"])
        self.assertEqual(self.reconcile()["status"], "saved")

    def test_attempt_ids_differ_even_when_clock_does_not_advance(self):
        instant = queue.now()
        with patch.object(queue, "now", return_value=instant):
            first = self.authorize()
            self.reconcile(self.evidence(first))
            second = self.authorize()
        self.assertEqual(first["attempt_recorded_at"], second["attempt_recorded_at"])
        self.assertNotEqual(first["attempt_id"], second["attempt_id"])

    def test_retryable_marker_without_current_proof_is_not_authorization(self):
        self.authorize()
        journal = queue.read(self.journal_path)
        journal["status"] = "retryable"
        queue.atomic(self.journal_path, journal)
        with self.assertRaisesRegex(queue.ProtocolError, "current write attempt"):
            self.authorize()


if __name__ == "__main__":
    unittest.main()
