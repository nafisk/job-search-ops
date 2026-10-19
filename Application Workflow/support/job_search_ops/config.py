"""Versioned choices around the reusable toolkit profile; no connected effects."""
from __future__ import annotations

import copy
import importlib.util
import json
import math
import re
from pathlib import Path


SUPPORT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = SUPPORT_ROOT.parent
REPO_ROOT = WORKFLOW_ROOT.parent
MODULES = ("main", "blind", "calendar", "messages", "excel_export", "manual_outreach")


class ConfigError(ValueError):
    """A bounded, value-free configuration error."""


def require(condition, field, reason):
    if not condition:
        raise ConfigError(f"{field}: {reason}")


def keys(value, expected, field):
    require(type(value) is dict and set(value) == set(expected.split()), field,
            "missing or unknown fields")


def text(value, field):
    require(type(value) is str and bool(value.strip()) and not any(ord(c) < 32 for c in value),
            field, "expected nonempty text without control characters")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON", "duplicate object key")
        result[key] = value
    return result


def read_json(path):
    try:
        p = Path(path)
        require(p.stat().st_size <= 2_000_000, "JSON", "file exceeds configuration limit")
        return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ConfigError("JSON: nonfinite number")))
    except ConfigError:
        raise
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise ConfigError("JSON: cannot read valid bounded UTF-8 JSON") from None


def no_symlink(path):
    """Reject redirected private paths, including a nonexistent child of a symlink."""
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "path", "symlinks are not supported")
    return path


def local_path(value, base, field, *, absolute=False):
    text(value, field)
    require(not any(s in value for s in ("~", "$", "://")), field, "use an explicit local path")
    path = Path(value)
    require(".." not in path.parts, field, "parent traversal is not supported")
    require(not absolute or path.is_absolute(), field, "must be absolute")
    if not path.is_absolute():
        path = base / path
    return no_symlink(path)


