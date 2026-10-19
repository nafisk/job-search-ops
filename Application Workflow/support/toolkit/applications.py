"""Pure exact-identity application evidence union; proposals only, no account access."""
from copy import deepcopy
from dataclasses import dataclass

from contracts import check, digest, keys, text, texts, timestamp
from portals import json_data

ORIGINS = ("sheet", "manual_history", "batch_manifest", "unresolved_association", "correspondence")
BASELINES = ORIGINS[:3]
MATCH_BASES = ("exact_role", "exact_requisition", "exact_application_ref", "independent_exact_role")
EVIDENCE_KINDS = ("email_receipt", "confirmation_page", "user_report")


@dataclass(frozen=True)
class SubmissionAcceptance:
    """Host's independent full-source and exact-role proof; never deserialize from worker JSON."""
    profile_id: str
    event_id: str
    source_digest: str
    application_key: str
    match_basis: str
    evidence_kind: str
    submission_at: str | None
    reviewed_at: str
    evidence_ref: str
    full_source_read: bool


def application_key(profile_id, employer_id, role_id):
    """Exact canonical identities only; no URL/title/alias inference."""
    for value in (profile_id, employer_id, role_id):
        text(value, "application identity")
    return digest([profile_id, employer_id, role_id])


def _past(value, now):
    if value is None:
        return None
    result = timestamp(value)
    check(result <= now, "timestamp", "future source/review time forbidden")
    return result


def _sources(payload):
    keys(payload, "schema_version profile_id as_of sources", "application input")
    check(type(payload["schema_version"]) is int and payload["schema_version"] == 1, "schema_version", "unsupported version")
    text(payload["profile_id"], "profile_id")
    now = timestamp(payload["as_of"])
    check(type(payload["sources"]) is list, "sources", "expected supplied source list")
    events, native_ids = {}, {}
    for source in payload["sources"]:
        keys(source, "event_id origin source_item_id observed_at employer_id role_id requisition_id application_ref evidence_refs payload", "source")
        for field in ("event_id", "source_item_id"):
            text(source[field], field)
        check(source["origin"] in ORIGINS, "origin", "unsupported source origin")
        _past(source["observed_at"], now)
        for field in ("employer_id", "role_id", "requisition_id", "application_ref"):
            if source[field] is not None:
                text(source[field], field)
        texts(source["evidence_refs"], "evidence_refs")
        check(bool(source["evidence_refs"]), "evidence_refs", "source evidence required")
        check(type(source["payload"]) is dict, "payload", "complete original JSON object required")
        digest(source["payload"])
        json_data(source["payload"])
        event_id = source["event_id"]
        check(event_id not in events or events[event_id] == source, "event_id", "immutable source event collision")
        native = (source["origin"], source["source_item_id"])
        check(native not in native_ids or native_ids[native] == event_id, "source_item_id", "same native event under another event ID")
        native_ids[native] = event_id
        events[event_id] = deepcopy(source)
    return [events[key] for key in sorted(events)], now


def _resolve(source, apps, profile_id):
    employer = source["employer_id"]
    if employer is None:
        return [], "Exact employer identity unresolved"
    if source["role_id"] is not None:
        key = application_key(profile_id, employer, source["role_id"])
        return ([key], None) if key in apps else ([], "Exact role is not a registered application")
    known_sets = []
    for field, registered in (("requisition_id", "requisition_ids"), ("application_ref", "application_refs")):
        if source[field] is not None:
            ids = {key for key, app in apps.items() if app["employer_id"] == employer and source[field] in app[registered]}
            if ids:
                known_sets.append(ids)
    matches = sorted(set.intersection(*known_sets)) if known_sets else []
    if known_sets and not matches:
        return sorted(set.union(*known_sets)), "Exact references bind to different applications"
    return (matches, None) if len(matches) == 1 else (matches, "Exact identity is unknown or ambiguous; no title/time match")


def _append(app, source):
    if source not in app["source_events"]:
        app["source_events"].append(deepcopy(source))
    for field, registered in (("requisition_id", "requisition_ids"), ("application_ref", "application_refs")):
        if source[field] is not None and source[field] not in app[registered]:
            app[registered].append(source[field])


