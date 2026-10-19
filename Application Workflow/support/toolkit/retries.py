"""Pure coordinator-owned retry accounting and acceptance gate; no reads or writes."""
from copy import deepcopy
from dataclasses import asdict, dataclass

from contracts import check, digest, keys, text, texts, timestamp
from portals import json_data

MAX_ATTEMPTS = 3
OUTCOMES = ("read", "failed", "inaccessible", "invalid")


@dataclass(frozen=True)
class RetryOwner:
    """Trusted host coordinator only; a worker/source cannot supply ownership."""
    profile_id: str
    coordinator_id: str
    pass_id: str


@dataclass(frozen=True)
class LedgerHead:
    """Host-verified authoritative persistence anchor, not loaded from source JSON."""
    profile_id: str
    coordinator_id: str
    active_pass_id: str
    ledger_digest: str


@dataclass(frozen=True)
class RecoveryApproval:
    """Trusted explicit recovery authorization for this exact accepted prior ledger."""
    profile_id: str
    coordinator_id: str
    prior_pass_id: str
    prior_ledger_digest: str
    new_pass_id: str
    approved_at: str
    approval_ref: str


@dataclass(frozen=True)
class CompletionAcceptance:
    """Independent host acceptance of full pages, current decisions and persistence."""
    profile_id: str
    pass_id: str
    scope_digest: str
    page_keys: frozenset
    resolved_candidate_ids: frozenset
    verification_ref: str
    commit_ref: str


def _past(value, now):
    result = timestamp(value)
    check(result <= now, "timestamp", "future evidence forbidden")
    return result


def _source(source):
    keys(source, "source_id item_id cursor", "source")
    for field in ("source_id", "item_id"):
        text(source[field], field)
    digest(source["cursor"])
    json_data(source["cursor"])
    return digest([source["source_id"], source["item_id"]])


def _head(ledger):
    return (ledger["profile_id"], ledger["coordinator_id"], ledger["active_pass_id"])


def _owner(ledger, owner):
    check(type(owner) is RetryOwner and (owner.profile_id, owner.coordinator_id, owner.pass_id) == _head(ledger),
          "owner", "current trusted coordinator ownership required")


def _latest(ledger):
    times = [timestamp(p["started_at"]) for p in ledger["passes"]]
    for p in ledger["passes"]:
        for a in p["attempts"]:
            times.append(timestamp(a["reserved_at"]))
            if a["result"] is not None:
                times.append(timestamp(a["result"]["finished_at"]))
    return max(times)


def new_ledger(profile_id, pass_id, coordinator_id, *, started_at, as_of):
    """Initialize one genuinely new host pass; never use initialization to resume."""
    for value in (profile_id, pass_id, coordinator_id):
        text(value, "identity")
    _past(started_at, timestamp(as_of))
    return {"schema_version": 1, "profile_id": profile_id, "coordinator_id": coordinator_id,
            "active_pass_id": pass_id, "passes": [
                {"pass_id": pass_id, "started_at": started_at, "recovery": None, "attempts": []}]}