def toolkit_profile_module():
    # ponytail: the existing standalone validator has no third-party imports.
    path = SUPPORT_ROOT / "toolkit" / "profile.py"
    require(path.is_file(), "toolkit", "reviewed profile validator is missing")
    spec = importlib.util.spec_from_file_location("job_ops_profile_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public_settings(config):
    """Serializable private settings; excludes transient resolved objects."""
    return {k: copy.deepcopy(v) for k, v in config.items() if not k.startswith("_")}


def execution_plan(config):
    """One selection model for both versions; never rewrite legacy settings."""
    legacy = config["schema_version"] == 1
    modules = config["modules"]
    discovery = {"email": modules["main"], "portals": modules["main"]} if legacy else config["discovery"]
    tracking = {"gmail": modules["main"]} if legacy else config["tracking"]
    tracker = {"provider": "google_sheets", "path": None} if legacy else config["tracker"]
    sources = [name for name, enabled in (("email", discovery["email"]), ("portal", discovery["portals"]), ("blind", modules["blind"])) if enabled]
    tracked = [name for name, enabled in (("gmail", tracking["gmail"]), ("calendar", modules["calendar"]), ("messages", modules["messages"])) if enabled]
    chats = ["central"] + ["portals" if x == "portal" else x for x in sources]
    schedules = [name for name, entry in config["schedules"].items() if entry["enabled"]]
    source_files = [name for name, enabled in (("referral_companies_path", discovery["portals"]), ("rated_companies_path", modules["blind"])) if enabled]
    browser = config.get("_profile", {}).get("integrations", {}).get("browser", {})
    gmail = discovery["email"] or tracking["gmail"] or config["report"]["delivery"] == "email"
    selectors = {
        "always": True, "main": modules["main"], "blind": modules["blind"],
        "email_discovery": discovery["email"], "portal_discovery": discovery["portals"],
        "gmail_read": gmail, "gmail_tracking": tracking["gmail"],
        "google_tracker": tracker["provider"] == "google_sheets", "local_tracker": tracker["provider"] == "local_xlsx",
        "public_research": bool(sources), "delegation": len(chats) > 1,
        "calendar": modules["calendar"], "messages": modules["messages"],
        "manual_outreach": modules["manual_outreach"],
        "authenticated_browser": modules["manual_outreach"] or browser.get("required", False),
        "email_delivery": config["report"]["delivery"] == "email", "scheduled": bool(schedules),
        "artifact_tool": tracker["provider"] == "local_xlsx" or config["adapters"]["spreadsheet_templates"] == "artifact_tool" or modules["excel_export"],
    }
    return {"tracker": copy.deepcopy(tracker), "discovery": sources, "tracking": tracked,
            "chats": chats, "schedules": schedules, "source_files": source_files,
            "staging": ["staging/" + x for x in chats if x != "central"],
            "selectors": selectors}


def load_config(path):
    """Read and validate settings/profile only; never create state or contact accounts."""
    source = no_symlink(Path(path).absolute())
    value = read_json(source)
    require(type(value) is dict and type(value.get("schema_version")) is int and value["schema_version"] in (1, 2),
            "schema_version", "unsupported version")
    legacy = value["schema_version"] == 1
    fields = "schema_version installation_id profile_path instance_root modules candidate blind_policy sources schedules report adapters"
    keys(value, fields + ("" if legacy else " tracker discovery tracking"), "installation")
    require(type(value["installation_id"]) is str and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value["installation_id"]),
            "installation_id", "expected lowercase identifier")
    root = local_path(value["instance_root"], source.parent, "instance_root", absolute=True)
    require(not root.is_relative_to(REPO_ROOT) and not REPO_ROOT.is_relative_to(root),
            "instance_root", "must be separate from the repository")
    require(root != root.parent and len(root.parts) >= 4, "instance_root", "choose a dedicated private subdirectory")
    profile_path = local_path(value["profile_path"], source.parent, "profile_path")
    validator = toolkit_profile_module()
    try:
        profile = validator.load_profile(profile_path)
    except ValueError as error:
        raise ConfigError(str(error)) from None
    require(profile["profile_id"] == value["installation_id"], "profile_id", "must match installation_id")
    resolved = validator.resolved_private_paths(profile, profile_path)
    require(Path(resolved["state_root"]) == root / "state", "private.state_root", "must match instance_root/state")
    for name, ref in resolved.items():
        no_symlink(ref)
        require(not Path(ref).is_relative_to(REPO_ROOT), "private reference", "must be outside repository")

    keys(value["modules"], " ".join(MODULES), "modules")
    require(all(type(v) is bool for v in value["modules"].values()), "modules", "expected booleans")
    if legacy:
        require(value["modules"]["main"] or value["modules"]["blind"], "modules", "enable at least one discovery workflow")
        require(value["modules"]["main"] or not any(value["modules"][x] for x in ("calendar", "messages", "manual_outreach")),
                "modules", "tracking/manual extensions require main")
    else:
        require(value["modules"]["main"], "modules.main", "the central coordinator is required")
        for name, fields in (("discovery", "email portals"), ("tracking", "gmail")):
            keys(value[name], fields, name)
            require(all(type(x) is bool for x in value[name].values()), name, "expected booleans")
        keys(value["tracker"], "provider path", "tracker")
        require(value["tracker"]["provider"] in ("google_sheets", "local_xlsx"), "tracker.provider", "unsupported tracker")
        if value["tracker"]["provider"] == "local_xlsx":
            target = local_path(value["tracker"]["path"], source.parent, "tracker.path", absolute=True)
            require(target.is_relative_to(root) and target.suffix.lower() == ".xlsx", "tracker.path", "choose an .xlsx file inside the private instance")
            require(target.relative_to(root).parts[0] not in {"state", "staging", "prompts", "evidence", "integrations"}, "tracker.path", "use a dedicated workbook path outside managed state")
            value["tracker"]["path"] = str(target)
        else:
            require(value["tracker"]["path"] is None, "tracker.path", "Google tracker uses its verified native ID, not a local path")
        require(any(value["discovery"].values()) or value["modules"]["blind"] or value["tracking"]["gmail"] or value["modules"]["calendar"] or value["modules"]["messages"], "modules", "select discovery or at least one tracking source")
    # Validate the choices used by execution_plan before deriving any selectors.
    keys(value["report"], "delivery send_opt_in", "report")
    keys(value["adapters"], "html_parser simplify_decoder spreadsheet_templates", "adapters")
    keys(value["schedules"], "main blind", "schedules")
    for name, schedule in value["schedules"].items():
        keys(schedule, "enabled local_time notifications", f"schedules.{name}")
        require(type(schedule["enabled"]) is bool, "schedules", "expected boolean")
    plan = execution_plan({**value, "_profile": profile})
    if plan["discovery"]:
        require(bool(profile["role_policy"]["families"] and profile["role_policy"]["preferred_levels"]), "role_policy", "selected discovery needs role families and levels")
        require(bool(profile["locations"]["onsite_regions"] or profile["locations"]["remote_countries"]), "locations", "selected discovery needs geographic scope")
        text(profile["locations"]["residency_region"], "locations.residency_region")
    for name, needed in (("calendar", value["modules"]["calendar"]), ("messages", value["modules"]["messages"]),
                         ("sheets", plan["selectors"]["google_tracker"]), ("mail", plan["selectors"]["gmail_read"]),
                         ("browser", plan["selectors"]["authenticated_browser"])):
        entry = profile["integrations"].get(name)
        require(not needed or (entry and entry["enabled"]), "integrations", "required workflow connection missing")
        if legacy and name in ("calendar", "messages"):
            require(not (entry and entry["required"]) or needed, "integrations", "required source cannot be disabled by installation")
    if plan["selectors"]["google_tracker"] or plan["selectors"]["gmail_read"] or value["modules"]["calendar"]:
        require(profile["identity"]["account_identity"] is not None, "identity.account_identity", "selected Google access needs its account identity")
    if value["report"]["delivery"] == "email":
        require(profile["identity"]["report_recipient"] is not None, "identity.report_recipient", "email delivery needs a named recipient")

    keys(value["candidate"], "actual_experience_years resume_path", "candidate")
    years = value["candidate"]["actual_experience_years"]
    require((not legacy and not plan["discovery"] and years is None) or (type(years) in (int, float) and math.isfinite(years) and years >= 0),
            "candidate.actual_experience_years", "expected finite truthful nonnegative years")
    resume = value["candidate"]["resume_path"]
    if resume is not None:
        resume = local_path(resume, source.parent, "candidate.resume_path", absolute=True)
        require(not resume.is_relative_to(REPO_ROOT), "candidate.resume_path", "must remain outside repository")
        value["candidate"]["resume_path"] = str(resume)
    if legacy or value["modules"]["blind"] or value["blind_policy"] is not None:
        keys(value["blind_policy"], "version max_required_years stretch_required_years exclude_explicit_senior min_rating excluded_title_terms", "blind_policy")
        text(value["blind_policy"]["version"], "blind_policy.version")
        for name in ("max_required_years", "stretch_required_years"):
            years = value["blind_policy"][name]
            require(type(years) in (int, float) and math.isfinite(years) and years >= 0, "blind_policy", "expected finite thresholds")
        require(value["blind_policy"]["stretch_required_years"] >= value["blind_policy"]["max_required_years"], "blind_policy", "stretch must not be below base")
        require(type(value["blind_policy"]["exclude_explicit_senior"]) is bool, "blind_policy", "expected boolean")
        rating = value["blind_policy"]["min_rating"]
        require(type(rating) in (int, float) and math.isfinite(rating) and 0 <= rating <= 5, "blind_policy.min_rating", "expected rating from zero to five")
        terms = value["blind_policy"]["excluded_title_terms"]
        require(type(terms) is list and all(type(x) is str and x.strip() and len(x) <= 100 and not any(ord(c) < 32 for c in x) for x in terms), "blind_policy.excluded_title_terms", "expected bounded literal terms")
        require(len(set(terms)) == len(terms), "blind_policy.excluded_title_terms", "duplicate terms")

    keys(value["sources"], "gmail_queries initial_lookback_days referral_companies_path rated_companies_path", "sources")
    queries = value["sources"]["gmail_queries"]
    require(type(queries) is list and all(type(q) is str and q.strip() and not any(ord(c) < 32 for c in q) for q in queries), "sources.gmail_queries", "expected query list")
    require(len(set(queries)) == len(queries) and (queries or "email" not in plan["discovery"]), "sources.gmail_queries", "missing or duplicate queries")
    days = value["sources"]["initial_lookback_days"]
    require(type(days) is int and 1 <= days <= 365, "sources.initial_lookback_days", "expected 1 to 365")
    for name in ("referral_companies_path", "rated_companies_path"):
        ref = value["sources"][name]
        if ref is not None:
            ref = local_path(ref, source.parent, f"sources.{name}")
            require(not ref.is_relative_to(REPO_ROOT), f"sources.{name}", "private source choices must be outside repository")
            value["sources"][name] = str(ref)

    keys(value["schedules"], "main blind", "schedules")
    for name, schedule in value["schedules"].items():
        keys(schedule, "enabled local_time notifications", f"schedules.{name}")
        require(type(schedule["enabled"]) is bool and (not schedule["enabled"] or value["modules"][name]), "schedules", "schedule requires enabled module")
        require((not legacy and not schedule["enabled"] and schedule["local_time"] is None) or
                (type(schedule["local_time"]) is str and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", schedule["local_time"])), "schedules.local_time", "use HH:MM for an enabled schedule")
        require(schedule["notifications"] in ("meaningful_changes", "failed_runs_only"), "schedules.notifications", "unsupported preference")
    keys(value["report"], "delivery send_opt_in", "report")
    require(value["report"]["delivery"] in ("chat", "email"), "report.delivery", "choose chat or email")
    require(type(value["report"]["send_opt_in"]) is bool, "report.send_opt_in", "expected boolean")
    require(value["report"]["delivery"] != "email" or value["report"]["send_opt_in"], "report", "email requires explicit send opt-in")
    require(value["report"]["delivery"] != "email" or value["modules"]["main"], "report", "email brief requires main workflow")
    require(value["report"]["delivery"] == "email" or not value["report"]["send_opt_in"], "report", "chat delivery must not authorize email")
    keys(value["adapters"], "html_parser simplify_decoder spreadsheet_templates", "adapters")
    require(value["adapters"]["html_parser"] == "stdlib", "adapters", "only the maintained stdlib HTML path is shipped")
    require(value["adapters"]["simplify_decoder"] == "python", "adapters", "only the maintained Python decoder is shipped")
    require(value["adapters"]["spreadsheet_templates"] in ("prebuilt", "artifact_tool"), "adapters", "unsupported template adapter")

    result = copy.deepcopy(value)
    result.update(profile_path=str(root / "profile.json"), instance_root=str(root))
    normalized_profile = copy.deepcopy(profile)
    normalized_profile["private"] = {"state_root": str(root / "state"),
                                     "refs": {key: ref for key, ref in resolved.items() if key != "state_root"}}
    result["_profile"] = normalized_profile
    result["_profile_path"] = str(profile_path)
    result["_config_path"] = str(source)
    result["_private_paths"] = resolved
    return result
