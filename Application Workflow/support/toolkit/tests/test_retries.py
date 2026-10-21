"""Independent budget and completion checks using fictional finite scopes."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from contracts import ContractError, digest
from retries import (CompletionAcceptance, LedgerHead, RecoveryApproval, RetryOwner,
                     begin_recovery_pass, completion_status, finish_attempt, new_ledger,
                     reserve_attempt, resume_ledger, validate_ledger)


PROFILE = "fictional-profile"
COORDINATOR = "fictional-owner"
PASS = "pass-1"
NOW = "2026-10-06T14:00:00Z"
START = "2026-10-06T12:00:00Z"
READ = NOW
FINISH = NOW


def source(item="page-1", source_id="example-board"):
    # ponytail: fixed finite fixtures; expected budgets/decisions are declared in tests.
    return {"source_id": source_id, "item_id": item,
            "cursor": {"page": 1, "url": "https://jobs.example.test/search?query=software&page=1"}}


def fresh():
    return new_ledger(PROFILE, PASS, COORDINATOR, started_at=START, as_of=NOW)


def owner(pass_id=PASS):
    return RetryOwner(PROFILE, COORDINATOR, pass_id)


def reserve(ledger, attempt, unit=None, worker="worker-a", method="background", pass_owner=None):
    return reserve_attempt(ledger, pass_owner or owner(), unit or source(),
                           attempt_id=attempt, worker_id=worker, method=method,
                           reserved_at=READ, as_of=NOW)


def finish(ledger, attempt, outcome="failed", pass_owner=None):
    return finish_attempt(ledger, pass_owner or owner(), attempt, outcome=outcome,
                          evidence_refs=["fictional-read#" + attempt], finished_at=FINISH, as_of=NOW)


def accepted(scope, ledger):
    return CompletionAcceptance(PROFILE, ledger["active_pass_id"], digest(scope),
                                frozenset(digest([u["source_id"], u["item_id"]]) for u in scope["page_items"]),
                                frozenset(scope["current_candidate_ids"]), "fictional-verification", "fictional-commit")


class RetryTests(unittest.TestCase):
    def denied_completion(self, ledger, scope, acceptance=None):
        try:
            result = completion_status(ledger, scope, as_of=NOW, acceptance=acceptance)
        except ContractError:
            return
        self.assertIs(result["operational_complete"], False)
        self.assertEqual(result["status"], "incomplete")

    def test_three_attempts_shared_across_workers_and_methods(self):
        ledger = fresh()
        for number, (worker, method) in enumerate([
                ("worker-a", "background"), ("worker-b", "builtin-browser"),
                ("coordinator", "reload")], 1):
            ledger = finish(reserve(ledger, f"attempt-{number}", worker=worker, method=method), f"attempt-{number}")
        self.assertEqual(len(ledger["passes"][0]["attempts"]), 3)
        with self.assertRaises(ContractError):
            reserve(ledger, "attempt-4", worker="new-worker", method="new-tab")

    def test_pending_interrupted_reservations_consume_all_three_slots(self):
        ledger = fresh()
        for number in range(1, 4):
            ledger = reserve(ledger, f"reserved-{number}")
        self.assertTrue(all(a["result"] is None for a in ledger["passes"][0]["attempts"]))
        with self.assertRaises(ContractError):
            reserve(ledger, "fourth-after-interruption")
        head = LedgerHead(PROFILE, COORDINATOR, PASS, digest(ledger))
        resumed = resume_ledger(deepcopy(ledger), head, as_of=NOW)
        self.assertEqual(resumed, ledger)
        with self.assertRaises(ContractError):
            reserve(resumed, "fourth-after-resume", worker="another-worker", method="browser")

    def test_exact_source_cursor_is_preserved_and_rebinding_is_rejected(self):
        unit = source()
        ledger = reserve(fresh(), "attempt-1", unit)
        self.assertEqual(ledger["passes"][0]["attempts"][0]["source"], unit)
        changed = deepcopy(unit)
        changed["cursor"]["page"] = 2
        with self.assertRaises(ContractError):
            reserve(ledger, "attempt-2", changed)
        resumed = resume_ledger(ledger, LedgerHead(PROFILE, COORDINATOR, PASS, digest(ledger)), as_of=NOW)
        result = completion_status(resumed, {"page_items": [unit], "current_candidate_ids": []}, as_of=NOW)
        self.assertEqual(result["unresolved_cursors"], [unit])
        self.assertIs(result["operational_complete"], False)

    def test_independent_source_item_remains_runnable_after_exhaustion(self):
        ledger = fresh()
        for n in range(3):
            ledger = finish(reserve(ledger, f"a-{n}"), f"a-{n}", "inaccessible")
        other = source("page-2")
        ledger = finish(reserve(ledger, "independent", other), "independent", "read")
        scope = {"page_items": [source(), other], "current_candidate_ids": []}
        result = completion_status(ledger, scope, as_of=NOW, acceptance=accepted(scope, ledger))
        self.assertIs(result["operational_complete"], False)
        self.assertIn(source(), result["unresolved_cursors"])
        self.assertEqual(len(result["exhausted_items"]), 1)

    def test_budget_binds_source_and_item_not_only_item_name(self):
        ledger = fresh()
        for n in range(3):
            ledger = reserve(ledger, f"first-{n}")
        different_source = source(source_id="different-board")
        ledger = reserve(ledger, "different-board-read", different_source)
        self.assertEqual(len(ledger["passes"][0]["attempts"]), 4)

    def test_untrusted_or_mismatched_owner_denied(self):
        variants = [None, {"profile_id": PROFILE, "coordinator_id": COORDINATOR, "pass_id": PASS},
                    RetryOwner("other-profile", COORDINATOR, PASS),
                    RetryOwner(PROFILE, "other-owner", PASS), RetryOwner(PROFILE, COORDINATOR, "other-pass")]
        for claim in variants:
            with self.subTest(owner=claim), self.assertRaises(ContractError):
                reserve_attempt(fresh(), claim, source(), attempt_id="a", worker_id="w",
                                method="background", reserved_at=READ, as_of=NOW)

    def test_resume_requires_authoritative_exact_head(self):
        ledger = reserve(fresh(), "a")
        head = LedgerHead(PROFILE, COORDINATOR, PASS, digest(ledger))
        altered = deepcopy(ledger)
        altered["passes"][0]["attempts"] = []
        with self.assertRaises(ContractError):
            resume_ledger(altered, head, as_of=NOW)
        for bad in [None, {"ledger_digest": digest(ledger)}, LedgerHead(PROFILE, "wrong", PASS, digest(ledger))]:
            with self.subTest(head=bad), self.assertRaises(ContractError):
                resume_ledger(ledger, bad, as_of=NOW)

    def test_recovery_requires_current_bound_trusted_approval(self):
        ledger = reserve(fresh(), "a")
        valid = RecoveryApproval(PROFILE, COORDINATOR, PASS, digest(ledger), "pass-2", FINISH, "human:recovery")
        variants = [None, valid.__dict__,
                    RecoveryApproval(PROFILE, COORDINATOR, PASS, "wrong-digest", "pass-2", FINISH, "human:recovery"),
                    RecoveryApproval("other", COORDINATOR, PASS, digest(ledger), "pass-2", FINISH, "human:recovery"),
                    RecoveryApproval(PROFILE, COORDINATOR, "other-pass", digest(ledger), "pass-2", FINISH, "human:recovery"),
                    RecoveryApproval(PROFILE, COORDINATOR, PASS, digest(ledger), PASS, FINISH, "human:recovery")]
        for claim in variants:
            with self.subTest(approval=claim), self.assertRaises(ContractError):
                begin_recovery_pass(ledger, owner(), claim, as_of=NOW)

    def test_authorized_new_recovery_pass_retains_every_old_attempt(self):
        ledger = fresh()
        for n in range(3):
            ledger = reserve(ledger, f"old-{n}")
        before = deepcopy(ledger)
        approval = RecoveryApproval(PROFILE, COORDINATOR, PASS, digest(ledger), "pass-2", FINISH, "human:recovery")
        recovered = begin_recovery_pass(ledger, owner(), approval, as_of=NOW)
        self.assertEqual(recovered["passes"][0], before["passes"][0])
        self.assertEqual(ledger, before)
        self.assertEqual(recovered["active_pass_id"], "pass-2")
        recovered = reserve(recovered, "new-pass-first", pass_owner=owner("pass-2"))
        self.assertEqual(len(recovered["passes"][1]["attempts"]), 1)
        with self.assertRaises(ContractError):
            reserve(recovered, "stale-owner", pass_owner=owner())

    def test_old_pass_read_is_not_current_pass_completion(self):
        ledger = finish(reserve(fresh(), "old-read"), "old-read", "read")
        approval = RecoveryApproval(PROFILE, COORDINATOR, PASS, digest(ledger), "pass-2", FINISH, "human:recovery")
        ledger = begin_recovery_pass(ledger, owner(), approval, as_of=NOW)
        scope = {"page_items": [source()], "current_candidate_ids": []}
        self.denied_completion(ledger, scope, accepted(scope, ledger))

    def test_finite_scope_requires_read_and_trusted_verification_commit(self):
        ledger = finish(reserve(fresh(), "read"), "read", "read")
        scope = {"page_items": [source()], "current_candidate_ids": []}
        self.denied_completion(ledger, scope)
        receipt = accepted(scope, ledger)
        self.denied_completion(ledger, scope, receipt.__dict__)
        result = completion_status(ledger, scope, as_of=NOW, acceptance=receipt)
        self.assertIs(result["operational_complete"], True)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["gaps"], [])

    def test_current_unread_candidate_cannot_be_hidden_by_page_success(self):
        ledger = finish(reserve(fresh(), "read-page"), "read-page", "read")
        scope = {"page_items": [source()], "current_candidate_ids": ["ats:new-unread-role"]}
        receipt = CompletionAcceptance(PROFILE, PASS, digest(scope), accepted(scope, ledger).page_keys,
                                       frozenset(), "verification", "commit")
        self.denied_completion(ledger, scope, receipt)
        for unknown in ("human_review", "historical_backlog"):
            bad_scope = deepcopy(scope)
            bad_scope[unknown] = ["ats:new-unread-role"]
            with self.subTest(route=unknown), self.assertRaises(ContractError):
                completion_status(ledger, bad_scope, as_of=NOW, acceptance=receipt)

    def test_completion_receipt_binding_is_exact_and_nonempty(self):
        ledger = finish(reserve(fresh(), "read"), "read", "read")
        scope = {"page_items": [source()], "current_candidate_ids": ["ats:role"]}
        base = accepted(scope, ledger)
        variants = [CompletionAcceptance("other", PASS, digest(scope), base.page_keys, base.resolved_candidate_ids, "v", "c"),
                    CompletionAcceptance(PROFILE, "other", digest(scope), base.page_keys, base.resolved_candidate_ids, "v", "c"),
                    CompletionAcceptance(PROFILE, PASS, "wrong-scope", base.page_keys, base.resolved_candidate_ids, "v", "c"),
                    CompletionAcceptance(PROFILE, PASS, digest(scope), frozenset(), base.resolved_candidate_ids, "v", "c"),
                    CompletionAcceptance(PROFILE, PASS, digest(scope), base.page_keys, frozenset(), "v", "c"),
                    CompletionAcceptance(PROFILE, PASS, digest(scope), base.page_keys, base.resolved_candidate_ids, "", "c"),
                    CompletionAcceptance(PROFILE, PASS, digest(scope), base.page_keys, base.resolved_candidate_ids, "v", "")]
        for receipt in variants:
            with self.subTest(receipt=receipt):
                self.denied_completion(ledger, scope, receipt)

    def test_inaccessible_failed_invalid_are_never_no_match_or_complete(self):
        scope = {"page_items": [source()], "current_candidate_ids": []}
        for outcome in ["failed", "inaccessible", "invalid"]:
            ledger = finish(reserve(fresh(), "a"), "a", outcome)
            with self.subTest(outcome=outcome):
                self.denied_completion(ledger, scope, accepted(scope, ledger))
        for bad in ["no_match", "closed", "complete", "human_review", "historical"]:
            with self.subTest(outcome=bad), self.assertRaises(ContractError):
                finish(reserve(fresh(), "a"), "a", bad)

    def test_usable_read_stops_same_operation_retries(self):
        ledger = finish(reserve(fresh(), "usable"), "usable", "read")
        with self.assertRaises(ContractError):
            reserve(ledger, "unnecessary-retry", worker="different-worker", method="builtin-browser")

    def test_later_pending_or_failed_reservation_cannot_hide_behind_earlier_read(self):
        ledger = reserve(reserve(fresh(), "first"), "later-pending")
        ledger = finish(ledger, "first", "read")
        scope = {"page_items": [source()], "current_candidate_ids": []}
        self.denied_completion(ledger, scope, accepted(scope, ledger))
        ledger = finish(ledger, "later-pending", "inaccessible")
        self.denied_completion(ledger, scope, accepted(scope, ledger))

    def test_saved_fourth_attempt_duplicate_id_and_rebinding_rejected(self):
        ledger = fresh()
        for n in range(3):
            ledger = reserve(ledger, f"a-{n}")
        bad = deepcopy(ledger)
        fourth = deepcopy(bad["passes"][0]["attempts"][0]); fourth["attempt_id"] = "fourth"
        bad["passes"][0]["attempts"].append(fourth)
        duplicate = deepcopy(ledger); duplicate["passes"][0]["attempts"][1]["attempt_id"] = "a-0"
        rebound = deepcopy(ledger); rebound["passes"][0]["attempts"][1]["source"]["cursor"]["page"] = 999
        for state in [bad, duplicate, rebound]:
            with self.subTest(state=state), self.assertRaises(ContractError):
                validate_ledger(state, as_of=NOW)

    def test_finish_is_one_shot_and_requires_original_reservation(self):
        ledger = finish(reserve(fresh(), "a"), "a")
        with self.assertRaises(ContractError):
            finish(ledger, "a", "read")
        with self.assertRaises(ContractError):
            finish(ledger, "not-reserved", "read")
        with self.assertRaises(ContractError):
            finish_attempt(reserve(fresh(), "pending"), owner(), "pending", outcome="read",
                           evidence_refs=[], finished_at=FINISH, as_of=NOW)

    def test_malformed_saved_state_and_time_rejected(self):
        ledger = reserve(fresh(), "a")
        variants = []
        for field, val in [("active_pass_id", "missing"), ("schema_version", True), ("passes", []), ("profile_id", "")]:
            bad = deepcopy(ledger); bad[field] = val; variants.append(bad)
        bad = deepcopy(ledger); bad["unexpected"] = True; variants.append(bad)
        bad = deepcopy(ledger); bad["passes"][0]["attempts"][0]["reserved_at"] = "2026-10-07T12:00:00Z"; variants.append(bad)
        bad = deepcopy(ledger); bad["passes"][0]["started_at"] = "2026-10-06T12:00:00"; variants.append(bad)
        for bad in variants:
            with self.subTest(state=bad), self.assertRaises(ContractError):
                validate_ledger(bad, as_of=NOW)
        with self.assertRaises(ContractError):
            reserve_attempt(fresh(), owner(), source(), attempt_id="future", worker_id="worker", method="background",
                            reserved_at="2026-10-07T12:00:00Z", as_of=NOW)

    def test_opaque_json_cursors_are_inert_and_preserved(self):
        for cursor in [None, "opaque-token:page-two", ["page", 2, None], 7, True,
                       {"url": "https://jobs.example.test/role/123", "post": {"query": "software", "offset": 20}}]:
            unit = source(); unit["cursor"] = cursor
            with self.subTest(cursor=cursor):
                ledger = reserve(fresh(), "a", unit)
                head = LedgerHead(PROFILE, COORDINATOR, PASS, digest(ledger))
                resumed = resume_ledger(ledger, head, as_of=NOW)
                self.assertEqual(resumed["passes"][0]["attempts"][0]["source"]["cursor"], cursor)
                self.assertEqual(resumed, ledger)

    def test_saved_recovery_chain_cannot_rebind_prior_history(self):
        ledger = reserve(fresh(), "old")
        approval = RecoveryApproval(PROFILE, COORDINATOR, PASS, digest(ledger), "pass-2", FINISH, "human:recovery")
        recovered = begin_recovery_pass(ledger, owner(), approval, as_of=NOW)
        for field, value in [("prior_pass_id", "another-pass"), ("prior_ledger_digest", "invented-hash"),
                             ("profile_id", "other-profile"), ("new_pass_id", "pass-3")]:
            changed = deepcopy(recovered)
            changed["passes"][1]["recovery"][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_ledger(changed, as_of=NOW)
        changed = deepcopy(recovered)
        changed["passes"][0]["attempts"][0]["worker_id"] = "rewritten-old-worker"
        with self.assertRaises(ContractError):
            validate_ledger(changed, as_of=NOW)

    def test_nonfinite_or_nonjson_cursor_rejected(self):
        for value in [float("nan"), float("inf"), {1: "bad-key"}, {"set"}]:
            bad = source(); bad["cursor"]["invalid"] = value
            with self.subTest(value=repr(value)), self.assertRaises(ContractError):
                reserve(fresh(), "a", bad)

    def test_duplicate_or_empty_scope_not_a_completion_shortcut(self):
        for scope in [{"page_items": [], "current_candidate_ids": []},
                      {"page_items": [source(), source()], "current_candidate_ids": []},
                      {"page_items": [source()], "current_candidate_ids": ["same", "same"]}]:
            with self.subTest(scope=scope), self.assertRaises(ContractError):
                completion_status(fresh(), scope, as_of=NOW)

    def test_inputs_not_mutated_outputs_not_shared_and_replay_deterministic(self):
        ledger = fresh(); unit = source(); before = deepcopy((ledger, unit))
        first = reserve(ledger, "a", unit); second = reserve(ledger, "a", unit)
        self.assertEqual(first, second)
        self.assertEqual((ledger, unit), before)
        first["passes"][0]["attempts"][0]["source"]["cursor"]["page"] = 99
        self.assertEqual((ledger, unit), before)
        read = finish(second, "a", "read"); snapshot = deepcopy(read)
        scope = {"page_items": [unit], "current_candidate_ids": []}
        receipt = accepted(scope, read)
        completion_status(read, scope, as_of=NOW, acceptance=receipt)
        self.assertEqual(read, snapshot)

    def test_pure_helpers_do_not_read_files_or_open_network(self):
        with patch("builtins.open", side_effect=AssertionError("file effect")), \
             patch("socket.socket", side_effect=AssertionError("network effect")):
            ledger = finish(reserve(fresh(), "a"), "a", "read")
            validate_ledger(ledger, as_of=NOW)
            scope = {"page_items": [source()], "current_candidate_ids": []}
            completion_status(ledger, scope, as_of=NOW, acceptance=accepted(scope, ledger))


if __name__ == "__main__":
    unittest.main()
