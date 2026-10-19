"""Fictional, offline acceptance checks for read-only email alert extraction."""
import base64
from copy import deepcopy
from datetime import datetime
import unittest
from urllib.parse import urlencode
import zlib

from alerts import CardReview, collect, extract, posting
from contracts import ContractError, digest


START = "2026-10-01T00:00:00+00:00"
END = "2026-10-02T00:00:00+00:00"
MATCH = "11111111-2222-3333-4444-555555555555"
OTHER_MATCH = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def html(*ids):
    cards = "".join(f'<a href="https://www.linkedin.com/jobs/view/{job}/?tracking=fictional">View job</a>' for job in ids)
    return f"<html><body>LinkedIn job alert {cards} Unsubscribe</body></html>"


def plain(*ids):
    cards = "\n".join(f"View job: https://www.linkedin.com/jobs/view/{job}/" for job in ids)
    return f"LinkedIn job alert\n{cards}\nUnsubscribe"


def message(mid="m1", content=None, *, mime="text/html", at=START, thread="thread-1"):
    content = html("101") if content is None else content
    encoded = base64.urlsafe_b64encode(content.encode()).decode().rstrip("=")
    return {"id": mid, "threadId": thread, "internalDate": str(int(datetime.fromisoformat(at).timestamp() * 1000)),
            "payload": {"mimeType": mime, "body": {"data": encoded}}}


def review(raw, *ids, unresolved=0, non_alert=False):
    # Inventory is stated by the fixture author independently of parser results.
    return CardReview(raw["id"], digest(raw), frozenset(ids), unresolved, non_alert, "fictional:card-inventory")


def scope():
    return {"profile_id": "fictional-profile", "start": START, "end": END, "max_attempts": 3,
            "queries": [{"id": "labeled", "query": "label:fictional-applications"},
                        {"id": "alerts", "query": "fictional-linkedin-alerts"}]}


def page(*ids, next_token=None, complete=True):
    return {"complete": complete, "message_ids": list(ids), "next_page_token": next_token,
            "evidence_ref": "fictional:page"}


def tracking(payload):
    token = base64.urlsafe_b64encode(zlib.compress(payload.encode())).decode().rstrip("=")
    return "https://email.matches.simplify.jobs/c/" + token + ".fictional-recipient"


class Adapter:
    """Only the two permitted read calls exist; fixtures never contact an account."""
    def __init__(self, pages, messages):
        self.pages, self.messages = pages, messages
        self.page_calls, self.message_calls = [], []

    def list_messages(self, query, start, end, token):
        self.page_calls.append((query, start, end, token))
        value = self.pages[(query, token)]
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)

    def read_message(self, mid):
        self.message_calls.append(mid)
        value = self.messages[mid]
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)


