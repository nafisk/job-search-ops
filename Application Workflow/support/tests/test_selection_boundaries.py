"""Reproduce unsupported selections through the real public CLI."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from job_search_ops import config, google_tracking, setup
from test_pipeline import NativeConnector, WORKBOOK


class SelectionBoundaryTests(unittest.TestCase):
    def setUp(self):
        from test_selection import SelectionTests
        self.h = SelectionTests('runTest')
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', '-m', 'job_search_ops', *args],
                              cwd=config.SUPPORT_ROOT, text=True, capture_output=True)

    def test_reserved_state_name_fails_before_initialization(self):
        fixture = self.h.h
        root = fixture.base / 'state'
        fixture.settings['instance_root'] = str(root)
        fixture.profile['private']['state_root'] = str(root / 'state')
        fixture.save_sources()
        process = self.cli('init', '--config', str(fixture.config_path))
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('state is reserved', process.stderr)
        self.assertFalse(root.exists())

    def tracking_request(self, enabled):
        fixture = self.h.h
        fixture.settings['tracking']['gmail'] = enabled
        fixture.settings['discovery']['portals'] = True
        cfg = self.h.load()
        setup.init_instance(cfg)
        fixture.bind('tracker', 'tracker', WORKBOOK)
        snapshot = NativeConnector().snapshot()
        snap_path = fixture.base / 'native.json'
        snap_path.write_text(json.dumps(snapshot))
        plan = {'workbook_id': WORKBOOK,
                'expected_state_sha256': google_tracking.review(snapshot, WORKBOOK)['expected_state_sha256'],
                'updates': [], 'new_records': [{
                    'job_key': 'example:tracking', 'company': 'Example', 'title': 'Engineer',
                    'url': 'https://careers.example.com/role', 'status': 'Applied',
                    'observed_at': '2026-10-19T12:00:00+00:00',
                    'evidence_ref': 'fictional accepted application', 'role_evidence_ref': 'fictional verified official role'}]}
        plan_path = fixture.base / 'plan.json'
        plan_path.write_text(json.dumps(plan))
        return self.cli('tracking-prepare', '--root', str(fixture.root), '--workbook', WORKBOOK,
                        '--snapshot', str(snap_path), '--plan', str(plan_path)), fixture.root

    def test_google_tracking_disabled_selection_creates_no_write_journal(self):
        process, root = self.tracking_request(False)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('tracking is not selected', process.stderr)
        self.assertFalse(list((root / 'state/writer/journals').glob('*.json')))
        self.assertFalse(list((root / 'state/writer/receipts').glob('*.json')))

    def test_google_tracking_selected_cli_can_prepare_same_fictional_plan(self):
        process, _ = self.tracking_request(True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['status'], 'prepared')
