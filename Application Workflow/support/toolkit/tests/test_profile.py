"""acceptance checks derived from README, PROFILE and fictional examples.

Only copied toolkit files and temporary synthetic fixtures are accessed.
Run: python3 -B -m unittest discover -s tests -v
"""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOLKIT = Path(__file__).resolve().parents[1]
# Literal differences documented in the two examples; no validator-derived oracle.
EXPECTED = {
    "alex": {
        "schema_version": 1,
        "profile_id": "example-alex",
        "identity": {"display_name": "Alex Example", "account_identity": "alex@example.invalid",
                     "report_recipient": "alex+brief@example.invalid"},
        "timezone": "Europe/London",
        "role_policy": {
            "version": "example-v1", "families": ["backend", "full-stack"],
            "preferred_levels": ["intermediate"], "excluded_duties": ["pure research"],
            "excluded_levels": ["principal"], "excluded_employers": ["Fictional Excluded Ltd"],
            "experience": {"max_required_years": 3, "preferred_required_years": 2,
                           "senior_low_experience_exception": False,
                           "unknown_minimum": "review", "ambiguous_range": "review"}},
        "locations": {"onsite_regions": ["London"], "remote_countries": ["United Kingdom"],
                      "residency_region": "London, United Kingdom", "allow_relocation": False},
        "trackers": {"jobs": {"workbook_id": "SYNTHETIC_ALEX_JOBS", "worksheet": "Opportunities",
                              "header_row": 1, "columns": {
                                  "company": {"index": 1, "header": "Employer"},
                                  "title": {"index": 2, "header": "Role"},
                                  "job_link": {"index": 3, "header": "Posting"},
                                  "status": {"index": 4, "header": "Stage"}}}},
        "capacity": {"application_pages": 10, "initial_application_total": 2,
                     "next_application_additional": 3, "outreach_drafts": 5, "workers": 2,
                     "recruiter_target": 25, "recruiter_stretch_target": 50},
        "integrations": {
            "mail": {"enabled": True, "required": True, "connection_ref": "fictional-mail-alex",
                     "expected_identity": "alex@example.invalid"},
            "sheets": {"enabled": True, "required": True, "connection_ref": "fictional-sheets-alex",
                       "expected_identity": "alex@example.invalid"},
            "calendar": {"enabled": False, "required": False, "connection_ref": None,
                         "expected_identity": None},
            "messages": {"enabled": False, "required": False, "connection_ref": None,
                         "expected_identity": None}},
        "source_access": {"google": "connector_only", "public_portals": ["background", "builtin_browser"],
                          "authenticated_browser": "chrome", "email_job_browser": "chrome", "read_attempts": 3},
        "private": {"state_root": "../../job-search-private/example-alex/state", "refs": {
            "applicant_facts": "../../job-search-private/example-alex/applicant.json",
            "referral_scope": "../../job-search-private/example-alex/referrals.json",
            "approved_copy": "../../job-search-private/example-alex/copy.md"}}},
    "sam": {
        "schema_version": 1,
        "profile_id": "example-sam",
        "identity": {"display_name": "Sam Example", "account_identity": "sam@example.invalid",
                     "report_recipient": "sam+digest@example.invalid"},
        "timezone": "Asia/Tokyo",
        "role_policy": {
            "version": "example-v1", "families": ["applied AI"],
            "preferred_levels": ["senior individual contributor"], "excluded_duties": ["mobile-only"],
            "excluded_levels": ["management"], "excluded_employers": [],
            "experience": {"max_required_years": 6, "preferred_required_years": 5,
                           "senior_low_experience_exception": True,
                           "unknown_minimum": "review", "ambiguous_range": "review"}},
        "locations": {"onsite_regions": ["Tokyo"], "remote_countries": ["Japan"],
                      "residency_region": "Tokyo, Japan", "allow_relocation": True},
        "trackers": {"jobs": {"workbook_id": "SYNTHETIC_SAM_JOBS", "worksheet": "Roles",
                              "header_row": 3, "columns": {
                                  "company": {"index": 4, "header": "Company"},
                                  "title": {"index": 2, "header": "Title"},
                                  "job_link": {"index": 1, "header": "URL"},
                                  "status": {"index": 7, "header": "Decision"}}}},
        "capacity": {"application_pages": 8, "initial_application_total": 4,
                     "next_application_additional": 2, "outreach_drafts": 12, "workers": 0,
                     "recruiter_target": 40, "recruiter_stretch_target": 80},
        "integrations": {
            "mail": {"enabled": True, "required": True, "connection_ref": "fictional-mail-sam",
                     "expected_identity": "sam@example.invalid"},
            "sheets": {"enabled": True, "required": True, "connection_ref": "fictional-sheets-sam",
                       "expected_identity": "sam@example.invalid"},
            "calendar": {"enabled": True, "required": False, "connection_ref": "fictional-calendar-sam",
                         "expected_identity": "sam@example.invalid"},
            "messages": {"enabled": True, "required": True, "connection_ref": "fictional-messages-sam",
                         "expected_identity": "sam@example.invalid"}},
        "source_access": {"google": "connector_only", "public_portals": ["background", "builtin_browser"],
                          "authenticated_browser": "edge", "email_job_browser": "edge", "read_attempts": 2},
        "private": {"state_root": "../../job-search-private/example-sam/state", "refs": {
            "applicant_facts": "../../job-search-private/example-sam/applicant.json",
            "interview_source_checks": "../../job-search-private/example-sam/source-checks.md"}}},
}


class ProfileAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="profile-acceptance-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.package = self.root / "workspace" / "toolkit"
        (self.package / "examples").mkdir(parents=True)
        for name in ("profile.py", "README.md", "PROFILE.md", "examples/alex.json", "examples/sam.json"):
            shutil.copyfile(TOOLKIT / name, self.package / name)
        self.other_cwd = self.root / "other-cwd"
        self.other_cwd.mkdir()
        spec = importlib.util.spec_from_file_location("copied_profile", self.package / "profile.py")
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.profile_path = self.package / "examples" / "alex.json"

    def config(self, person="alex"):
        return copy.deepcopy(EXPECTED[person])

    def reject(self, profile, field):
        before = copy.deepcopy(profile)
        with self.assertRaises(self.api.ProfileError) as caught:
            self.api.validate_profile(profile, self.profile_path)
        self.assertIn(field, str(caught.exception))
        self.assertEqual(profile, before)

    def cli(self, path):
        return subprocess.run([sys.executable, "-B", str(self.package / "profile.py"), str(path)],
                              cwd=self.other_cwd, capture_output=True, text=True, timeout=10)

    def test_both_unchanged_examples_preserve_all_settings_from_other_cwd(self):
        old_cwd = Path.cwd()
        self.addCleanup(os.chdir, old_cwd)
        os.chdir(self.other_cwd)
        for person in ("alex", "sam"):
            with self.subTest(person=person):
                path = self.package / "examples" / f"{person}.json"
                before = path.read_bytes()
                self.assertEqual(self.api.load_profile(path), EXPECTED[person])
                self.assertEqual(path.read_bytes(), before)
                result = self.cli(path)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), {
                    "status": "configuration_valid", "schema_version": 1,
                    "profile_id": f"example-{person}", "effects": [], "live_readiness_verified": False})
        self.assertFalse((self.root / "workspace" / "job-search-private").exists())

    def test_private_paths_resolve_against_profile_parent(self):
        self.assertEqual(self.api.resolved_private_paths(self.config(), self.profile_path), {
            "state_root": str(self.root / "workspace/job-search-private/example-alex/state"),
            "applicant_facts": str(self.root / "workspace/job-search-private/example-alex/applicant.json"),
            "referral_scope": str(self.root / "workspace/job-search-private/example-alex/referrals.json"),
            "approved_copy": str(self.root / "workspace/job-search-private/example-alex/copy.md")})
        private_profile = self.root / "private" / "profiles" / "config.json"
        data = self.config()
        data["private"] = {"state_root": "../state", "refs": {"facts": "../sources/../facts.json",
                                                               "ledger": str(self.root / "ledger.json")}}
        self.assertEqual(self.api.resolved_private_paths(data, private_profile), {
            "state_root": str(self.root / "private/state"),
            "facts": str(self.root / "private/facts.json"), "ledger": str(self.root / "ledger.json")})

    def test_load_reads_only_supplied_json_and_has_no_effects(self):
        data = self.config()
        private_dir = self.root / "private"
        private_dir.mkdir()
        profile_path = private_dir / "profile.json"
        data["private"] = {"state_root": "state", "refs": {"facts": "facts.json", "absent": "missing.json"}}
        profile_path.write_text(json.dumps(data), encoding="utf-8")
        (private_dir / "facts.json").write_text("THIS IS NOT JSON AND MUST NOT BE READ", encoding="utf-8")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        original_read = Path.read_text
        original_open = io.open
        def read_config_only(path, *args, **kwargs):
            self.assertEqual(path, profile_path, "read a referenced source instead of the config")
            return original_read(path, *args, **kwargs)
        def open_config_only(path, mode="r", *args, **kwargs):
            self.assertEqual(Path(path), profile_path, "opened a referenced source")
            self.assertIn(mode, ("r", "rb"), "attempted a write")
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, "read_text", read_config_only), \
             patch.object(io, "open", open_config_only), \
             patch("builtins.open", side_effect=AssertionError("unexpected file open")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("unexpected state creation")), \
             patch.object(Path, "write_text", side_effect=AssertionError("unexpected write")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("unexpected subprocess")), \
             patch.object(socket, "socket", side_effect=AssertionError("unexpected network")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("unexpected network")):
            self.assertEqual(self.api.load_profile(profile_path), data)
            self.assertEqual(self.api.validate_profile(data, profile_path), data)
            self.api.resolved_private_paths(data, profile_path)
        self.assertFalse((private_dir / "state").exists())
        self.assertEqual({p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)

    def test_missing_and_unknown_fields_at_every_fixed_object(self):
        objects = [(), ("identity",), ("role_policy",), ("role_policy", "experience"),
                   ("locations",), ("trackers", "jobs"), ("trackers", "jobs", "columns", "company"),
                   ("capacity",), ("integrations", "mail"), ("source_access",), ("private",)]
        for path in objects:
            for change in ("missing", "unknown"):
                with self.subTest(path=path, change=change):
                    data = self.config()
                    obj = data
                    for key in path:
                        obj = obj[key]
                    if change == "missing":
                        del obj[next(iter(obj))]
                    else:
                        obj["unexpected"] = "synthetic"
                    self.reject(data, ".".join(path) or "profile")

    def test_invalid_types_and_boolean_in_integer_fields(self):
        cases = [(("schema_version",), True), (("schema_version",), 3), (("profile_id",), 4),
                 (("identity", "display_name"), []), (("identity", "account_identity"), "bad address"),
                 (("role_policy", "families"), "backend"), (("role_policy", "preferred_levels"), []),
                 (("role_policy", "experience", "max_required_years"), True),
                 (("role_policy", "experience", "preferred_required_years"), "2"),
                 (("locations", "allow_relocation"), 1), (("trackers", "jobs", "header_row"), True),
                 (("trackers", "jobs", "columns", "company", "index"), False),
                 (("capacity", "application_pages"), True), (("capacity", "workers"), False),
                 (("capacity", "outreach_drafts"), 2.0), (("integrations", "mail", "enabled"), 1),
                 (("integrations", "mail", "required"), "true"), (("source_access", "read_attempts"), True),
                 (("private", "refs"), []), (("private", "state_root"), None)]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                data = self.config()
                obj = data
                for key in path[:-1]:
                    obj = obj[key]
                obj[path[-1]] = value
                self.reject(data, ".".join(path))

    def test_numeric_boundaries_and_review_policy(self):
        for field, value in (("max_required_years", -1), ("max_required_years", float("inf")),
                             ("preferred_required_years", 4), ("unknown_minimum", "accept"),
                             ("ambiguous_range", "accept"), ("senior_low_experience_exception", 0)):
            with self.subTest(field=field, value=value):
                data = self.config()
                data["role_policy"]["experience"][field] = value
                self.reject(data, "role_policy.experience")
        for field in self.config()["capacity"]:
            for value in (-1 if field == "workers" else 0, True):
                data = self.config()
                data["capacity"][field] = value
                self.reject(data, f"capacity.{field}")
        data = self.config()
        data["capacity"]["workers"] = 0
        data["role_policy"]["experience"].update(max_required_years=2.5, preferred_required_years=0)
        self.assertEqual(self.api.validate_profile(data, self.profile_path), data)

    def test_experience_policy_options_are_explicit_and_independent(self):
        for unknown in ("review", "include"):
            for ranges in ("review", "accept_lower_bound"):
                with self.subTest(unknown=unknown, ranges=ranges):
                    data = self.config()
                    data["role_policy"]["experience"].update(unknown_minimum=unknown, ambiguous_range=ranges)
                    before = copy.deepcopy(data)
                    self.assertEqual(self.api.validate_profile(data, self.profile_path), before)
                    self.assertEqual(data, before)
        for field, values in (("unknown_minimum", ("accept_lower_bound", "accept", None, True, [])),
                              ("ambiguous_range", ("include", "accept", None, True, []))):
            for value in values:
                with self.subTest(field=field, value=value):
                    data = self.config()
                    data["role_policy"]["experience"][field] = value
                    self.reject(data, "role_policy.experience." + field)

    def test_source_access_and_geographic_scope_remain_explicit(self):
        for field, value in (("google", "browser"), ("public_portals", ["builtin_browser", "background"]),
                             ("authenticated_browser", "builtin_browser"), ("email_job_browser", "safari"),
                             ("read_attempts", 0)):
            data = self.config()
            data["source_access"][field] = value
            self.reject(data, f"source_access.{field}")
        data = self.config()
        data["locations"].update(onsite_regions=[], remote_countries=[])
        self.reject(data, "locations")

    def test_disabled_required_and_optional_sources(self):
        for source, field, value in (("calendar", "required", True), ("calendar", "connection_ref", "name"),
                                     ("calendar", "expected_identity", "fictional"), ("mail", "connection_ref", None),
                                     ("mail", "expected_identity", "")):
            with self.subTest(source=source, field=field):
                data = self.config()
                data["integrations"][source][field] = value
                self.reject(data, f"integrations.{source}")
        self.assertEqual(self.api.load_profile(self.package / "examples/sam.json")["integrations"]["calendar"],
                         {"enabled": True, "required": False, "connection_ref": "fictional-calendar-sam",
                          "expected_identity": "sam@example.invalid"})
        data = self.config()
        data["trackers"] = {}
        data["integrations"] = {}
        self.assertEqual(self.api.validate_profile(data, self.profile_path), data)

    def test_version_two_identity_can_be_unset_without_inventing_an_account(self):
        data = self.config()
        data["schema_version"] = 2
        data["identity"].update(account_identity=None, report_recipient=None)
        data["integrations"] = {}
        data["role_policy"].update(families=[], preferred_levels=[])
        data["locations"].update(onsite_regions=[], remote_countries=[], residency_region=None)
        self.assertEqual(self.api.validate_profile(data, self.profile_path), data)
        data["identity"]["account_identity"] = "not an email"
        self.reject(data, "identity.account_identity")
        data["identity"]["account_identity"] = None
        data["schema_version"] = 1
        self.reject(data, "identity.account_identity")

    def test_unknown_timezone_and_duplicate_columns(self):
        data = self.config()
        data["timezone"] = "Fictional/Nowhere"
        self.reject(data, "timezone")
        for key, value in (("index", 1), ("header", "Employer")):
            data = self.config()
            data["trackers"]["jobs"]["columns"]["title"][key] = value
            self.reject(data, "trackers.jobs.columns")

    def test_duplicate_json_keys_at_top_level_and_nested(self):
        raw = json.dumps(self.config())
        for modified in (raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'),
                         raw.replace('"display_name": "Alex Example"',
                                     '"display_name": "Alex Example", "display_name": "Alex Example"')):
            path = self.root / "duplicate.json"
            path.write_text(modified, encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaisesRegex(self.api.ProfileError, "JSON"):
                self.api.load_profile(path)
            result = self.cli(path)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_private_paths_and_symlinks_cannot_resolve_inside_package(self):
        alias = self.root / "alias"
        alias.symlink_to(self.package, target_is_directory=True)
        for target in (self.package, self.package / "nonexistent", alias / "README.md"):
            for field in ("state_root", "ref"):
                with self.subTest(target=target, field=field):
                    data = self.config()
                    if field == "state_root":
                        data["private"]["state_root"] = str(target)
                    else:
                        data["private"]["refs"]["facts"] = str(target)
                    self.reject(data, "private.")
        data = self.config()
        data["private"]["state_root"] = str(self.root)
        self.reject(data, "private.state_root")
        outside = self.root / "outside"
        outside.mkdir()
        (self.package / "external-link").symlink_to(outside, target_is_directory=True)
        data = self.config()
        data["private"]["state_root"] = str(self.package / "external-link" / "state")
        self.assertEqual(self.api.resolved_private_paths(data, self.profile_path)["state_root"], str(outside / "state"))

    def test_substitutions_urls_and_reserved_reference_are_rejected(self):
        for value in ("~/private", "$SYNTHETIC/state", "https://example.invalid/private"):
            data = self.config()
            data["private"]["state_root"] = value
            self.reject(data, "private.state_root")
        data = self.config()
        data["private"]["refs"]["state_root"] = "../../outside"
        self.reject(data, "private.refs")

    def test_malformed_configs_have_bounded_private_cli_errors(self):
        path = self.root / "broken.json"
        for content in (b"{", b"\xff", b"null", b"[]", b'{"private_marker":"SYNTHETIC_SECRET_MARKER"}'):
            with self.subTest(content=content):
                path.write_bytes(content)
                with self.assertRaises(self.api.ProfileError):
                    self.api.load_profile(path)
                result = self.cli(path)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertLess(len(result.stderr), 300)
                self.assertNotIn("SYNTHETIC_SECRET_MARKER", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(path.read_bytes(), content)
        with self.assertRaises(self.api.ProfileError):
            self.api.load_profile(self.root / "missing.json")

    def test_deeply_nested_malformed_json_is_a_profile_error(self):
        path = self.root / "deep.json"
        path.write_text("[" * 1200 + "0" + "]" * 1200, encoding="utf-8")
        with self.assertRaises(self.api.ProfileError):
            self.api.load_profile(path)
        result = self.cli(path)
        self.assertEqual(result.returncode, 2)
        self.assertLess(len(result.stderr), 300)
        self.assertNotIn("Traceback", result.stderr)

    def test_large_finite_integer_experience_is_valid_and_unchanged(self):
        data = self.config()
        data["role_policy"]["experience"]["max_required_years"] = 10 ** 400
        before = copy.deepcopy(data)
        self.assertEqual(self.api.validate_profile(data, self.profile_path), before)
        path = self.root / "large-number.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        original = path.read_bytes()
        self.assertEqual(self.api.load_profile(path), before)
        self.assertEqual(path.read_bytes(), original)
        result = self.cli(path)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_integer_parser_limit_failure_is_a_bounded_profile_error(self):
        limit = getattr(sys, "get_int_max_str_digits", lambda: 0)()
        if not limit:
            self.skipTest("Python runtime has no enabled integer parsing length limit")
        path = self.root / "parser-limit.json"
        content = '{"schema_version":' + "9" * max(5000, limit + 1) + "}"
        path.write_text(content, encoding="utf-8")
        with self.assertRaises(self.api.ProfileError):
            self.api.load_profile(path)
        result = self.cli(path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertLess(len(result.stderr), 300)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(path.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
