"""Project saved discovery data for the selected presentation workbook."""

import re

from . import queue as q, setup, sheets
from .config import REPO_ROOT, filesystem_contains, local_path, no_symlink, read_json, require


TABS = {"email": "LinkedIn Alerts", "blind": "Blind Research", "portal": "Referral Portals"}
HEADERS = ["Found on", "Company", "Job title", "Location", "Official posting URL", "Min. years", "Fit"]
EXTRA = {"blind": "Blind rating"}
FIT = {"core": "Core", "stretch": "Stretch", "senior_exception": "Senior exception"}


STATUS_HEADER = "Application status"
STATUSES = ("Not applied", "Applied", "On hold")
URL_INDEX = HEADERS.index("Official posting URL")


def posting_headers(source):
    extra = [EXTRA[source]] if source in EXTRA else []
    return [*HEADERS, *extra, STATUS_HEADER]


def _settings_path(base):
    return no_symlink(base / "discovery-export.json")


def _settings(base):
    path = _settings_path(base)
    settings = read_json(path) if path.exists() else {"destination": "off"}
    require(isinstance(settings, dict), "export settings", "expected a JSON object")
    return settings


def _destination(root, settings, tracker):
    destination = settings.get("destination")
    if destination == "local_xlsx":
        path = local_path(settings.get("local_path"), root, "export path", absolute=True)
        require(path.suffix.lower() == ".xlsx" and not filesystem_contains(REPO_ROOT, path),
                "export path", "choose a private .xlsx outside the repository")
        tracker_path = tracker.get("path")
        if tracker_path:
            other = no_symlink(tracker_path)
            require(path != other and not filesystem_contains(other, path),
                    "export path", "choose a separate file from the jobs tracker")
        return {"destination": destination, "path": str(path)}
    if destination == "google_sheets":
        spreadsheet_id = settings.get("google_spreadsheet_id")
        identity = settings.get("google_identity")
        require(isinstance(spreadsheet_id, str) and re.fullmatch(r"[A-Za-z0-9_-]+", spreadsheet_id)
                and spreadsheet_id != tracker.get("resource_id"),
                "export spreadsheet", "use the verified native ID of a separate export workbook")
        q.text(identity, "verified Google connector identity")
        return {"destination": destination, "spreadsheet_id": spreadsheet_id, "google_identity": identity}
    require(destination == "off", "export destination", "choose off, local_xlsx or google_sheets")
    return {"destination": "off"}


def select(config, destination, *, local=None, spreadsheet_id=None, google_identity=None):
    root = config["instance_root"]
    with q.locked(root) as base:
        tracker = setup.load_instance(config)["resources"].get("tracker:tracker", {})
        require(tracker.get("status") == "verified", "export", "bind the jobs tracker first")
        settings = _settings(base)
        settings["destination"] = destination
        if local is not None:
            require(destination == "local_xlsx", "export path", "select local_xlsx to bind a file")
            settings["local_path"] = local
        if spreadsheet_id is not None or google_identity is not None:
            require(destination == "google_sheets" and spreadsheet_id and google_identity,
                    "export spreadsheet", "bind the verified native ID and connector identity together")
            settings.update(google_spreadsheet_id=spreadsheet_id, google_identity=google_identity)
        selected = _destination(root, settings, tracker)
        q.atomic(_settings_path(base), settings)
    return selected


def _accepted_packets(base, workbook_id):
    for receipt in q._saved_receipts(base):
        if receipt["workbook_id"] != workbook_id:
            continue
        for key in receipt.get("packet_keys", []):
            file = next((p for state in ("done", "pending")
                         if (p := base / "queue" / state / f"{key}.json").is_file()), None)
            require(file is not None, "export", "restore the accepted source packet before exporting")
            entry = q.read(file)
            packet = q.validate_packet(entry["packet"])
            require(entry.get("packet_key") == key and entry["packet_sha256"] == q.digest(packet)
                    and packet["workbook_id"] == workbook_id,
                    "export", "accepted source evidence differs")
            yield packet


def _posting_tabs(base, workbook_id, timezone):
    aliases, urls, _ = sheets._role_history(base, workbook_id, sheets._accepted_links(base, workbook_id))
    findings = {source: {} for source in TABS}
    for packet in _accepted_packets(base, workbook_id):
        source = packet["source"]
        for job in packet["jobs"]:
            key = aliases.get(job["job_key"]) or urls.get(job["url"])
            require(key is not None, "export", "missing accepted role identity")
            first = min(sheets.serial(event["observed_at"], timezone) for event in job["sightings"])
            qualification = job["qualification"]
            newest = q.timestamp(qualification["checked_at"]), packet["packet_id"]
            fields = [job["company"], job["title"], job["location"], job["url"],
                      qualification["required_years"], FIT[qualification["tier"]]]
            if source == "blind":
                fields.append(job["rating"])
            prior = findings[source].get(key)
            if prior:
                first = min(first, prior[0])
                if prior[1] > newest:
                    newest, fields = prior[1:]
            findings[source][key] = first, newest, fields
    tabs = {}
    for source, title in TABS.items():
        jobs = findings[source]
        ordered = sorted(jobs.values(), key=lambda item: (-item[0], item[2][0], item[2][3]))
        tabs[title] = {
            "headers": posting_headers(source),
            "rows": [[first, *fields, STATUSES[0]] for first, _, fields in ordered],
            "url_aliases": {url: jobs[key][2][3] for url, key in urls.items()
                            if key in jobs and url != jobs[key][2][3]},
        }
    return tabs


def merge_status(plan, current):
    """Carry a destination's manually selected status through refresh and sorting."""
    require(isinstance(plan, dict), "export plan", "expected a prepared export object")
    tabs = plan.get("tabs")
    require(isinstance(tabs, dict) and set(tabs) == set(TABS.values()),
            "export plan", "prepare a current three-tab export first")
    require(isinstance(current, dict) and set(current) == set(tabs),
            "export readback", "provide the current posting rows for all three tabs")
    merged = {}
    for source, title in TABS.items():
        tab = tabs[title]
        width = len(posting_headers(source))
        require(tab["headers"] == posting_headers(source), title, "unexpected export headers")
        require(isinstance(current[title], list), title, "expected posting rows")
        known = {row[URL_INDEX] for row in tab["rows"]}
        saved = {}
        for row in current[title]:
            require(isinstance(row, list), title, "expected a posting row")
            if all(value in ("", None) for value in row):
                continue
            require(len(row) in (width - 1, width), title, "unexpected posting column count")
            url = q.url(row[URL_INDEX])
            url = tab["url_aliases"].get(url, url)
            status = row[-1] if len(row) == width else None
            if status in ("", None):
                status = STATUSES[0]
            require(status in STATUSES, title, "unexpected application status")
            require(url in known or status == STATUSES[0], title,
                    "a previously marked posting is missing from the export")
            require(saved.setdefault(url, status) == status, title,
                    "conflicting statuses for the same posting")
        rows = [[*row[:-1], saved.get(row[URL_INDEX], STATUSES[0])] for row in tab["rows"]]
        merged[title] = {**tab, "rows": rows}
    return {**plan, "tabs": merged}


def prepare(config):
    root = config["instance_root"]
    with q.locked(root) as base:
        tracker = setup.load_instance(config)["resources"].get("tracker:tracker", {})
        selected = _destination(root, _settings(base), tracker)
        if selected["destination"] == "off":
            return selected
        setup.require_execution(root, "main")
        require(tracker.get("status") == "verified", "export", "bind the jobs tracker first")
        return selected | {"tabs": _posting_tabs(base, tracker["resource_id"], config["_profile"]["timezone"])}
