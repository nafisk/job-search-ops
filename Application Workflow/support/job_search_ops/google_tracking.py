"""Plan evidence-reviewed Google tracking edits; native tools execute the batch.

Reuses the discovery writer's ownership, attempt, reconciliation and readback
protocol. No connector, account access or application-status inference lives here.
"""
from __future__ import annotations

import re

from . import queue as q, sheets

FIELDS = {"Application Status", "Notes", "Referral Contact"}


def validate_plan(value, workbook_id, hash_field):
    plan = q.read(value)
    required = {"workbook_id", hash_field, "updates"}
    if not isinstance(plan, dict) or set(plan) not in (required, required | {"new_records"}) or plan["workbook_id"] != workbook_id:
        raise q.ProtocolError(f"Tracking plan must bind workbook_id, {hash_field} and updates")
    additions = plan.get("new_records", [])
    if not re.fullmatch(r"[0-9a-f]{64}", str(plan[hash_field])) or not isinstance(plan["updates"], list) or not isinstance(additions, list) or not 1 <= len(plan["updates"]) + len(additions) <= 1000:
        raise q.ProtocolError("Invalid tracking plan hash or update count")
    for item in plan["updates"]:
        if not isinstance(item, dict) or set(item) != {"job_key", "field", "old_value", "new_value", "evidence_ref"}:
            raise q.ProtocolError("Tracking update requires key, field, old/new value and evidence_ref")
        q.identifier(item["job_key"])
        if item["field"] not in FIELDS:
            raise q.ProtocolError("Tracking update can only change status, notes or referral contact")
        q.text(item["old_value"], "old tracking value", 8000, empty=True)
        q.text(item["new_value"], "new tracking value", 8000, empty=True)
        q.text(item["evidence_ref"], "reviewed tracking evidence", 2000)
        if item["old_value"] == item["new_value"]:
            raise q.ProtocolError("Tracking update must change the reviewed value")
        if item["field"] == "Application Status" and item["new_value"] not in sheets.STATUSES:
            raise q.ProtocolError("Unknown application status")
    for item in additions:
        required = {"job_key", "company", "title", "url", "status", "observed_at", "evidence_ref", "role_evidence_ref"}
        if not isinstance(item, dict) or set(item) != required:
            raise q.ProtocolError("New tracking record requires exact role identity, verified URL, status/date and application plus role evidence references")
        q.identifier(item["job_key"])
        q.url(item["url"])
        q.timestamp(item["observed_at"])
        for field in ("company", "title", "evidence_ref", "role_evidence_ref"):
            q.text(item[field], "tracking " + field, 2000)
        if item["status"] not in {"Applied", "Interviewing", "Rejected", "Closed"}:
            raise q.ProtocolError("New tracking records require actual application/interview status evidence")
    q.canonical(plan)
    return plan


def review(snapshot, workbook_id):
    snap = sheets.Snapshot(snapshot, workbook_id)
    return {"workbook_id": workbook_id, "expected_state_sha256": q.digest(snap.state()), "jobs": [
        {"job_key": values["Job Key"], "company": values["Company"], "title": values["Title"],
         "url": snap.link_target(snap.tables["Jobs"]["cells"][(row, snap.tables["Jobs"]["headers"]["Job Link"])]),
         "values": {field: values[field] for field in sorted(FIELDS)}}
        for row, values in snap.rows("Jobs")]}


def describe_updates(snapshot, updates):
    """Freeze public role identities separately from private tracking evidence."""
    jobs = sheets._index(snapshot, "Jobs", "Job Key")
    result = []
    for item in updates:
        if item["job_key"] not in jobs:
            raise q.ProtocolError("Tracking job key is missing")
        row, values = jobs[item["job_key"]]
        q.text(values["Company"], "saved company", 2000)
        q.text(values["Title"], "saved title", 2000)
        result.append(dict(item, company=values["Company"], title=values["Title"],
                           url=snapshot.link_target(snapshot.tables["Jobs"]["cells"][(row, snapshot.tables["Jobs"]["headers"]["Job Link"])])))
    return result


