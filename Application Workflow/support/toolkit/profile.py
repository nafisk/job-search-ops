"""Versioned local configuration validation; no network, effects or state migration."""
import argparse
import json
import math
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PACKAGE_ROOT = Path(__file__).resolve().parent


class ProfileError(ValueError):
    pass


def require(condition, field, reason):
    if not condition:
        raise ProfileError(f"{field}: {reason}")


def fields(value, names, field):
    require(type(value) is dict, field, "must be an object")
    require(set(value) == set(names.split()), field, "missing or unknown fields")


def string(value, field):
    require(type(value) is str and bool(value.strip()), field, "must be a nonempty string")
    require(not any(ord(c) < 32 for c in value), field, "control characters are forbidden")


def identifier(value, field):
    string(value, field)
    require(re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value) is not None,
            field, "must be a lowercase identifier of at most 64 characters")


def strings(value, field, nonempty=False):
    require(type(value) is list, field, "must be a list")
    if nonempty:
        require(bool(value), field, "must not be empty")
    for item in value:
        string(item, field)
    require(len(value) == len(set(value)), field, "duplicate entries")


def integer(value, field, minimum=1):
    require(type(value) is int and value >= minimum, field, f"must be an integer >= {minimum}")


def boolean(value, field):
    require(type(value) is bool, field, "must be a boolean")


def address(value, field):
    string(value, field)
    require(re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value) is not None,
            field, "must be a single email address")


def local_path(value, base, field):
    string(value, field)
    require(not any(mark in value for mark in ("~", "$", "://")),
            field, "use an explicit local path without substitutions")
    path = Path(value)
    try:
        return (path if path.is_absolute() else base / path).resolve()
    except (OSError, RuntimeError, ValueError):
        raise ProfileError(f"{field}: cannot resolve local path") from None


def resolved_private_paths(profile, profile_path):
    base = Path(profile_path).resolve().parent
    values = {"state_root": profile["private"]["state_root"], **profile["private"]["refs"]}
    result = {}
    for key, value in values.items():
        path = local_path(value, base, f"private.{key}")
        require(not path.is_relative_to(PACKAGE_ROOT), f"private.{key}", "must be outside package")
        if key == "state_root":
            require(not PACKAGE_ROOT.is_relative_to(path), "private.state_root", "must not contain package")
        result[key] = str(path)
    return result


