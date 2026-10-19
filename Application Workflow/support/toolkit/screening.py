"""Deterministic policy decisions over independently reviewed, quoted role evidence."""
from dataclasses import dataclass
from math import isfinite
from contracts import check, digest, text, texts, timestamp
from sheet_values import safe_url


@dataclass(frozen=True)
class ScreeningReview:
    """Host acceptance of independent evidence review, not a worker authorization flag."""
    profile_digest: str
    packet_digest: str
    complete_inventory: bool
    unread_requirements: int
    evidence_ref: str


def fields(value, expected, label):
    check(type(value) is dict and set(value) == set(expected.split()), label, "unexpected or missing fields")


def number(value, label):
    check(type(value) in (int, float) and isfinite(value) and value >= 0, label, "nonnegative finite years required")


def screen(profile, packet, review=None):
    """Pure decision; no account reads, writes, link resolution or application permission."""
    fields(packet, "job_id job_url as_of max_age_days sources facts applicant", "packet")
    text(packet["job_id"], "job identity")
    safe_url(packet["job_url"])
    now = timestamp(packet["as_of"])
    number(packet["max_age_days"], "freshness window")
    check(type(packet["sources"]) is list and bool(packet["sources"]), "sources", "exact role evidence required")
    sources, unread = {}, []
    for source in packet["sources"]:
        fields(source, "id url captured_at access content", "source")
        text(source["id"], "source ID")
        check(source["id"] not in sources, "source ID", "duplicate")
        safe_url(source["url"])
        age = (now - timestamp(source["captured_at"])).total_seconds() / 86400
        check(source["access"] in ("full", "partial", "unread"), "access", "unknown source state")
        check(type(source["content"]) is str, "content", "text required")
        sources[source["id"]] = source
        if source["access"] != "full" or not source["content"].strip():
            unread.append("Exact source is unread or incomplete")
        if age < 0 or age > packet["max_age_days"]:
            unread.append("Source observation falls outside the requested freshness window")
    check(any(s["url"] == packet["job_url"] for s in sources.values()), "job URL", "exact source link is absent")

    def result(decision, reasons, branches=(), minimum=None, senior=False):
        return {"job_id": packet["job_id"], "job_url": packet["job_url"], "profile_id": profile["profile_id"],
                "policy_version": profile["role_policy"]["version"], "decision": decision,
                "reasons": sorted(set(reasons)), "applicable_branches": list(branches),
                "required_years": minimum, "senior_exception": senior,
                "priority": "lower" if senior else "preferred" if decision == "QUALIFY" and
                    minimum == profile["role_policy"]["experience"]["preferred_required_years"] and
                    level.casefold() in {x.casefold() for x in profile["role_policy"]["preferred_levels"]} else "standard",
                "evidence_refs": list(sources), "evidence_digest": digest(packet),
                "review_ref": review.evidence_ref if type(review) is ScreeningReview else None,
                "application_authorized": False}

    if unread:
        return result("UNVERIFIED", unread)
    bound = (type(review) is ScreeningReview and review.profile_digest == digest(profile)
             and review.packet_digest == digest(packet))
    if not bound:
        return result("UNVERIFIED", ["Independent full-description review for this profile and evidence is required"])
    text(review.evidence_ref, "review evidence")
    check(type(review.complete_inventory) is bool and type(review.unread_requirements) is int and
          review.unread_requirements >= 0, "review", "invalid coverage receipt")
    if not review.complete_inventory or review.unread_requirements:
        return result("UNVERIFIED", ["Description or qualification inventory is not fully accounted for"])

    def quote(fact):
        text(fact["source"], "fact source")
        value = fact["quote"]
        check(type(value) is str and bool(value.strip()) and not any(
            ord(c) < 32 and c not in "\n\r\t" or ord(c) == 127 for c in value), "fact quote", "nonempty source text required")
        check(fact["source"] in sources and fact["quote"] in sources[fact["source"]]["content"],
              "fact quote", "not present in captured source")

    def fact(name, plural=False):
        value = facts[name]
        fields(value, "source quote " + ("values" if plural else "value"), name)
        quote(value)
        if plural:
            texts(value["values"], name)
            return value["values"]
        text(value["value"], name)
        return value["value"]

    facts = packet["facts"]
    fields(facts, "title company families primary_duties level employers availability location common branches", "facts")
    text(facts["title"], "title")
    text(facts["company"], "company")
    families, duties = fact("families", True), fact("primary_duties", True)
    employers, level, availability = fact("employers", True), fact("level").casefold(), fact("availability")
    check(facts["company"].casefold() in {e.casefold() for e in employers}, "employers", "actual employer must be represented")
    check(availability in ("open", "closed", "unknown"), "availability", "unknown classification")
    policy, location_policy = profile["role_policy"], profile["locations"]
    exp = policy["experience"]
    excluded, ambiguous = [], []
    def overlap(a, b):
        return set(x.casefold() for x in a) & set(x.casefold() for x in b)
    if overlap(employers, policy["excluded_employers"]):
        excluded.append("Employer or verified owner is excluded by profile")
    if overlap(duties, policy["excluded_duties"]):
        excluded.append("Primary duties are excluded by profile")
    if overlap([level], policy["excluded_levels"]):
        excluded.append("Verified responsibility level is excluded by profile")
    if not families:
        ambiguous.append("Role family is ambiguous")
    elif not overlap(families, policy["families"]):
        excluded.append("Primary role family is outside profile")
    if level == "unknown":
        ambiguous.append("Responsibility level is ambiguous")
    senior = level in ("senior", "senior individual contributor")
    if senior and not exp["senior_low_experience_exception"] and not overlap([level], policy["preferred_levels"]):
        excluded.append("Senior role is outside the configured level policy")
    if availability == "unknown":
        unread.append("Current opening availability is not verified")

    location = facts["location"]
    fields(location, "source quote mode region country residency", "location")
    quote(location)
    check(location["mode"] in ("onsite", "hybrid", "remote", "unknown"), "location", "unknown mode")
    check(location["residency"] in ("allowed", "excluded", "unknown"), "residency", "unknown classification")
    for key in ("region", "country"):
        if location[key] is not None:
            text(location[key], "location " + key)
    if location["mode"] in ("onsite", "hybrid"):
        if location["region"] is None:
            ambiguous.append("Onsite region is not established")
        elif not overlap([location["region"]], location_policy["onsite_regions"]):
            if location_policy["allow_relocation"]:
                ambiguous.append("Relocation destination needs review")
            else:
                excluded.append("Mandatory onsite region is outside profile")
    elif location["mode"] == "remote":
        if location["country"] is None or location["residency"] == "unknown":
            ambiguous.append("Remote country or permitted residency is unknown")
        if location["country"] is not None and not overlap([location["country"]], location_policy["remote_countries"]):
            excluded.append("Remote country is outside profile")
        if location["residency"] == "excluded":
            excluded.append("Remote opening excludes applicant residency")
    else:
        ambiguous.append("Work location is ambiguous")

    applicant = packet["applicant"]
    fields(applicant, "degrees degrees_complete evidence_ref", "applicant")
    texts(applicant["degrees"], "held degrees")
    check(type(applicant["degrees_complete"]) is bool, "degrees", "explicit inventory state required")
    text(applicant["evidence_ref"], "applicant evidence")

    def requirements(items):
        check(type(items) is list, "requirements", "explicit clause inventory required")
        hard, review_reasons, overall, minima = [], [], [], []
        for req in items:
            fields(req, "source quote required kind minimum maximum range_resolved", "requirement")
            quote(req)
            check(type(req["required"]) is bool and type(req["range_resolved"]) is bool, "requirement", "explicit booleans required")
            check(req["kind"] in ("overall", "specialty"), "requirement", "unknown experience kind")
            for key in ("minimum", "maximum"):
                if req[key] is not None:
                    number(req[key], key)
            check(req["maximum"] is None or req["minimum"] is None or req["maximum"] >= req["minimum"],
                  "range", "invalid bounds")
            if not req["required"]:
                continue
            if req["minimum"] is None:
                if exp["unknown_minimum"] == "review":
                    review_reasons.append("Mandatory experience minimum is unknown")
                continue
            minima.append(req["minimum"])
            if req["kind"] == "overall":
                overall.append(req["minimum"])
            if req["minimum"] > exp["max_required_years"]:
                hard.append("Mandatory " + req["kind"] + " experience exceeds profile ceiling")
            elif (req["maximum"] is not None and req["maximum"] > req["minimum"]
                  and not req["range_resolved"] and exp["ambiguous_range"] == "review"):
                review_reasons.append("Experience range needs clarification")
        if not overall and exp["unknown_minimum"] == "review":
            review_reasons.append("No explicit mandatory overall experience minimum")
        return hard, review_reasons, max(minima) if minima else None

    check(type(facts["common"]) is list and type(facts["branches"]) is list and bool(facts["branches"]),
          "branches", "explicit common clauses and one or more alternatives required")
    texts([b["id"] for b in facts["branches"]], "branch IDs")
    branch_results = []
    for branch in facts["branches"]:
        fields(branch, "id source quote degree other_condition requirements", "branch")
        quote(branch)
        check(branch["other_condition"] in ("met", "unmet", "unknown"), "branch", "unknown applicant condition")
        if branch["degree"] is not None:
            text(branch["degree"], "degree branch")
        check(type(branch["requirements"]) is list, "branch requirements", "list required")
        hard, pending, minimum = requirements(facts["common"] + branch["requirements"])
        if branch["degree"] is not None and not overlap([branch["degree"]], applicant["degrees"]):
            (hard if applicant["degrees_complete"] else pending).append("Degree alternative is unavailable or unknown")
        if branch["other_condition"] == "unmet":
            hard.append("Other mandatory branch condition is not met")
        elif branch["other_condition"] == "unknown":
            pending.append("Other mandatory branch condition needs review")
        branch_results.append((branch["id"], hard, pending, minimum))

    # ponytail: reviewed clauses, not a natural-language classifier; OR branches and AND clauses only.
    if availability == "closed":
        return result("CLOSED", ["Exact role source explicitly reports closure"])
    if unread:
        return result("UNVERIFIED", unread)
    if excluded:
        return result("EXCLUDED", excluded)
    feasible = [b for b in branch_results if not b[1]]
    if not feasible:
        return result("EXCLUDED", [r for b in branch_results for r in b[1]])
    qualified = [b for b in feasible if not b[2]]
    if not qualified or ambiguous:
        return result("NEEDS_REVIEW", ambiguous + ([] if qualified else [r for b in feasible for r in b[2]]))
    selected = min(qualified, key=lambda b: (b[3] is None,
                   abs(b[3] - exp["preferred_required_years"]) if b[3] is not None else 0,
                   b[3] if b[3] is not None else 0, b[0]))
    exception = senior and not overlap([level], policy["preferred_levels"])
    return result("QUALIFY", ["Current reviewed role meets configured discovery policy"],
                  [b[0] for b in qualified], selected[3], exception)