def validate_identities(base, workbook_id, snapshot, plan, accepted_links=None):
    """Resolve accepted identities before accepting any tracking append.

    An existing role still needs an expected-old-value update. A new-record
    proposal cannot implicitly replace its manual status, notes or canonical URL.
    """
    accepted = sheets._accepted_links(base, workbook_id) if accepted_links is None else accepted_links
    aliases, urls, _ = sheets._role_history(base, workbook_id, accepted)
    jobs = sheets._index(snapshot, "Jobs", "Job Key")
    for item in plan["updates"]:
        canonical = aliases.get(item["job_key"], item["job_key"])
        if canonical != item["job_key"]:
            raise q.ProtocolError(f"Tracking update uses an accepted alias; review canonical Job Key {canonical} and its expected old value")
        if canonical not in jobs:
            raise q.ProtocolError("Tracking job key is missing")
    for item in plan.get("new_records", []):
        matches = {mapping[value] for mapping, value in ((aliases, item["job_key"]), (urls, item["url"])) if value in mapping}
        if len(matches) > 1:
            raise q.ProtocolError("Conflicting tracking identity: accepted job key and URL resolve to different canonical roles")
        if matches:
            canonical = matches.pop()
            raise q.ProtocolError(f"Tracking record already exists as canonical Job Key {canonical}; review an expected-old-value update")
        # Also reject duplicate identity proposals within this exact plan.
        aliases[item["job_key"]] = item["job_key"]
        urls[item["url"]] = item["job_key"]


