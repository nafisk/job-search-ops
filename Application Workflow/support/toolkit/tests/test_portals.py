"""offline acceptance checks using fictional employers and host receipts.

Receipts model independent trusted host review; this suite does not prove source
provenance, live filters, pagination, or current discovery coverage. No private
registry, account, employer evidence, or network service is accessed.
Run: python3 -B -m unittest discover -s tests -p test_portals.py -v
"""
import copy
from dataclasses import asdict, replace
from pathlib import Path
import unittest
from unittest.mock import patch

from contracts import ContractError, digest
from portals import SearchValidation, prepare_search, validate_registry


NOW = "2026-10-06T13:00:00Z"
ENTRY = "https://careers.example.invalid/search?location=Fictional+City&role=software"
TERMINAL = ENTRY + "&start=100&page=5&pid=fictional-selected-job"


def registry():
    return {
        "schema_version": 1, "profile_id": "fictional-profile",
        "scope_evidence": ["fictional/scope.json#/employers"],
        "companies": [{
            "company_id": "fictional-north", "employer_name": "Fictional North",
            "referral_hold": True, "scope_refs": ["fictional/scope.json#/employers/0"],
            "watchlist_rows": [7],
            "official_urls": [{"url": "https://careers.example.invalid/",
                               "evidence_ref": "fictional/watchlist.json#/rows/7"}],
            "historical_evidence": {"portal_family": "fictional-board",
                                    "source_date": "2026-09-01", "terminal_url": TERMINAL,
                                    "successor": None, "historical_count": 125},
            "searches": [{"search_id": "fictional-city-software", "label": "City software",
                          "observed_urls": [TERMINAL],
                          "evidence_refs": ["fictional/observation.json#/searches/0"],
                          "details": {"location_label": "Fictional City", "remote": None,
                                      "terminal": True, "selected_job": "fictional-selected-job",
                                      "hazards": ["Saved terminal page is historical only"]}}],
        }],
    }


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"profile_id": "fictional-profile", "role_policy": {"version": "fictional-v1"}}
        self.registry = registry()
        self.company = self.registry["companies"][0]
        self.search = self.company["searches"][0]

    def receipt(self, **changes):
        # ENTRY is observed in the current host review, not inferred from TERMINAL.
        good = SearchValidation(digest(self.profile), digest(self.company),
                                self.search["search_id"], ENTRY, NOW, True, True, True,
                                "fictional/current-review.json#/entry-and-pagination")
        return replace(good, **changes)

    def prepare(self, proof=None, **changes):
        args = {"as_of": NOW, "max_age_days": 1, "proof": proof}
        args.update(changes)
        return prepare_search(self.profile, self.registry, self.company["company_id"],
                              self.search["search_id"], **args)

    def assert_needs_validation(self, result):
        self.assertEqual(result["status"], "needs_validation")
        self.assertIsNone(result["entry_url"])
        self.assertTrue(result["reasons"])
        self.assertIs(result["discovery_complete"], False)
        self.assertIs(result["referral_hold"], True)

    def test_employer_and_search_identities_must_be_unique(self):
        for identity in ("company_id", "employer_name"):
            data = registry()
            other = copy.deepcopy(data["companies"][0])
            other.update(company_id="fictional-south", employer_name="Fictional South")
            other[identity] = data["companies"][0][identity]
            if identity == "employer_name":
                other[identity] = other[identity].upper()
            data["companies"].append(other)
            with self.subTest(identity=identity), self.assertRaises(ContractError):
                validate_registry(data)
        data = registry()
        data["companies"][0]["searches"].append(copy.deepcopy(data["companies"][0]["searches"][0]))
        with self.assertRaisesRegex(ContractError, "search IDs.*duplicates"):
            validate_registry(data)

    def test_explicit_holds_evidence_fields_and_version_are_required(self):
        changes = (
            ("root", "schema_version", 2), ("root", "schema_version", True),
            ("root", "scope_evidence", []), ("root", "invented", "value"),
            ("company", "referral_hold", None), ("company", "referral_hold", 1),
            ("company", "scope_refs", []), ("company", "watchlist_rows", [True]),
            ("company", "invented", "value"), ("search", "evidence_refs", []),
            ("search", "invented", "value"),
        )
        for level, key, value in changes:
            data = registry()
            target = {"root": data, "company": data["companies"][0],
                      "search": data["companies"][0]["searches"][0]}[level]
            target[key] = value
            with self.subTest(level=level, key=key, value=value), self.assertRaises(ContractError):
                validate_registry(data)
        data = registry()
        data["companies"][0]["official_urls"][0]["evidence_ref"] = ""
        with self.assertRaises(ContractError):
            validate_registry(data)
        for field in ("company_id", "employer_name", "referral_hold"):
            data = registry()
            del data["companies"][0][field]
            with self.subTest(missing_company_field=field), self.assertRaises(ContractError):
                validate_registry(data)
        for level in ("company", "search", "official_url"):
            for malformed in ({}, None, "malformed", []):
                data = registry()
                if level == "company":
                    data["companies"] = [malformed]
                elif level == "search":
                    data["companies"][0]["searches"] = [malformed]
                else:
                    data["companies"][0]["official_urls"] = [malformed]
                with self.subTest(level=level, malformed=malformed), self.assertRaises(ContractError):
                    validate_registry(data)
        for url in ("javascript:alert(1)", "http://careers.example.invalid/", "https://user@careers.example.invalid/"):
            data = registry()
            data["companies"][0]["searches"][0]["observed_urls"] = [url]
            with self.subTest(url=url), self.assertRaises(ContractError):
                validate_registry(data)

    def test_separate_employers_sharing_portal_and_watchlist_row_are_preserved(self):
        other = copy.deepcopy(self.company)
        other.update(company_id="fictional-south", employer_name="Fictional South", referral_hold=False)
        other["scope_refs"] = ["fictional/scope.json#/employers/1"]
        self.registry["companies"].append(other)
        result = validate_registry(self.registry)
        self.assertEqual([c["company_id"] for c in result["companies"]],
                         ["fictional-north", "fictional-south"])
        self.assertEqual([c["referral_hold"] for c in result["companies"]], [True, False])
        self.assertEqual(result["companies"][0]["watchlist_rows"], result["companies"][1]["watchlist_rows"])
        self.assertEqual(result["companies"][0]["official_urls"], result["companies"][1]["official_urls"])
        # Search IDs are namespaced by company, so a shared ID is intentional.
        self.assertEqual(result["companies"][0]["searches"][0]["search_id"],
                         result["companies"][1]["searches"][0]["search_id"])

    def test_historical_terminal_pagination_selected_job_and_unknown_url_never_grant_readiness(self):
        for urls in ([TERMINAL], [ENTRY + "&page=5"], [ENTRY + "&pid=fictional-selected-job"], [], [ENTRY]):
            self.search["observed_urls"] = urls
            with self.subTest(urls=urls):
                self.assert_needs_validation(self.prepare())

    def test_dictionary_and_mismatched_profile_company_search_receipts_are_rejected(self):
        good = self.receipt()
        for bad in (asdict(good), replace(good, profile_digest="wrong-profile"),
                    replace(good, company_digest="wrong-company"), replace(good, search_id="another-search")):
            with self.subTest(proof=bad):
                self.assert_needs_validation(self.prepare(bad))
        self.profile["role_policy"]["version"] = "fictional-v2"
        self.assert_needs_validation(self.prepare(good))
        self.profile["role_policy"]["version"] = "fictional-v1"
        self.company["historical_evidence"]["new_source"] = "fictional/new.json"
        self.assert_needs_validation(self.prepare(good))
        self.registry["profile_id"] = "another-profile"
        with self.assertRaisesRegex(ContractError, "another profile"):
            self.prepare()

    def test_freshness_requires_current_nonfuture_receipt_and_finite_nonnegative_age(self):
        for date in ("2026-10-05T12:59:59Z", "2026-10-06T13:00:01Z"):
            with self.subTest(date=date):
                self.assert_needs_validation(self.prepare(self.receipt(checked_at=date)))
        self.assertEqual(self.prepare(self.receipt(checked_at="2026-10-05T13:00:00Z"))["status"], "ready")
        for age in (-1, True, float("nan"), float("inf")):
            with self.subTest(age=age), self.assertRaises(ContractError):
                self.prepare(self.receipt(), max_age_days=age)

    def test_verification_flags_require_actual_boolean_true(self):
        for field in ("first_page_verified", "filters_verified", "pagination_verified"):
            with self.subTest(field=field, value=False):
                self.assert_needs_validation(self.prepare(self.receipt(**{field: False})))
            for value in (1, "true", [], None):
                with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                    self.prepare(self.receipt(**{field: value}))

    def test_exact_current_observed_entry_accepted_with_hold_and_no_discovery_claim(self):
        proof = self.receipt()
        result = self.prepare(proof)
        self.assertEqual(result, {"status": "ready", "company_id": "fictional-north",
                                 "search_id": "fictional-city-software", "entry_url": ENTRY,
                                 "reasons": [], "referral_hold": True, "discovery_complete": False})
        self.assertEqual(self.search["observed_urls"], [TERMINAL])
        for url in ("http://careers.example.invalid/", "https://user:password@careers.example.invalid/"):
            with self.subTest(url=url), self.assertRaises(ContractError):
                self.prepare(replace(proof, entry_url=url))

    def test_inputs_preserved_copied_and_no_file_network_process_effects(self):
        proof = self.receipt()
        before = copy.deepcopy((self.profile, self.registry, proof))
        with patch("builtins.open", side_effect=AssertionError("file effect")) as files, \
             patch("socket.socket", side_effect=AssertionError("network effect")) as network, \
             patch("subprocess.run", side_effect=AssertionError("process effect")) as process, \
             patch.object(Path, "write_text", side_effect=AssertionError("write effect")) as writes:
            copied = validate_registry(self.registry)
            self.prepare(proof)
            self.prepare()
            with self.assertRaises(ContractError):
                self.prepare(replace(proof, filters_verified=1))
            for effect in (files, network, process, writes):
                effect.assert_not_called()
        self.assertEqual((self.profile, self.registry, proof), before)
        copied["companies"][0]["searches"][0]["details"]["hazards"].append("copy-only")
        self.assertEqual((self.profile, self.registry, proof), before)

    def test_only_finite_json_metadata_is_accepted_and_unknowns_preserved(self):
        metadata = {"null": None, "text": "unknown", "integer": 7, "fraction": 0.5,
                    "boolean": False, "nested": [{"unresolved": None}]}
        self.company["historical_evidence"] = copy.deepcopy(metadata)
        self.search["details"] = copy.deepcopy(metadata)
        self.assertEqual(validate_registry(self.registry), self.registry)
        for value in (float("nan"), float("inf"), float("-inf"), object(), {"unsupported"},
                      ("tuple",), {1: "integer key"}):
            for field in ("historical_evidence", "details"):
                data = registry()
                target = data["companies"][0] if field == "historical_evidence" else data["companies"][0]["searches"][0]
                target[field]["bad"] = value
                with self.subTest(field=field, value=type(value).__name__), self.assertRaises(ContractError):
                    validate_registry(data)


if __name__ == "__main__":
    unittest.main()
