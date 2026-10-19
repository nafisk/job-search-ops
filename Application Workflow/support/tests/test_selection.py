"""Synthetic choice combinations and actual local-file setup readback."""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from job_search_ops import config, doctor, queue, setup


class SelectionTests(unittest.TestCase):
    def setUp(self):
        from test_setup import SetupTests
        self.h = SetupTests(methodName="runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.h.settings.update(schema_version=2, tracker={"provider": "google_sheets", "path": None},
                               discovery={"email": False, "portals": False}, tracking={"gmail": True})
        self.h.settings["modules"]["blind"] = False
        self.h.settings["blind_policy"] = None
        self.h.settings["sources"].update(gmail_queries=[], referral_companies_path=None, rated_companies_path=None)
        for schedule in self.h.settings["schedules"].values():
            schedule.update(enabled=False, local_time=None)
        self.h.profile["schema_version"] = 2

    def load(self):
        self.h.save_sources()
        self.h.config = config.load_config(self.h.config_path)
        return self.h.config

    def local(self):
        self.h.settings["tracker"] = {"provider": "local_xlsx", "path": str(self.h.root / "tracker.xlsx")}

    def bind_selected(self, cfg):
        setup.init_instance(cfg)
        if cfg["tracker"]["provider"] == "google_sheets":
            self.h.bind("tracker", "tracker", "shared-workbook")
        else:
            from test_local_excel import NODE, MODULES, RUNTIME
            from job_search_ops import local_excel
            if not RUNTIME:
                self.skipTest("Bundled artifact runtime unavailable; local setup integration is unverified")
            setup.prepare_resource(cfg, "tracker", "tracker", cfg["tracker"])
            evidence = local_excel.initialize(cfg, NODE, MODULES)
            setup.record_local_tracker(cfg, evidence)
        for name in config.execution_plan(cfg)["chats"]:
            self.h.bind("chat", name)

    def test_choice_matrix_has_no_unselected_dependencies_or_chats(self):
        original = copy.deepcopy(self.h.settings)
        for provider, email, portals, blind, tracking in itertools.product(("google_sheets", "local_xlsx"), (False, True), (False, True), (False, True), (False, True)):
            if not any((email, portals, blind, tracking)):
                continue
            with self.subTest(provider=provider, email=email, portals=portals, blind=blind, tracking=tracking):
                self.h.settings = copy.deepcopy(original)
                self.h.settings.update(tracker={"provider": provider, "path": str(self.h.root / "tracker.xlsx") if provider == "local_xlsx" else None},
                                       discovery={"email": email, "portals": portals}, tracking={"gmail": tracking})
                self.h.settings["modules"]["blind"] = blind
                if blind:
                    self.h.settings["blind_policy"] = json.loads((config.SUPPORT_ROOT / "config/legacy/installation.json").read_text())["blind_policy"]
                self.h.settings["sources"]["gmail_queries"] = ["from:alerts.example.invalid"] if email else []
                cfg = self.load()
                plan = config.execution_plan(cfg)
                caps = {x["id"] for x in doctor.required_capabilities(cfg)}
                self.assertEqual("gmail_read" in caps, email or tracking)
                self.assertEqual("google_sheets" in caps, provider == "google_sheets")
                self.assertEqual("drive_setup" in caps, provider == "google_sheets")
                self.assertEqual("local_workbook" in caps, provider == "local_xlsx")
                self.assertEqual("public_browser" in caps, email or portals or blind)
                self.assertNotIn("schedule_management", caps)
                self.assertEqual(plan["chats"], ["central"] + (["email"] if email else []) + (["portals"] if portals else []) + (["blind"] if blind else []))
                self.assertFalse(self.h.root.exists())

    def test_alerts_without_tracking_or_email_delivery_do_not_require_sent_readback(self):
        self.h.settings["discovery"]["email"] = True
        self.h.settings["tracking"]["gmail"] = False
        self.h.settings["sources"]["gmail_queries"] = ["from:alerts.example.invalid"]
        required = next(x for x in doctor.required_capabilities(self.load()) if x["id"] == "gmail_read")
        self.assertNotIn("sent_readback", required["verification_operations"])
        self.h.settings["tracking"]["gmail"] = True
        required = next(x for x in doctor.required_capabilities(self.load()) if x["id"] == "gmail_read")
        self.assertIn("sent_readback", required["verification_operations"])

    def test_local_public_only_needs_no_google_identity_and_ignores_unused_evidence(self):
        self.local()
        self.h.settings["discovery"]["portals"] = True
        self.h.settings["tracking"]["gmail"] = False
        self.h.profile["identity"].update(account_identity=None, report_recipient=None)
        cfg = self.load()
        unused = self.h.receipt("gmail_read", identity="wrong@example.invalid")
        with patch.object(doctor, "validate_receipt", side_effect=AssertionError("unselected evidence verifier called")):
            result = doctor.run_doctor(cfg, [unused], verify=self.h.verified)
        self.assertEqual(result["not_requested_observations"], ["gmail_read"])
        self.assertFalse(result["rejected_observations"])
        self.assertNotIn("gmail_read", {x["capability"] for x in result["checks"]})
        self.assertIsNone(setup.setup_plan(cfg)["report"].get("recipient"))

    def test_tracking_only_has_no_discovery_criteria_helpers_source_files_or_folders(self):
        for provider in ("google_sheets", "local_xlsx"):
            with self.subTest(provider=provider):
                self.h.settings["tracker"] = {"provider": provider, "path": str(self.h.root / "tracker.xlsx") if provider == "local_xlsx" else None}
                self.h.settings["candidate"]["actual_experience_years"] = None
                self.h.profile["role_policy"].update(families=[], preferred_levels=[])
                self.h.profile["locations"].update(onsite_regions=[], remote_countries=[], residency_region=None)
                cfg = self.load()
                self.assertEqual(config.execution_plan(cfg)["chats"], ["central"])
                self.assertEqual(setup._approved_policies(cfg)["sources"], {})
                self.assertEqual(config.execution_plan(cfg)["source_files"], [])
                self.assertEqual(config.execution_plan(cfg)["staging"], [])
        setup.init_instance(cfg)
        self.assertFalse((self.h.root / "staging").exists())
        self.assertEqual(doctor.check_staging(cfg), [])
        self.assertEqual(json.loads((self.h.root / "state/approved-policies.json").read_text())["sources"], {})
        self.assertTrue((self.h.root / "execution-plan.json").is_file())

    def test_calendar_or_messages_tracking_does_not_enable_gmail(self):
        self.local()
        self.h.settings["tracking"]["gmail"] = False
        for source in ("calendar", "messages"):
            self.h.settings["modules"].update(calendar=source == "calendar", messages=source == "messages")
            self.h.profile["integrations"][source] = {"enabled": True, "required": False, "connection_ref": "selected-source", "expected_identity": "alex@example.invalid"}
            cfg = self.load()
            caps = {x["id"] for x in doctor.required_capabilities(cfg)}
            self.assertIn(source, caps)
            self.assertNotIn("gmail_read", caps)
            self.assertNotIn("public_research", caps)
            self.assertNotIn("chat_delegation", caps)

    def test_setup_plan_cli_is_read_only_and_manual_mode_has_no_schedule_effect(self):
        cfg = self.load()
        process = subprocess.run([sys.executable, "-B", "-m", "job_search_ops", "setup-plan", "--config", str(self.h.config_path)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["effects"], [])
        self.assertEqual(result["chats"], ["central"])
        self.assertEqual(result["schedules"], {})
        self.assertNotIn("dispatch_helpers", {x["operation"] for x in result["permissions_to_review"]})
        self.assertFalse(self.h.root.exists())
        with patch.object(setup, "run_doctor", side_effect=AssertionError("manual setup probed scheduler")):
            self.assertEqual(setup.prepare_schedules(cfg), [])
        setup.init_instance(cfg)
        for kind, key in (("chat", "email"), ("chat", "portals"), ("chat", "blind"), ("schedule", "main"), ("schedule", "blind")):
            with self.subTest(kind=kind, key=key), self.assertRaises(config.ConfigError):
                setup.prepare_resource(cfg, kind, key, {"title": "unselected"})
        self.assertFalse(setup.load_instance(cfg)["resources"])

    def test_local_binding_requires_real_file_hash_and_generates_only_selected_prompts(self):
        self.local()
        cfg = self.load()
        self.bind_selected(cfg)
        binding = setup.load_instance(cfg)["resources"]["tracker:tracker"]
        self.assertEqual(binding["provider"], "local_xlsx")
        self.assertEqual(binding["resource_id"], "local:" + cfg["installation_id"])
        runtime = setup.runtime_profile(cfg)
        self.assertFalse(runtime["integrations"]["sheets"]["enabled"])
        self.assertEqual(runtime["trackers"]["jobs"]["workbook_id"], binding["resource_id"])
        prompts = setup.prepare_prompts(cfg)
        self.assertEqual(set(prompts), {"main"})
        body = Path(prompts["main"]).read_text()
        self.assertIn(str(self.h.root / "tracker.xlsx"), body)
        self.assertNotIn("shared Google workbook", body)
        self.assertNotIn("Email producer:", body)
        report = doctor.run_doctor(cfg)
        self.assertTrue(next(x for x in report["checks"] if x["capability"] == "local_workbook")["ready"])
        forged = {"provider": "local_xlsx", "installation_id": cfg["installation_id"], "resource_id": binding["resource_id"],
                  "intent_id": binding["intent_id"], "request_digest": binding["request_digest"], "path": cfg["tracker"]["path"], "file_sha256": "0" * 64}
        with self.assertRaises(ValueError):
            setup.record_local_tracker(cfg, forged)
        receipt = self.h.receipt("first_live_pass", identity="alex@example.invalid", resource="local-pilot", evidence={
            "workflow": "main", "status": "complete", "unsynced_count": 0, "accepted_manifest_sha256": "a" * 64,
            "workbook_id": binding["resource_id"], "delivery": "chat_verified", "tracker_file_sha256": "0" * 64})
        with self.assertRaisesRegex(config.ConfigError, "bytes differ"):
            setup.record_first_pass(cfg, "main", receipt, self.h.verified, now=receipt.checked_at)
        receipt.evidence["tracker_file_sha256"] = binding["file_sha256"]
        self.h.trust(receipt)
        self.assertEqual(setup.record_first_pass(cfg, "main", receipt, self.h.verified, now=receipt.checked_at)["run_id"], "local-pilot")

    def test_tracking_only_rejects_every_discovery_packet(self):
        from test_pipeline import packet
        cfg = self.load()
        self.bind_selected(cfg)
        for source in ("email", "portal", "blind"):
            proposal = packet(source)
            proposal["workbook_id"] = "shared-workbook"
            with self.subTest(source=source), self.assertRaises(queue.ProtocolError):
                queue.enqueue(self.h.root, proposal)
        self.assertEqual(queue.pending(self.h.root), [])

    def test_selected_accounts_recipients_and_schedule_times_cannot_be_missing(self):
        self.h.profile["identity"].update(account_identity=None, report_recipient=None)
        with self.assertRaisesRegex(config.ConfigError, "account_identity"):
            self.load()
        self.h.profile["identity"]["account_identity"] = "alex@example.invalid"
        self.h.settings["report"].update(delivery="email", send_opt_in=True)
        with self.assertRaisesRegex(config.ConfigError, "report_recipient"):
            self.load()
        self.h.settings["report"].update(delivery="chat", send_opt_in=False)
        self.h.settings["schedules"]["main"]["enabled"] = True
        with self.assertRaisesRegex(config.ConfigError, "local_time"):
            self.load()

    def test_local_tracker_cannot_escape_private_instance_or_use_managed_state(self):
        for target in (self.h.base / "tracker.xlsx", self.h.root / "state/tracker.xlsx", config.REPO_ROOT / "LinkedIn/tracker.xlsx"):
            self.h.settings["tracker"] = {"provider": "local_xlsx", "path": str(target)}
            with self.subTest(path=target), self.assertRaises(config.ConfigError):
                self.load()

    def test_google_provider_rejects_local_command_before_any_export(self):
        cfg = self.load()
        from job_search_ops.__main__ import parser, run
        args = parser().parse_args(["local-init", "--config", str(self.h.config_path), "--node", "/unused/node", "--node-modules", "/unused/modules"])
        with self.assertRaisesRegex(config.ConfigError, "not selected"):
            run(args)
        self.assertFalse(self.h.root.exists())

    def test_legacy_config_keeps_its_serialized_shape_and_blind_only_has_writer_prompt(self):
        self.h.settings = json.loads((config.SUPPORT_ROOT / "config/legacy/installation.json").read_text())
        self.h.settings.update(instance_root=str(self.h.root), profile_path="profile.json")
        self.h.settings["modules"]["main"] = False
        self.h.settings["schedules"]["main"]["enabled"] = False
        cfg = self.load()
        self.assertNotIn("tracker", config.public_settings(cfg))
        self.assertNotIn("discovery", config.public_settings(cfg))
        setup.init_instance(cfg)
        self.h.bind("tracker", "tracker", "shared-workbook")
        self.h.bind("chat", "central")
        self.h.bind("chat", "blind")
        self.assertEqual(set(setup.prepare_prompts(cfg)), {"main", "blind"})
        self.assertEqual(setup.init_instance(config.load_config(self.h.root / "config.json")), setup.load_instance(cfg))


if __name__ == "__main__":
    unittest.main()
