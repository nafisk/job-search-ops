"""Offline setup boundaries using independently bound fictional host receipts."""
from dataclasses import asdict, replace
from pathlib import Path
import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from job_search_ops.config import ConfigError, REPO_ROOT, SUPPORT_ROOT, WORKFLOW_ROOT, load_config
from job_search_ops.doctor import HostReceipt, required_capabilities, run_doctor
from job_search_ops import setup


NOW = "2026-10-18T12:00:00+00:00"


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="job-ops-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "private-instance"
        self.profile = json.loads((SUPPORT_ROOT / "config/legacy/profile.json").read_text())
        self.profile["private"] = {"state_root": str(self.root / "state"), "refs": {}}
        self.settings = json.loads((SUPPORT_ROOT / "config/legacy/installation.json").read_text())
        self.settings["instance_root"] = str(self.root)
        self.settings["profile_path"] = "profile.json"
        for name in ("referral_companies_path", "rated_companies_path"):
            path = self.base / (name + ".json")
            path.write_text('{"companies": []}\n')
            self.settings["sources"][name] = str(path)
        self.config_path = self.base / "installation.json"
        self.profile_path = self.base / "profile.json"
        self.native_receipts = {}
        self.save_sources()
        self.config = load_config(self.config_path)

    def save_sources(self):
        self.config_path.write_text(json.dumps(self.settings))
        self.profile_path.write_text(json.dumps(self.profile))

    def verified(self, receipt):
        # A test host records exact independently accepted evidence, not a bool flag.
        return self.native_receipts.get(receipt.observation_id) == setup.digest(asdict(receipt))

    def trust(self, receipt):
        self.native_receipts[receipt.observation_id] = setup.digest(asdict(receipt))
        return receipt

    def receipt(self, cap, *, stage="operation_verified", resource="native-resource", identity=None, evidence=None):
        index = len(self.native_receipts)
        return self.trust(HostReceipt(cap, stage, f"native-{index}", NOW,
                                     identity, resource, "native-tool-readback",
                                     {"installation_id": self.config["installation_id"], **(evidence or {})}))

    def bind(self, kind, key, actual=None):
        intent = setup.prepare_resource(self.config, kind, key, {"title": key})
        evidence = {"intent_id": intent["intent_id"], "request_digest": intent["request_digest"]}
        if kind == "chat":
            evidence.update(workspace_path=str(self.root / "staging"), staging_write_readback=True)
        receipt = self.receipt(f"resource.{kind}", resource=actual or f"native-{kind}-{key}",
                               identity="alex@example.invalid" if kind == "tracker" else None,
                               evidence=evidence)
        return setup.record_resource(self.config, kind, key, receipt, self.verified, now=NOW)

    def bind_all(self):
        setup.init_instance(self.config)
        self.bind("tracker", "tracker", "shared-workbook")
        for name in ("central", "email", "portals", "blind"):
            self.bind("chat", name)

    def observations(self):
        rows = []
        for requirement in required_capabilities(self.config):
            if requirement["id"] in ("python", "curl"):
                continue
            identity = "alex@example.invalid" if requirement["id"] in ("gmail_read", "google_sheets", "drive_setup", "gmail_send", "calendar", "authenticated_browser") else None
            rows.append(self.receipt(requirement["id"], stage=requirement["required_stage"], identity=identity,
                                     resource="shared-workbook" if requirement["id"] == "google_sheets" else "native-resource",
                                     evidence={"operations": requirement["verification_operations"]}))
        return rows

    def first_pass(self, name):
        receipt = self.receipt("first_live_pass", resource=f"run-{name}", identity="alex@example.invalid",
                              evidence={"workflow": name, "status": "complete_with_exceptions", "unsynced_count": 0,
                                        "accepted_manifest_sha256": "a" * 64, "workbook_id": "shared-workbook",
                                        "delivery": "chat_verified"})
        return setup.record_first_pass(self.config, name, receipt, self.verified, now=NOW)

    def test_load_has_no_effect_and_preserves_true_experience_distinct_from_policy(self):
        self.assertFalse(self.root.exists())
        self.assertEqual(self.config["candidate"]["actual_experience_years"], 2)
        self.assertEqual(self.config["blind_policy"]["stretch_required_years"], 3)
        self.assertEqual(self.config["_profile"]["role_policy"]["experience"]["max_required_years"], 2)
        self.assertEqual(self.config["profile_path"], str(self.root / "profile.json"))

    def test_unknown_credentials_and_duplicate_keys_fail_without_echoing_secret(self):
        self.settings["access_token"] = "PRIVATE-MARKER"
        self.save_sources()
        with self.assertRaises(ConfigError) as caught:
            load_config(self.config_path)
        self.assertNotIn("PRIVATE-MARKER", str(caught.exception))
        self.config_path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ConfigError, "duplicate"):
            load_config(self.config_path)

    def test_email_requires_explicit_send_choice(self):
        self.settings["report"]["delivery"] = "email"
        self.save_sources()
        with self.assertRaisesRegex(ConfigError, "opt-in"):
            load_config(self.config_path)

    def test_required_messages_cannot_be_disabled_by_installation(self):
        self.profile["integrations"]["messages"] = {"enabled": True, "required": True,
                                                     "connection_ref": "private-local", "expected_identity": "my-private-binding"}
        self.save_sources()
        with self.assertRaisesRegex(ConfigError, "required source"):
            load_config(self.config_path)

    def test_path_traversal_repository_roots_and_symlink_parents_rejected(self):
        variants = [str(self.base / "../escaped"), str(REPO_ROOT / "private"), str(REPO_ROOT.parent),
                    str(REPO_ROOT / "LinkedIn" / "private"), str(WORKFLOW_ROOT / "docs" / "private")]
        self.base.joinpath("redirect").symlink_to(self.base, target_is_directory=True)
        variants.append(str(self.base / "redirect" / "private"))
        for root in variants:
            self.settings["instance_root"] = root
            self.save_sources()
            with self.subTest(root=root), self.assertRaises(ConfigError):
                load_config(self.config_path)

    def test_private_inputs_cannot_live_in_sibling_repository_directories(self):
        for target in (REPO_ROOT / "LinkedIn" / "private.json", WORKFLOW_ROOT / "docs" / "private.json"):
            for kind in ("resume", "source", "profile_ref"):
                with self.subTest(target=target, kind=kind):
                    settings, profile = copy.deepcopy(self.settings), copy.deepcopy(self.profile)
                    if kind == "resume":
                        settings["candidate"]["resume_path"] = str(target)
                    elif kind == "source":
                        settings["sources"]["rated_companies_path"] = str(target)
                    else:
                        profile["private"]["refs"]["private_input"] = str(target)
                    self.config_path.write_text(json.dumps(settings))
                    self.profile_path.write_text(json.dumps(profile))
                    with self.assertRaisesRegex(ConfigError, "outside repository"):
                        load_config(self.config_path)

    def test_main_does_not_require_authenticated_browser_but_manual_outreach_does(self):
        self.profile["integrations"]["browser"] = {"enabled": False, "required": False,
                                                     "connection_ref": None, "expected_identity": None}
        self.save_sources()
        config = load_config(self.config_path)
        self.assertTrue(config["modules"]["main"])
        self.assertNotIn("authenticated_browser", {x["id"] for x in required_capabilities(config)})
        self.settings["modules"]["manual_outreach"] = True
        self.save_sources()
        with self.assertRaisesRegex(ConfigError, "required workflow connection"):
            load_config(self.config_path)

    def test_init_is_idempotent_preserves_unknown_state_and_supports_durable_config(self):
        first = setup.init_instance(self.config)
        user_file = self.root / "state" / "user-history.json"
        user_file.write_text('{"preserve":"forever"}')
        second = setup.init_instance(self.config)
        self.assertEqual(first, second)
        self.assertEqual(user_file.read_text(), '{"preserve":"forever"}')
        durable = load_config(self.root / "config.json")
        self.assertEqual(setup.init_instance(durable), first)
        self.assertEqual((self.root / "profile.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

    def test_policy_setup_preserves_ids_tiers_and_binds_only_after_tracker_readback(self):
        setup.init_instance(self.config)
        path = self.root / "state" / "approved-policies.json"
        initial = json.loads(path.read_text())
        self.assertIsNone(initial["workbook_id"])
        self.assertEqual(initial["sources"]["email"]["id"], "core")
        self.assertEqual(initial["sources"]["blind"]["id"], "rated-companies")
        self.assertEqual(initial["sources"]["blind"]["max_required_years"], 3)
        self.assertEqual(initial["sources"]["blind"]["base_required_years"], 2)
        self.assertEqual(initial["sources"]["blind"]["min_rating"], 3.5)
        self.bind("tracker", "tracker", "shared-workbook")
        self.assertEqual(json.loads(path.read_text())["workbook_id"], "shared-workbook")
        runtime = setup.runtime_profile(self.config)
        self.assertEqual(runtime["trackers"]["jobs"]["workbook_id"], "shared-workbook")
        self.assertEqual(runtime["trackers"]["jobs"]["columns"]["status"], {"index": 6, "header": "Application Status"})
        self.assertEqual(json.loads((self.root / "profile.json").read_text())["trackers"], {})
        self.assertEqual(json.loads((self.root / "runtime-profile.json").read_text()), runtime)

    def test_disabled_source_has_no_approved_runtime_policy(self):
        self.settings["modules"]["blind"] = False
        self.settings["schedules"]["blind"]["enabled"] = False
        self.save_sources()
        self.config = load_config(self.config_path)
        setup.init_instance(self.config)
        policy = json.loads((self.root / "state/approved-policies.json").read_text())
        self.assertEqual(set(policy["sources"]), {"email", "portal"})

    def test_changed_profile_does_not_reset_existing_installation(self):
        setup.init_instance(self.config)
        before = (self.root / "installation.json").read_bytes()
        self.profile["role_policy"]["experience"]["max_required_years"] = 4
        self.save_sources()
        changed = load_config(self.config_path)
        with self.assertRaisesRegex(ConfigError, "configuration changed"):
            setup.init_instance(changed)
        self.assertEqual((self.root / "installation.json").read_bytes(), before)

    def test_setup_lock_is_not_stolen(self):
        setup.init_instance(self.config)
        lock = self.root / ".setup.lock"
        lock.write_text("interrupted-owner")
        with self.assertRaisesRegex(ConfigError, "interrupted lock"):
            setup.init_instance(self.config)
        self.assertEqual(lock.read_text(), "interrupted-owner")

    def test_permissions_and_symlink_state_do_not_get_silently_repaired(self):
        setup.init_instance(self.config)
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ConfigError, "owner-only"):
            setup.load_instance(self.config)
        self.root.chmod(0o700)
        original = self.root / "installation.json"
        outside = self.base / "outside.json"
        original.rename(outside)
        original.symlink_to(outside)
        with self.assertRaisesRegex(ConfigError, "symlink"):
            setup.load_instance(self.config)

    def test_uncertain_resource_resumes_same_intent_without_another_create(self):
        setup.init_instance(self.config)
        first = setup.prepare_resource(self.config, "tracker", "tracker", {"title": "Mine"})
        self.assertEqual(first["action"], "perform_once")
        setup.mark_resource_uncertain(self.config, "tracker", "tracker")
        resumed = setup.prepare_resource(self.config, "tracker", "tracker", {"title": "Mine"})
        self.assertEqual(resumed["action"], "reconcile_existing_intent")
        self.assertEqual(first["intent_id"], resumed["intent_id"])
        with self.assertRaisesRegex(ConfigError, "intent changed"):
            setup.prepare_resource(self.config, "tracker", "tracker", {"title": "Replacement"})

    def test_resource_requires_independent_bound_native_evidence_and_identity(self):
        setup.init_instance(self.config)
        intent = setup.prepare_resource(self.config, "tracker", "tracker", {"title": "Mine"})
        raw_claim = {"verified": True, "resource_id": "pretend"}
        with self.assertRaises(ConfigError):
            setup.record_resource(self.config, "tracker", "tracker", raw_claim, self.verified, now=NOW)
        receipt = self.receipt("resource.tracker", identity="wrong@example.invalid", evidence={
            "intent_id": intent["intent_id"], "request_digest": intent["request_digest"]})
        with self.assertRaisesRegex(ConfigError, "wrong account"):
            setup.record_resource(self.config, "tracker", "tracker", receipt, self.verified, now=NOW)
        corrected = self.trust(replace(receipt, identity="alex@example.invalid"))
        with self.assertRaisesRegex(ConfigError, "verifier"):
            setup.record_resource(self.config, "tracker", "tracker", corrected, None, now=NOW)
        mismatched = self.trust(replace(corrected, evidence={**corrected.evidence, "intent_id": "another"}))
        with self.assertRaisesRegex(ConfigError, "bound"):
            setup.record_resource(self.config, "tracker", "tracker", mismatched, self.verified, now=NOW)

    def test_resource_replay_reuses_actual_binding_and_rejects_replacement(self):
        setup.init_instance(self.config)
        self.bind("tracker", "tracker", "first")
        self.assertEqual(setup.prepare_resource(self.config, "tracker", "tracker", {"title": "tracker"})["action"], "reuse_verified")
        with self.assertRaisesRegex(ConfigError, "replace"):
            self.bind("tracker", "tracker", "second")

    def test_doctor_catalog_and_local_tools_do_not_prove_live_readiness(self):
        result = run_doctor(self.config, now=NOW)
        self.assertFalse(result["ready"])
        by_cap = {x["capability"]: x for x in result["checks"]}
        self.assertEqual(by_cap["google_sheets"]["state"], "missing")
        self.assertNotIn("messages", by_cap)
        self.assertNotIn("beautifulsoup4", by_cap)
        self.assertNotIn("node", by_cap)
        self.assertNotIn("curl", by_cap)
        self.assertNotIn("collaboration", by_cap)
        self.assertNotIn("authenticated_browser", by_cap)
        self.assertNotIn("messages_decoder", result["local_probes"])
        self.assertNotIn("mac-messages-mcp", result["local_probes"])
        self.assertNotIn("mcp", result["local_probes"])

    def test_unavailable_optional_messages_reports_partial_without_blocking_core(self):
        self.profile["integrations"]["messages"] = {"enabled": True, "required": False,
                                                     "connection_ref": "upstream-read-only", "expected_identity": "configured-conversation"}
        self.settings["modules"]["messages"] = True
        self.save_sources()
        self.config = load_config(self.config_path)
        observations = [x for x in self.observations() if x.capability != "messages"]
        report = run_doctor(self.config, observations, self.verified, now=NOW)
        self.assertTrue(report["ready"])
        self.assertEqual(report["optional_modules"]["messages"], {"status": "partial", "required": False})
        stale = self.receipt("messages", identity="configured-conversation")
        stale = self.trust(replace(stale, checked_at="2026-10-17T12:00:00Z"))
        report = run_doctor(self.config, [*observations, stale], self.verified, now=NOW)
        self.assertTrue(report["ready"])
        self.assertTrue(report["rejected_observations"])
        self.profile["integrations"]["messages"]["required"] = True
        self.save_sources()
        self.assertFalse(run_doctor(load_config(self.config_path), observations, self.verified, now=NOW)["ready"])

    def test_doctor_rejects_stale_cross_installation_and_incomplete_operations(self):
        receipt = self.receipt("google_sheets", identity="alex@example.invalid", evidence={"operations": ["get_profile"]})
        result = run_doctor(self.config, [receipt], self.verified, now=NOW)
        sheets = next(x for x in result["checks"] if x["capability"] == "google_sheets")
        self.assertEqual(sheets["state"], "connected")
        for changes in ({"checked_at": "2026-10-17T12:00:00Z"}, {"checked_at": "2026-10-19T12:00:00Z"},
                        {"evidence": {**receipt.evidence, "installation_id": "another"}}):
            bad = self.trust(replace(receipt, **changes))
            rejected = run_doctor(self.config, [bad], self.verified, now=NOW)
            self.assertTrue(rejected["rejected_observations"])
            self.assertFalse(rejected["ready"])

    def test_authenticated_browser_identity_must_match_configured_session(self):
        self.settings["modules"]["manual_outreach"] = True
        self.profile["integrations"]["browser"] = {"enabled": True, "required": True,
                                                     "connection_ref": "my-supported-browser", "expected_identity": "alex@example.invalid"}
        self.save_sources()
        self.config = load_config(self.config_path)
        receipt = self.receipt("authenticated_browser", identity="somebody-else@example.invalid",
                               evidence={"operations": ["browser_inventory", "account_identity", "exact_job_navigation"]})
        report = run_doctor(self.config, [receipt], self.verified, now=NOW)
        self.assertTrue(any("wrong account" in x for x in report["rejected_observations"]))

    def test_explicit_required_browser_is_checked_without_enabling_outreach(self):
        self.profile["integrations"]["browser"] = {"enabled": True, "required": True,
                                                     "connection_ref": "my-supported-browser", "expected_identity": "alex@example.invalid"}
        self.save_sources()
        config = load_config(self.config_path)
        self.assertFalse(config["modules"]["manual_outreach"])
        self.assertIn("authenticated_browser", {x["id"] for x in required_capabilities(config)})
        report = run_doctor(config, now=NOW)
        self.assertFalse(next(x for x in report["checks"] if x["capability"] == "authenticated_browser")["ready"])

    def test_generated_prompts_resolve_workflow_runbooks_and_support_command_directory(self):
        self.bind_all()
        paths = setup.prepare_prompts(self.config)
        runbooks = {"main": WORKFLOW_ROOT / "run.md", "blind": WORKFLOW_ROOT / "blind.md",
                    "email": WORKFLOW_ROOT / "helpers/email-discovery.md",
                    "portals": WORKFLOW_ROOT / "helpers/referral-portals.md"}
        for name, path in paths.items():
            with self.subTest(name=name):
                text = Path(path).read_text()
                self.assertIn(str(runbooks[name]), text)
                self.assertTrue(runbooks[name].is_file())
                self.assertIn(f"commands from {SUPPORT_ROOT}", text)
                self.assertIn(f"Repository: {REPO_ROOT}", text)

    def test_private_messages_identity_reference_requires_exact_resolved_binding(self):
        source = self.base / "private-message-source.json"
        source.write_text('{"identity":"configured-conversation"}')
        self.profile["private"]["refs"]["message_source"] = str(source)
        self.profile["integrations"]["messages"] = {"enabled": True, "required": True,
                                                     "connection_ref": "local-read-only", "expected_identity": "private:message_source"}
        self.settings["modules"]["messages"] = True
        self.save_sources()
        self.config = load_config(self.config_path)
        requirement = next(x for x in required_capabilities(self.config) if x["id"] == "messages")
        receipt = self.receipt("messages", identity="configured-conversation",
                               evidence={"operations": requirement["verification_operations"]})
        self.assertTrue(run_doctor(self.config, [receipt], self.verified, now=NOW)["rejected_observations"])
        binding = {"reference": "message_source", "path": str(source), "identity": "configured-conversation"}
        good = self.trust(replace(receipt, evidence={**receipt.evidence, "identity_binding": binding}))
        report = run_doctor(self.config, [good], self.verified, now=NOW)
        self.assertFalse(report["rejected_observations"])
        self.assertTrue(next(x for x in report["checks"] if x["capability"] == "messages")["ready"])

    def test_unshipped_legacy_parser_cannot_be_selected_by_dependency_presence(self):
        self.settings["adapters"]["html_parser"] = "beautifulsoup4"
        self.save_sources()
        with self.assertRaisesRegex(ConfigError, "maintained stdlib"):
            load_config(self.config_path)

    def test_scoped_staging_probe_is_explicit_and_never_claims_child_access(self):
        setup.init_instance(self.config)
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        report = run_doctor(self.config, now=NOW, check_staging=True)
        self.assertTrue(all(x["local_write_readback"] for x in report["staging"]))
        self.assertTrue(all(not x["child_access_verified"] for x in report["staging"]))
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))

    def test_schedule_preparation_requires_native_readiness_resources_and_both_live_passes(self):
        self.bind_all()
        observations = self.observations()
        self.assertTrue(run_doctor(self.config, observations, self.verified, now=NOW)["ready"])
        with self.assertRaisesRegex(ConfigError, "first live pass"):
            setup.prepare_schedules(self.config, observations, self.verified, now=NOW)
        self.first_pass("main")
        with self.assertRaisesRegex(ConfigError, "first live pass"):
            setup.prepare_schedules(self.config, observations, self.verified, now=NOW)
        self.first_pass("blind")
        proposals = setup.prepare_schedules(self.config, observations, self.verified, now=NOW)
        self.assertEqual([p["workflow"] for p in proposals], ["main", "blind"])
        self.assertTrue(all(p["intent"]["action"] == "perform_once" for p in proposals))
        self.assertTrue(all("shared-workbook" in p["prompt"] for p in proposals))
        self.assertTrue(all("RRULE" not in p["prompt"] for p in proposals))
        repeated = setup.prepare_schedules(self.config, observations, self.verified, now=NOW)
        self.assertTrue(all(p["intent"]["action"] == "reconcile_existing_intent" for p in repeated))

    def test_first_pass_cannot_accept_unsaved_work_or_unverified_delivery(self):
        self.bind_all()
        receipt = self.receipt("first_live_pass", resource="run", identity="alex@example.invalid", evidence={
            "workflow": "main", "status": "complete_with_exceptions", "unsynced_count": 1,
            "accepted_manifest_sha256": "a" * 64, "workbook_id": "shared-workbook", "delivery": "chat_verified"})
        with self.assertRaisesRegex(ConfigError, "unsaved"):
            setup.record_first_pass(self.config, "main", receipt, self.verified, now=NOW)
        bad = self.trust(replace(receipt, evidence={**receipt.evidence, "unsynced_count": 0, "delivery": "send_returned_success"}))
        with self.assertRaisesRegex(ConfigError, "output readback"):
            setup.record_first_pass(self.config, "main", bad, self.verified, now=NOW)

    def test_schedule_readback_must_match_frozen_chat_time_prompt_and_preferences(self):
        self.bind_all()
        for name in ("main", "blind"):
            self.first_pass(name)
        proposal = setup.prepare_schedules(self.config, self.observations(), self.verified, now=NOW)[0]
        intent = proposal["intent"]
        request = intent["request"]
        receipt = self.receipt("resource.schedule", resource="new-native-schedule", evidence={
            **request, "intent_id": intent["intent_id"], "request_digest": intent["request_digest"],
            "next_run_at": "2026-10-19T06:00:00Z", "local_time": "09:00"})
        with self.assertRaisesRegex(ConfigError, "differs"):
            setup.record_resource(self.config, "schedule", "main", receipt, self.verified, now=NOW)
        good = self.trust(replace(receipt, evidence={**receipt.evidence, "local_time": "06:00"}))
        bound = setup.record_resource(self.config, "schedule", "main", good, self.verified, now=NOW)
        self.assertEqual(bound["resource_id"], "new-native-schedule")

    def test_generated_prompts_preserve_central_writer_and_send_boundary(self):
        self.bind_all()
        paths = setup.prepare_prompts(self.config)
        main = Path(paths["main"]).read_text()
        blind = Path(paths["blind"]).read_text()
        self.assertIn("No email send is authorized", main)
        self.assertIn("only the coordinator writes", blind)
        self.assertIn(str(self.root / "config.json"), main)
        self.assertIn("pending until", blind)


if __name__ == "__main__":
    unittest.main()
