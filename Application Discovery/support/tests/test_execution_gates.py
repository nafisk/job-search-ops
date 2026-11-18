"""Exercise pending-pilot restrictions through queue, writer and CLI boundaries."""
import json
import subprocess
import sys
import unittest

from job_search_ops import queue, sheets, setup
from job_search_ops.config import ConfigError
import test_pipeline as fixtures
from test_pipeline import WORKBOOK, packet


class ExecutionGateTests(unittest.TestCase):
    def setUp(self):
        self.h = fixtures.PipelineTests(methodName="runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def hold(self, *workflows):
        (self.h.root / "installation.json").write_text(json.dumps({
            "preferences_update": {"update_id": "reviewed-update", "pilot_required": list(workflows)}}))

    def test_cli_enqueue_requires_explicit_current_manual_pilot(self):
        self.hold("main")
        path = self.h.root / "source.json"
        path.write_text(json.dumps(packet()))
        command = [sys.executable, "-B", "-m", "job_search_ops", "enqueue", "--root", str(self.h.root), "--packet", str(path)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("replacement pilot pending", result.stderr)
        self.assertEqual(queue.pending(self.h.root), [])
        result = subprocess.run(command + ["--pilot-update-id", "stale"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        result = subprocess.run(command + ["--pilot-update-id", "reviewed-update"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(queue.pending(self.h.root)), 1)
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            sheets.prepare(self.h.root, WORKBOOK, self.h.connector.snapshot(), "central")

    def test_held_rated_packet_cannot_claim_writer_or_resume_old_plan(self):
        queue.enqueue(self.h.root, packet(source="blind"))
        self.hold("blind")
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            sheets.prepare(self.h.root, WORKBOOK, self.h.connector.snapshot(), "central")
        self.assertFalse(list((self.h.root / "state/writer/claims").glob("*.json")))
        with setup.execution_context(pilot_update_id="reviewed-update"):
            journal = sheets.prepare(self.h.root, WORKBOOK, self.h.connector.snapshot(), "central")
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            sheets.prepare(self.h.root, WORKBOOK, self.h.connector.snapshot(), "central")
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            sheets.authorize_write(self.h.root, journal["journal_id"], self.h.connector.snapshot())
        with setup.execution_context(pilot_update_id="reviewed-update"):
            batch = sheets.authorize_write(self.h.root, journal["journal_id"], self.h.connector.snapshot())
        self.h.connector.apply(batch["requests"])
        # Recovery/readback must stay available after the explicit pilot scope ends.
        receipt = sheets.verify_and_commit(self.h.root, journal["journal_id"], self.h.connector.snapshot())
        self.assertEqual(receipt["status"], "saved")

    def test_unaffected_main_packet_remains_available_during_rated_pilot(self):
        self.hold("blind")
        journal, receipt = self.h.save(packet())
        self.assertEqual(receipt["status"], "saved")
        self.assertEqual(journal["attempts"], 0)


if __name__ == "__main__":
    unittest.main()
