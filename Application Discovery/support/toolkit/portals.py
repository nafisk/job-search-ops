"""Historical search registry and fail-closed readiness check; no portal access."""
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from contracts import check, digest, text, texts, timestamp
from sheet_values import safe_url

def json_data(value):
    if type(value) is dict:
        check(all(type(k) is str for k in value), "metadata", "JSON object keys must be strings")
        for item in value.values():
            json_data(item)
    elif type(value) is list:
        for item in value:
            json_data(item)
    else:
        check(value is None or type(value) in (str, bool, int) or type(value) is float and isfinite(value),
              "metadata", "finite JSON values required")


def validate_registry(registry):
    check(type(registry) is dict and set(registry) == {"schema_version", "profile_id", "scope_evidence", "companies"},
          "registry", "unsupported fields")
    check(type(registry["schema_version"]) is int and registry["schema_version"] == 1, "registry", "unsupported version")
    text(registry["profile_id"], "profile_id")
    texts(registry["scope_evidence"], "scope evidence")
    check(bool(registry["scope_evidence"]), "scope evidence", "required")
    check(type(registry["companies"]) is list and bool(registry["companies"]), "companies", "explicit nonempty scope required")
    for company in registry["companies"]:
        check(type(company) is dict and set(company) == {"company_id", "employer_name", "referral_hold", "scope_refs", "watchlist_rows",
                              "official_urls", "historical_evidence", "searches"}, "company", "unsupported fields")
        text(company["company_id"], "company ID")
        text(company["employer_name"], "employer name")
        check(type(company["referral_hold"]) is bool, "referral hold", "explicit state required")
        texts(company["scope_refs"], "company scope evidence")
        check(bool(company["scope_refs"]), "company scope evidence", "required")
        check(type(company["watchlist_rows"]) is list and all(type(r) is int and r > 0 for r in company["watchlist_rows"]),
              "watchlist rows", "positive observed rows required")
        check(type(company["official_urls"]) is list, "official URLs", "list required")
        for observed in company["official_urls"]:
            check(type(observed) is dict and set(observed) == {"url", "evidence_ref"}, "official URL", "URL and evidence required")
            safe_url(observed["url"])
            text(observed["evidence_ref"], "URL evidence")
        check(type(company["historical_evidence"]) is dict, "historical evidence", "source detail required")
        check(type(company["searches"]) is list and bool(company["searches"]), "searches", "declared scope required")
        for search in company["searches"]:
            check(type(search) is dict and set(search) == {"search_id", "label", "observed_urls", "evidence_refs", "details"},
                  "search", "unsupported fields")
            text(search["search_id"], "search ID")
            text(search["label"], "scope label")
            texts(search["observed_urls"], "observed URLs")
            for url in search["observed_urls"]:
                safe_url(url)
            texts(search["evidence_refs"], "search evidence")
            check(bool(search["evidence_refs"]), "search evidence", "required even when URL is unknown")
            check(type(search["details"]) is dict, "search details", "explicit metadata required")
        texts([s["search_id"] for s in company["searches"]], "search IDs")
    texts([c["company_id"] for c in registry["companies"]], "company IDs")
    texts([c["employer_name"].casefold() for c in registry["companies"]], "employer names")
    json_data(registry)
    return deepcopy(registry)


@dataclass(frozen=True)
class SearchValidation:
    """Accepted current portal readback, supplied by host; saved history cannot mint this."""
    profile_digest: str
    company_digest: str
    search_id: str
    entry_url: str
    checked_at: str
    first_page_verified: bool
    filters_verified: bool
    pagination_verified: bool
    evidence_ref: str


def prepare_search(profile, registry, company_id, search_id, *, as_of, max_age_days, proof=None):
    """Return a verified entry point or explicit needs_validation; never fetch or infer a URL."""
    validate_registry(registry)
    check(registry["profile_id"] == profile["profile_id"], "profile", "registry belongs to another profile")
    check(type(max_age_days) in (int, float) and max_age_days >= 0, "freshness", "nonnegative age required")
    digest(max_age_days)
    now = timestamp(as_of)
    company = next((c for c in registry["companies"] if c["company_id"] == company_id), None)
    check(company is not None, "company", "not in declared scope")
    search = next((s for s in company["searches"] if s["search_id"] == search_id), None)
    check(search is not None, "search", "not in declared scope")
    reasons = []
    bound = (type(proof) is SearchValidation and proof.profile_digest == digest(profile)
             and proof.company_digest == digest(company) and proof.search_id == search_id)
    if not bound:
        reasons.append("Current independent entry/filter/pagination validation is required")
    else:
        safe_url(proof.entry_url)
        text(proof.evidence_ref, "validation evidence")
        for flag in (proof.first_page_verified, proof.filters_verified, proof.pagination_verified):
            check(type(flag) is bool, "validation", "explicit boolean evidence required")
        if not all((proof.first_page_verified, proof.filters_verified, proof.pagination_verified)):
            reasons.append("First page, displayed filters or pagination remain unverified")
        age = (now - timestamp(proof.checked_at)).total_seconds() / 86400
        if age < 0 or age > max_age_days:
            reasons.append("Portal validation is stale or future-dated")
    return {"status": "needs_validation" if reasons else "ready", "company_id": company_id, "search_id": search_id,
            "entry_url": None if reasons else proof.entry_url, "reasons": reasons,
            "referral_hold": company["referral_hold"], "discovery_complete": False}
