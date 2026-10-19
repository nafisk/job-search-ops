"""Independent exact application union and submission-evidence tests."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from applications import SubmissionAcceptance, application_key, reconcile
from contracts import ContractError


PROFILE = "fictional-applicant"
NOW = "2026-10-06T14:00:00Z"
SEEN = "2026-10-06T12:00:00Z"
REVIEWED = "2026-10-06T13:00:00Z"
SUBMITTED = "2026-10-05T15:00:00Z"


def fingerprint(value):
    # ponytail: independent contract digest, no model-created expected decisions.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def key(company="example-co", role="ats:123", profile=PROFILE):
    return fingerprint([profile, company, role])


def record(event_id, origin="sheet", company="example-co", role="ats:123",
           requisition="REQ-123", ref="APP-123", payload=None):
    return {"event_id": event_id, "origin": origin, "source_item_id": event_id + ":source",
            "observed_at": SEEN, "employer_id": company, "role_id": role,
            "requisition_id": requisition, "application_ref": ref,
            "evidence_refs": ["fictional-source#" + event_id],
            "payload": deepcopy(payload) if payload is not None else {"title": "Software Engineer II", "status": "unverified"}}


def packet(*sources, profile=PROFILE):
    return {"schema_version": 1, "profile_id": profile, "as_of": NOW, "sources": list(sources)}


def receipt(event, role="ats:123", company="example-co", basis="exact_role", kind="email_receipt", full=True,
            profile=PROFILE, submitted=SUBMITTED, reviewed=REVIEWED, evidence="fictional-reviewed-source"):
    return SubmissionAcceptance(profile, event["event_id"], fingerprint(event), key(company, role, profile),
                                basis, kind, submitted, reviewed, evidence, full)


class ApplicationTests(unittest.TestCase):
    def test_key_binds_profile_employer_and_exact_role(self):
        self.assertEqual(application_key(PROFILE, "example-co", "ats:123"), key())
        self.assertNotEqual(key(), key("other-co"))
        self.assertNotEqual(key(), key(role="ats:124"))
        self.assertNotEqual(key(), key(profile="another-profile"))

    def test_union_all_five_origins_preserves_complete_source_history(self):
        sources = [record("sheet", "sheet", payload={"manual_status": "Applied", "notes": "preserve me"}),
                   record("manual", "manual_history", payload={"user_note": "application history"}),
                   record("batch", "batch_manifest", payload={"tab_state": "closed", "reservation": "old-slot"}),
                   record("association", "unresolved_association", payload={"old_association": "still not a receipt"}),
                   record("mail", "correspondence", payload={"full_body": "Application-related correspondence"})]
        result = reconcile(packet(*sources))
        self.assertEqual(len(result["applications"]), 1)
        app = result["applications"][0]
        self.assertEqual(app["application_key"], key())
        self.assertEqual(set(app["origins"]), {"sheet", "manual_history", "batch_manifest", "unresolved_association", "correspondence"})
        self.assertEqual({x["event_id"] for x in result["source_events"]}, {x["event_id"] for x in sources})
        self.assertEqual({x["event_id"]: x for x in result["source_events"]}, {x["event_id"]: x for x in sources})
        self.assertEqual(app["confirmation_status"], "unconfirmed")
        self.assertEqual(app["submission_facts"], [])
        self.assertEqual(result["proposals"], [])
        self.assertIs(result["operational_complete"], False)

    def test_one_exact_role_receipt_updates_only_its_application(self):
        first = record("first")
        second = record("second", role="ats:456", requisition="REQ-456", ref="APP-456")
        mail = record("receipt", "correspondence", payload={"full_body": "Application received for REQ-123"})
        result = reconcile(packet(first, second, mail), {"receipt": receipt(mail)})
        apps = {x["application_key"]: x for x in result["applications"]}
        self.assertEqual(apps[key()]["confirmation_status"], "confirmed")
        self.assertEqual(len(apps[key()]["submission_facts"]), 1)
        self.assertEqual(apps[key(role="ats:456")]["confirmation_status"], "unconfirmed")
        self.assertEqual(apps[key(role="ats:456")]["submission_facts"], [])
        self.assertEqual(len(result["proposals"]), 1)

    def test_generic_same_employer_receipt_cannot_confirm_two_roles(self):
        first = record("first")
        second = record("second", role="ats:456", requisition="REQ-456", ref="APP-456")
        mail = record("generic", "correspondence", role=None, requisition=None, ref=None,
                      payload={"full_body": "Thank you for applying to Example", "title": "Software Engineer II"})
        result = reconcile(packet(first, second, mail))
        self.assertTrue(all(x["confirmation_status"] == "unconfirmed" for x in result["applications"]))
        self.assertEqual(result["proposals"], [])
        self.assertIn("generic", {x["source_event"]["event_id"] for x in result["unresolved"]})
        for role in ["ats:123", "ats:456"]:
            result = reconcile(packet(first, second, mail), {"generic": receipt(mail, role=role)})
            self.assertEqual(result["proposals"], [])

    def test_generic_even_single_known_role_does_not_gain_exact_identity(self):
        mail = record("generic", "correspondence", role=None, requisition=None, ref=None,
                      payload={"full_body": "Your application was received"})
        result = reconcile(packet(record("known"), mail))
        self.assertEqual(result["proposals"], [])
        self.assertEqual(result["applications"][0]["confirmation_status"], "unconfirmed")
        self.assertTrue(result["unresolved"])

    def test_new_unmatched_exact_role_correspondence_remains_unresolved(self):
        mail = record("new-role", "correspondence", role="ats:brand-new", requisition="REQ-NEW", ref="APP-NEW")
        result = reconcile(packet(record("known"), mail), {"new-role": receipt(mail, role="ats:brand-new")})
        self.assertEqual(len(result["applications"]), 1)
        self.assertEqual(result["applications"][0]["application_key"], key())
        self.assertEqual(result["proposals"], [])
        self.assertIn("new-role", {x["source_event"]["event_id"] for x in result["unresolved"]})

    def test_unresolved_association_cannot_register_unknown_application(self):
        association = record("new-association", "unresolved_association", role="ats:unknown", requisition="REQ-NEW", ref="APP-NEW")
        result = reconcile(packet(association))
        self.assertEqual(result["applications"], [])
        self.assertEqual(result["proposals"], [])
        self.assertEqual(result["unresolved"][0]["source_event"], association)

    def test_exact_requisition_associates_only_unique_employer_bound_role(self):
        mail = record("req-only", "correspondence", role=None, ref=None)
        result = reconcile(packet(record("known"), mail), {"req-only": receipt(mail, basis="exact_requisition")})
        self.assertEqual(result["applications"][0]["confirmation_status"], "confirmed")
        self.assertEqual(len(result["proposals"]), 1)
        wrong = record("wrong-employer", "correspondence", company="other-co", role=None, ref=None)
        result = reconcile(packet(record("known"), wrong), {"wrong-employer": receipt(wrong, basis="exact_requisition")})
        self.assertEqual(result["proposals"], [])
        self.assertTrue(result["unresolved"])

    def test_exact_application_reference_requires_employer_and_unique_binding(self):
        mail = record("ref-only", "correspondence", role=None, requisition=None)
        result = reconcile(packet(record("known"), mail), {"ref-only": receipt(mail, basis="exact_application_ref")})
        self.assertEqual(len(result["proposals"]), 1)
        wrong = record("wrong-ref", "correspondence", company="other-co", role=None, requisition=None)
        result = reconcile(packet(record("known"), wrong), {"wrong-ref": receipt(wrong, basis="exact_application_ref")})
        self.assertEqual(result["proposals"], [])
        self.assertTrue(result["unresolved"])

    def test_same_title_with_no_exact_id_is_not_a_match(self):
        known = record("known", payload={"title": "Software Engineer II"})
        other = record("other", role="ats:456", requisition="REQ-456", ref="APP-456", payload={"title": "Software Engineer II"})
        mail = record("title-only", "correspondence", role=None, requisition=None, ref=None,
                      payload={"title": "Software Engineer II", "application_date": SUBMITTED})
        result = reconcile(packet(known, other, mail))
        self.assertEqual(result["proposals"], [])
        self.assertTrue(result["unresolved"])

    def test_tabs_sheet_applied_and_legacy_assumptions_never_confirm_submission(self):
        for origin, body in [
                ("batch_manifest", {"tab_state": "opened", "form_status": "prepared"}),
                ("batch_manifest", {"tab_state": "closed", "assumed_submitted": True}),
                ("sheet", {"Application Status": "Applied"}),
                ("manual_history", {"legacy_submission_assumption": True})]:
            source = record("legacy", origin, payload=body)
            with self.subTest(origin=origin, body=body):
                result = reconcile(packet(source))
                self.assertEqual(result["applications"][0]["confirmation_status"], "unconfirmed")
                self.assertEqual(result["proposals"], [])

    def test_trusted_explicit_user_report_can_confirm_exact_manual_role(self):
        manual = record("manual", "manual_history", payload={"user_statement": "I submitted this exact role"})
        result = reconcile(packet(manual), {"manual": receipt(manual, kind="user_report")})
        self.assertEqual(result["applications"][0]["confirmation_status"], "confirmed")
        self.assertEqual(len(result["proposals"]), 1)

    def test_same_event_replay_deduplicates_without_duplicate_submission_fact(self):
        known = record("known")
        mail = record("receipt", "correspondence")
        result = reconcile(packet(known, deepcopy(known), mail, deepcopy(mail)), {"receipt": receipt(mail)})
        self.assertEqual(len(result["source_events"]), 2)
        self.assertEqual(len(result["applications"]), 1)
        self.assertEqual(len(result["applications"][0]["submission_facts"]), 1)
        self.assertEqual(len(result["proposals"]), 1)
        self.assertEqual(result, reconcile(packet(mail, known), {"receipt": receipt(mail)}))

    def test_changed_event_id_and_new_event_id_for_same_source_item_rejected(self):
        first = record("same-event")
        changed = deepcopy(first); changed["payload"]["title"] = "Different role body"
        with self.assertRaises(ContractError):
            reconcile(packet(first, changed))
        alias = deepcopy(first); alias["event_id"] = "new-event-same-source"
        with self.assertRaises(ContractError):
            reconcile(packet(first, alias))

    def test_requisition_collision_surfaces_and_blocks_submission_proposals(self):
        first = record("first")
        other = record("other", role="ats:456", requisition="REQ-123", ref="APP-456")
        mail = record("ambiguous", "correspondence", role=None, ref=None)
        result = reconcile(packet(first, other, mail), {"ambiguous": receipt(mail, basis="exact_requisition")})
        self.assertTrue(result["conflicts"])
        self.assertEqual(len(result["applications"]), 2)
        self.assertEqual(result["proposals"], [])
        self.assertTrue(result["unresolved"])

    def test_same_employer_requisition_collision_is_proactive_and_blocks_exact_role_receipt(self):
        first = record("first")
        other = record("other", role="ats:456", requisition="REQ-123", ref="APP-456")
        baseline = reconcile(packet(first, other))
        self.assertTrue(baseline["conflicts"])
        affected = {k for conflict in baseline["conflicts"] for k in conflict["application_keys"]}
        self.assertEqual(affected, {key(), key(role="ats:456")})
        mail = record("exact-role-receipt", "correspondence", role="ats:456", requisition="REQ-123", ref="APP-456")
        result = reconcile(packet(first, other, mail), {mail["event_id"]: receipt(mail, role="ats:456")})
        self.assertEqual(result["proposals"], [])

    def test_same_requisition_in_different_employers_remains_separate(self):
        first = record("first")
        other = record("other", company="another-co", role="ats:456", requisition="REQ-123", ref="APP-456")
        result = reconcile(packet(first, other))
        self.assertEqual(len(result["applications"]), 2)
        self.assertEqual(result["conflicts"], [])

    def test_unknown_capture_and_submission_dates_are_not_fabricated(self):
        manual = record("manual", "manual_history", payload={"legacy_date": "2026-09-19", "explicit_report": "submitted"})
        manual["observed_at"] = None
        result = reconcile(packet(manual), {"manual": receipt(manual, kind="user_report", submitted=None)})
        fact = result["applications"][0]["submission_facts"][0]
        self.assertIsNone(fact["observed_at"])
        self.assertIsNone(fact["submission_at"])
        self.assertEqual(result["source_events"][0]["payload"]["legacy_date"], "2026-09-19")
        self.assertEqual(fact["reviewed_at"], REVIEWED)

    def test_independently_exact_role_can_match_receipt_without_requisition(self):
        known = record("known", requisition=None, ref=None)
        mail = record("exact-independent", "correspondence", role=None, requisition=None, ref=None,
                      payload={"full_body": "Receipt for the exact engineer position", "official_role_url": "https://jobs.example.test/123"})
        proof = receipt(mail, basis="independent_exact_role", evidence="independent-official-role-and-full-receipt-proof")
        result = reconcile(packet(known, mail), {mail["event_id"]: proof})
        self.assertEqual(result["applications"][0]["confirmation_status"], "confirmed")
        self.assertEqual(len(result["proposals"]), 1)
        self.assertEqual(result["proposals"][0]["fact"]["match_basis"], "independent_exact_role")

    def test_conflicting_baseline_req_and_reference_does_not_invent_third_application(self):
        first = record("first")
        other = record("other", role="ats:456", requisition="REQ-456", ref="APP-456")
        conflict = record("conflicting-manual", "manual_history", role=None, requisition="REQ-123", ref="APP-456")
        result = reconcile(packet(first, other, conflict))
        self.assertEqual({x["application_key"] for x in result["applications"]}, {key(), key(role="ats:456")})
        self.assertIn("conflicting-manual", {x["source_event"]["event_id"] for x in result["unresolved"]})
        self.assertTrue(result["conflicts"])
        self.assertEqual(result["proposals"], [])

    def test_baseline_exact_requisition_merges_to_unique_registered_role(self):
        known = record("known")
        manual = record("manual-req-only", "manual_history", role=None, ref=None)
        result = reconcile(packet(known, manual))
        self.assertEqual(len(result["applications"]), 1)
        self.assertEqual(result["applications"][0]["application_key"], key())
        self.assertEqual({x["event_id"] for x in result["applications"][0]["source_events"]}, {"known", "manual-req-only"})

    def test_new_baseline_requisition_without_conflict_creates_exact_target(self):
        manual = record("manual-req-only", "manual_history", role=None, requisition="REQ-NEW", ref=None)
        result = reconcile(packet(manual))
        self.assertEqual(len(result["applications"]), 1)
        self.assertEqual(result["applications"][0]["role_id"], "requisition:REQ-NEW")
        self.assertEqual(result["applications"][0]["confirmation_status"], "unconfirmed")
        self.assertEqual(result["proposals"], [])

    def test_independently_reviewed_confirmation_page_can_confirm_exact_role(self):
        page = record("confirmation-page", "batch_manifest", payload={"complete_page": "Application received for the exact role"})
        result = reconcile(packet(page), {"confirmation-page": receipt(page, kind="confirmation_page")})
        self.assertEqual(len(result["proposals"]), 1)
        self.assertEqual(result["applications"][0]["confirmation_status"], "confirmed")

    def test_application_reference_collision_surfaces(self):
        first = record("first")
        other = record("other", role="ats:456", requisition="REQ-456", ref="APP-123")
        mail = record("ambiguous-ref", "correspondence", role=None, requisition=None)
        result = reconcile(packet(first, other, mail), {"ambiguous-ref": receipt(mail, basis="exact_application_ref")})
        self.assertTrue(result["conflicts"])
        self.assertEqual(result["proposals"], [])

    def test_source_and_acceptance_disagreement_cannot_cross_role(self):
        mail = record("receipt", "correspondence")
        result = reconcile(packet(record("first"), record("second", role="ats:456", requisition="REQ-456", ref="APP-456"), mail),
                           {"receipt": receipt(mail, role="ats:456")})
        self.assertEqual(result["proposals"], [])
        self.assertTrue(result["unresolved"])

    def test_untrusted_wrong_profile_changed_source_and_incomplete_receipts_denied(self):
        known, mail = record("known"), record("receipt", "correspondence")
        valid = receipt(mail)
        wrong_digest = SubmissionAcceptance(PROFILE, mail["event_id"], "wrong", key(), "exact_role",
                                            "email_receipt", SUBMITTED, REVIEWED, "proof", True)
        variants = [valid.__dict__, receipt(mail, profile="other-profile"), receipt(mail, full=False), wrong_digest]
        for proof in variants:
            with self.subTest(proof=proof):
                try:
                    result = reconcile(packet(known, mail), {"receipt": proof})
                except ContractError:
                    continue
                self.assertEqual(result["proposals"], [])
                self.assertEqual(result["applications"][0]["confirmation_status"], "unconfirmed")

    def test_invalid_evidence_kind_and_future_acceptance_denied(self):
        known, mail = record("known"), record("receipt", "correspondence")
        for proof in [receipt(mail, kind="tab_closed"), receipt(mail, reviewed="2026-10-07T13:00:00Z"),
                      receipt(mail, submitted="2026-10-07T13:00:00Z"), receipt(mail, evidence="")]:
            with self.subTest(proof=proof):
                try:
                    result = reconcile(packet(known, mail), {"receipt": proof})
                except ContractError:
                    continue
                self.assertEqual(result["proposals"], [])

    def test_finite_payload_and_timestamps_are_validated(self):
        for value in [float("nan"), float("inf"), {1: "bad-key"}, {"set"}]:
            bad = record("bad"); bad["payload"]["bad"] = value
            with self.subTest(value=repr(value)), self.assertRaises(ContractError):
                reconcile(packet(bad))
        for date in ["2026-10-07T12:00:00Z", "2026-10-06T12:00:00", "invalid"]:
            bad = record("bad"); bad["observed_at"] = date
            with self.subTest(date=date), self.assertRaises(ContractError):
                reconcile(packet(bad))

    def test_unknown_shape_origin_and_missing_evidence_denied(self):
        for field, value in [("origin", "tab_state"), ("evidence_refs", []), ("employer_id", "")]:
            bad = record("bad"); bad[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                reconcile(packet(bad))
        bad = record("bad"); bad["profile_id"] = "foreign-profile"
        with self.assertRaises(ContractError):
            reconcile(packet(bad))

    def test_profile_separation_and_detached_immutable_history(self):
        sources = [record("known"), record("mail", "correspondence")]
        payload = packet(*sources); original = deepcopy(payload)
        result = reconcile(payload, {"mail": receipt(sources[1])})
        self.assertEqual(payload, original)
        result["source_events"][0]["payload"]["title"] = "edited output"
        self.assertEqual(payload, original)
        other = reconcile(packet(record("known"), profile="different-profile"))
        self.assertEqual(other["applications"][0]["application_key"], key(profile="different-profile"))
        self.assertNotEqual(other["applications"][0]["application_key"], key())

    def test_pure_reconciliation_has_no_file_network_or_checkpoint_effect(self):
        with patch("builtins.open", side_effect=AssertionError("file effect")), \
             patch("socket.socket", side_effect=AssertionError("network effect")):
            result = reconcile(packet(record("known")))
        self.assertIs(result["operational_complete"], False)
        self.assertNotIn("checkpoint", result)
        self.assertNotIn("writes", result)


if __name__ == "__main__":
    unittest.main()
