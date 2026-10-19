"""Regression cases for full recurrence checks and preference pilot isolation."""
from dataclasses import replace
import copy
import hashlib
import json
import unittest

from job_search_ops import host_evidence, preferences, setup
from job_search_ops.config import ConfigError, load_config
from job_search_ops.doctor import HostReceipt, required_capabilities, run_doctor


NOW = "2026-10-18T12:00:00+00:00"


class ScheduleGuardsTests(unittest.TestCase):
    def setUp(self):
        from test_preferences import PreferencesTests
        self.h = PreferencesTests(methodName="runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def native_schedule(self, rule):
        response = {"id": "native-automation", "thread_id": "central", "rrule": rule,
                    "timezone": "America/New_York", "status": "ACTIVE", "notification_policy": None,
                    "prompt": "workflow", "next_run_at": "2026-10-19T13:00:00Z"}
        evidence = {"thread_id": "central", "cadence": "daily", "local_time": "09:00",
                    "timezone": response["timezone"], "status": "ACTIVE", "notification_policy": "meaningful_changes",
                    "prompt_digest": hashlib.sha256(b"workflow").hexdigest(), "next_run_at": response["next_run_at"],
                    "operations": ["read_schedule"], "native_checks": [{"operation": "read_schedule",
                    "tool": "mcp__codex_app__automation_update", "request": {"mode": "view", "id": response["id"]},
                    "response": response, "assertions": [{"path": "/id", "equals": response["id"]}]}]}
        evidence["field_checks"] = {key: {"check": 0, "path": "/" + ("prompt" if key == "prompt_digest" else key)}
                                    for key in ("thread_id", "timezone", "status", "prompt_digest", "next_run_at")}
        evidence["field_checks"].update(cadence={"check": 0, "path": "/rrule", "transform": "rrule_daily"},
                                        local_time={"check": 0, "path": "/rrule", "transform": "rrule_time"},
                                        notification_policy={"check": 0, "path": "/notification_policy", "transform": "notification_policy"})
        return HostReceipt("resource.schedule", "operation_verified", "native-schedule-readback", NOW,
                           None, response["id"], "read_schedule", evidence)

    def test_full_daily_recurrence_accepts_only_same_unbounded_cadence(self):
        for rule in ("FREQ=DAILY;BYHOUR=9;BYMINUTE=0", "RRULE:FREQ=DAILY;INTERVAL=1;BYHOUR=09;BYMINUTE=00;BYSECOND=0"):
            self.assertTrue(host_evidence.verify(self.native_schedule(rule)))
        for rule in ("FREQ=WEEKLY;INTERVAL=2;BYHOUR=9;BYMINUTE=0;COUNT=1",
                     "FREQ=DAILY;INTERVAL=2;BYHOUR=9;BYMINUTE=0", "FREQ=DAILY;BYHOUR=9;BYMINUTE=0;COUNT=1",
                     "FREQ=DAILY;BYHOUR=9;BYMINUTE=0;UNTIL=20261020T130000Z",
                     "FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYDAY=MO,TU,WE,TH,FR",
                     "FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYSECOND=30", "FREQ=DAILY;BYHOUR=9,10;BYMINUTE=0",
                     "FREQ=DAILY;BYHOUR=9;BYMINUTE=0;INTERVAL=1;INTERVAL=2"):
            with self.subTest(rule=rule):
                self.assertFalse(host_evidence.verify(self.native_schedule(rule)))

    def test_cadence_cannot_be_a_normalized_unverified_label(self):
        receipt = self.native_schedule("FREQ=WEEKLY;BYHOUR=9;BYMINUTE=0")
        evidence = copy.deepcopy(receipt.evidence)
        evidence["native_checks"][0]["response"]["cadence"] = "daily"
        evidence["native_checks"][0]["response"]["local_time"] = "09:00"
        evidence["field_checks"]["cadence"] = {"check": 0, "path": "/cadence"}
        evidence["field_checks"]["local_time"] = {"check": 0, "path": "/local_time"}
        self.assertFalse(host_evidence.verify(replace(receipt, evidence=evidence)))

    def test_recurrence_time_cannot_disagree_with_separate_native_display_time(self):
        receipt = self.native_schedule("FREQ=DAILY;BYHOUR=10;BYMINUTE=0")
        evidence = copy.deepcopy(receipt.evidence)
        evidence["native_checks"][0]["response"]["local_time"] = "09:00"
        evidence["field_checks"]["local_time"] = {"check": 0, "path": "/local_time"}
        self.assertFalse(host_evidence.verify(replace(receipt, evidence=evidence)))

    def test_active_schedule_cannot_consume_changed_preferences_without_explicit_pilot(self):
        self.h.schedule(status="ACTIVE")
        old = setup.load_instance(self.h.current)["resources"]["schedule:main"]
        plan = preferences.preference_plan(self.h.current, self.h.candidate(lambda c: c["tracking"].update(gmail=False)))
        self.h.apply(plan)
        current = load_config(self.h.h.root / "config.json")
        self.assertEqual(setup.load_instance(current)["resources"]["schedule:main"], old)
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            setup.run_check(current, "main")
        with self.assertRaisesRegex(ConfigError, "current preferences_update_id"):
            setup.run_check(current, "main", pilot_update_id="stale-update")
        self.assertEqual(setup.run_check(current, "main", pilot_update_id=plan["update_id"])["mode"], "manual_pilot")
        with setup.execution_context(pilot_update_id=plan["update_id"]):
            self.assertEqual(setup.require_execution(self.h.h.root, "main")["mode"], "manual_pilot")
            self.assertEqual(setup.require_execution(self.h.h.root, "blind")["mode"], "ordinary")
        with self.assertRaises(ConfigError):
            setup.require_execution(self.h.h.root, "main")
        self.assertEqual(setup.run_check(current, "blind")["mode"], "ordinary")
        self.assertIn("run-check", setup.render_prompts(current, setup.load_instance(current))["main"])

    def test_role_change_is_held_even_when_scheduler_needs_no_prompt_change(self):
        self.h.schedule(status="ACTIVE")
        candidate = self.h.candidate(profile_change=lambda p: p["role_policy"].update(families=["frontend"], version="core-v2"))
        plan = preferences.preference_plan(self.h.current, candidate)
        self.assertEqual(plan["schedule_actions"], [])
        self.assertEqual(set(plan["pilot_required"]), {"main", "blind"})
        self.h.apply(plan)
        current = load_config(self.h.h.root / "config.json")
        for workflow in ("main", "blind"):
            with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
                setup.run_check(current, workflow)
        self.assertEqual(setup.run_check(current, "main", pilot_update_id=plan["update_id"])["mode"], "manual_pilot")

    def test_old_captured_pilot_cannot_be_relabelled_for_new_preferences(self):
        from test_native_bridge import check
        manifest = {"workflow": "main", "run_id": "old-run", "status": "complete", "unsynced_count": 0,
                    "workbook_id": "shared-workbook", "delivery": "chat_verified"}
        captured = check("accepted_manifest_readback", "exec_command", {"exit_code": 0, "output": json.dumps(manifest)},
                         [{"path": "/exit_code", "equals": 0}])
        delivery = check("delivery_readback", "mcp__codex_app__read_thread", {"text": "saved"},
                         [{"path": "/text", "equals": "saved"}])
        evidence = {**manifest, "preferences_update_id": "new-update", "accepted_manifest": manifest,
                    "accepted_manifest_sha256": setup.digest(manifest), "operations": ["accepted_manifest_readback", "delivery_readback"],
                    "native_checks": [captured, delivery]}
        receipt = HostReceipt("first_live_pass", "operation_verified", "pilot-readback", NOW, None, "old-run", "run-readback", evidence)
        self.assertFalse(host_evidence.verify(receipt))
        manifest["preferences_update_id"] = "new-update"
        captured["response"]["output"] = json.dumps(manifest)
        evidence["accepted_manifest_sha256"] = setup.digest(manifest)
        self.assertTrue(host_evidence.verify(receipt))

    def test_rated_policy_change_holds_only_rated_scope(self):
        plan = preferences.preference_plan(self.h.current, self.h.candidate(lambda c: c["blind_policy"].update(version="rated-v2", max_required_years=1)))
        self.assertEqual(plan["pilot_required"], ["blind"])
        self.h.apply(plan)
        current = load_config(self.h.h.root / "config.json")
        self.assertEqual(setup.run_check(current, "main")["mode"], "ordinary")
        with self.assertRaisesRegex(ConfigError, "replacement pilot pending"):
            setup.run_check(current, "blind")

    def test_rated_schedule_uses_its_dependencies_with_main_gmail_missing(self):
        h = self.h.h
        candidate = self.h.candidate(lambda c: c["schedules"]["blind"].update(enabled=True, local_time="09:00"))
        plan = preferences.preference_plan(self.h.current, candidate)
        self.h.apply(plan)
        current = load_config(h.root / "config.json")
        manifest = setup.load_instance(current)
        manifest["first_passes"]["blind"] = {"run_id": "accepted-rated-pilot"}
        setup._atomic_json(h.root / "installation.json", manifest)
        h.config = current
        observations = [item for item in h.observations() if not item.capability.startswith("gmail")]
        self.assertFalse(run_doctor(current, observations, h.verified, NOW)["ready"])
        scoped = run_doctor(current, observations, h.verified, NOW, workflow="blind")
        self.assertTrue(scoped["ready"], scoped)
        self.assertNotIn("gmail_read", {item["id"] for item in required_capabilities(current, "blind")})
        proposals = setup.prepare_schedules(current, observations, h.verified, NOW, workflow="blind")
        self.assertEqual([item["workflow"] for item in proposals], ["blind"])


if __name__ == "__main__":
    unittest.main()