def validate_ledger(ledger, *, as_of):
    """Validate full serializable history; authoritative resume additionally needs LedgerHead."""
    now = timestamp(as_of)
    keys(ledger, "schema_version profile_id coordinator_id active_pass_id passes", "ledger")
    check(type(ledger["schema_version"]) is int and ledger["schema_version"] == 1, "ledger", "unsupported version")
    for field in ("profile_id", "coordinator_id", "active_pass_id"):
        text(ledger[field], field)
    check(type(ledger["passes"]) is list and bool(ledger["passes"]), "passes", "nonempty history required")
    pass_ids, attempt_ids, sources = [], [], {}
    latest = None
    for index, p in enumerate(ledger["passes"]):
        keys(p, "pass_id started_at recovery attempts", "pass")
        text(p["pass_id"], "pass_id")
        pass_ids.append(p["pass_id"])
        started = _past(p["started_at"], now)
        check(latest is None or started >= latest, "pass", "recovery precedes prior history")
        approval = p["recovery"]
        if index == 0:
            check(approval is None, "recovery", "initial pass cannot claim recovery")
        else:
            keys(approval, "profile_id coordinator_id prior_pass_id prior_ledger_digest new_pass_id approved_at approval_ref", "recovery")
            prefix = {**ledger, "active_pass_id": ledger["passes"][index - 1]["pass_id"], "passes": ledger["passes"][:index]}
            check((approval["profile_id"], approval["coordinator_id"], approval["prior_pass_id"], approval["new_pass_id"])
                  == (ledger["profile_id"], ledger["coordinator_id"], prefix["active_pass_id"], p["pass_id"]), "recovery", "binding mismatch")
            check(approval["prior_ledger_digest"] == digest(prefix) and approval["approved_at"] == p["started_at"],
                  "recovery", "prior history or approval time changed")
            text(approval["approval_ref"], "approval_ref")
        check(type(p["attempts"]) is list, "attempts", "expected list")
        counts = {}
        latest = started
        reserved_previous = started
        for a in p["attempts"]:
            keys(a, "attempt_id source worker_id method reserved_at result", "attempt")
            for field in ("attempt_id", "worker_id", "method"):
                text(a[field], field)
            attempt_ids.append(a["attempt_id"])
            key = _source(a["source"])
            check(key not in sources or sources[key] == a["source"], "source", "exact cursor/source rebinding forbidden")
            sources[key] = a["source"]
            counts[key] = counts.get(key, 0) + 1
            check(counts[key] <= MAX_ATTEMPTS, "attempts", "shared three-attempt budget exceeded")
            reserved = _past(a["reserved_at"], now)
            check(reserved >= reserved_previous, "attempt", "reservation chronology regressed")
            reserved_previous = reserved
            latest = max(latest, reserved)
            if a["result"] is not None:
                result = a["result"]
                keys(result, "outcome evidence_refs finished_at", "attempt.result")
                check(result["outcome"] in OUTCOMES, "outcome", "unsupported read outcome")
                texts(result["evidence_refs"], "evidence_refs")
                check(bool(result["evidence_refs"]), "evidence_refs", "observed outcome evidence required")
                finished = _past(result["finished_at"], now)
                check(finished >= reserved, "attempt", "finish precedes reservation")
                latest = max(latest, finished)
    texts(pass_ids, "pass IDs")
    texts(attempt_ids, "attempt IDs")
    check(ledger["active_pass_id"] == pass_ids[-1], "active_pass_id", "must identify final retained pass")
    return deepcopy(ledger)


def resume_ledger(ledger, head, *, as_of):
    """Accept only the host's anchored authoritative ledger; pending reads remain charged."""
    validate_ledger(ledger, as_of=as_of)
    check(type(head) is LedgerHead and (head.profile_id, head.coordinator_id, head.active_pass_id) == _head(ledger)
          and head.ledger_digest == digest(ledger), "resume", "trusted authoritative ledger anchor mismatch")
    return deepcopy(ledger)


def reserve_attempt(ledger, owner, source, *, attempt_id, worker_id, method, reserved_at, as_of):
    """Charge a unique reservation BEFORE the host persists it and performs an external read."""
    validate_ledger(ledger, as_of=as_of)
    _owner(ledger, owner)
    key = _source(source)
    for value in (attempt_id, worker_id, method):
        text(value, "reservation identity")
    check(_past(reserved_at, timestamp(as_of)) >= _latest(ledger), "reservation", "backdated reservation")
    for p in ledger["passes"]:
        for a in p["attempts"]:
            check(a["attempt_id"] != attempt_id, "attempt_id", "reservation IDs cannot be replayed for another read")
            check(_source(a["source"]) != key or a["source"] == source, "source", "exact cursor/source rebinding forbidden")
    attempts = ledger["passes"][-1]["attempts"]
    check(not any(_source(a["source"]) == key and a["result"] is not None
                  and a["result"]["outcome"] == "read" for a in attempts),
          "attempts", "usable read already recorded; further retries forbidden")
    check(sum(_source(a["source"]) == key for a in attempts) < MAX_ATTEMPTS, "attempts", "shared three-attempt budget exhausted")
    result = deepcopy(ledger)
    result["passes"][-1]["attempts"].append({"attempt_id": attempt_id, "source": deepcopy(source),
        "worker_id": worker_id, "method": method, "reserved_at": reserved_at, "result": None})
    return result


def finish_attempt(ledger, owner, attempt_id, *, outcome, evidence_refs, finished_at, as_of):
    """Attach a read outcome; failed/inaccessible/invalid reads never become no-match."""
    validate_ledger(ledger, as_of=as_of)
    _owner(ledger, owner)
    text(attempt_id, "attempt_id")
    check(outcome in OUTCOMES, "outcome", "unsupported read outcome")
    texts(evidence_refs, "evidence_refs")
    check(bool(evidence_refs), "evidence_refs", "observed outcome evidence required")
    finished = _past(finished_at, timestamp(as_of))
    attempt = next((a for a in ledger["passes"][-1]["attempts"] if a["attempt_id"] == attempt_id), None)
    check(attempt is not None and finished >= timestamp(attempt["reserved_at"]), "attempt", "unknown reservation or regressing finish")
    payload = {"outcome": outcome, "evidence_refs": deepcopy(evidence_refs), "finished_at": finished_at}
    check(attempt["result"] is None or attempt["result"] == payload, "attempt", "immutable result collision")
    result = deepcopy(ledger)
    next(a for a in result["passes"][-1]["attempts"] if a["attempt_id"] == attempt_id)["result"] = payload
    return result


