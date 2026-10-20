"""Preference updates use disposable installations, never connected tools."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from job_search_ops import preferences, setup
from job_search_ops.config import ConfigError, load_config


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        from test_setup import SetupTests
        self.h = SetupTests(methodName="runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.h.settings.update(schema_version=2, tracker={"provider": "google_sheets", "path": None},
                               discovery={"email": True, "portals": True}, tracking={"gmail": True})
        self.h.profile["schema_version"] = 2
        for entry in self.h.settings["schedules"].values():
            entry.update(enabled=False, local_time=None)
        self.h.save_sources()
        self.h.config = load_config(self.h.config_path)
        self.h.bind_all()
        setup.prepare_prompts(self.h.config)
        self.current = load_config(self.h.root / "config.json")

    def candidate(self, change=None, profile_change=None):
        settings = copy.deepcopy(setup.public_settings(self.current))
        profile = copy.deepcopy(self.current["_profile"])
        if change:
            change(settings)
        if profile_change:
            profile_change(profile)
            if profile["role_policy"]["version"] != self.current["_profile"]["role_policy"]["version"] and settings["modules"]["blind"]:
                settings["blind_policy"]["version"] = "blind-v2"
        settings["profile_path"] = str(self.h.base / "candidate-profile.json")
        (self.h.base / "candidate.json").write_text(json.dumps(settings))
        (self.h.base / "candidate-profile.json").write_text(json.dumps(profile))
        return load_config(self.h.base / "candidate.json")

    def apply(self, plan):
        return preferences.apply_preferences(self.h.root / "config.json", plan, plan["expected_digest"])

    def schedule(self, name="main", status="PAUSED"):
        manifest = setup.load_instance(self.current)
        body = Path(manifest["prompts"][name]["path"]).read_text()
        import hashlib
        request = {"name": "Original saved name", "thread_id": "native-chat-central", "local_time": "08:30",
                   "timezone": self.current["_profile"]["timezone"], "cadence": "daily", "status": status,
                   "notification_policy": "failed_runs_only", "prompt_digest": hashlib.sha256(body.encode()).hexdigest()}
        manifest["resources"]["schedule:" + name] = {"kind": "schedule", "key": name, "intent_id": "existing-intent",
            "request": request, "request_digest": setup.digest(request), "status": "verified", "resource_id": "existing-automation", "next_run_at": "saved-native-next-run"}
        setup._atomic_json(self.h.root / "installation.json", manifest)
        return manifest["resources"]["schedule:" + name]

    def test_manual_to_nine_am_preserves_every_history_and_binding(self):
        history = self.h.root / "state/history.json"
        history.write_text('{"keep":"forever"}')
        receipt = self.h.root / "state/writer/receipts/saved.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text('{"status":"saved"}')
        original = setup.load_instance(self.current)
        candidate = self.candidate(lambda c: c["schedules"]["main"].update(enabled=True, local_time="09:00"))
        plan = preferences.preference_plan(self.current, candidate)
        self.assertFalse((self.h.root / "state/preferences-update.json").exists())
        self.assertEqual(plan["pilot_required"], [])
        result = self.apply(plan)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["connected_effects"], [])
        self.assertEqual(result["schedule_actions"][0]["action"], "create_after_doctor_and_pilot")
        current = load_config(self.h.root / "config.json")
        self.assertEqual(current["schedules"]["main"]["local_time"], "09:00")
        self.assertEqual(setup.load_instance(current)["resources"], original["resources"])
        self.assertEqual(setup.load_instance(current)["first_passes"], original["first_passes"])
        self.assertEqual(history.read_text(), '{"keep":"forever"}')
        self.assertEqual(receipt.read_text(), '{"status":"saved"}')
        self.assertEqual(self.apply(plan)["status"], "already_applied")
        self.assertTrue(Path(result["backup"]).is_file())

    def test_criteria_update_and_disabled_integration_refresh_runtime_and_prompts(self):
        candidate = self.candidate(lambda c: c["tracking"].update(gmail=False),
                                   lambda p: p["role_policy"].update(families=["frontend"], version="core-v2"))
        old_bindings = copy.deepcopy(setup.load_instance(self.current)["resources"])
        plan = preferences.preference_plan(self.current, candidate)
        self.apply(plan)
        current = load_config(self.h.root / "config.json")
        self.assertEqual(setup.runtime_profile(current)["role_policy"]["families"], ["frontend"])
        self.assertFalse(current["tracking"]["gmail"])
        self.assertIn("Application and interview tracking is disabled", (self.h.root / "prompts/main.md").read_text())
        self.assertEqual(setup.load_instance(current)["resources"], old_bindings)
        self.assertEqual(json.loads((self.h.root / "state/approved-policies.json").read_text())["sources"]["email"]["version"], "core-v2")

    def test_disable_discovery_keeps_binding_and_staging_without_running_old_prompt(self):
        candidate = self.candidate(lambda c: c["discovery"].update(email=False))
        staging = self.h.root / "staging/email/retained.json"
        staging.write_text('{"evidence":"retained"}')
        self.apply(preferences.preference_plan(self.current, candidate))
        current = load_config(self.h.root / "config.json")
        self.assertIn("chat:email", setup.load_instance(current)["resources"])
        self.assertNotIn("email", setup.load_instance(current)["prompts"])
        self.assertIn("disabled", (self.h.root / "prompts/email.md").read_text())
        self.assertEqual(staging.read_text(), '{"evidence":"retained"}')

    def test_existing_schedule_preserves_pause_timing_id_and_reconciles_native_readback(self):
        bound = self.schedule()
        candidate = self.candidate(lambda c: c["tracking"].update(gmail=False))
        plan = preferences.preference_plan(self.current, candidate)
        action = plan["schedule_actions"][0]
        self.assertEqual(action["resource_id"], "existing-automation")
        self.assertEqual(action["request"]["status"], "PAUSED")
        self.assertEqual(action["request"]["local_time"], "08:30")
        self.apply(plan)
        current = load_config(self.h.root / "config.json")
        self.assertEqual(setup.load_instance(current)["resources"]["schedule:main"], bound)
        evidence = {**action["request"], "preferences_update_id": plan["update_id"], "next_run_at": "native-next-run"}
        receipt = self.h.receipt("resource.schedule", resource="existing-automation", evidence=evidence)
        from test_setup import NOW
        result = preferences.record_schedule_reconciliation(current, plan["update_id"], "main", receipt, self.h.verified, now=NOW)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(preferences.record_schedule_reconciliation(current, plan["update_id"], "main", receipt, self.h.verified, now=NOW)["status"], "already_verified")
        manifest = setup.load_instance(current)
        self.assertFalse(manifest["preferences_update"]["pending_schedules"])
        self.assertEqual(manifest["resources"]["schedule:main"]["resource_id"], "existing-automation")
        self.assertEqual(manifest["resources"]["schedule:main"]["request"], action["request"])

    def test_native_schedule_adapter_accepts_paused_null_next_run_and_requires_exact_binding(self):
        self.schedule()
        plan = preferences.preference_plan(self.current, self.candidate(lambda c: c["tracking"].update(gmail=False)))
        action = plan["schedule_actions"][0]
        self.apply(plan)
        current = load_config(self.h.root / "config.json")
        from job_search_ops.doctor import HostReceipt
        from job_search_ops import host_evidence
        from test_setup import NOW
        response = {"id": "existing-automation", **action["request"], "rrule": "FREQ=DAILY;BYHOUR=8;BYMINUTE=30", "prompt": action["prompt"], "next_run_at": None}
        field_checks = {key: {"check": 0, "path": "/" + ("prompt" if key == "prompt_digest" else key)}
                        for key in ("thread_id", "local_time", "timezone", "status", "notification_policy", "prompt_digest", "next_run_at")}
        field_checks["cadence"] = {"check": 0, "path": "/rrule", "transform": "rrule_daily"}
        evidence = {**action["request"], "installation_id": current["installation_id"], "preferences_update_id": plan["update_id"],
                    "next_run_at": None, "field_checks": field_checks, "operations": ["read_schedule"],
                    "native_checks": [{"operation": "read_schedule", "tool": "mcp__codex_app__automation_update",
                        "request": {"mode": "view", "id": "existing-automation"}, "response": response,
                        "assertions": [{"path": "/id", "equals": "existing-automation"}]}]}
        receipt = HostReceipt("resource.schedule", "operation_verified", "native-schedule-readback", NOW,
                              None, "existing-automation", "read_schedule", evidence)
        self.assertTrue(host_evidence.verify(receipt))
        preferences.record_schedule_reconciliation(current, plan["update_id"], "main", receipt, host_evidence.verify, now=NOW)
        self.assertIsNone(setup.load_instance(current)["resources"]["schedule:main"]["next_run_at"])

    def test_disabling_mail_integration_removes_runtime_requirement_retains_identity(self):
        candidate = self.candidate(lambda c: (c["discovery"].update(email=False), c["tracking"].update(gmail=False)),
                                   lambda p: p["integrations"]["mail"].update(enabled=False, required=False, connection_ref=None, expected_identity=None))
        plan = preferences.preference_plan(self.current, candidate)
        self.assertNotIn("gmail_read", {x["capability"] for x in plan["requirements"]})
        self.apply(plan)
        current = load_config(self.h.root / "config.json")
        self.assertFalse(setup.runtime_profile(current)["integrations"]["mail"]["enabled"])
        self.assertIsNone(current["_profile"]["integrations"]["mail"]["connection_ref"])
        journal = json.loads((self.h.root / "state/preferences-update.json").read_text())
        self.assertEqual(journal["plan"]["before"]["profile"]["integrations"]["mail"], self.current["_profile"]["integrations"]["mail"])

    def test_changed_scope_pilot_is_version_bound_and_preserves_initial_acceptance(self):
        from test_setup import NOW
        self.schedule(status="ACTIVE")
        manifest = setup.load_instance(self.current)
        initial = {"run_id": "historical-pilot", "accepted_manifest_sha256": "a" * 64}
        manifest["first_passes"]["main"] = initial
        setup._atomic_json(self.h.root / "installation.json", manifest)
        plan = preferences.preference_plan(self.current, self.candidate(lambda c: c["tracking"].update(gmail=False)))
        self.assertEqual(plan["pilot_required"], ["main"])
        self.apply(plan)
        current = load_config(self.h.root / "config.json")
        action = plan["schedule_actions"][0]
        schedule_evidence = {**action["request"], "preferences_update_id": plan["update_id"], "next_run_at": "native-next-run"}
        schedule_receipt = self.h.receipt("resource.schedule", resource="existing-automation", evidence=schedule_evidence)
        with self.assertRaisesRegex(ConfigError, "live pilot"):
            preferences.record_schedule_reconciliation(current, plan["update_id"], "main", schedule_receipt, self.h.verified, now=NOW)
        evidence = {"workflow": "main", "status": "complete", "unsynced_count": 0, "accepted_manifest_sha256": "b" * 64,
                    "workbook_id": "shared-workbook", "delivery": "chat_verified"}
        old_receipt = self.h.receipt("first_live_pass", resource="new-pilot", identity="alex@example.invalid", evidence=evidence)
        with patch("job_search_ops.referrals.require_seed"), self.assertRaisesRegex(ConfigError, "preferences_update_id"):
            setup.record_first_pass(current, "main", old_receipt, self.h.verified, now=NOW)
        evidence["preferences_update_id"] = plan["update_id"]
        receipt = self.h.receipt("first_live_pass", resource="new-pilot", identity="alex@example.invalid", evidence=evidence)
        with patch("job_search_ops.referrals.require_seed"):
            setup.record_first_pass(current, "main", receipt, self.h.verified, now=NOW)
        accepted = setup.load_instance(current)
        self.assertEqual(accepted["first_passes"]["main"], initial)
        self.assertEqual(accepted["preferences_update"]["pilot_passes"]["main"]["run_id"], "new-pilot")
        self.assertFalse(accepted["preferences_update"]["pilot_required"])
        self.assertEqual(preferences.record_schedule_reconciliation(current, plan["update_id"], "main", schedule_receipt, self.h.verified, now=NOW)["status"], "verified")

    def test_schedule_only_followup_cannot_erase_unfinished_scope_pilot(self):
        first = preferences.preference_plan(self.current, self.candidate(lambda c: c["tracking"].update(gmail=False)))
        self.apply(first)
        self.current = load_config(self.h.root / "config.json")
        second = preferences.preference_plan(self.current, self.candidate(lambda c: c["schedules"]["main"].update(enabled=True, local_time="09:00")))
        self.assertEqual(second["pilot_required"], ["main"])
        self.apply(second)
        current = load_config(self.h.root / "config.json")
        with self.assertRaisesRegex(ConfigError, "preferences_update_id"):
            setup.prepare_schedules(current)

    def test_rejects_stale_digest_plan_and_changed_binding(self):
        plan = preferences.preference_plan(self.current, self.candidate(lambda c: c["tracking"].update(gmail=False)))
        with self.assertRaisesRegex(ConfigError, "expected old digest"):
            preferences.apply_preferences(self.h.root / "config.json", plan, "0" * 64)
        changed = copy.deepcopy(plan)
        changed["after"]["config"]["tracking"]["gmail"] = True
        with self.assertRaises(ConfigError):
            self.apply(changed)
        manifest = setup.load_instance(self.current)
        manifest["first_passes"]["main"] = {"run_id": "new-pilot"}
        setup._atomic_json(self.h.root / "installation.json", manifest)
        with self.assertRaisesRegex(ConfigError, "bindings or acceptance changed"):
            self.apply(plan)
        self.assertFalse((self.h.root / "state/preferences-update.json").exists())

    def test_rejects_account_root_or_tracker_replacement(self):
        variants = [(lambda c: c["tracker"].update(provider="local_xlsx", path=str(self.h.root / "replacement.xlsx")), None),
                    (None, lambda p: p["identity"].update(account_identity="another@example.invalid")),
                    (None, lambda p: p["integrations"]["mail"].update(connection_ref="another-account"))]
        for change, profile_change in variants:
            with self.subTest(change=change, profile_change=profile_change), self.assertRaises(ConfigError):
                preferences.preference_plan(self.current, self.candidate(change, profile_change))

    def test_unfinished_writer_and_brief_reject_without_touching_config(self):
        candidate = self.candidate(lambda c: c["tracking"].update(gmail=False))
        before = (self.h.root / "config.json").read_bytes()
        for folder, status, message in (("writer/journals", "write_pending", "unfinished tracker writes"), ("delivery", "sending", "outstanding briefs")):
            path = self.h.root / "state" / folder / "unfinished.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"status": status}))
            with self.assertRaisesRegex(ConfigError, message):
                preferences.preference_plan(self.current, candidate)
            path.unlink()
        self.assertEqual((self.h.root / "config.json").read_bytes(), before)

    def test_queued_packet_requires_old_policy_before_criteria_update_but_schedule_can_change(self):
        pending = self.h.root / "state/queue/pending/existing.json"
        pending.parent.mkdir(parents=True)
        pending.write_text('{"original":"evidence"}')
        criteria = self.candidate(profile_change=lambda p: p["role_policy"].update(families=["frontend"], version="core-v2"))
        with self.assertRaisesRegex(ConfigError, "queued discoveries"):
            preferences.preference_plan(self.current, criteria)
        schedule = self.candidate(lambda c: c["schedules"]["main"].update(enabled=True, local_time="09:00"))
        old_policy = (self.h.root / "state/approved-policies.json").read_bytes()
        self.apply(preferences.preference_plan(self.current, schedule))
        self.assertEqual(pending.read_text(), '{"original":"evidence"}')
        self.assertEqual((self.h.root / "state/approved-policies.json").read_bytes(), old_policy)

    def test_interrupted_multifile_update_resumes_without_losing_history(self):
        plan = preferences.preference_plan(self.current, self.candidate(lambda c: c["tracking"].update(gmail=False),
                                                                      lambda p: p["role_policy"].update(families=["frontend"], version="core-v2")))
        original = setup._atomic_text
        def fail(path, body):
            if Path(path) == self.h.root / "profile.json":
                raise OSError("synthetic interruption")
            return original(path, body)
        with patch.object(setup, "_atomic_text", side_effect=fail):
            with self.assertRaisesRegex(OSError, "synthetic interruption"):
                self.apply(plan)
        journal = json.loads((self.h.root / "state/preferences-update.json").read_text())
        self.assertEqual(journal["status"], "applying")
        self.assertEqual(self.apply(plan)["status"], "applied")
        current = load_config(self.h.root / "config.json")
        self.assertEqual(setup.runtime_profile(current)["role_policy"]["families"], ["frontend"])
        self.assertEqual(self.apply(plan)["status"], "already_applied")

    def test_setup_lock_excludes_another_operation_without_removing_the_inode(self):
        import fcntl
        lock = self.h.root / ".setup.lock"
        inode = lock.stat().st_ino
        with lock.open("r+") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ConfigError, "another operation is active"):
                setup.prepare_prompts(self.current)
            self.assertEqual(lock.stat().st_ino, inode)
            fcntl.flock(held, fcntl.LOCK_UN)
        setup.prepare_prompts(self.current)
        self.assertEqual(lock.stat().st_ino, inode)

    def test_process_death_releases_locks_and_cli_recovers_the_published_plan(self):
        import os
        import signal
        import subprocess
        import sys
        plan = preferences.preference_plan(self.current, self.candidate(lambda c: c["tracking"].update(gmail=False),
                                                                      lambda p: p["role_policy"].update(families=["frontend"], version="core-v2")))
        plan_path = self.h.base / "reviewed-plan.json"
        setup._atomic_json(plan_path, plan)
        code = """import os, signal, sys
