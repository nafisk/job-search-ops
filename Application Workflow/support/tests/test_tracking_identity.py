"""Offline public-command and actual XLSX regressions for accepted role aliases."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from job_search_ops import config, google_tracking, local_excel, queue, setup, sheets
from test_local_excel import MODULES, NODE, RUNTIME
from test_pipeline import NativeConnector, WORKBOOK, packet, policies
from test_role_merge import alias
from test_tracking import application

ALIAS_KEY = "alternate:req-9"
ALIAS_URL = "https://alternate.example/jobs/9"
CANONICAL_KEY = "example:req-1"
CANONICAL_URL = "https://careers.example.com/jobs/req-1"


def original_packet(workbook=WORKBOOK):
    value = packet("portal", "original")
    value["workbook_id"] = workbook
    value["jobs"][0]["aliases"] = [alias(ALIAS_KEY, ALIAS_URL)]
    return value


def status_update(key=CANONICAL_KEY):
    return {"job_key": key, "field": "Application Status", "old_value": "New",
            "new_value": "Applied", "evidence_ref": "fictional reviewed application confirmation"}


class PublicTrackingIdentityTests(unittest.TestCase):
    def setUp(self):
        from test_selection import SelectionTests
        self.h = SelectionTests("runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        fixture = self.h.h
        fixture.settings["discovery"]["portals"] = True
        cfg = self.h.load()
        setup.init_instance(cfg)
        fixture.bind("tracker", "tracker", WORKBOOK)
        self.root = fixture.root
        self.files = fixture.base
        queue.configure_policies(self.root, WORKBOOK, policies())
        self.native = NativeConnector()
        self.discovery(original_packet())

    def cli(self, *args, error=None):
        result = subprocess.run([sys.executable, "-B", "-m", "job_search_ops", *map(str, args)],
                                cwd=config.SUPPORT_ROOT, capture_output=True, text=True)
        if error is not None:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(error, result.stderr)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def write(self, name, value):
        path = self.files / (name + ".json")
        path.write_text(json.dumps(value))
        return path

    def snapshot(self):
        return self.write("native-snapshot", self.native.snapshot())

    def commit(self, journal):
        payload = self.cli("authorize-write", "--root", self.root, "--journal", journal["journal_id"],
                           "--snapshot", self.snapshot())
        self.native.apply(payload["requests"])
        return self.cli("commit", "--root", self.root, "--journal", journal["journal_id"],
                        "--snapshot", self.snapshot())

    def discovery(self, value):
        self.cli("enqueue", "--root", self.root, "--packet", self.write("packet", value))
        journal = self.cli("prepare", "--root", self.root, "--workbook", WORKBOOK,
                           "--snapshot", self.snapshot(), "--owner", "central")
        return self.commit(journal)

    def plan(self, updates=None, additions=None):
        review = self.cli("tracking-review", "--workbook", WORKBOOK, "--snapshot", self.snapshot())
        return {"workbook_id": WORKBOOK, "expected_state_sha256": review["expected_state_sha256"],
                "updates": updates or [], "new_records": additions or []}

    def prepare(self, plan, error=None):
        return self.cli("tracking-prepare", "--root", self.root, "--workbook", WORKBOOK,
                        "--snapshot", self.snapshot(), "--plan", self.write("tracking-plan", plan), error=error)

    def check_alias_is_not_new(self, key, url):
        self.native.set("Jobs", 4, "Notes", "Private manual note")
        self.native.set("Jobs", 4, "Referral Contact", "Chosen manual contact")
        before = self.native.snapshot()
        journals = sorted((self.root / "state/writer/journals").glob("*.json"))
        proposed = application(key)
        proposed["url"] = url
        self.prepare(self.plan(additions=[proposed]), error="canonical Job Key " + CANONICAL_KEY)
        self.assertEqual(self.native.snapshot(), before)
        self.assertEqual(sorted((self.root / "state/writer/journals").glob("*.json")), journals)
        tracked = self.commit(self.prepare(self.plan(updates=[status_update()])))
        self.assertEqual(tracked["new_records"], [])
        self.assertEqual(tracked["updates"][0]["job_key"], CANONICAL_KEY)
        later = packet("portal", "next-discovery", key, "later-event")
        later["jobs"][0]["url"] = url
        self.assertEqual(self.discovery(later)["new_jobs"], [])
        rows = sheets.Snapshot(self.native.snapshot(), WORKBOOK).state()["Jobs"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], CANONICAL_URL)
        self.assertEqual(rows[0]["values"]["Job Key"], CANONICAL_KEY)
        self.assertEqual(rows[0]["values"]["Application Status"], "Applied")
        self.assertEqual(rows[0]["values"]["Notes"], "Private manual note")
        self.assertEqual(rows[0]["values"]["Referral Contact"], "Chosen manual contact")
        self.assertEqual(sheets.role_state(self.root, WORKBOOK)["aliases"][key], CANONICAL_KEY)

    def test_public_google_key_alias_rejects_append_and_discovery_continues(self):
        self.check_alias_is_not_new(ALIAS_KEY, "https://careers.example.com/jobs/alternate-live")

    def test_public_google_url_alias_rejects_append_and_discovery_continues(self):
        self.check_alias_is_not_new("another:req-10", ALIAS_URL)

    def test_public_google_conflicting_key_and_url_fail_without_journal(self):
        self.discovery(packet("portal", "second-role", "example:req-2", "second-event"))
        proposed = application(ALIAS_KEY)
        proposed["url"] = "https://careers.example.com/jobs/req-2"
        journals = sorted((self.root / "state/writer/journals").glob("*.json"))
        self.prepare(self.plan(additions=[proposed]), error="Conflicting tracking identity")
        self.assertEqual(sorted((self.root / "state/writer/journals").glob("*.json")), journals)
        self.assertEqual(len(sheets.Snapshot(self.native.snapshot(), WORKBOOK).rows("Jobs")), 2)

    def test_alias_update_gives_canonical_guidance_without_overwrite(self):
        before = self.native.snapshot()
        self.prepare(self.plan(updates=[status_update(ALIAS_KEY)]), error="review canonical Job Key " + CANONICAL_KEY)
        self.assertEqual(self.native.snapshot(), before)

    def test_pre_fix_prepared_journal_cannot_authorize_alias_duplicate(self):
        proposed = application(ALIAS_KEY)
        proposed["url"] = "https://careers.example.com/jobs/alternate-live"
        plan = self.plan(additions=[proposed])
        # Model an unattempted journal produced by the old, row-only check.
        with patch.object(google_tracking, "validate_identities"):
            journal = google_tracking.prepare(self.root, WORKBOOK, self.native.snapshot(), plan)
        self.cli("authorize-write", "--root", self.root, "--journal", journal["journal_id"],
                 "--snapshot", self.snapshot(), error="canonical Job Key " + CANONICAL_KEY)
        saved = queue.read(self.root / "state/writer/journals" / (journal["journal_id"] + ".json"))
        self.assertEqual(saved["status"], "prepared")
        self.assertEqual(saved["attempts"], 0)
        self.cli("cancel-unattempted", "--root", self.root, "--journal", journal["journal_id"], "--owner", "central")
        self.assertEqual(self.discovery(packet("portal", "after-cancel", ALIAS_KEY, "after-event"))["new_jobs"], [])

    def test_conflicting_accepted_history_cannot_prepare_tracking(self):
        receipt = next((self.root / "state/writer/receipts").glob("*.json"))
        data = queue.read(receipt)
        data["role_aliases"].append(dict(alias(ALIAS_KEY), canonical_key="missing:canonical", verified_at=data["verified_at"]))
        queue.atomic(receipt, data)
        self.prepare(self.plan(additions=[application("unseen:req-5")]), error="no saved canonical role")


@unittest.skipUnless(RUNTIME, "Bundled XLSX runtime unavailable")
class LocalTrackingIdentityTests(unittest.TestCase):
    def test_actual_xlsx_key_url_conflicts_and_continued_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "tracker.xlsx"
            workbook = "local:fictional-installation"
            cfg = {"instance_root": str(root), "installation_id": "fictional-installation",
                   "tracker": {"provider": "local_xlsx", "path": str(path)}}
            intent = {"intent_id": "fictional-intent", "request_digest": "fixture-request", "request": cfg["tracker"]}
            queue.atomic(root / "installation.json", {"resources": {"tracker:tracker": intent}})
            queue.configure_policies(root, workbook, policies())
            local_excel.initialize(cfg, NODE, MODULES)
            queue.enqueue(root, original_packet(workbook))
            second = packet("portal", "second-role", "example:req-2", "second-event")
            second["workbook_id"] = workbook
            queue.enqueue(root, second)
            local_excel.merge(root, workbook, path, NODE, MODULES)
            manual = root / "manual.xlsx"
            first_row = next(row for row, values in local_excel.inspect_workbook(path, workbook).rows("Jobs") if values["Job Key"] == CANONICAL_KEY)
            local_excel._artifact(path, manual, [
                {"tab": "Jobs", "row": first_row, "column": 9, "after": sheets.native("Chosen manual contact")},
                {"tab": "Jobs", "row": first_row, "column": 13, "after": sheets.native("Private manual note")},
            ], NODE, MODULES)
            os.replace(manual, path)
            before_bytes = path.read_bytes()
            original_hash = local_excel.file_hash(path)
            for key, url, expected in (
                    (ALIAS_KEY, "https://careers.example.com/jobs/alternate-live", "canonical Job Key " + CANONICAL_KEY),
                    ("another:req-10", ALIAS_URL, "canonical Job Key " + CANONICAL_KEY),
                    (ALIAS_KEY, "https://careers.example.com/jobs/req-2", "Conflicting tracking identity")):
                with self.subTest(key=key, url=url):
                    item = application(key)
                    item["url"] = url
                    plan = {"workbook_id": workbook, "expected_file_sha256": original_hash, "updates": [], "new_records": [item]}
                    with self.assertRaisesRegex(queue.ProtocolError, expected):
                        local_excel.update_tracking(root, workbook, path, plan, NODE, MODULES)
                    self.assertEqual(path.read_bytes(), before_bytes)
                    self.assertFalse(list((root / "state/writer/local-tracking").glob("*.json")))
            plan = {"workbook_id": workbook, "expected_file_sha256": original_hash, "updates": [status_update()]}
            receipt = local_excel.update_tracking(root, workbook, path, plan, NODE, MODULES)
            self.assertEqual(receipt["new_records"], [])
            later = packet("portal", "next-discovery", ALIAS_KEY, "later-event")
            later["workbook_id"] = workbook
            later["jobs"][0]["url"] = ALIAS_URL
            queue.enqueue(root, later)
            self.assertEqual(local_excel.merge(root, workbook, path, NODE, MODULES)["new_jobs"], [])
            rows = local_excel.inspect_workbook(path, workbook).state()["Jobs"]["rows"]
            self.assertEqual(len(rows), 2)
            row = next(row for row in rows if row["values"]["Job Key"] == CANONICAL_KEY)
            self.assertEqual(row["url"], CANONICAL_URL)
            self.assertEqual(row["values"]["Application Status"], "Applied")
            self.assertEqual(row["values"]["Notes"], "Private manual note")
            self.assertEqual(row["values"]["Referral Contact"], "Chosen manual contact")
            self.assertEqual(sheets.role_state(root, workbook)["aliases"][ALIAS_KEY], CANONICAL_KEY)


if __name__ == "__main__":
    unittest.main()