def prepare(root, workbook_id, snapshot, plan, owner="central"):
    if owner != "central" or workbook_id.startswith("local:"):
        raise q.ProtocolError("Only the central coordinator plans Google tracking edits")
    plan = validate_plan(plan, workbook_id, "expected_state_sha256")
    journal_id = q.digest(["google-tracking", plan])
    with q.locked(root) as base:
        from .setup import require_execution
        require_execution(root, "main")
        q.acquire_claim(base, workbook_id, owner)
        for path in (base / "writer/journals").glob("*.json"):
            prior = q.read(path)
            if prior["workbook_id"] != workbook_id:
                continue
            if prior["journal_id"] == journal_id and prior["status"] != "cancelled":
                return prior
            if prior["status"] not in {"committed", "cancelled"}:
                raise q.ProtocolError("Reconcile the outstanding writer journal before tracking edits")
        for path in (base / "writer/local-tracking").glob("*.json"):
            record = q.read(path)
            if record.get("workbook_id") == workbook_id and record.get("status") != "committed":
                raise q.ProtocolError("Reconcile the outstanding local tracking journal")
        snap = sheets.Snapshot(snapshot, workbook_id)
        before = snap.state()
        if q.digest(before) != plan["expected_state_sha256"]:
            raise q.ProtocolError("Workbook changed since tracking review; review fresh values")
        jobs = sheets._index(snap, "Jobs", "Job Key")
        accepted = sheets._accepted_links(base, workbook_id)
        links, destinations = {}, set()
        for entry in before["Jobs"]["rows"]:
            key, url = entry["values"]["Job Key"], entry["url"]
            if accepted.get(key) != url or url in destinations:
                raise q.ProtocolError("Tracking requires independent accepted role URLs and unique destinations")
            links[key] = {"url": url}
            destinations.add(url)
        validate_identities(base, workbook_id, snap, plan, accepted)
        changes, coordinates = [], set()
        def put(tab, row, field, value):
            table = snap.summary if tab == "Daily Summary" else snap.tables[tab]
            col = table["headers"][field]
            if (tab, row, col) in coordinates:
                raise q.ProtocolError("Duplicate tracking target")
            coordinates.add((tab, row, col))
            changes.append({"tab": tab, "row": row, "column": col,
                            "before": table["cells"].get((row, col), {}).get("userEnteredValue", {}),
                            "after": value if isinstance(value, dict) else sheets.native(value)})
        tracking_changes = describe_updates(snap, plan["updates"])
        for item in plan["updates"]:
            row, values = jobs[item["job_key"]]
            if values[item["field"]] != item["old_value"]:
                raise q.ProtocolError("Changed old tracking value; review fresh evidence")
            put("Jobs", row, item["field"], item["new_value"])
        policy = q.read(base / "approved-policies.json")
        if policy.get("workbook_id") != workbook_id:
            raise q.ProtocolError("Approved policy belongs to another workbook")
        next_rows = {tab: max((row for row, _ in snap.rows(tab)), default=3) + 1 for tab in ("Jobs", "Job Sources")}
        insertion_starts = dict(next_rows)
        addition_rows = []
        for item in plan.get("new_records", []):
            links[item["job_key"]] = {"url": item["url"]}
            date = sheets.serial(item["observed_at"], policy["timezone"])
            fields = dict(zip(sheets.JOBS, [date, date, item["company"], item["title"], sheets.hyperlink(item["url"]), item["status"], "Tracking evidence", "", "", "", "", "Application evidence; discovery screening not evaluated", 1, "Tracked application: " + item["evidence_ref"], item["job_key"]]))
            event = q.digest(["tracking", item["job_key"], item["evidence_ref"]])
            source_fields = dict(zip(sheets.SOURCES, [event, item["job_key"], "Tracking evidence", item["job_key"], "tracking", "v1", "not_screened", "", "", item["observed_at"], q.now(), item["url"], "TRACKED_APPLICATION", item["role_evidence_ref"]]))
            addition_rows.append(next_rows["Jobs"])
            for tab, values in (("Jobs", fields), ("Job Sources", source_fields)):
                row = next_rows[tab]
                next_rows[tab] += 1
                for field, value in values.items():
                    put(tab, row, field, value)
        requests, insertions = [], {}
        for tab, end in next_rows.items():
            start = insertion_starts[tab]
            if end > start:
                insertions[tab] = {"start": start, "length": end - start, "before_row_count": snap.tables[tab]["rows"]}
                requests.append({"insertDimension": {"range": {"sheetId": snap.tables[tab]["id"], "dimension": "ROWS", "startIndex": start, "endIndex": end}, "inheritFromBefore": start > 4}})
        if addition_rows:
            # Row insertion can shift references at row 5. Reassert the same
            # summary contract used by discovery-only installations.
            metrics = ["Total jobs", "New", "Saved", "Asked for referral", "Applied", "Interviewing", "Rated companies", "Source sightings"]
            company = sheets.colname(snap.tables["Jobs"]["headers"]["Company"])
            status = sheets.colname(snap.tables["Jobs"]["headers"]["Application Status"])
            rating = sheets.colname(snap.tables["Rated Companies"]["headers"]["Company Key"])
            source = sheets.colname(snap.tables["Job Sources"]["headers"]["Source Event Key"])
            formulas = [f"=COUNTA(Jobs!{company}5:{company})"] + [f'=COUNTIF(Jobs!{status}5:{status},"{name}")' for name in metrics[1:6]] + [f"=COUNTA('Rated Companies'!{rating}5:{rating})", f"=COUNTA('Job Sources'!{source}5:{source})"]
            for row, (metric, formula) in enumerate(zip(metrics, formulas), 4):
                put("Daily Summary", row, "Metric", metric)
                put("Daily Summary", row, "Value", {"formulaValue": formula})
        for change in changes:
            table = snap.summary if change["tab"] == "Daily Summary" else snap.tables[change["tab"]]
            bounds = {"sheetId": table["id"], "startRowIndex": change["row"], "endRowIndex": change["row"] + 1, "startColumnIndex": change["column"], "endColumnIndex": change["column"] + 1}
            requests.append({"updateCells": {"range": bounds, "rows": [{"values": [{"userEnteredValue": change["after"]}]}], "fields": "userEnteredValue"}})
        table = snap.tables["Jobs"]
        for row in addition_rows:
            def bounds(field):
                col = table["headers"][field]
                return {"sheetId": table["id"], "startRowIndex": row, "endRowIndex": row + 1, "startColumnIndex": col, "endColumnIndex": col + 1}
            requests.append({"repeatCell": {"range": bounds("Job Link"), "cell": {"userEnteredFormat": {"textFormat": {}}, "textFormatRuns": []}, "fields": "userEnteredFormat.textFormat.link,textFormatRuns"}})
            for field in ("First Seen", "Last Seen"):
                requests.append({"repeatCell": {"range": bounds(field), "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}}, "fields": "userEnteredFormat.numberFormat"}})
            requests.append({"setDataValidation": {"range": bounds("Application Status"), "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": value} for value in sheets.STATUSES]}, "strict": True, "showCustomUi": True}}})
        if addition_rows:
            key_col = table["headers"]["Job Key"]
            requests.append({"updateDimensionProperties": {"range": {"sheetId": table["id"], "dimension": "COLUMNS", "startIndex": key_col, "endIndex": key_col + 1}, "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
        journal = {"schema_version": 1, "journal_id": journal_id, "operation": "tracking", "provider": "google_sheets", "workbook_id": workbook_id, "owner": owner, "status": "prepared", "prepared_at": q.now(), "policy_sha256": q.digest(policy), "packet_keys": [], "packet_hashes": {}, "before_state": before, "changes": changes, "insertions": insertions, "requests": requests, "new_jobs": [], "source_events": [], "expected_links": links, "attempts": 0, "tracking_plan": plan, "tracking_changes": tracking_changes, "before_geometry": {name: table["rows"] for name, table in snap.tables.items()}}
        q.atomic(sheets._journal_path(base, journal_id), journal)
        return journal
