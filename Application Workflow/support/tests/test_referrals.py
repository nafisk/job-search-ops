"""Private referral input -> actual watchlist -> validated portal-registry bridge."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from job_search_ops import config, doctor, local_excel, queue, referrals, setup
from test_pipeline import NativeConnector, WORKBOOK
import test_setup
from test_setup import NOW
from test_local_excel import NODE, MODULES, RUNTIME


class ReferralTests(unittest.TestCase):
    def setUp(self):
        self.h = test_setup.SetupTests(methodName="runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.source = json.loads((config.SUPPORT_ROOT / "config/examples/referral-companies.json").read_text())
        self.source["companies"][0].update(referral_contact="Fictional contact", referral_hold=True)
        self.source_path = Path(self.h.settings["sources"]["referral_companies_path"])
        self.source_path.write_text(json.dumps(self.source))
        self.cfg = self.h.config
        setup.init_instance(self.cfg)
        self.h.bind("tracker", "tracker", WORKBOOK)
        self.native = NativeConnector()

    def prepare(self):
        return referrals.prepare(self.cfg, self.native.snapshot())

    def write_and_commit(self):
        plan = self.prepare()
        referrals.authorize(self.cfg, self.native.snapshot())
        self.native.apply(plan["requests"])
        return referrals.commit(self.cfg, self.native.snapshot())

    def test_fresh_install_maps_private_file_to_watchlist_and_unverified_registry(self):
        journal = self.write_and_commit()
        self.assertEqual(journal["status"], "committed")
        values = self.native.cell("Referral Watchlist", 4, "Targeting Notes")["userEnteredValue"]["stringValue"]
        self.assertTrue(values.startswith("Referral hold: yes"))
        registry = json.loads((self.h.root / "portal-registry.json").read_text())
        company = registry["companies"][0]
        self.assertEqual(company["watchlist_rows"], [5])
        self.assertEqual(company["company_id"], self.source["companies"][0]["company_id"])
        self.assertTrue(company["referral_hold"])
        self.assertEqual(company["official_urls"], [])
        self.assertEqual(company["searches"][0]["observed_urls"], [])
        sys.path.insert(0, str(config.SUPPORT_ROOT / "toolkit"))
        try:
            from portals import validate_registry
            self.assertEqual(validate_registry(registry), registry)
        finally:
            sys.path.pop(0)
        self.assertEqual(self.prepare(), journal)
        self.assertEqual(referrals.commit(self.cfg, self.native.snapshot()), journal)
        self.assertEqual(len(referrals.watchlist(self.native.snapshot(), WORKBOOK)["rows"]), 1)

    def test_first_portal_pilot_requires_completed_seed(self):
        with self.assertRaisesRegex(ValueError, "complete and verify"):
            referrals.require_seed(self.cfg)
        self.prepare()
        with self.assertRaisesRegex(ValueError, "committed seed"):
            referrals.require_seed(self.cfg)
        self.write_and_commit()
        self.assertEqual(referrals.require_seed(self.cfg)["company_count"], 1)
        registry_path = self.h.root / "portal-registry.json"
        registry = json.loads(registry_path.read_text())
        registry["companies"][0]["referral_hold"] = False
        registry_path.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, "hold changed"):
            referrals.require_seed(self.cfg)

    def test_new_v2_pilot_gate_uses_the_completed_native_seed(self):
        from test_selection import SelectionTests
        h = SelectionTests(methodName="runTest")
        h.setUp()
        self.addCleanup(h.doCleanups)
        h.h.settings["discovery"]["portals"] = True
        h.h.settings["sources"]["referral_companies_path"] = str(self.source_path)
        cfg = h.load()
        h.bind_selected(cfg)
        with self.assertRaisesRegex(ValueError, "complete and verify"):
            h.h.first_pass("main")
        native = NativeConnector()
        native.raw["spreadsheetId"] = "shared-workbook"
        seed = referrals.prepare(cfg, native.snapshot())
        referrals.authorize(cfg, native.snapshot())
        native.apply(seed["requests"])
        referrals.commit(cfg, native.snapshot())
        self.assertEqual(h.h.first_pass("main")["run_id"], "run-main")

    def test_duplicate_company_and_alias_inputs_are_rejected(self):
        for field in ("company_id", "company"):
            source = copy.deepcopy(self.source)
            second = copy.deepcopy(source["companies"][0])
            second.update(company_id="different", company="Different company")
            second[field] = source["companies"][0][field]
            source["companies"].append(second)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "duplicate"):
                referrals.validate_source(source)

    def test_manual_contacts_holds_and_unlisted_companies_are_never_overwritten(self):
        self.native.set("Referral Watchlist", 4, "Company", self.source["companies"][0]["company"])
        self.native.set("Referral Watchlist", 4, "Referral Contact", "Someone manually entered")
        original = self.native.snapshot()
        with self.assertRaisesRegex(ValueError, "conflict"):
            self.prepare()
        self.assertEqual(self.native.snapshot(), original)
        self.assertFalse((self.h.root / "portal-registry.json").exists())
        self.native.set("Referral Watchlist", 4, "Company", "Another chosen company")
        with self.assertRaisesRegex(ValueError, "absent"):
            self.prepare()

    def test_google_write_requires_fresh_snapshot_and_exact_readback(self):
        journal = self.prepare()
        self.native.set("Referral Watchlist", 4, "Company", "Concurrent manual edit")
        with self.assertRaisesRegex(ValueError, "stale"):
            referrals.authorize(self.cfg, self.native.snapshot())
        self.native.set("Referral Watchlist", 4, "Company", "")
        referrals.authorize(self.cfg, self.native.snapshot())
        with self.assertRaisesRegex(ValueError, "already attempted"):
            referrals.authorize(self.cfg, self.native.snapshot())
        with self.assertRaisesRegex(ValueError, "readback differs"):
            referrals.commit(self.cfg, self.native.snapshot())
        self.assertFalse((self.h.root / "portal-registry.json").exists())
        self.native.apply(journal["requests"])
        self.assertEqual(referrals.commit(self.cfg, self.native.snapshot())["status"], "committed")

    def test_concurrent_manual_append_survives_native_seed(self):
        journal = self.prepare()
        referrals.authorize(self.cfg, self.native.snapshot())
        self.native.set("Referral Watchlist", 4, "Company", "Concurrent manual company")
        self.native.set("Referral Watchlist", 4, "Referral Contact", "Keep this person")
        self.native.apply(journal["requests"])
        self.assertEqual(self.native.cell("Referral Watchlist", 5, "Referral Contact")["userEnteredValue"]["stringValue"], "Keep this person")
        with self.assertRaisesRegex(ValueError, "readback differs"):
            referrals.commit(self.cfg, self.native.snapshot())

    def test_only_unattempted_seed_can_be_cancelled_and_source_replanned(self):
        self.prepare()
        self.source["companies"][0]["targeting_notes"] = "Corrected private input"
        self.source_path.write_text(json.dumps(self.source))
        cancelled = referrals.cancel_unattempted(self.cfg)
        self.assertTrue(Path(cancelled["archive"]).is_file())
        self.assertEqual(self.prepare()["status"], "prepared")
        referrals.authorize(self.cfg, self.native.snapshot())
        with self.assertRaisesRegex(ValueError, "unattempted"):
            referrals.cancel_unattempted(self.cfg)

    def test_replay_never_clears_manual_edits_or_changed_source_holds(self):
        self.write_and_commit()
        self.native.set("Referral Watchlist", 4, "Referral Contact", "Edited contact")
        with self.assertRaisesRegex(ValueError, "manual watchlist edit"):
            self.prepare()
        self.source["companies"][0]["referral_hold"] = False
        self.source_path.write_text(json.dumps(self.source))
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.prepare()

    def test_committed_replay_recovers_crash_before_claim_release(self):
        journal = self.prepare()
        referrals.authorize(self.cfg, self.native.snapshot())
        self.native.apply(journal["requests"])
        claim = queue.claim_path(self.h.root / "state", WORKBOOK)
        original_unlink = Path.unlink
        def fail_claim_unlink(path, *args, **kwargs):
            if path == claim:
                raise OSError("simulated interruption after commit")
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", fail_claim_unlink), self.assertRaisesRegex(OSError, "simulated interruption"):
            referrals.commit(self.cfg, self.native.snapshot())
        self.assertTrue(claim.exists())
        self.assertEqual(self.prepare()["status"], "committed")
        self.assertFalse(claim.exists())
        with queue.locked(self.h.root) as base:
            queue.acquire_claim(base, WORKBOOK, referrals.OWNER)
        referrals.commit(self.cfg, self.native.snapshot())
        self.assertFalse(claim.exists())
        with queue.locked(self.h.root) as base:
            queue.acquire_claim(base, WORKBOOK, "central")
        self.prepare()
        referrals.commit(self.cfg, self.native.snapshot())
        self.assertEqual(queue.read(claim)["owner"], "central")

    def test_terminal_failed_google_attempt_can_retry_but_timeout_cannot(self):
        self.prepare()
        pending = referrals.authorize(self.cfg, self.native.snapshot())
        settlement = {"kind": "native_terminal_failure", "attempt_id": pending["attempt_id"], "verified_at": queue.now(), "response": {"error": {"code": 504, "message": "fictional timeout"}}}
        with self.assertRaisesRegex(ValueError, "do not prove"):
            referrals.retry_google(self.cfg, self.native.snapshot(), settlement)
        settlement["response"] = {"error": {"code": 400, "message": "fictional rejected request"}}
        self.native.set("Referral Watchlist", 4, "Company", "Concurrent company")
        with self.assertRaisesRegex(ValueError, "before-state"):
            referrals.retry_google(self.cfg, self.native.snapshot(), settlement)
        self.native.set("Referral Watchlist", 4, "Company", "")
        rearmed = referrals.retry_google(self.cfg, self.native.snapshot(), settlement)
        self.assertEqual(rearmed["status"], "prepared")
        self.assertEqual(rearmed["settled_attempts"], [settlement])
        new_attempt = referrals.authorize(self.cfg, self.native.snapshot())
        self.assertNotEqual(new_attempt["attempt_id"], pending["attempt_id"])
        with self.assertRaisesRegex(ValueError, "exact pending attempt_id"):
            referrals.retry_google(self.cfg, self.native.snapshot(), settlement)
        self.native.apply(new_attempt["requests"])
        self.assertEqual(referrals.commit(self.cfg, self.native.snapshot())["status"], "committed")

    def test_registry_history_conflict_preserves_readback_and_pending_journal(self):
        journal = self.prepare()
        referrals.authorize(self.cfg, self.native.snapshot())
        self.native.apply(journal["requests"])
        target = self.h.root / "portal-registry.json"
        target.write_text('{"historical":"keep me"}')
        with self.assertRaisesRegex(ValueError, "existing registry differs"):
            referrals.commit(self.cfg, self.native.snapshot())
        self.assertEqual(json.loads(target.read_text()), {"historical": "keep me"})
        self.assertEqual(self.prepare()["status"], "write_pending")

    @unittest.skipUnless(RUNTIME, "Bundled artifact runtime unavailable")
    def test_local_excel_seed_and_replay_read_actual_saved_file(self):
        from test_selection import SelectionTests
        h = SelectionTests(methodName="runTest")
        h.setUp()
        self.addCleanup(h.doCleanups)
        h.local()
        h.h.settings["discovery"]["portals"] = True
        h.h.settings["sources"]["referral_companies_path"] = str(self.source_path)
        cfg = h.load()
        h.bind_selected(cfg)
        result = referrals.local_seed(cfg, NODE, MODULES)
        self.assertEqual(result["status"], "committed")
        actual = local_excel.inspect_workbook(cfg["tracker"]["path"], "local:" + cfg["installation_id"])
        self.assertEqual(referrals.watchlist(actual, actual.raw["workbook_id"])["rows"], result["after_rows"])
        before = actual.raw["file_sha256"]
        self.assertEqual(referrals.local_seed(cfg, NODE, MODULES), result)
        self.assertEqual(local_excel.file_hash(cfg["tracker"]["path"]), before)
        self.assertTrue(Path(result["backup"]).is_file())


class DoctorBindingRegression(unittest.TestCase):
    @unittest.skipUnless(RUNTIME, "Bundled artifact runtime unavailable")
    def test_private_message_identity_does_not_replace_local_tracker_binding(self):
        from test_selection import SelectionTests
        h = SelectionTests(methodName="runTest")
        h.setUp()
        self.addCleanup(h.doCleanups)
        h.local()
        source = h.h.base / "conversation.json"
        source.write_text('{"identity":"fictional-thread"}')
        h.h.profile["private"]["refs"]["message_source"] = str(source)
        h.h.profile["integrations"]["messages"] = {"enabled": True, "required": True, "connection_ref": "local-read-only", "expected_identity": "private:message_source"}
        h.h.settings["modules"]["messages"] = True
        cfg = h.load()
        h.bind_selected(cfg)
        cap = next(c for c in doctor.required_capabilities(cfg) if c["id"] == "messages")
        receipt = h.h.receipt("messages", identity="fictional-thread", evidence={"operations": cap["verification_operations"], "identity_binding": {"reference": "message_source", "path": str(source), "identity": "fictional-thread"}})
        report = doctor.run_doctor(cfg, [receipt], h.h.verified, now=NOW)
        self.assertFalse(report["rejected_observations"])
        checks = {check["capability"]: check for check in report["checks"]}
        self.assertTrue(checks["messages"]["ready"])
        self.assertTrue(checks["local_workbook"]["ready"])