def _review(review, source, profile_id, now):
    check(type(review) is SubmissionAcceptance, "acceptance", "trusted full-source acceptance required")
    check((review.profile_id, review.event_id, review.source_digest)
          == (profile_id, source["event_id"], digest(source)), "acceptance", "profile/event/source content mismatch")
    text(review.application_key, "application_key")
    check(review.match_basis in MATCH_BASES and review.evidence_kind in EVIDENCE_KINDS, "acceptance", "unsupported match/evidence kind")
    check(type(review.full_source_read) is bool and review.full_source_read, "acceptance", "independent full-source read required")
    text(review.evidence_ref, "acceptance evidence")
    reviewed = _past(review.reviewed_at, now)
    check(reviewed is not None, "reviewed_at", "actual review time required")
    observed = _past(source["observed_at"], now)
    check(observed is None or reviewed >= observed, "reviewed_at", "review precedes source capture")
    submitted = _past(review.submission_at, now)
    check(submitted is None or submitted <= reviewed, "submission_at", "submission follows review")
    if review.evidence_kind == "email_receipt":
        check(source["origin"] == "correspondence", "email_receipt", "must cite full supplied correspondence")


def reconcile(payload, acceptances=None):
    """Union all supplied origins; emit exact submission facts only after host acceptance."""
    sources, now = _sources(payload)
    profile_id = payload["profile_id"]
    acceptances = {} if acceptances is None else acceptances
    check(type(acceptances) is dict and all(type(k) is str for k in acceptances), "acceptances", "expected event mapping")
    check(set(acceptances) <= {s["event_id"] for s in sources}, "acceptances", "unknown source event")
    for source in sources:
        if source["event_id"] in acceptances:
            _review(acceptances[source["event_id"]], source, profile_id, now)
    apps, unresolved, conflicts, attached = {}, [], [], set()

    def seed(source, role_id):
        key = application_key(profile_id, source["employer_id"], role_id)
        if key not in apps:
            apps[key] = {"application_key": key, "employer_id": source["employer_id"], "role_id": role_id,
                         "requisition_ids": [], "application_refs": [], "origins": [], "source_events": [],
                         "submission_facts": [], "confirmation_status": "unconfirmed", "conflicts": []}
        _append(apps[key], source)
        attached.add(source["event_id"])

    for source in sources:
        if source["origin"] in BASELINES and source["employer_id"] is not None and source["role_id"] is not None:
            seed(source, source["role_id"])
    # ponytail: supplied small snapshots only; exact indexes are scanned, with no fuzzy identity engine.
    for source in sources:
        if source["origin"] in BASELINES and source["event_id"] not in attached:
            matches, reason = _resolve(source, apps, profile_id)
            if len(matches) == 1 and reason is None:
                _append(apps[matches[0]], source)
                attached.add(source["event_id"])
            elif (source["employer_id"] is not None and source["role_id"] is None
                  and source["requisition_id"] is not None and not matches
                  and not any(app["employer_id"] == source["employer_id"]
                              and source["requisition_id"] in app["requisition_ids"] for app in apps.values())):
                seed(source, "requisition:" + source["requisition_id"])

    def conflict(app_keys, event_ids, reason):
        item = {"application_keys": sorted(set(app_keys)), "event_ids": sorted(set(event_ids)), "reason": reason}
        if item not in conflicts:
            conflicts.append(item)
        for key in app_keys:
            if reason not in apps[key]["conflicts"]:
                apps[key]["conflicts"].append(reason)

    facts = []
    for source in sources:
        review = acceptances.get(source["event_id"])
        matches, reason = _resolve(source, apps, profile_id)
        if review is not None:
            if review.application_key not in apps:
                matches, reason = [], "Accepted target is not registered; resolve exact role first"
            else:
                app = apps[review.application_key]
                same_employer = source["employer_id"] == app["employer_id"]
                basis = ((review.match_basis == "exact_role" and source["role_id"] == app["role_id"])
                         or (review.match_basis == "exact_requisition" and source["requisition_id"] is not None
                             and source["requisition_id"] in app["requisition_ids"] and matches == [review.application_key])
                         or (review.match_basis == "exact_application_ref" and source["application_ref"] is not None
                             and source["application_ref"] in app["application_refs"] and matches == [review.application_key])
                         or (review.match_basis == "independent_exact_role" and source["role_id"] in (None, app["role_id"])))
                if same_employer and basis:
                    matches, reason = [review.application_key], None
                else:
                    conflict([review.application_key], [source["event_id"]], "Accepted exact identity conflicts with supplied source")
                    matches, reason = [], "Source cannot confirm the accepted employer/role"
        if len(matches) != 1 or reason is not None:
            if reason == "Exact references bind to different applications":
                conflict(matches, [source["event_id"]], reason)
            unresolved.append({"source_event": deepcopy(source), "reason": reason or "Ambiguous exact identity"})
            continue
        key = matches[0]
        app = apps[key]
        identity_conflict = (source["requisition_id"] is not None and app["requisition_ids"]
                             and source["requisition_id"] not in app["requisition_ids"])
        if identity_conflict:
            conflict([key], [source["event_id"]], "Canonical role has conflicting requisition evidence")
            unresolved.append({"source_event": deepcopy(source), "reason": "Conflicting exact requisition identity"})
            continue
        _append(app, source)
        if review is None:
            if source["origin"] in ("correspondence", "unresolved_association"):
                unresolved.append({"source_event": deepcopy(source), "reason": "Submission interpretation/association not independently accepted"})
            continue
        facts.append((key, {"event_id": source["event_id"], "application_key": key,
            "evidence_kind": review.evidence_kind, "evidence_ref": review.evidence_ref,
            "observed_at": source["observed_at"], "submission_at": review.submission_at,
            "reviewed_at": review.reviewed_at, "match_basis": review.match_basis}))

    refs, requisitions = {}, {}
    for key, app in apps.items():
        if len(app["requisition_ids"]) > 1:
            conflict([key], [s["event_id"] for s in app["source_events"]], "Canonical role has conflicting requisition evidence")
        for native in app["application_refs"]:
            refs.setdefault((app["employer_id"], native), []).append(key)
        for requisition in app["requisition_ids"]:
            requisitions.setdefault((app["employer_id"], requisition), []).append(key)
    for app_keys in refs.values():
        if len(app_keys) > 1:
            conflict(app_keys, [s["event_id"] for key in app_keys for s in apps[key]["source_events"]],
                     "Native application reference belongs to multiple canonical roles")
    for app_keys in requisitions.values():
        if len(app_keys) > 1:
            conflict(app_keys, [s["event_id"] for key in app_keys for s in apps[key]["source_events"]],
                     "Exact requisition belongs to multiple canonical roles")
    proposals = []
    for key, fact in facts:
        if apps[key]["conflicts"]:
            source = next(s for s in sources if s["event_id"] == fact["event_id"])
            item = {"source_event": deepcopy(source), "reason": "Conflicting identity prevents submission proposal"}
            if item not in unresolved:
                unresolved.append(item)
        else:
            apps[key]["submission_facts"].append(deepcopy(fact))
            apps[key]["confirmation_status"] = "confirmed"
            proposals.append({"kind": "confirm_submission", "application_key": key, "fact": deepcopy(fact)})
    for app in apps.values():
        app["requisition_ids"].sort()
        app["application_refs"].sort()
        app["origins"] = sorted({s["origin"] for s in app["source_events"]})
        app["source_events"].sort(key=lambda s: s["event_id"])
        app["conflicts"].sort()
    return {"profile_id": profile_id, "applications": [apps[key] for key in sorted(apps)],
            "unresolved": sorted(unresolved, key=lambda x: (x["source_event"]["event_id"], x["reason"])),
            "conflicts": sorted(conflicts, key=digest), "proposals": proposals,
            "source_events": deepcopy(sources), "operational_complete": False}