def begin_recovery_pass(ledger, owner, approval, *, as_of):
    """Append an explicitly approved fresh pass, retaining all charged prior attempts."""
    validate_ledger(ledger, as_of=as_of)
    _owner(ledger, owner)
    check(type(approval) is RecoveryApproval, "recovery", "trusted explicit approval required")
    check((approval.profile_id, approval.coordinator_id, approval.prior_pass_id, approval.prior_ledger_digest)
          == (*_head(ledger), digest(ledger)), "recovery", "approval is not bound to exact current history")
    text(approval.new_pass_id, "new_pass_id")
    text(approval.approval_ref, "approval_ref")
    check(approval.new_pass_id not in [p["pass_id"] for p in ledger["passes"]], "new_pass_id", "recovery pass ID already used")
    check(_past(approval.approved_at, timestamp(as_of)) >= _latest(ledger), "recovery", "approval precedes charged history")
    result = deepcopy(ledger)
    result["active_pass_id"] = approval.new_pass_id
    result["passes"].append({"pass_id": approval.new_pass_id, "started_at": approval.approved_at,
                             "recovery": asdict(approval), "attempts": []})
    return result


def completion_status(ledger, scope, *, as_of, acceptance=None):
    """Gate full declared pages + current verification + commit; no historical waiver."""
    validate_ledger(ledger, as_of=as_of)
    keys(scope, "page_items current_candidate_ids", "completion scope")
    check(type(scope["page_items"]) is list and bool(scope["page_items"]), "page_items", "explicit nonempty page scope required")
    page_keys = [_source(s) for s in scope["page_items"]]
    texts(page_keys, "page keys")
    texts(scope["current_candidate_ids"], "current_candidate_ids")
    if acceptance is not None:
        check(type(acceptance) is CompletionAcceptance, "acceptance", "trusted independent acceptance required")
        check((acceptance.profile_id, acceptance.pass_id, acceptance.scope_digest)
              == (ledger["profile_id"], ledger["active_pass_id"], digest(scope)), "acceptance", "scope/profile/pass mismatch")
        for ids in (acceptance.page_keys, acceptance.resolved_candidate_ids):
            check(type(ids) is frozenset, "acceptance", "immutable accepted ID sets required")
            for item in ids:
                text(item, "accepted item ID")
        check(acceptance.page_keys <= set(page_keys)
              and acceptance.resolved_candidate_ids <= set(scope["current_candidate_ids"]), "acceptance", "accepted items outside declared current scope")
        text(acceptance.verification_ref, "verification_ref")
        text(acceptance.commit_ref, "commit_ref")
    attempts = ledger["passes"][-1]["attempts"]
    gaps, cursors, exhausted = [], [], []
    for key, source in sorted(zip(page_keys, scope["page_items"]), key=lambda pair: pair[0]):
        matches = [a for a in attempts if _source(a["source"]) == key]
        check(all(a["source"] == source for a in matches), "scope", "declared cursor differs from charged source")
        read = (bool(matches) and matches[-1]["result"] is not None
                and matches[-1]["result"]["outcome"] == "read")
        if not read:
            gaps.append({"item_id": key, "reason": "Declared page unread or inaccessible; not no-match"})
            cursors.append(deepcopy(source))
            if len(matches) == MAX_ATTEMPTS:
                exhausted.append(key)
        if acceptance is None or key not in acceptance.page_keys:
            gaps.append({"item_id": key, "reason": "Independent full-page coverage acceptance required"})
    for item in sorted(scope["current_candidate_ids"]):
        if acceptance is None or item not in acceptance.resolved_candidate_ids:
            gaps.append({"item_id": item, "reason": "Current candidate verification unresolved; not human review or historical"})
    if acceptance is None:
        gaps.append({"item_id": "scope:" + digest(scope), "reason": "Accepted verification and verified commit required"})
    return {"status": "incomplete" if gaps else "complete", "operational_complete": not gaps,
            "gaps": gaps, "unresolved_cursors": cursors, "exhausted_items": exhausted}