def validate_profile(profile, profile_path):
    fields(profile, "schema_version profile_id identity timezone role_policy locations trackers capacity integrations source_access private", "profile")
    require(type(profile["schema_version"]) is int and profile["schema_version"] in (1, 2),
            "schema_version", "unsupported version")
    identifier(profile["profile_id"], "profile_id")
    identity = profile["identity"]
    fields(identity, "display_name account_identity report_recipient", "identity")
    string(identity["display_name"], "identity.display_name")
    for field in ("account_identity", "report_recipient"):
        if profile["schema_version"] == 1 or identity[field] is not None:
            address(identity[field], f"identity.{field}")
    string(profile["timezone"], "timezone")
    try:
        ZoneInfo(profile["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        raise ProfileError("timezone: unknown IANA zone or unavailable timezone data") from None
    policy = profile["role_policy"]
    fields(policy, "version families preferred_levels excluded_duties excluded_levels excluded_employers experience", "role_policy")
    string(policy["version"], "role_policy.version")
    for field in ("families", "preferred_levels", "excluded_duties", "excluded_levels", "excluded_employers"):
        strings(policy[field], f"role_policy.{field}", nonempty=profile["schema_version"] == 1 and field in ("families", "preferred_levels"))
    experience = policy["experience"]
    fields(experience, "max_required_years preferred_required_years senior_low_experience_exception unknown_minimum ambiguous_range", "role_policy.experience")
    for field in ("max_required_years", "preferred_required_years"):
        value = experience[field]
        require(type(value) in (int, float) and (type(value) is int or math.isfinite(value)) and value >= 0,
                f"role_policy.experience.{field}", "must be a finite nonnegative number")
    require(experience["preferred_required_years"] <= experience["max_required_years"],
            "role_policy.experience", "preferred years exceeds maximum")
    boolean(experience["senior_low_experience_exception"], "role_policy.experience.senior_low_experience_exception")
    for field, options in (("unknown_minimum", ("review", "include")),
                           ("ambiguous_range", ("review", "accept_lower_bound"))):
        require(experience[field] in options, f"role_policy.experience.{field}",
                "must be one of " + ", ".join(options))
    locations = profile["locations"]
    fields(locations, "onsite_regions remote_countries residency_region allow_relocation", "locations")
    for field in ("onsite_regions", "remote_countries"):
        strings(locations[field], f"locations.{field}")
    require(profile["schema_version"] == 2 or bool(locations["onsite_regions"] or locations["remote_countries"]), "locations", "must declare geographic scope")
    if profile["schema_version"] == 1 or locations["residency_region"] is not None:
        string(locations["residency_region"], "locations.residency_region")
    boolean(locations["allow_relocation"], "locations.allow_relocation")
    require(type(profile["trackers"]) is dict, "trackers", "must be an object")
    for name, tracker in profile["trackers"].items():
        identifier(name, "trackers key")
        field = f"trackers.{name}"
        fields(tracker, "workbook_id worksheet header_row columns", field)
        string(tracker["workbook_id"], f"{field}.workbook_id")
        string(tracker["worksheet"], f"{field}.worksheet")
        integer(tracker["header_row"], f"{field}.header_row")
        columns = tracker["columns"]
        require(type(columns) is dict and bool(columns), f"{field}.columns", "must be a nonempty object")
        indexes, headers = [], []
        for logical, column in columns.items():
            identifier(logical, f"{field}.columns key")
            fields(column, "index header", f"{field}.columns.{logical}")
            integer(column["index"], f"{field}.columns.{logical}.index")
            string(column["header"], f"{field}.columns.{logical}.header")
            indexes.append(column["index"])
            headers.append(column["header"])
        require(len(set(indexes)) == len(indexes) and len(set(headers)) == len(headers),
                f"{field}.columns", "duplicate index or header")
    capacity = profile["capacity"]
    fields(capacity, "application_pages initial_application_total next_application_additional outreach_drafts workers recruiter_target recruiter_stretch_target", "capacity")
    for field, value in capacity.items():
        integer(value, f"capacity.{field}", 0 if field == "workers" else 1)
    for field in ("initial_application_total", "next_application_additional"):
        require(capacity[field] <= capacity["application_pages"], f"capacity.{field}", "exceeds page ceiling")
    require(capacity["recruiter_target"] <= capacity["recruiter_stretch_target"], "capacity", "target exceeds stretch target")
    integrations = profile["integrations"]
    require(type(integrations) is dict, "integrations", "must be an object")
    for name, integration in integrations.items():
        identifier(name, "integrations key")
        field = f"integrations.{name}"
        fields(integration, "enabled required connection_ref expected_identity", field)
        for flag in ("enabled", "required"):
            boolean(integration[flag], f"{field}.{flag}")
        require(not integration["required"] or integration["enabled"], field, "required integration cannot be disabled")
        for setting in ("connection_ref", "expected_identity"):
            if integration["enabled"]:
                string(integration[setting], f"{field}.{setting}")
            else:
                require(integration[setting] is None, f"{field}.{setting}", "disabled integration must use null")
    access = profile["source_access"]
    fields(access, "google public_portals authenticated_browser email_job_browser read_attempts", "source_access")
    require(access["google"] == "connector_only", "source_access.google", "only connector access supported")
    require(access["public_portals"] == ["background", "builtin_browser"], "source_access.public_portals", "expected background then built-in browser")
    for field in ("authenticated_browser", "email_job_browser"):
        require(access[field] in ("chrome", "edge"), f"source_access.{field}", "requires supported external browser")
    integer(access["read_attempts"], "source_access.read_attempts")
    private = profile["private"]
    fields(private, "state_root refs", "private")
    require(type(private["refs"]) is dict, "private.refs", "must be an object")
    for key in private["refs"]:
        identifier(key, "private.refs key")
        require(key != "state_root", "private.refs", "reserved state_root key")
    for name, integration in integrations.items():
        expected = integration["expected_identity"]
        if isinstance(expected, str) and expected.startswith("private:"):
            require(expected.removeprefix("private:") in private["refs"],
                    f"integrations.{name}.expected_identity", "unknown private identity reference")
    resolved_private_paths(profile, profile_path)
    return profile


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON", "duplicate object key")
        result[key] = value
    return result


def load_profile(path):
    try:
        # ponytail: small local config only; no source documents, accounts or state are loaded here.
        raw = Path(path).read_text(encoding="utf-8")
        profile = json.loads(raw, object_pairs_hook=unique_object)
    except ProfileError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise ProfileError("profile: cannot read valid UTF-8 JSON") from None
    return validate_profile(profile, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        profile = load_profile(args.profile)
    except ProfileError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"status": "configuration_valid", "schema_version": profile["schema_version"],
                      "profile_id": profile["profile_id"], "effects": [],
                      "live_readiness_verified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
