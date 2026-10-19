"""Pure module boundary checks. No connector, browser, dispatcher or side effects."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json


class ContractError(ValueError):
    pass


class NotRequested(ContractError):
    """Caller must return not_requested without account calls, writes or retries."""


def check(ok, field, reason):
    if not ok:
        raise ContractError(f"{field}: {reason}")


def keys(value, expected, field):
    check(type(value) is dict and set(value) == set(expected.split()), field, "missing or unknown fields")


def text(value, field):
    check(type(value) is str and bool(value.strip()) and not any(ord(c) < 32 for c in value), field, "expected nonempty text")


def texts(value, field):
    check(type(value) is list, field, "expected list")
    for item in value:
        text(item, field)
    check(len(value) == len(set(value)), field, "duplicates")


def timestamp(value):
    text(value, "timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        check(result.tzinfo is not None and result.utcoffset() is not None, "timestamp", "timezone required")
        return result
    except ValueError:
        raise ContractError("timestamp: expected ISO datetime with timezone") from None


def digest(value):
    try:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError, RecursionError):
        raise ContractError("digest: expected finite JSON data") from None


# ponytail: one static catalog; no plugin registry until there are real adapters.
# Each tuple is (permitted effects, required completion proofs, manual-only).
MODULES = {
    "alert_extraction": ("read_mail write_state", "messages_accounted cards_accounted", False),
    "portal_inventory": ("read_public read_public_browser write_state", "filters_verified coverage_exhausted", False),
    "job_screening": ("read_public read_public_browser read_browser write_state", "requirements_read policy_applied", False),
    "identity_planning": ("read_sheets write_state", "identities_checked conflicts_accounted", False),
    "tracker_sync": ("read_sheets write_sheets write_state", "fresh_before write_readback links_verified", False),
    "application_reconciliation": ("read_mail read_sheets write_state", "messages_accounted exact_role_matching lifecycle_checked", False),
    "interview_sync": ("read_mail read_calendar read_messages write_state", "required_sources_checked interview_facts_checked", False),
    "brief_rendering": ("render_local write_state", "snapshot_consistent", False),
    "brief_delivery": ("read_mail send_report write_state", "delivery_journal_checked sent_readback", False),
    "application_opening": ("read_sheets read_browser open_applications write_state", "eligibility_checked capacity_checked destinations_verified handoff_saved", True),
    "recruiter_discovery": ("read_sheets read_browser write_state", "coverage_exhausted employment_checked roster_saved", True),
    "outreach_drafting": ("read_sheets read_browser create_drafts write_state", "employer_history_checked capacity_checked unsent_handoff_verified", True),
}


@dataclass(frozen=True)
class Permit:
    """Construct ONLY in trusted host code after reading the actual scoped request."""
    authorization_id: str
    origin: str
    event_id: str
    profile_id: str
    run_id: str
    module: str
    policy_version: str
    scope_digest: str
    effects: frozenset
    expires_at: str


@dataclass(frozen=True)
class Proof:
    """Coordinator-verified evidence receipt, never a worker/source assertion."""
    evidence_id: str
    kind: str
    profile_id: str
    run_id: str
    module: str
    policy_version: str
    scope_digest: str


def validate_invocation_shape(invocation):
    keys(invocation, "schema_version module module_version profile_id run_id policy_version authorization_id scope cutoff inputs effects", "invocation")
    for key in ("schema_version", "module_version"):
        check(type(invocation[key]) is int and invocation[key] == 1, key, "unsupported version")
    for key in ("module", "profile_id", "run_id", "policy_version", "authorization_id"):
        text(invocation[key], key)
    check(invocation["module"] in MODULES, "module", "unsupported module")
    scope = invocation["scope"]
    keys(scope, "kind items start end", "scope")
    texts(scope["items"], "scope.items")
    cutoff = timestamp(invocation["cutoff"])
    if scope["kind"] == "items":
        check(bool(scope["items"]) and scope["start"] is None and scope["end"] is None,
              "scope", "item scope needs explicit nonempty identities and null window")
    elif scope["kind"] == "window":
        check(not scope["items"] and timestamp(scope["start"]) < timestamp(scope["end"]) <= cutoff,
              "scope", "window must be finite, ordered and no later than cutoff")
    else:
        raise ContractError("scope.kind: expected items or window")
    if MODULES[invocation["module"]][2]:
        check(scope["kind"] == "items", "scope", "manual modules need named item/company scope")
    texts(invocation["inputs"], "inputs")
    texts(invocation["effects"], "effects")
    check(set(invocation["effects"]) <= set(MODULES[invocation["module"]][0].split()), "effects", "unsupported effect for module")
    return invocation


def validate_invocation(invocation, permit, *, event_id, now):
    """Shape first, then compare trusted caller scope; never construct a Permit from JSON."""
    validate_invocation_shape(invocation)
    text(event_id, "event_id")
    current = timestamp(now)
    if type(permit) is not Permit:
        raise NotRequested("authorization: missing trusted permit")
    expected = (invocation["authorization_id"], event_id, invocation["profile_id"], invocation["run_id"],
                invocation["module"], invocation["policy_version"], digest(invocation["scope"]))
    actual = (permit.authorization_id, permit.event_id, permit.profile_id, permit.run_id,
              permit.module, permit.policy_version, permit.scope_digest)
    if actual != expected or permit.origin not in ("human", "schedule") or current >= timestamp(permit.expires_at):
        raise NotRequested("authorization: stale or mismatched scoped permit")
    if MODULES[invocation["module"]][2] and permit.origin != "human":
        raise NotRequested("authorization: module requires explicit current human request")
    if type(permit.effects) is not frozenset or not set(invocation["effects"]) <= permit.effects:
        raise NotRequested("authorization: effects exceed trusted permit")
    return invocation


def validate_result(result, invocation, verified_proofs):
    """Check claims against externally accepted proof receipts; cannot establish their truth."""
    validate_invocation_shape(invocation)
    keys(result, "schema_version module module_version profile_id run_id policy_version scope_digest status evidence_refs proofs decisions gaps questions proposed_changes committed_changes effects resume_cursor stop_reason next_action", "result")
    for field in ("schema_version", "module_version", "module", "profile_id", "run_id", "policy_version"):
        check(type(result[field]) is type(invocation[field]) and result[field] == invocation[field], field, "invocation mismatch")
    check(result["scope_digest"] == digest(invocation["scope"]), "scope_digest", "scope mismatch")
    status = result["status"]
    check(status in ("complete", "incomplete", "blocked", "needs_review", "not_requested"), "status", "unknown status")
    for field in ("evidence_refs", "questions", "proposed_changes", "committed_changes", "effects"):
        texts(result[field], field)
    check(set(result["effects"]) <= set(invocation["effects"]), "effects", "unrequested effect")
    check(set(result["committed_changes"]) <= set(result["proposed_changes"]), "committed_changes", "commit must identify its proposal")
    text(result["stop_reason"], "stop_reason")
    keys(result["next_action"], "owner action", "next_action")
    for field in ("owner", "action"):
        text(result["next_action"][field], f"next_action.{field}")
    check(type(result["gaps"]) is list and type(result["decisions"]) is list, "result", "gaps/decisions must be lists")
    for gap in result["gaps"]:
        keys(gap, "item_id reason", "gap")
        text(gap["item_id"], "gap.item_id")
        text(gap["reason"], "gap.reason")
    items = []
    for decision in result["decisions"]:
        keys(decision, "item_id decision evidence_refs", "decision")
        text(decision["item_id"], "decision.item_id")
        text(decision["decision"], "decision.decision")
        texts(decision["evidence_refs"], "decision.evidence_refs")
        check(set(decision["evidence_refs"]) <= set(result["evidence_refs"]), "decision", "unknown evidence")
        items.append(decision["item_id"])
    check(len(items) == len(set(items)), "decisions", "duplicate item")
    if invocation["scope"]["kind"] == "items":
        check(set(items) <= set(invocation["scope"]["items"]), "decisions", "outside declared scope")
    if result["resume_cursor"] is not None:
        keys(result["resume_cursor"], "source_id position", "resume_cursor")
        for field in ("source_id", "position"):
            text(result["resume_cursor"][field], f"resume_cursor.{field}")
    check(type(result["proofs"]) is dict and type(verified_proofs) is dict, "proofs", "expected mapping")
    for kind, references in result["proofs"].items():
        text(kind, "proof kind")
        texts(references, "proof references")
        check(bool(references) and set(references) <= set(result["evidence_refs"]), "proofs", "missing evidence references")
        for ref in references:
            proof = verified_proofs.get(ref)
            check(type(proof) is Proof, "proofs", "no coordinator-verified receipt")
            check((proof.evidence_id, proof.kind, proof.profile_id, proof.run_id, proof.module, proof.policy_version, proof.scope_digest) ==
                  (ref, kind, result["profile_id"], result["run_id"], result["module"], result["policy_version"], result["scope_digest"]),
                  "proofs", "receipt belongs to another scope, run, profile or kind")
    if result["committed_changes"]:
        check("write_readback" in result["proofs"], "committed_changes", "verified readback required")
        check(bool(set(result["effects"]) & {"write_sheets", "write_state"}),
              "committed_changes", "commit requires an authorized performed write")
    if status in ("complete", "needs_review"):
        required = set(MODULES[invocation["module"]][1].split())
        check(required <= set(result["proofs"]), "proofs", "required completion proof missing")
        check(not result["gaps"] and result["resume_cursor"] is None, "status", "unfinished source work cannot complete")
        if invocation["scope"]["kind"] == "items":
            check(set(items) == set(invocation["scope"]["items"]), "decisions", "unaccounted items")
        check(bool(result["questions"]) == (status == "needs_review"), "questions", "review status mismatch")
    elif status == "not_requested":
        check(not any(result[k] for k in ("effects", "decisions", "proofs", "evidence_refs", "gaps", "questions", "proposed_changes", "committed_changes", "resume_cursor")),
              "not_requested", "must have no work/effects/retry")
    else:
        check(bool(result["gaps"]), "status", "incomplete/blocked requires exact gaps")
    return result