class AlertsTests(unittest.TestCase):
    def test_attempt_limit_rejects_more_than_three_boolean_and_nonpositive_before_reads(self):
        for limit in (4, 100, True, False, 0, -1):
            frozen = scope()
            frozen["max_attempts"] = limit
            adapter = Adapter({}, {})
            with self.subTest(max_attempts=limit), self.assertRaises(ContractError):
                collect(adapter, frozen)
            self.assertEqual(adapter.page_calls, [])
            self.assertEqual(adapter.message_calls, [])

    def test_three_failed_local_attempts_remain_charged_on_saved_state_replay(self):
        frozen = scope()
        frozen["queries"] = [{"id": "only-query", "query": "fictional-failing-query"}]
        adapter = Adapter({("fictional-failing-query", None): RuntimeError("fictional failure")}, {})
        first = collect(adapter, frozen)
        self.assertEqual(len(adapter.page_calls), 3)
        self.assertEqual(list(first["next_state"]["attempts"].values()), [3])
        self.assertEqual(list(first["next_state"]["errors"].values()), ["RuntimeError"])
        saved = deepcopy(first["next_state"])
        second = collect(adapter, frozen, first["next_state"])
        self.assertEqual(len(adapter.page_calls), 3)
        self.assertEqual(second["next_state"], saved)
        self.assertEqual(first["next_state"], saved)
        self.assertEqual(second["unresolved_cursors"], first["unresolved_cursors"])
        self.assertEqual(second["status"], "incomplete")

    def test_same_native_query_under_different_labels_cannot_reset_local_budget(self):
        frozen = scope()
        frozen["queries"] = [{"id": "worker-label-one", "query": "same-fictional-query"},
                             {"id": "worker-label-two", "query": "same-fictional-query"}]
        adapter = Adapter({}, {})
        with self.assertRaises(ContractError):
            collect(adapter, frozen)
        self.assertEqual(adapter.page_calls, [])
        self.assertEqual(adapter.message_calls, [])

    def test_all_frozen_queries_paginate_union_and_replay_without_reads(self):
        inventory = {"m1": "101", "m2": "102", "m3": "103"}
        raws = {mid: message(mid, html(job)) for mid, job in inventory.items()}
        reviews = {mid: review(raw, "linkedin:" + inventory[mid]) for mid, raw in raws.items()}
        adapter = Adapter({("label:fictional-applications", None): page("m1", next_token="second"),
                           ("label:fictional-applications", "second"): page("m2"),
                           ("fictional-linkedin-alerts", None): page("m2", "m3")}, raws)
        result = collect(adapter, scope(), reviews=reviews)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["counts"], {"message_ids": 3, "read_messages": 3, "sightings": 3, "unique_jobs": 3})
        self.assertEqual(adapter.message_calls, ["m1", "m2", "m3"])
        self.assertEqual([call[3] for call in adapter.page_calls], [None, "second", None])
        self.assertTrue(all(call[1:3] == (START, END) for call in adapter.page_calls))
        again = collect(adapter, scope(), result["next_state"], reviews)
        self.assertEqual(again["sightings"], result["sightings"])
        self.assertEqual(len(adapter.page_calls), 3)
        self.assertEqual(len(adapter.message_calls), 3)

    def test_same_thread_messages_remain_distinct_sightings(self):
        raws = {mid: message(mid) for mid in ("m1", "m2")}
        adapter = Adapter({("label:fictional-applications", None): page("m1", "m2"),
                           ("fictional-linkedin-alerts", None): page("m1")}, raws)
        result = collect(adapter, scope(), reviews={mid: review(raw, "linkedin:101") for mid, raw in raws.items()})
        self.assertEqual(result["counts"]["unique_jobs"], 1)
        self.assertEqual({s["id"] for s in result["sightings"]}, {"email:m1:linkedin:101", "email:m2:linkedin:101"})

    def test_repeated_anchors_and_connector_mime_variants_collapse(self):
        raw = message()
        raw["payload"] = {"mime_type": "multipart/alternative", "parts": [
            {"mime_type": "text/html", "body": {"content": html("101", "101", "102").replace(
                ">View job</a>", '><img alt="Fictional engineer"></a>', 1)}},
            {"mime_type": "text/plain", "body": {"content": plain("101", "102")}}]}
        result = extract(raw, review(raw, "linkedin:101", "linkedin:102"))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["jobs"]), 2)
        self.assertEqual(result["jobs"][0]["occurrences"], 3)
        self.assertEqual(result["jobs"][0]["parts"], [0, 1])
        self.assertEqual(result["jobs"][0]["job_url"], "https://www.linkedin.com/jobs/view/101/")

    def test_card_review_must_have_type_message_identity_and_current_body(self):
        raw = message()
        changed = deepcopy(raw)
        changed["threadId"] = "different-body-envelope"
        candidates = [None, {"message_id": "m1", "body_digest": digest(raw)},
                      CardReview("m2", digest(raw), frozenset({"linkedin:101"}), 0, False, "fictional:other"),
                      review(changed, "linkedin:101")]
        for candidate in candidates:
            with self.subTest(review=candidate):
                result = extract(raw, candidate)
                self.assertEqual(result["status"], "incomplete")
                self.assertIn("Independent full-message card inventory required", result["gaps"])

    def test_review_mismatch_missing_secondary_and_unresolved_cards_block_completion(self):
        raw = message(content=html("101", "102"))
        for candidate in [review(raw, "linkedin:101"), review(raw, "linkedin:101", "linkedin:102", unresolved=1),
                          review(raw, "linkedin:101", "linkedin:102", non_alert=True)]:
            with self.subTest(review=candidate):
                result = extract(raw, candidate)
                self.assertEqual(result["status"], "incomplete")
                self.assertIn("Independent card inventory is unresolved or disagrees", result["gaps"])

    def test_unknown_layout_or_footer_remains_incomplete_with_matching_inventory(self):
        for content in ['<html><a href="https://www.linkedin.com/jobs/view/101/">View job</a>Unsubscribe</html>',
                        html("101").replace("Unsubscribe", ""),
                        html("101").replace("Unsubscribe", '<a href="https://fictional.example/redirect">View job</a> Unsubscribe')]:
            with self.subTest(content=content):
                raw = message(content=content)
                self.assertEqual(extract(raw, review(raw, "linkedin:101"))["status"], "incomplete")

    def test_truncated_missing_and_unclosed_source_cannot_complete(self):
        for content in [html("101").replace("</html>", ""), html("101") + "[message clipped]",
                        '<html>LinkedIn job alert <a href="https://www.linkedin.com/jobs/view/101/">View job Unsubscribe</html>',
                        '<html>LinkedIn job alert <a>Engineer</a> Unsubscribe</html>']:
            with self.subTest(content=content):
                raw = message(content=content)
                self.assertEqual(extract(raw, review(raw, "linkedin:101"))["status"], "incomplete")

    def test_conflicting_html_plaintext_identity_sets_remain_incomplete(self):
        raw = message()
        raw["payload"] = {"mimeType": "multipart/alternative", "parts": [
            message(content=html("101"))["payload"], message(content=plain("102"), mime="text/plain")["payload"]]}
        result = extract(raw, review(raw, "linkedin:101", "linkedin:102"))
        self.assertIn("MIME representations disagree on job identities", result["gaps"])

    def test_plaintext_readable_card_is_complete_and_blank_card_is_not(self):
        raw = message(content=plain("101"), mime="text/plain")
        self.assertEqual(extract(raw, review(raw, "linkedin:101"))["status"], "complete")
        for missing in ["View job: ", "View job: [redacted]", "View job:\n"]:
            with self.subTest(missing=missing):
                raw = message(content=plain("101") + "\n" + missing, mime="text/plain")
                self.assertIn("Apparent job card lacks a readable URL", extract(raw, review(raw, "linkedin:101"))["gaps"])

    def test_known_source_identities_preserve_simplify_match(self):
        self.assertEqual(posting("https://www.linkedin.com/comm/jobs/view/123/?tracking=x")[0], "linkedin:123")
        self.assertEqual(posting("https://simplify.jobs/matches?viewMatch=" + MATCH + "&recipient=fictional"),
                         ("simplify:" + MATCH, "https://simplify.jobs/matches?viewMatch=" + MATCH))
        self.assertEqual(posting("https://simplify.jobs/p/" + OTHER_MATCH + "/fictional-role?tracking=x")[0], "simplify:" + OTHER_MATCH)
        self.assertIsNone(posting("https://fictional.example/jobs/123"))

    def test_local_simplify_tracking_decoder_extracts_without_recipient_tokens(self):
        wrapped = tracking(urlencode({"l": "https://simplify.jobs/matches?viewMatch=" + MATCH + "&recipient=fictional-secret", "r": "fictional-token"}))
        raw = message(content=f'<html>Simplify job matches <a href="{wrapped}">View job</a> Unsubscribe</html>')
        result = extract(raw, review(raw, "simplify:" + MATCH))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["jobs"][0]["job_url"], "https://simplify.jobs/matches?viewMatch=" + MATCH)
        self.assertNotIn("fictional-token", str(result))
        self.assertNotIn("fictional-secret", str(result))

    def test_local_tracking_decoder_rejects_bounds_invalid_and_ambiguous_payloads(self):
        target = "https://simplify.jobs/matches?viewMatch=" + MATCH
        bad = ["https://email.matches.simplify.jobs/c/" + "a" * 8193,
               tracking(urlencode({"l": target, "padding": "x" * 65536})),
               tracking(urlencode([("l", target), ("l", target)])), tracking("r=fictional"),
               tracking(urlencode({"l": "https://email.matches.simplify.jobs/c/abc"})),
               tracking(urlencode({"l": "javascript:fictional"})), "https://email.matches.simplify.jobs/c/%%%%"]
        packed = zlib.compress(urlencode({"l": target}).encode())[:-2]
        bad.append("https://email.matches.simplify.jobs/c/" + base64.urlsafe_b64encode(packed).decode().rstrip("="))
        for wrapped in bad:
            with self.subTest(length=len(wrapped)):
                with self.assertRaises((ValueError, zlib.error)):
                    posting(wrapped)
                raw = message(content=f'<html>Simplify job matches <a href="{wrapped}">View job</a> Unsubscribe</html>')
                result = extract(raw, review(raw))
                self.assertEqual(result["status"], "incomplete")
                self.assertNotIn(wrapped, str(result))

    def test_failed_page_preserves_budget_and_other_query_continues(self):
        raws = {mid: message(mid) for mid in ("m0", "m1")}
        reviews = {mid: review(raw, "linkedin:101") for mid, raw in raws.items()}
        adapter = Adapter({("label:fictional-applications", None): page("m0", next_token="failed-page"),
                           ("label:fictional-applications", "failed-page"): RuntimeError("fictional-private-marker"),
                           ("fictional-linkedin-alerts", None): page("m1")}, raws)
        first = collect(adapter, scope(), reviews=reviews)
        self.assertEqual(first["status"], "incomplete")
        self.assertEqual(first["counts"]["sightings"], 2)
        self.assertEqual(len(adapter.page_calls), 5)
        self.assertEqual(first["unresolved_cursors"], [{"query_id": "labeled", "page_token": "failed-page",
                                                       "reason": "Read attempts exhausted"}])
        self.assertNotIn("fictional-private-marker", str(first))
        replay = collect(adapter, scope(), first["next_state"], reviews)
        self.assertEqual(replay["unresolved_cursors"], first["unresolved_cursors"])
        self.assertEqual(len(adapter.page_calls), 5)
        self.assertEqual(adapter.message_calls, ["m0", "m1"])

    def test_wrong_message_id_exhausts_three_attempts_without_blocking_other_message(self):
        raw = message("good")
        adapter = Adapter({("label:fictional-applications", None): page("bad", "good"),
                           ("fictional-linkedin-alerts", None): page()}, {"bad": message("wrong"), "good": raw})
        result = collect(adapter, scope(), reviews={"good": review(raw, "linkedin:101")})
        self.assertEqual(adapter.message_calls.count("bad"), 3)
        self.assertEqual(adapter.message_calls.count("good"), 1)
        self.assertEqual(result["counts"]["sightings"], 1)
        self.assertEqual(result["next_state"]["attempts"]["message:bad"], 3)
        adapter.messages["bad"] = message("bad")
        again = collect(adapter, scope(), result["next_state"])
        self.assertEqual(adapter.message_calls.count("bad"), 3)
        self.assertEqual(again["status"], "incomplete")

    def test_truncated_transport_reads_are_bounded_and_not_cached(self):
        broken = []
        raw = message(); raw["truncated"] = True; broken.append(raw)
        raw = message(); raw["payload"]["body"]["size"] = 999999; broken.append(raw)
        raw = message(); raw["payload"]["body"] = {"attachmentId": "fictional-attachment"}; broken.append(raw)
        raw = message(); raw["payload"]["body"] = {"data": base64.urlsafe_b64encode(b"\xff").decode()}; broken.append(raw)
        for raw in broken:
            with self.subTest(raw=raw):
                adapter = Adapter({("label:fictional-applications", None): page("m1"),
                                   ("fictional-linkedin-alerts", None): page()}, {"m1": raw})
                result = collect(adapter, scope())
                self.assertEqual(adapter.message_calls, ["m1"] * 3)
                self.assertEqual(result["next_state"]["messages"], {})
                self.assertEqual(result["status"], "incomplete")
        adapter = Adapter({("label:fictional-applications", None): page("m1", complete=False),
                           ("fictional-linkedin-alerts", None): page()}, {"m1": message()})
        result = collect(adapter, scope())
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(len(adapter.page_calls), 4)
        self.assertEqual(adapter.message_calls, [])
        collect(adapter, scope(), result["next_state"])
        self.assertEqual(len(adapter.page_calls), 4)

    def test_local_receipt_window_includes_start_excludes_end(self):
        times = {"before": "2026-09-30T23:59:59.999+00:00", "start": START,
                 "inside": "2026-10-01T19:59:59.999-04:00", "end": END}
        raws = {mid: message(mid, at=at) for mid, at in times.items()}
        adapter = Adapter({("label:fictional-applications", None): page(*times),
                           ("fictional-linkedin-alerts", None): page()}, raws)
        result = collect(adapter, scope(), reviews={mid: review(raw, "linkedin:101") for mid, raw in raws.items()})
        self.assertEqual(result["status"], "complete")
        self.assertEqual({s["message_id"] for s in result["sightings"]}, {"start", "inside"})
        self.assertEqual({m["message_id"] for m in result["messages"] if m["status"] == "outside_window"}, {"before", "end"})

    def test_frozen_scope_binding_review_resume_and_pagination_loop(self):
        raw = message()
        adapter = Adapter({("label:fictional-applications", None): page("m1"),
                           ("fictional-linkedin-alerts", None): page()}, {"m1": raw})
        first = collect(adapter, scope())
        saved = deepcopy(first["next_state"])
        accepted = collect(adapter, scope(), saved, {"m1": review(raw, "linkedin:101")})
        self.assertEqual(accepted["status"], "complete")
        self.assertEqual(saved, first["next_state"])
        for field, value in [("end", "2026-10-03T00:00:00+00:00"), ("max_attempts", 4), ("profile_id", "other")]:
            with self.subTest(field=field):
                changed = scope(); changed[field] = value
                with self.assertRaises(ContractError):
                    collect(adapter, changed, saved)
        looping = Adapter({("label:fictional-applications", None): page(next_token="loop"),
                           ("label:fictional-applications", "loop"): page(next_token="loop"),
                           ("fictional-linkedin-alerts", None): page()}, {})
        result = collect(looping, scope())
        self.assertIn("Repeated pagination token", [gap["reason"] for gap in result["gaps"]])

    def test_non_alert_requires_full_bound_review_and_no_jobs(self):
        content = "Fictional meeting notes — café."
        raw = message(content=content, mime="text/plain")
        raw["payload"]["body"]["size"] = len(content.encode("utf-8"))
        self.assertEqual(extract(raw, review(raw, non_alert=True))["status"], "non_alert")
        self.assertEqual(extract(raw)["status"], "incomplete")
        truncated = deepcopy(raw); truncated["truncated"] = True
        self.assertEqual(extract(truncated, review(truncated, non_alert=True))["status"], "incomplete")
        alert = message()
        self.assertEqual(extract(alert, review(alert, non_alert=True))["status"], "incomplete")
        invalid = CardReview(raw["id"], digest(raw), frozenset(), True, True, "fictional:invalid")
        with self.assertRaises(ContractError):
            extract(raw, invalid)


if __name__ == "__main__":
    unittest.main()
