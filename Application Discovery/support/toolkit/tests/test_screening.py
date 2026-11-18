"""Independent policy checks; only fictional examples and captured text.

Expectations come from SCREENING.md, not from a generated decision inventory.
The receipt helper stands for independent semantic review of each explicit fixture;
these checks do not establish live reviewer/connector provenance.
"""
import copy
import json
from dataclasses import replace
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from contracts import ContractError, digest
from profile import validate_profile
from screening import ScreeningReview, screen


TOOLKIT = Path(__file__).resolve().parents[1]


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((TOOLKIT / "examples/alex.json").read_text())
        policy = self.profile["role_policy"]
        policy["families"] = ["backend", "full-stack", "applied AI"]
        policy["excluded_duties"] = ["pure research", "mobile-only", "database administration"]
        policy["excluded_levels"] = ["principal", "staff", "management"]
        policy["experience"]["max_required_years"] = 2
        policy["experience"]["senior_low_experience_exception"] = True
        validate_profile(self.profile, TOOLKIT / "examples/alex.json")
        self.packet = {
            "job_id": "fictional-match-42",
            "job_url": "https://simplify.jobs/matches/fictional-match-42",
            "as_of": "2026-10-06T12:00:00Z", "max_age_days": 2,
            "sources": [{"id": "role", "url": "https://simplify.jobs/matches/fictional-match-42",
                         "captured_at": "2026-10-06T10:00:00Z", "access": "full", "content": ""}],
            "facts": {"title": "Software Engineer II", "company": "Fictional Systems",
                      "common": [], "branches": []},
            "applicant": {"degrees": ["bachelor"], "degrees_complete": True,
                          "evidence_ref": "fictional-applicant-inventory"},
        }
        self.fact("families", "Build backend services.", ["backend"], plural=True)
        self.fact("primary_duties", "Develop service APIs using AWS, SQL and React.", ["service development"], plural=True)
        self.fact("level", "Intermediate individual contributor; no supervisory duties.", "intermediate")
        self.fact("employers", "Employer: Fictional Systems.", ["Fictional Systems"], plural=True)
        self.fact("availability", "This opening accepts applications.", "open")
        self.location("remote", country="United Kingdom", residency="allowed",
                      quote="Remote within the UK, including residents of London.")
        self.packet["facts"]["branches"] = [self.branch("general", "General qualifications:", [
            self.clause("At least 2 years of professional software experience.", 2)])]

    def quoted(self, quote, source="role"):
        next(s for s in self.packet["sources"] if s["id"] == source)["content"] += quote + "\n"
        return {"source": source, "quote": quote}

    def fact(self, name, quote, value, plural=False):
        self.packet["facts"][name] = {**self.quoted(quote), "values" if plural else "value": value}

    def clause(self, quote, minimum, maximum=None, required=True, kind="overall", resolved=False):
        return {**self.quoted(quote), "required": required, "kind": kind,
                "minimum": minimum, "maximum": maximum, "range_resolved": resolved}

    def branch(self, identity, quote, requirements, degree=None, condition="met"):
        return {"id": identity, **self.quoted(quote), "degree": degree,
                "other_condition": condition, "requirements": requirements}

    def location(self, mode, country=None, region=None, residency="unknown", quote="Location unknown."):
        self.packet["facts"]["location"] = {**self.quoted(quote), "mode": mode, "country": country,
                                            "region": region, "residency": residency}

    def review(self):
        return ScreeningReview(digest(self.profile), digest(self.packet), True, 0, "fictional-independent-review")

    def decide(self, expected):
        before = copy.deepcopy((self.profile, self.packet))
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            result = screen(self.profile, self.packet, self.review())
        self.assertEqual(result["decision"], expected)
        self.assertFalse(result["application_authorized"])
        self.assertEqual((self.profile, self.packet), before, "screening must preserve caller-owned input")
        return result

    def test_two_plus_qualifies_with_exact_simplify_link_without_ats(self):
        self.packet["facts"]["branches"][0]["requirements"] = [self.clause(
            "Qualifications:\r\n\tAt least 2 years of professional software experience.", 2)]
        result = self.decide("QUALIFY")
        self.assertEqual(result["required_years"], 2)
        self.assertEqual(result["priority"], "preferred")
        self.assertEqual(result["job_url"], "https://simplify.jobs/matches/fictional-match-42")
        self.assertEqual(result["applicable_branches"], ["general"])
        self.assertEqual(result["policy_version"], "example-v1")
        self.assertEqual(result["evidence_digest"], digest(self.packet))
        self.assertEqual(result["review_ref"], "fictional-independent-review")

    def test_mandatory_three_plus_and_three_to_five_exclude(self):
        for quote, maximum in [("3+ years of professional experience required.", None),
                               ("3-5 years of professional experience required.", 5)]:
            with self.subTest(quote=quote):
                self.packet["facts"]["branches"][0]["requirements"] = [self.clause(quote, 3, maximum)]
                self.decide("EXCLUDED")

    def test_mandatory_specialty_minimum_applies_and_preference_does_not(self):
        requirements = self.packet["facts"]["branches"][0]["requirements"]
        requirements.append(self.clause("3 years of Python experience required.", 3, kind="specialty"))
        self.decide("EXCLUDED")
        requirements[-1] = self.clause("3 years of Python experience preferred.", 3, required=False, kind="specialty")
        self.decide("QUALIFY")

    def test_five_preferred_years_do_not_raise_required_minimum(self):
        self.packet["facts"]["common"] = [self.clause("5 years of software experience preferred.", 5, required=False)]
        self.assertEqual(self.decide("QUALIFY")["required_years"], 2)

    def test_two_to_four_requires_explicit_resolution(self):
        requirements = self.packet["facts"]["branches"][0]["requirements"]
        requirements[:] = [self.clause("2-4 years of software experience required.", 2, 4)]
        self.decide("NEEDS_REVIEW")
        requirements[:] = [self.clause("2-4 years required; applicants with exactly 2 years satisfy this requirement.",
                                      2, 4, resolved=True)]
        self.decide("QUALIFY")

    def test_degree_alternatives_require_an_actually_held_degree(self):
        self.packet["facts"]["branches"] = [
            self.branch("bachelor", "Bachelor degree plus 3 years:", [self.clause("Bachelor branch: 3 years required.", 3)], "bachelor"),
            self.branch("master", "Master degree plus 1 year:", [self.clause("Master branch: 1 year required.", 1)], "master")]
        self.decide("EXCLUDED")
        self.packet["applicant"]["degrees_complete"] = False
        self.decide("NEEDS_REVIEW")
        self.packet["applicant"].update(degrees=["master"], degrees_complete=True)
        result = self.decide("QUALIFY")
        self.assertEqual(result["applicable_branches"], ["master"])
        self.assertEqual(result["required_years"], 1)

    def test_common_three_year_requirement_cannot_be_bypassed(self):
        self.packet["applicant"]["degrees"] = ["master"]
        self.packet["facts"]["common"] = [self.clause("All applicants must have 3 years of professional experience.", 3)]
        self.packet["facts"]["branches"] = [self.branch("master", "Master degree alternative:",
            [self.clause("Master applicants need 1 year of software experience.", 1)], "master")]
        self.decide("EXCLUDED")

    def test_missing_or_unknown_overall_minimum_needs_review(self):
        inventories = [[], [self.clause("Professional software experience required.", None)],
                       [self.clause("Up to 2 years of professional experience required.", None, 2)],
                       [self.clause("2 years of Python required.", 2, kind="specialty")]]
        for requirements in inventories:
            with self.subTest(requirements=requirements):
                self.packet["facts"]["branches"][0]["requirements"] = requirements
                self.decide("NEEDS_REVIEW")

    def test_explicit_no_prior_experience_qualifies(self):
        self.packet["facts"]["branches"][0]["requirements"] = [self.clause("No prior professional experience required.", 0)]
        self.assertEqual(self.decide("QUALIFY")["required_years"], 0)

    def test_opt_in_fully_read_unstated_years_preserves_unknown_without_tenure_guess(self):
        self.profile["role_policy"]["experience"]["unknown_minimum"] = "include"
        original = self.packet["facts"]["branches"][0]["requirements"][0]["quote"] + "\n"
        self.packet["sources"][0]["content"] = self.packet["sources"][0]["content"].replace(original, "")
        inventories = [[], [self.clause("Professional software experience required.", None)],
                       [self.clause("Up to 2 years of professional experience required.", None, 2)],
                       [self.clause("5 years of software experience preferred.", 5, required=False)]]
        for requirements in inventories:
            with self.subTest(requirements=requirements):
                self.packet["facts"]["branches"][0]["requirements"] = requirements
                result = self.decide("QUALIFY")
                self.assertIsNone(result["required_years"])
                self.assertEqual(result["priority"], "standard")
                self.assertEqual(set(self.packet["applicant"]), {"degrees", "degrees_complete", "evidence_ref"})
        self.packet["facts"]["branches"][0]["requirements"] = [self.clause("2 years of Python required.", 2, kind="specialty")]
        self.assertEqual(self.decide("QUALIFY")["required_years"], 2)

    def test_opt_in_ranges_use_lower_bound_without_changing_legacy_review(self):
        for quote, minimum, maximum in [("2–4 years required.", 2, 4),
                                        ("2–10+ years required.", 2, 10),
                                        ("1–3 years required.", 1, 3)]:
            with self.subTest(quote=quote):
                self.packet["facts"]["branches"][0]["requirements"] = [self.clause(quote, minimum, maximum)]
                self.profile["role_policy"]["experience"]["ambiguous_range"] = "review"
                self.decide("NEEDS_REVIEW")
                self.profile["role_policy"]["experience"]["ambiguous_range"] = "accept_lower_bound"
                self.assertEqual(self.decide("QUALIFY")["required_years"], minimum)

    def test_opt_ins_keep_mandatory_overall_specialty_and_degree_exclusions(self):
        self.profile["role_policy"]["experience"].update(unknown_minimum="include", ambiguous_range="accept_lower_bound")
        for kind in ("overall", "specialty"):
            for maximum in (None, 5):
                with self.subTest(kind=kind, maximum=maximum):
                    self.packet["facts"]["branches"][0]["requirements"] = [self.clause(
                        "Mandatory " + kind + " experience: 3 years minimum.", 3, maximum, kind=kind)]
                    self.decide("EXCLUDED")
        self.packet["facts"]["branches"] = [
            self.branch("bachelor", "Bachelor plus 3 years required:", [self.clause("Bachelor: 3 years required.", 3)], "bachelor"),
            self.branch("master", "Master plus 1 year required:", [self.clause("Master: 1 year required.", 1)], "master")]
        self.decide("EXCLUDED")
        self.packet["applicant"]["degrees_complete"] = False
        self.decide("NEEDS_REVIEW")
        self.packet["applicant"].update(degrees=["master"], degrees_complete=True)
        self.packet["facts"]["common"] = [self.clause("All applicants require 3 years of software experience.", 3)]
        self.decide("EXCLUDED")

    def test_opt_in_mixed_or_branches_select_known_minima_and_sort_unknown_safely(self):
        self.profile["role_policy"]["experience"]["unknown_minimum"] = "include"
        self.packet["facts"]["branches"] = [
            self.branch("unstated-z", "Equivalent practical software experience required:", []),
            self.branch("one", "One-year alternative:", [self.clause("1 year required.", 1)]),
            self.branch("two", "Two-year alternative:", [self.clause("2 years required.", 2)]),
            self.branch("too-high", "Experienced alternative:", [self.clause("3 years required.", 3)])]
        result = self.decide("QUALIFY")
        self.assertEqual(result["required_years"], 2)
        self.assertEqual(result["applicable_branches"], ["unstated-z", "one", "two"])
        self.packet["facts"]["branches"] = [self.packet["facts"]["branches"][0],
            self.branch("unstated-a", "Alternative practical qualifications:", [])]
        self.assertIsNone(self.decide("QUALIFY")["required_years"])

    def test_opt_in_unstated_senior_exception_is_lower_priority_and_levels_still_exclude(self):
        self.profile["role_policy"]["experience"]["unknown_minimum"] = "include"
        self.packet["facts"]["branches"][0]["requirements"] = []
        self.fact("level", "Senior individual contributor implementing backend services.", "senior")
        result = self.decide("QUALIFY")
        self.assertTrue(result["senior_exception"])
        self.assertEqual(result["priority"], "lower")
        self.assertIsNone(result["required_years"])
        self.profile["role_policy"]["experience"]["senior_low_experience_exception"] = False
        self.decide("EXCLUDED")
        self.profile["role_policy"]["experience"]["senior_low_experience_exception"] = True
        for level in ("principal", "staff", "management"):
            with self.subTest(level=level):
                self.fact("level", "Actual responsibility level: " + level + ".", level)
                self.decide("EXCLUDED")

    def test_opt_ins_preserve_full_inventory_review_quotes_and_residency_protections(self):
        self.profile["role_policy"]["experience"].update(unknown_minimum="include", ambiguous_range="accept_lower_bound")
        self.packet["facts"]["branches"][0]["requirements"] = []
        self.decide("QUALIFY")
        for access in ("unread", "partial"):
            self.packet["sources"][0]["access"] = access
            self.decide("UNVERIFIED")
        self.packet["sources"][0]["access"] = "full"
        for receipt in (None, replace(self.review(), complete_inventory=False),
                        replace(self.review(), unread_requirements=1)):
            self.assertEqual(screen(self.profile, self.packet, receipt)["decision"], "UNVERIFIED")
        receipt = self.review()
        self.profile["role_policy"]["version"] = "changed-policy"
        self.assertEqual(screen(self.profile, self.packet, receipt)["decision"], "UNVERIFIED")
        self.location("remote", country="United Kingdom", residency="unknown")
        self.decide("NEEDS_REVIEW")
        self.location("remote", country="United Kingdom", residency="excluded")
        self.decide("EXCLUDED")
        self.location("remote", country="United Kingdom", residency="allowed")
        self.packet["facts"]["branches"][0]["other_condition"] = "unknown"
        self.decide("NEEDS_REVIEW")
        self.packet["facts"]["branches"][0]["quote"] = "Uncaptured invented qualifications."
        with self.assertRaises(ContractError):
            screen(self.profile, self.packet, self.review())

    def test_unread_partial_stale_and_future_sources_are_unverified(self):
        source = self.packet["sources"][0]
        for access, captured in [("unread", "2026-10-06T10:00:00Z"), ("partial", "2026-10-06T10:00:00Z"),
                                 ("full", "2026-10-01T10:00:00Z"), ("full", "2026-10-07T10:00:00Z")]:
            with self.subTest(access=access, captured=captured):
                source.update(access=access, captured_at=captured)
                self.decide("UNVERIFIED")
        source.update(access="unread", captured_at="2026-10-06T10:00:00Z", content="")
        self.packet.update(facts=None, applicant=None)
        self.decide("UNVERIFIED")

    def test_full_description_ambiguity_is_review_not_unread(self):
        self.fact("families", "Responsibilities span several unspecified disciplines.", [], plural=True)
        self.decide("NEEDS_REVIEW")
        self.fact("families", "Build backend services.", ["backend"], plural=True)
        self.fact("level", "Responsibility level is not described.", "unknown")
        self.decide("NEEDS_REVIEW")

    def test_independent_review_is_required_and_bound_to_original_inputs(self):
        receipt = self.review()
        invalid = [None, receipt.__dict__, replace(receipt, complete_inventory=False),
                   replace(receipt, unread_requirements=1)]
        for review in invalid:
            with self.subTest(review=review):
                result = screen(self.profile, self.packet, review)
                self.assertEqual(result["decision"], "UNVERIFIED")
                self.assertFalse(result["application_authorized"])
        self.packet["sources"][0]["content"] += "Additional qualifications were captured.\n"
        self.assertEqual(screen(self.profile, self.packet, receipt)["decision"], "UNVERIFIED")
        receipt = self.review()
        self.profile["role_policy"]["experience"]["max_required_years"] = 1
        self.assertEqual(screen(self.profile, self.packet, receipt)["decision"], "UNVERIFIED")
        self.decide("EXCLUDED")

    def test_quotes_are_bound_to_their_named_captured_source(self):
        self.packet["sources"].append({"id": "other", "url": "https://example.invalid/other-role",
            "captured_at": "2026-10-06T10:00:00Z", "access": "full", "content": "An unrelated role."})
        self.packet["facts"]["level"]["source"] = "other"
        with self.assertRaises(ContractError):
            screen(self.profile, self.packet, self.review())
        self.packet["facts"]["level"]["source"] = "role"
        self.packet["facts"]["level"]["quote"] = "Invented qualification absent from the page."
        with self.assertRaises(ContractError):
            screen(self.profile, self.packet, self.review())
        self.packet["job_url"] = "https://simplify.jobs/matches/different-fictional-role"
        with self.assertRaises(ContractError):
            screen(self.profile, self.packet, self.review())

    def test_remote_country_requires_permitted_actual_residency(self):
        cases = [("United Kingdom", "unknown", "NEEDS_REVIEW"),
                 ("United Kingdom", "excluded", "EXCLUDED"),
                 ("France", "allowed", "EXCLUDED"), (None, "allowed", "NEEDS_REVIEW"),
                 ("United Kingdom", "allowed", "QUALIFY")]
        for country, residency, expected in cases:
            with self.subTest(country=country, residency=residency):
                self.location("remote", country=country, residency=residency,
                              quote=f"Fictional reviewed remote terms: country={country}, London residency={residency}.")
                self.decide(expected)

    def test_onsite_region_and_relocation_follow_profile(self):
        for mode in ("onsite", "hybrid"):
            with self.subTest(mode=mode):
                self.location(mode, region="London", quote=f"This role requires {mode} work in London.")
                self.decide("QUALIFY")
                self.location(mode, region="Paris", quote=f"This role requires {mode} work in Paris.")
                self.decide("EXCLUDED")
                self.profile["locations"]["allow_relocation"] = True
                self.decide("NEEDS_REVIEW")
                self.profile["locations"]["allow_relocation"] = False
        self.location("onsite", quote="Office attendance is required; office city is unspecified.")
        self.decide("NEEDS_REVIEW")

    def test_actual_employer_and_verified_owner_exclude_but_vendor_mentions_do_not(self):
        self.decide("QUALIFY")  # AWS/SQL/React in source text are ordinary tools.
        self.quoted("Our service interoperates with Fictional Excluded Ltd's SDK.")
        self.decide("QUALIFY")
        self.fact("employers", "Fictional Systems is owned by Fictional Excluded Ltd.",
                  ["Fictional Systems", "Fictional Excluded Ltd"], plural=True)
        self.decide("EXCLUDED")
        self.packet["facts"]["company"] = "Fictional Excluded Ltd"
        self.fact("employers", "Employer: Fictional Excluded Ltd.", ["Fictional Excluded Ltd"], plural=True)
        self.decide("EXCLUDED")

    def test_primary_duty_and_family_exclusions_are_enforced(self):
        for duty in ("pure research", "mobile-only", "database administration"):
            with self.subTest(duty=duty):
                self.fact("primary_duties", f"The primary work is {duty}.", [duty], plural=True)
                self.decide("EXCLUDED")
        self.fact("primary_duties", "Develop service APIs.", ["service development"], plural=True)
        self.fact("families", "Primary work is graphic design.", ["graphic design"], plural=True)
        self.decide("EXCLUDED")
        for family in ("backend", "full-stack", "applied AI"):
            with self.subTest(family=family):
                self.fact("families", f"Primary work is {family} engineering.", [family], plural=True)
                self.decide("QUALIFY")

    def test_real_level_exclusions_and_numbered_mts_titles(self):
        for level in ("principal", "staff", "management"):
            with self.subTest(level=level):
                self.fact("level", f"Actual responsibility level: {level}.", level)
                self.decide("EXCLUDED")
        self.fact("level", "Intermediate individual contributor scope.", "intermediate")
        for title in ("Software Engineer III", "Member of Technical Staff"):
            with self.subTest(title=title):
                self.packet["facts"]["title"] = title
                self.quoted(title)
                self.decide("QUALIFY")
        self.packet["facts"]["title"] = "Software Engineer III"
        self.packet["facts"]["branches"][0]["requirements"] = []
        self.decide("NEEDS_REVIEW")  # The III title does not supply an experience clause.

    def test_senior_exception_needs_every_mandatory_clause_to_pass(self):
        self.fact("level", "Senior individual contributor with service implementation duties.", "Senior")
        result = self.decide("QUALIFY")
        self.assertTrue(result["senior_exception"])
        self.assertEqual(result["priority"], "lower")
        self.packet["facts"]["common"] = [self.clause("3 years of database experience required.", 3, kind="specialty")]
        self.decide("EXCLUDED")
        self.packet["facts"]["common"] = []
        self.packet["facts"]["branches"][0]["requirements"] = []
        self.decide("NEEDS_REVIEW")
        self.packet["facts"]["branches"][0]["requirements"] = [self.clause("2 years required.", 2)]
        self.profile["role_policy"]["experience"]["senior_low_experience_exception"] = False
        self.decide("EXCLUDED")

    def test_configured_preferred_senior_level_is_not_a_lower_priority_exception(self):
        self.profile["role_policy"]["preferred_levels"] = ["senior individual contributor"]
        self.profile["role_policy"]["experience"]["senior_low_experience_exception"] = False
        self.fact("level", "Senior individual contributor implementing backend services.", "senior individual contributor")
        result = self.decide("QUALIFY")
        self.assertFalse(result["senior_exception"])
        self.assertEqual(result["priority"], "preferred")

    def test_other_mandatory_conditions_and_a_passing_or_alternative(self):
        branch = self.packet["facts"]["branches"][0]
        branch["other_condition"] = "unknown"
        self.decide("NEEDS_REVIEW")
        branch["other_condition"] = "unmet"
        self.decide("EXCLUDED")
        self.packet["facts"]["branches"].append(self.branch("alternative", "Alternative qualifications:",
            [self.clause("Alternative applicants require 2 years of professional experience.", 2)]))
        self.assertEqual(self.decide("QUALIFY")["applicable_branches"], ["alternative"])

    def test_explicit_closed_vs_unknown_availability_and_input_preservation(self):
        self.fact("availability", "This role is closed and no longer accepts applications.", "closed")
        self.decide("CLOSED")
        self.fact("availability", "Generic missing page; role availability could not be established.", "unknown")
        self.decide("UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