from pathlib import Path
from job_search_ops import preferences, setup
from job_search_ops.config import read_json
original = setup._atomic_text
def interrupt(path, body):
    if Path(path) == Path(sys.argv[1]).parent / 'profile.json':
        os.kill(os.getpid(), signal.SIGKILL)
    return original(path, body)
setup._atomic_text = interrupt
preferences.apply_preferences(sys.argv[1], read_json(sys.argv[2]), sys.argv[3])
"""
        args = [str(self.h.root / "config.json"), str(plan_path), plan["expected_digest"]]
        killed = subprocess.run([sys.executable, "-B", "-c", code, *args], capture_output=True, text=True, timeout=10)
        self.assertEqual(killed.returncode, -signal.SIGKILL, killed.stderr)
        self.assertEqual(json.loads((self.h.root / "state/preferences-update.json").read_text())["status"], "applying")
        recovered = subprocess.run([sys.executable, "-B", "-m", "job_search_ops", "preferences-apply",
                                    "--config", args[0], "--plan", args[1], "--expected-digest", args[2]], capture_output=True, text=True, timeout=10)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertEqual(json.loads(recovered.stdout)["status"], "applied")
        self.assertEqual(setup.load_instance(load_config(self.h.root / "config.json"))["preferences_update"]["update_id"], plan["update_id"])

    def test_interrupted_update_never_overwrites_an_unexpected_edit(self):
        plan = preferences.preference_plan(self.current, self.candidate(lambda c: c["tracking"].update(gmail=False)))
        original = setup._atomic_text
        def fail(path, body):
            if Path(path) == self.h.root / "prompts/main.md":
                raise OSError("synthetic interruption")
            return original(path, body)
        with patch.object(setup, "_atomic_text", side_effect=fail), self.assertRaises(OSError):
            self.apply(plan)
        target = self.h.root / "execution-plan.json"
        target.write_text('{"unexpected":"manual edit"}')
        with self.assertRaisesRegex(ConfigError, "managed file changed"):
            self.apply(plan)
        self.assertEqual(target.read_text(), '{"unexpected":"manual edit"}')


if __name__ == "__main__":
    unittest.main()
