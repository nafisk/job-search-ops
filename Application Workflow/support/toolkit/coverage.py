"""Pure source-coverage projection with explicit configured scope and retained gaps."""
from copy import deepcopy
from dataclasses import asdict, dataclass
import re

from contracts import check, text, texts, timestamp

SERVICES = ("mail", "calendar", "messages")


@dataclass(frozen=True)
class SourceGap:
    gap_id: str
    reason: str
    first_observed_at: str | None
    last_attempt_at: str | None


@dataclass(frozen=True)
class SourceCheck:
    """Host-verified observation after identity/scope checks; not a source JSON flag."""
    profile_id: str
    service: str
    connection_ref: str
    scope_digest: str
    checked_at: str
    covered_through: str | None
    last_successful_at: str | None
    status: str
    gaps: tuple
    evidence_refs: tuple


def _time(value, latest):
    if value is None:
        return None
    parsed = timestamp(value)
    check(parsed <= latest, "time", "future or regressing source chronology")
    return parsed


def coverage_status(profile, scopes, checks, *, cutoff, as_of):
    """Project actual coverage, not source truth, ingestion acceptance or delivery."""
    now, horizon = timestamp(as_of), timestamp(cutoff)
    check(horizon <= now, "cutoff", "cannot follow evaluation time")
    check(type(profile) is dict and type(profile.get("integrations")) is dict,
          "profile", "validated profile required")
    text(profile.get("profile_id"), "profile_id")
    check(type(scopes) is dict and type(checks) is dict, "sources", "expected mappings")
    configs = {}
    for service in SERVICES:
        config = profile["integrations"].get(service, {"enabled": False, "required": False})
        check(type(config) is dict and type(config.get("enabled")) is bool
              and type(config.get("required")) is bool, service, "explicit configuration required")
        check(not config["required"] or config["enabled"], service, "required source cannot be disabled")
        if config["enabled"]:
            text(config.get("connection_ref"), "connection_ref")
        configs[service] = config
    enabled = {s for s, config in configs.items() if config["enabled"]}
    check(set(scopes) == enabled and set(checks) <= enabled,
          "scope", "declare every enabled source; disabled/unknown sources forbidden")
    check(all(type(value) is SourceCheck for value in checks.values()),
          "checks", "omit missing checks; supplied entries require trusted SourceCheck")
    for value in scopes.values():
        check(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None,
              "scope", "expected approved full-source scope SHA256")

    projected, gaps = {}, []
    for service, config in configs.items():
        row = {"status": "not_configured", "required": config["required"],
               "scope_digest": scopes.get(service), "checked_at": None,
               "covered_through": None, "last_successful_at": None,
               "gaps": [], "evidence_refs": []}
        observed = checks.get(service)
        if config["enabled"] and observed is None:
            row["status"] = "not_checked"
            row["gaps"] = [{"gap_id": "missing:" + service, "reason": "No accepted source check supplied",
                            "first_observed_at": None, "last_attempt_at": None}]
        elif observed is not None:
            check(type(observed) is SourceCheck, service, "trusted SourceCheck required")
            check((observed.profile_id, observed.service, observed.connection_ref, observed.scope_digest)
                  == (profile["profile_id"], service, config["connection_ref"], scopes[service]),
                  service, "profile, connection or complete source scope mismatch")
            checked = _time(observed.checked_at, now)
            check(checked is not None, service, "actual check time required")
            through = _time(observed.covered_through, checked)
            _time(observed.last_successful_at, checked)
            check(observed.status in ("checked", "partial", "blocked"), service, "unsupported source status")
            check(type(observed.gaps) is tuple and type(observed.evidence_refs) is tuple,
                  service, "immutable gap/evidence containers required")
            texts(list(observed.evidence_refs), "source evidence")
            check(bool(observed.evidence_refs), service, "actual source evidence required")
            normalized = []
            for gap in observed.gaps:
                check(type(gap) is SourceGap, "gap", "trusted source gap required")
                text(gap.gap_id, "gap_id")
                text(gap.reason, "reason")
                first = _time(gap.first_observed_at, checked)
                last = _time(gap.last_attempt_at, checked)
                check(first is None or last is None or first <= last, "gap", "attempt precedes original gap")
                normalized.append(asdict(gap))
            texts([g["gap_id"] for g in normalized], "gap IDs")
            check((observed.status == "checked" and through is not None and not normalized)
                  or (observed.status != "checked" and bool(normalized)),
                  service, "complete coverage cannot hide gaps; partial/blocked needs exact gaps")
            row.update(status=observed.status, checked_at=observed.checked_at,
                       covered_through=observed.covered_through,
                       last_successful_at=observed.last_successful_at,
                       gaps=normalized, evidence_refs=list(observed.evidence_refs))
            if observed.status == "checked" and through < horizon:
                row["status"] = "stale"
                row["gaps"].append({"gap_id": "stale:" + service,
                    "reason": "Verified source window does not reach the frozen cutoff",
                    "first_observed_at": None, "last_attempt_at": observed.checked_at})
        projected[service] = row
        gaps.extend({"service": service, **gap} for gap in row["gaps"])
    return deepcopy({"profile_id": profile["profile_id"], "cutoff": cutoff, "as_of": as_of,
                     "sources": projected, "gaps": gaps,
                     "required_complete": all(r["status"] == "checked" for r in projected.values() if r["required"]),
                     "all_enabled_complete": all(projected[s]["status"] == "checked" for s in enabled),
                     "operational_complete": False})
