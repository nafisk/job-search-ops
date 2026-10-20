"""Build and verify native Google Sheets requests; the agent invokes the connector.

No Google SDK, credentials, network access, send action, or scheduler lives here.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from . import queue as q

JOBS = ["First Seen", "Last Seen", "Company", "Title", "Job Link", "Application Status", "Source", "Location", "Level", "Referral Contact", "Target Fit", "Fit Reason", "Seen Count", "Notes", "Job Key"]
SOURCES = ["Source Event Key", "Job Key", "Provider", "Source Job ID", "Policy ID", "Policy Version", "Qualification Tier", "Rating", "Rating As Of", "Observed At", "Checked At", "Job Link", "Disposition", "Evidence Link"]
COMPANIES = ["Company Key", "Company", "Rating", "Rating As Of", "Careers URL", "Enabled", "Notes", "Checked At"]
COVERAGE = ["Coverage Key", "Company Key", "Company", "Run ID", "Scope", "Status", "Checked At", "Observed Jobs", "Qualified Jobs", "Notes"]
STATUSES = ["New", "Saved", "Asked for referral", "Referred", "Applied", "Interviewing", "Rejected", "Closed", "Skip"]
SCHEMAS = {"Jobs": JOBS, "Daily Summary": ["Metric", "Value"], "Referral Watchlist": ["Company", "Referral Contact", "Official Careers Search", "Alert Method", "Targeting Notes"], "How to Use": ["Topic", "Instructions"], "Rated Companies": COMPANIES, "Rated Search Coverage": COVERAGE, "Job Sources": SOURCES}
MANAGED = {"Jobs": JOBS, "Job Sources": SOURCES, "Rated Companies": COMPANIES, "Rated Search Coverage": COVERAGE}
CELL_FIELDS = "userEnteredValue,effectiveValue,hyperlink,userEnteredFormat(textFormat),effectiveFormat(textFormat),textFormatRuns"


def workbook_schema():
    return {"schema_version": 1, "header_row": 4, "first_data_row": 5, "tabs": [{"name": name, "headers": headers, "frozen_rows": 4, "hidden_columns": ["Job Key"] if name == "Jobs" else []} for name, headers in SCHEMAS.items()], "job_statuses": STATUSES, "job_providers": ["Official ATS", "LinkedIn", "Simplify"], "cell_fields": CELL_FIELDS}


def colnum(name):
    total = 0
    for letter in name.upper():
        total = total * 26 + ord(letter) - 64
    return total - 1


def colname(index):
    result = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def cellvalue(cell):
    value = cell.get("userEnteredValue", {})
    return next((value[k] for k in ("stringValue", "numberValue", "boolValue", "formulaValue") if k in value), "")


def native(value):
    if value is None or value == "":
        return {}
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, (int, float)):
        q.number(value, "sheet number", low=-1e12, high=1e12)
        return {"numberValue": value}
    return {"stringValue": str(value)}


def hyperlink(url):
    return {"formulaValue": '=HYPERLINK("' + q.url(url).replace('"', '""') + '","Open job")'}


def link_target(cell):
    formula = cell.get("userEnteredValue", {}).get("formulaValue", "")
    match = re.fullmatch(r'=HYPERLINK\("((?:[^"]|"")*)","Open job"\)', formula)
    if not match:
        raise q.ProtocolError("Job Link is not the canonical role-specific hyperlink formula")
    expected = q.url(match.group(1).replace('""', '"'))
    if cell.get("hyperlink") != expected:
        raise q.ProtocolError("Effective clickable Job Link is missing or mismatched")
    links = []
    for style in ("userEnteredFormat", "effectiveFormat"):
        link = cell.get(style, {}).get("textFormat", {}).get("link", {}).get("uri")
        if link:
            links.append(link)
    links.extend(run.get("format", {}).get("link", {}).get("uri") for run in cell.get("textFormatRuns", []) if run.get("format", {}).get("link"))
    if any(link != expected for link in links):
        raise q.ProtocolError("Formatting/rich-text link disagrees with the role URL")
    return expected


def unwrap(value):
    value = q.read(value)
    if isinstance(value, dict) and (value.get("isError") or value.get("error")):
        raise q.ProtocolError("Expected successful native Sheets response")
    if isinstance(value, dict) and "structuredContent" in value:
        return unwrap(value["structuredContent"])
    if isinstance(value, dict) and "content" in value and "sheets" not in value:
        for item in value["content"]:
            if item.get("type") == "text":
                try:
                    parsed = json.loads(item["text"])
                except (ValueError, KeyError):
                    continue
                if isinstance(parsed, dict) and ("sheets" in parsed or "structuredContent" in parsed):
                    return unwrap(parsed)
    if not isinstance(value, dict):
        raise q.ProtocolError("Expected native Sheets JSON")
    return value


def combine_snapshot(metadata, cell_responses, read_ranges, cell_fields=CELL_FIELDS):
    """Combine real bounded connector responses; request ranges remain explicit."""
    result = copy.deepcopy(unwrap(metadata))
    sheets = {s["properties"]["sheetId"]: s for s in result.get("sheets", [])}
    for sheet in sheets.values():
        sheet["data"] = []
    for response in cell_responses:
        response = unwrap(response)
        if response.get("spreadsheetId") != result.get("spreadsheetId"):
            raise q.ProtocolError("Mixed workbook responses")
        for sheet in response.get("sheets", []):
            key = sheet["properties"]["sheetId"]
            if key not in sheets or sheet["properties"].get("title") != sheets[key]["properties"].get("title"):
                raise q.ProtocolError("Sheet identity changed between reads")
            sheets[key]["data"].extend(copy.deepcopy(sheet.get("data", [])))
    result["_read_ranges"] = read_ranges
    result["_cell_fields"] = cell_fields
    return result


class Snapshot:
    provider = "google_sheets"
    link_target = staticmethod(link_target)

    def __init__(self, value, workbook_id):
        raw = unwrap(value)
        if "metadata" in raw:
            raw = combine_snapshot(raw["metadata"], raw["cell_responses"], raw["_read_ranges"], raw.get("_cell_fields", ""))
        if raw.get("spreadsheetId") != workbook_id:
            raise q.ProtocolError("Snapshot workbook does not match configured workbook")
        fields = raw.get("_cell_fields", "")
        for required in ("userEnteredValue", "effectiveValue", "hyperlink", "userEnteredFormat", "effectiveFormat", "textFormatRuns"):
            if required not in fields:
                raise q.ProtocolError(f"Native cell read must request {required}")
        self.raw = raw
        self.tables = {}
        self.summary = None
        for sheet in raw.get("sheets", []):
            props = sheet.get("properties", {})
            name = props.get("title")
            if name not in MANAGED and name != "Daily Summary":
                continue
            if name in self.tables or (name == "Daily Summary" and self.summary is not None):
                raise q.ProtocolError("Duplicate sheet name")
            grid = props.get("gridProperties", {})
            if not isinstance(props.get("sheetId"), int) or not isinstance(grid.get("rowCount"), int) or grid["rowCount"] < 5:
                raise q.ProtocolError("Missing native sheet dimensions")
            cells = {}
            for block in sheet.get("data", []):
                for ri, row in enumerate(block.get("rowData", []), block.get("startRow", 0)):
                    for ci, cell in enumerate(row.get("values", []), block.get("startColumn", 0)):
                        if (ri, ci) in cells and cells[ri, ci] != cell:
                            raise q.ProtocolError("Conflicting overlapping CellData reads")
                        cells[ri, ci] = cell
            headers = {}
            expected_headers = SCHEMAS[name]
            for ci in range(grid.get("columnCount", len(expected_headers))):
                label = cellvalue(cells.get((3, ci), {}))
                if label in expected_headers:
                    if label in headers:
                        raise q.ProtocolError("Duplicate managed header")
                    headers[label] = ci
            if set(headers) != set(expected_headers):
                raise q.ProtocolError(f"Missing/changed {name} headers; setup or explicit migration required")
            self._coverage(name, headers.values(), 12 if name == "Daily Summary" else grid["rowCount"], raw.get("_read_ranges", []))
            table = {"name": name, "id": props["sheetId"], "rows": grid["rowCount"], "columns": grid.get("columnCount", 0), "headers": headers, "cells": cells}
            if name == "Daily Summary":
                if grid["rowCount"] < 12:
                    raise q.ProtocolError("Daily Summary needs the eight managed metric rows")
                self.summary = table
            else:
                self.tables[name] = table
        if set(self.tables) != set(MANAGED):
            raise q.ProtocolError("Snapshot needs all four managed data tabs")
        if self.summary is None:
            raise q.ProtocolError("Snapshot needs Daily Summary A4:B12 for formula verification")

    @staticmethod
    def _coverage(name, columns, rows, ranges):
        spans = {c: [] for c in columns}
        for a1 in ranges:
            match = re.fullmatch(r"(?:'((?:[^']|'')+)'|([^!]+))!\$?([A-Za-z]+)\$?(\d+):\$?([A-Za-z]+)\$?(\d+)", a1)
            if not match:
                raise q.ProtocolError("Read ranges must be bounded, sheet-qualified A1 ranges")
            label = (match[1] or match[2]).replace("''", "'")
            if label != name:
                continue
            c1, c2 = colnum(match[3]), colnum(match[5])
            r1, r2 = int(match[4]) - 1, int(match[6])
            for col in spans:
                if c1 <= col <= c2:
                    spans[col].append((r1, r2))
        for intervals in spans.values():
            end = 3
            for start, stop in sorted(intervals):
                if start > end:
                    break
                end = max(end, stop)
            if end < rows:
                raise q.ProtocolError(f"Incomplete {name} native read coverage")

    def rows(self, name):
        table = self.summary if name == "Daily Summary" else self.tables[name]
        result = []
        for row in range(4, 12 if name == "Daily Summary" else table["rows"]):
            values = {header: cellvalue(table["cells"].get((row, col), {})) for header, col in table["headers"].items()}
            if any(v != "" for v in values.values()):
                result.append((row, values))
        return result

    def state(self):
        # Only user-entered values and link identities participate; computed
        # values and date formatting are not stable comparison tokens.
        result = {}
        for name, table in {**self.tables, "Daily Summary": self.summary}.items():
            rows = []
            for row, values in self.rows(name):
                item = {"row": row, "values": values}
                if name == "Jobs":
                    item["url"] = self.link_target(table["cells"].get((row, table["headers"]["Job Link"]), {}))
                rows.append(item)
            result[name] = {"id": table["id"], "headers": table["headers"], "rows": rows}
        return result


def snapshot_view(value, workbook_id):
    # Local snapshots are constructed from real XLSX bytes, never JSON dressed
    # up as a native Google response. The merge rules share a normalized view.
    if isinstance(value, Snapshot) and value.provider == "local_xlsx":
        if value.raw.get("workbook_id") != workbook_id:
            raise q.ProtocolError("Local snapshot belongs to another workbook")
        return value
    return Snapshot(value, workbook_id)


def serial(value, timezone="UTC"):
    return (q.timestamp(value).astimezone(ZoneInfo(timezone)).date() - dt.date(1899, 12, 30)).days


def event_key(source, event_id):
    return q.digest([source, event_id])


def _index(snapshot, tab, key):
    result = {}
    for row, values in snapshot.rows(tab):
        identity = values[key]
        if not isinstance(identity, str) or not identity or identity in result:
            raise q.ProtocolError(f"Missing/duplicate managed identity in {tab}")
        result[identity] = (row, values)
    return result


def _journal_path(base, journal_id):
    if not re.fullmatch(r"[0-9a-f]{64}", journal_id):
        raise q.ProtocolError("Invalid journal id")
    return base / "writer/journals" / f"{journal_id}.json"


def _accepted_links(base, workbook_id):
    result = {}
    baseline = base / "writer/baseline-links.json"
    if baseline.exists():
        data = q.read(baseline)
        if data.get("workbook_id") != workbook_id:
            raise q.ProtocolError("Baseline link manifest belongs to another workbook")
        for item in data.get("rows", []):
            key = q.identifier(item.get("job_key"))
            q.url(item.get("evidence_url"))
            q.timestamp(item.get("verified_at"))
            result[key] = q.url(item.get("url"))
    for path in (base / "writer/receipts").glob("*.json"):
        receipt = q.read(path)
        if receipt["workbook_id"] != workbook_id:
            continue
        for job in receipt.get("new_jobs", []) + receipt.get("new_records", []):
            prior = result.setdefault(job["job_key"], job["url"])
            if prior != job["url"]:
                raise q.ProtocolError("Conflicting independent accepted link evidence")
    for path in (base / "writer/local-tracking").glob("*.json"):
        record = q.read(path)
        if record.get("workbook_id") != workbook_id or record.get("status") != "committed":
            continue
        for item in record["receipt"].get("new_records", []):
            url = q.url(item["url"])
            if result.setdefault(item["job_key"], url) != url:
                raise q.ProtocolError("Conflicting accepted tracking role evidence")
    return result


def _role_history(base, workbook_id, accepted_links):
    """Restore source-owned identity/restriction facts from verified saves.

    These facts deliberately do not occupy the user's Notes or Referral Contact
    cells. A hold is sticky; a new discovery cannot silently release it.
    """
    aliases = {key: key for key in accepted_links}
    urls = {url: key for key, url in accepted_links.items()}
    restrictions = {}
    receipts = [q.read(path) for path in sorted((base / "writer/receipts").glob("*.json"))]
    receipts = sorted((r for r in receipts if r.get("workbook_id") == workbook_id), key=lambda r: r.get("verified_at", ""))

    def bind(item):
        key = q.identifier(item.get("job_key"), "alias job_key")
        canonical = q.identifier(item.get("canonical_key"), "canonical job_key")
        if canonical not in accepted_links:
            raise q.ProtocolError("Accepted alias has no saved canonical role")
        q.url(item.get("evidence_url"))
        q.text(item.get("quote"), "accepted alias identity evidence", 12000)
        q.timestamp(item.get("verified_at"))
        if aliases.setdefault(key, canonical) != canonical:
            raise q.ProtocolError("Conflicting accepted alias mapping")
        if item.get("url") is not None:
            url = q.url(item["url"])
            if urls.setdefault(url, canonical) != canonical:
                raise q.ProtocolError("Conflicting accepted alias URL")

    for receipt in receipts:
        if receipt.get("status") != "saved":
            raise q.ProtocolError("Only verified saves may restore role history")
        for item in receipt.get("role_aliases", []):
            bind(item)
        for item in receipt.get("referral_restrictions", []):
            key = q.identifier(item.get("job_key"))
            if key not in accepted_links or item.get("url") != accepted_links[key]:
                raise q.ProtocolError("Referral restrictions have no matching saved role")
            prior = restrictions.setdefault(key, dict(item, contacts=[], evidence=[]))
            prior["referral_hold"] = prior.get("referral_hold", False) or item.get("referral_hold", False)
            for contact in item.get("contacts", []):
                q.text(contact, "saved referral contact")
                if contact not in prior["contacts"]:
                    prior["contacts"].append(contact)
            for evidence in item.get("evidence", []):
                if evidence not in prior["evidence"]:
                    prior["evidence"].append(evidence)

    # Older receipts did not carry these facts. Their already-accepted packets
    # remain available for an evidence-bound, read-only upgrade of the history.
    legacy = []
    for receipt in receipts:
        if "role_aliases" in receipt:
            continue
        for key in receipt.get("packet_keys", []):
            paths = [base / "queue" / part / f"{key}.json" for part in ("done", "pending")]
            path = next((path for path in paths if path.exists()), None)
            if path is None:
                raise q.ProtocolError("Accepted legacy source packet is missing; restore it before importing")
            entry = q.read(path)
            packet = q.validate_packet(entry["packet"])
            if entry.get("packet_key") != key or q.digest(packet) != entry.get("packet_sha256") or packet["workbook_id"] != workbook_id:
                raise q.ProtocolError("Accepted legacy source evidence changed")
            legacy.extend(packet["jobs"])
    for job in legacy:
        candidates = {aliases[key] for key in [job["job_key"]] + [a["job_key"] for a in job.get("aliases", [])] if key in aliases}
        if job["url"] in urls:
            candidates.add(urls[job["url"]])
        if len(candidates) != 1:
            raise q.ProtocolError("Legacy accepted role mapping needs explicit reconciliation")
        canonical = candidates.pop()
        evidence = job["qualification"]["evidence"]["identity"]
        for item in [{"job_key": job["job_key"], "url": job["url"], "evidence_url": evidence["url"], "quote": evidence["quote"]}] + job.get("aliases", []):
            bind(dict(item, canonical_key=canonical, verified_at=job["qualification"]["checked_at"]))
        if job.get("referral_hold") or job.get("referral_contact"):
            prior = restrictions.setdefault(canonical, {"job_key": canonical, "company": job["company"], "title": job["title"], "url": accepted_links[canonical], "referral_hold": False, "contacts": [], "evidence": []})
            prior["referral_hold"] = prior["referral_hold"] or job.get("referral_hold", False)
            if job.get("referral_contact") and job["referral_contact"] not in prior["contacts"]:
                prior["contacts"].append(job["referral_contact"])
    return aliases, urls, restrictions


def role_state(root, workbook_id):
    """Read private accepted role facts before any application/referral action."""
    with q.locked(root) as base:
        aliases, urls, restrictions = _role_history(base, workbook_id, _accepted_links(base, workbook_id))
        return {"workbook_id": workbook_id, "aliases": aliases, "alias_urls": urls, "referral_restrictions": [restrictions[key] for key in sorted(restrictions)]}


def prepare(root, workbook_id, snapshot, owner):
    with q.locked(root) as base:
        from .setup import require_execution
        require_execution(root, "main")
        entries = q.pending(root, workbook_id)
        for entry in entries:
            require_execution(root, "blind" if entry["packet"]["source"] == "blind" else "main")
        q.acquire_claim(base, workbook_id, owner)
        for path in (base / "writer/journals").glob("*.json"):
            prior = q.read(path)
            if prior["workbook_id"] == workbook_id and prior["status"] not in {"committed", "cancelled"}:
                if prior.get("operation") == "tracking":
                    raise q.ProtocolError("Reconcile the outstanding tracking journal before discovery")
                return prior
        if not entries:
            return {"status": "empty", "workbook_id": workbook_id}
        snap = snapshot_view(snapshot, workbook_id)
        before = snap.state()
        jobs = _index(snap, "Jobs", "Job Key")
        original_job_keys = set(jobs)
        sources = _index(snap, "Job Sources", "Source Event Key")
        companies = _index(snap, "Rated Companies", "Company Key")
        coverage = _index(snap, "Rated Search Coverage", "Coverage Key")
        next_rows = {name: max((r for r, _ in snap.rows(name)), default=3) + 1 for name in MANAGED}
        insertion_starts = dict(next_rows)
        approved_policy = q.read(base / "approved-policies.json")
        timezone = approved_policy.get("timezone")
        if not isinstance(timezone, str):
            raise q.ProtocolError("Approved installation policy must declare its IANA timezone")
        ZoneInfo(timezone)
        mutations = {}
        new_jobs = []
        source_events = []
        existing_urls = {}
        accepted_links = _accepted_links(base, workbook_id)
        aliases, alias_urls, restrictions = _role_history(base, workbook_id, accepted_links)
        role_aliases, referral_updates = [], []
        touched_restrictions = set()
        for key, (row, values) in jobs.items():
            url = snap.link_target(snap.tables["Jobs"]["cells"][(row, snap.tables["Jobs"]["headers"]["Job Link"])])
            if accepted_links.get(key) != url:
                raise q.ProtocolError("Saved role lacks matching independent accepted link evidence; verify adoption/repair separately")
            if url in existing_urls and existing_urls[url] != key:
                raise q.ProtocolError("Two saved identities share one destination; reconcile before import")
            existing_urls[url] = key
        def put(tab, row, field, value, formula=False):
            table = snap.summary if tab == "Daily Summary" else snap.tables[tab]
            col = table["headers"][field]
            entered = value if formula else native(value)
            old = table["cells"].get((row, col), {}).get("userEnteredValue", {})
            if entered != old:
                mutations[(tab, row, col)] = {"tab": tab, "row": row, "column": col, "before": old, "after": entered}
        def append(tab, fields):
            row = next_rows[tab]
            next_rows[tab] += 1
            for field, value in fields.items():
                put(tab, row, field, value, field == "Job Link" and tab == "Jobs")
            return row
        for entry in entries:
            packet = q.validate_packet(entry["packet"])
            q.validate_policy(base, packet)
            if entry["packet_sha256"] != q.digest(packet):
                raise q.ProtocolError("Queued packet bytes changed")
            for job in packet["jobs"]:
                key = job["job_key"]
                mapped = {aliases[alias["job_key"]] for alias in job.get("aliases", []) if alias["job_key"] in aliases}
                if key in jobs:
                    mapped.add(key)
                if key in aliases:
                    mapped.add(aliases[key])
                if job["url"] in existing_urls:
                    mapped.add(existing_urls[job["url"]])
                if job["url"] in alias_urls:
                    mapped.add(alias_urls[job["url"]])
                if len(mapped) > 1:
                    raise q.ProtocolError("Conflicting cross-source identity mapping")
                canonical_key = next(iter(mapped), key)
                if canonical_key not in jobs and canonical_key != key:
                    raise q.ProtocolError("Accepted canonical role is missing from the tracker")
                if canonical_key in jobs and jobs[canonical_key][1]["Company"].strip().casefold() != job["company"].strip().casefold():
                    raise q.ProtocolError("Company conflicts with saved stable job identity")
                evidence = job["qualification"]["evidence"]["identity"]
                assertions = [{"job_key": key, "url": job["url"], "evidence_url": evidence["url"], "quote": evidence["quote"]}] + job.get("aliases", [])
                for alias in assertions:
                    alias_key = alias["job_key"]
                    prior_key = aliases.get(alias_key)
                    prior_url = alias_urls.get(alias.get("url"))
                    if prior_key is not None and prior_key != canonical_key:
                        raise q.ProtocolError("Ambiguous verified alias")
                    if prior_url is not None and prior_url != canonical_key:
                        raise q.ProtocolError("Ambiguous verified alias URL")
                    aliases[alias_key] = canonical_key
                    if alias.get("url"):
                        alias_urls[alias["url"]] = canonical_key
                    if prior_key is None or (alias.get("url") and prior_url is None):
                        role_aliases.append(dict(alias, canonical_key=canonical_key, verified_at=job["qualification"]["checked_at"]))
                if job.get("referral_hold") or job.get("referral_contact"):
                    canonical = jobs[canonical_key][1] if canonical_key in jobs else {"Company": job["company"], "Title": job["title"]}
                    identity = {"job_key": canonical_key, "company": canonical["Company"], "title": canonical["Title"], "url": accepted_links.get(canonical_key, next((u for u, k in existing_urls.items() if k == canonical_key), job["url"]))}
                    restriction = restrictions.setdefault(canonical_key, dict(identity, referral_hold=False, contacts=[], evidence=[]))
                    new_hold = job.get("referral_hold", False) and not restriction["referral_hold"]
                    new_contact = bool(job.get("referral_contact")) and job["referral_contact"] not in restriction["contacts"]
                    restriction["referral_hold"] = restriction["referral_hold"] or new_hold
                    if new_contact:
                        restriction["contacts"].append(job["referral_contact"])
                    if new_hold or new_contact:
                        restriction["evidence"].append({"source": packet["source"], "packet_key": entry["packet_key"], "checked_at": job["qualification"]["checked_at"], "identity": evidence})
                        referral_updates.append(dict(identity, referral_hold_added=new_hold, referral_contact_added=new_contact))
                    touched_restrictions.add(canonical_key)
                    for saved in new_jobs:
                        if saved["job_key"] == canonical_key:
                            saved["referral_hold"] = restriction["referral_hold"]
                events = []
                for event in job["sightings"]:
                    eid = event_key(packet["source"], event["id"])
                    if eid in sources:
                        prior = sources[eid][1]
                        if prior["Job Key"] != canonical_key or prior["Source Job ID"] != job["source_job_id"]:
                            raise q.ProtocolError("Source event replay points to another identity")
                        continue
                    events.append(event)
                    fields = dict(zip(SOURCES, [eid, canonical_key, job["provider"], job["source_job_id"], packet["policy"]["id"], packet["policy"]["version"], job["qualification"]["tier"], job.get("rating", ""), job.get("rating_as_of", ""), event["observed_at"], job["qualification"]["checked_at"], job["url"], "QUALIFY", job["qualification"]["evidence"]["requirements"]["url"]]))
                    row = append("Job Sources", fields)
                    sources[eid] = (row, fields)
                    source_events.append(eid)
                if not events:
                    continue
                first, last = min(serial(e["observed_at"], timezone) for e in events), max(serial(e["observed_at"], timezone) for e in events)
                if canonical_key in jobs:
                    row, fields = jobs[canonical_key]
                    old_count = fields["Seen Count"]
                    if isinstance(old_count, bool) or not isinstance(old_count, (int, float)) or old_count < 1 or int(old_count) != old_count:
                        raise q.ProtocolError("Invalid existing Seen Count")
                    old_last = fields["Last Seen"]
                    q.number(old_last, "Last Seen")
                    fields["Seen Count"] = int(old_count) + len(events)
                    fields["Last Seen"] = max(old_last, last)
                    if canonical_key not in original_job_keys:
                        fields["First Seen"] = min(fields["First Seen"], first)
                        put("Jobs", row, "First Seen", fields["First Seen"])
                    put("Jobs", row, "Seen Count", fields["Seen Count"])
                    put("Jobs", row, "Last Seen", fields["Last Seen"])
                else:
                    notes = job.get("notes", "")
                    if job["qualification"]["tier"] != "core":
                        notes = job["qualification"]["tier"] + ": " + job.get("experience", "") + ". " + notes
                    values = [first, last, job["company"], job["title"], hyperlink(job["url"]), "New", job["provider"], job["location"], job.get("level", ""), "", job.get("target_fit", ""), job["fit_reason"], len(events), notes, canonical_key]
                    fields = dict(zip(JOBS, values))
                    row = append("Jobs", fields)
                    fields["Job Link"] = values[4]["formulaValue"]
                    jobs[canonical_key] = (row, fields)
                    existing_urls[job["url"]] = canonical_key
                    new_jobs.append({"job_key": canonical_key, "company": job["company"], "title": job["title"], "url": job["url"], "source": packet["source"], "policy": packet["policy"], "tier": job["qualification"]["tier"], "referral_hold": job.get("referral_hold", False)})
            for company in packet.get("companies", []):
                key = company["company_key"]
                fields = dict(zip(COMPANIES, [key, company["company"], company["rating"], company["rating_as_of"], company["careers_url"], True, "User-supplied rating list", company["checked_at"]]))
                if key in companies:
                    row, old = companies[key]
                    if q.timestamp(company["checked_at"]) <= q.timestamp(old["Checked At"]):
                        continue
                    for field in ("Rating", "Rating As Of", "Careers URL", "Checked At"):
                        put("Rated Companies", row, field, fields[field])
                        old[field] = fields[field]
                else:
                    row = append("Rated Companies", fields)
                    companies[key] = (row, fields)
            for item in packet.get("coverage", []):
                key = q.digest([packet["source"], packet["packet_id"], item["company_key"], item["scope"]])
                if key in coverage:
                    continue
                fields = dict(zip(COVERAGE, [key, item["company_key"], item["company"], packet["packet_id"], item["scope"], item["status"], item["checked_at"], item.get("observed_jobs"), item.get("qualified_jobs"), item.get("notes", "")]))
                row = append("Rated Search Coverage", fields)
                coverage[key] = (row, fields)
        requests = []
        insertions = {}
        for tab, end in next_rows.items():
            start = insertion_starts[tab]
            if end > start:
                insertions[tab] = {"start": start, "length": end - start, "before_row_count": snap.tables[tab]["rows"]}
                requests.append({"insertDimension": {"range": {"sheetId": snap.tables[tab]["id"], "dimension": "ROWS", "startIndex": start, "endIndex": end}, "inheritFromBefore": start > 4}})
        # Inserting at the range's first row can move Google formula references
        # down. Reassert the full managed summary after all insertions.
        metrics = ["Total jobs", "New", "Saved", "Asked for referral", "Applied", "Interviewing", "Rated companies", "Source sightings"]
        company_col = colname(snap.tables["Jobs"]["headers"]["Company"])
        status_col = colname(snap.tables["Jobs"]["headers"]["Application Status"])
        rating_col = colname(snap.tables["Rated Companies"]["headers"]["Company Key"])
        source_col = colname(snap.tables["Job Sources"]["headers"]["Source Event Key"])
        ends = {name: str(max(1000, end + 100)) if snap.provider == "local_xlsx" else "" for name, end in next_rows.items()}
        formulas = [f"=COUNTA(Jobs!{company_col}5:{company_col}{ends['Jobs']})"] + [f'=COUNTIF(Jobs!{status_col}5:{status_col}{ends["Jobs"]},"{name}")' for name in metrics[1:6]] + [f"=COUNTA('Rated Companies'!{rating_col}5:{rating_col}{ends['Rated Companies']})", f"=COUNTA('Job Sources'!{source_col}5:{source_col}{ends['Job Sources']})"]
        for row, (metric, formula) in enumerate(zip(metrics, formulas), 4):
            for field, entered in (("Metric", native(metric)), ("Value", {"formulaValue": formula})):
                col = snap.summary["headers"][field]
                mutations[("Daily Summary", row, col)] = {"tab": "Daily Summary", "row": row, "column": col, "before": snap.summary["cells"].get((row, col), {}).get("userEnteredValue", {}), "after": entered}
        changes = list(mutations.values())
        for change in changes:
            table = snap.summary if change["tab"] == "Daily Summary" else snap.tables[change["tab"]]
            requests.append({"updateCells": {"range": {"sheetId": table["id"], "startRowIndex": change["row"], "endRowIndex": change["row"] + 1, "startColumnIndex": change["column"], "endColumnIndex": change["column"] + 1}, "rows": [{"values": [{"userEnteredValue": change["after"]}]}], "fields": "userEnteredValue"}})
        jobs_table = snap.tables["Jobs"]
        requests.append({"updateDimensionProperties": {"range": {"sheetId": jobs_table["id"], "dimension": "COLUMNS", "startIndex": jobs_table["headers"]["Job Key"], "endIndex": jobs_table["headers"]["Job Key"] + 1}, "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
        for job in new_jobs:
            row = jobs[job["job_key"]][0]
            link_col = jobs_table["headers"]["Job Link"]
            requests.append({"repeatCell": {"range": {"sheetId": jobs_table["id"], "startRowIndex": row, "endRowIndex": row + 1, "startColumnIndex": link_col, "endColumnIndex": link_col + 1}, "cell": {"userEnteredFormat": {"textFormat": {}}, "textFormatRuns": []}, "fields": "userEnteredFormat.textFormat.link,textFormatRuns"}})
            for field in ("First Seen", "Last Seen"):
                col = jobs_table["headers"][field]
                requests.append({"repeatCell": {"range": {"sheetId": jobs_table["id"], "startRowIndex": row, "endRowIndex": row + 1, "startColumnIndex": col, "endColumnIndex": col + 1}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}}, "fields": "userEnteredFormat.numberFormat"}})
            col = jobs_table["headers"]["Application Status"]
            requests.append({"setDataValidation": {"range": {"sheetId": jobs_table["id"], "startRowIndex": row, "endRowIndex": row + 1, "startColumnIndex": col, "endColumnIndex": col + 1}, "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in STATUSES]}, "strict": True, "showCustomUi": True}}})
        journal_id = q.digest([workbook_id, [e["packet_key"] for e in entries], q.digest(before)])
        journal = {"schema_version": 1, "journal_id": journal_id, "workbook_id": workbook_id, "owner": owner, "status": "prepared", "prepared_at": q.now(), "policy_sha256": q.digest(q.read(base / "approved-policies.json")), "packet_keys": [e["packet_key"] for e in entries], "packet_hashes": {e["packet_key"]: e["packet_sha256"] for e in entries}, "before_state": before, "changes": changes, "insertions": insertions, "requests": requests, "new_jobs": new_jobs, "source_events": source_events, "expected_links": {key: {"url": url} for url, key in existing_urls.items()}, "attempts": 0}
        journal.update(role_aliases=role_aliases, referral_restrictions=[restrictions[key] for key in sorted(touched_restrictions)], referral_updates=referral_updates)
        journal["provider"] = snap.provider
        if snap.provider == "local_xlsx":
            journal.update(requests=[], insertions={})
        q.atomic(_journal_path(base, journal_id), journal)
        return journal


def _load(base, journal_id):
    journal = q.read(_journal_path(base, journal_id))
    claim = q.claim_path(base, journal["workbook_id"])
    if not claim.exists() or q.read(claim)["owner"] != journal["owner"]:
        raise q.ProtocolError("Journal no longer owns workbook")
    return journal


def authorize_write(root, journal_id, fresh_snapshot):
    """Call immediately before connector mutation. Records uncertain attempt first."""
    with q.locked(root) as base:
        from .setup import require_execution
        require_execution(root, "main")
        journal = _load(base, journal_id)
        if journal["status"] not in {"prepared", "retryable"}:
            raise q.ProtocolError("Write already attempted; use reconciliation")
        if journal.get("provider", "google_sheets") == "google_sheets" and journal["status"] == "retryable" and not _settled(journal, journal.get("settlement_evidence")):
            raise q.ProtocolError("Retry requires settlement for the current write attempt")
        if q.digest(q.read(base / "approved-policies.json")) != journal["policy_sha256"]:
            raise q.ProtocolError("Approved policy changed after planning")
        for key in journal["packet_keys"]:
            entry = q.read(base / "queue/pending" / f"{key}.json")
            if q.digest(entry["packet"]) != journal["packet_hashes"][key]:
                raise q.ProtocolError("Queued evidence changed after planning")
            require_execution(root, "blind" if entry["packet"]["source"] == "blind" else "main")
            q.validate_policy(base, entry["packet"])
        view = snapshot_view(fresh_snapshot, journal["workbook_id"])
        if view.provider != journal.get("provider", "google_sheets"):
            raise q.ProtocolError("Readback provider differs from journal")
        actual = view.state()
        if journal.get("operation") == "tracking" and {name: table["rows"] for name, table in view.tables.items()} != journal["before_geometry"]:
            raise q.ProtocolError("Workbook geometry changed since tracking planning; cancel and re-plan")
        if actual != journal["before_state"]:
            raise q.ProtocolError("User edit, sort, or other change since planning; cancel unattempted plan and re-plan")
        if journal.get("operation") == "tracking":
            from .google_tracking import validate_identities
            validate_identities(base, journal["workbook_id"], view, journal["tracking_plan"])
        recorded_at = q.now()
        attempt = journal["attempts"] + 1
        attempt_id = q.digest([journal_id, journal["workbook_id"], attempt, recorded_at])
        journal.update(status="write_pending", attempts=attempt, attempt_id=attempt_id, attempt_recorded_at=recorded_at)
        # A settled earlier call cannot settle the new call. Keep its audit
        # record separately, but require fresh evidence for this attempt.
        journal.pop("settlement_evidence", None)
        q.atomic(_journal_path(base, journal_id), journal)
        return {"spreadsheet_id": journal["workbook_id"], "requests": journal["requests"], "journal_id": journal_id, "attempt_id": attempt_id, "attempt_recorded_at": recorded_at, "attempts": attempt}


def _expected(journal):
    state = copy.deepcopy(journal["before_state"])
    rows = {tab: {r["row"]: r for r in value["rows"]} for tab, value in state.items()}
    for change in journal["changes"]:
        tab, row = change["tab"], change["row"]
        record = rows[tab].setdefault(row, {"row": row, "values": {h: "" for h in state[tab]["headers"]}})
        field = next(h for h, col in state[tab]["headers"].items() if col == change["column"])
        record["values"][field] = cellvalue({"userEnteredValue": change["after"]})
        if tab == "Jobs" and field == "Job Link":
            match = re.fullmatch(r'=HYPERLINK\("((?:[^"]|"")*)","Open job"\)', change["after"]["formulaValue"])
            record["url"] = match[1].replace('""', '"')
    for tab in state:
        state[tab]["rows"] = [v for _, v in sorted(rows[tab].items()) if any(x != "" for x in v["values"].values())]
    return state


def _commit(base, journal, snapshot):
    actual = snapshot.state()
    if journal.get("operation") == "tracking":
        expected_geometry = {name: rows + journal["insertions"].get(name, {}).get("length", 0) for name, rows in journal["before_geometry"].items()}
        if {name: table["rows"] for name, table in snapshot.tables.items()} != expected_geometry:
            raise q.ProtocolError("Tracking readback geometry differs from the planned workbook")
    if actual != _expected(journal):
        raise q.ProtocolError("Readback differs from exact planned values or preserved manual fields")
    for row in actual["Jobs"]["rows"]:
        expected = journal["expected_links"].get(row["values"]["Job Key"])
        if expected is None or row["url"] != expected["url"]:
            raise q.ProtocolError("Independent per-role URL manifest mismatch")
    for key in journal["packet_keys"]:
        pending = base / "queue/pending" / f"{key}.json"
        done = base / "queue/done" / f"{key}.json"
        entry = q.read(pending if pending.exists() else done)
        if entry["packet_sha256"] != journal["packet_hashes"][key] or q.digest(entry["packet"]) != journal["packet_hashes"][key]:
            raise q.ProtocolError("Packet changed before receipt installation")
    receipt_id = journal["journal_id"]
    path = base / "writer/receipts" / f"{receipt_id}.json"
    if path.exists():
        receipt = q.read(path)
    else:
        receipt = {"schema_version": 1, "receipt_id": receipt_id, "workbook_id": journal["workbook_id"], "verified_at": q.now(), "packet_keys": journal["packet_keys"], "new_jobs": journal["new_jobs"], "new_source_events": len(journal["source_events"]), "readback_sha256": q.digest(snapshot.raw), "status": "saved"}
        if journal.get("operation") != "tracking":
            receipt.update({key: journal.get(key, []) for key in ("role_aliases", "referral_restrictions", "referral_updates")})
        if journal.get("operation") == "tracking":
            receipt.update(operation="tracking", provider="google_sheets", updates=journal["tracking_plan"]["updates"], new_records=journal["tracking_plan"].get("new_records", []), tracking_changes=journal["tracking_changes"], verification="native_cell_readback")
        if snapshot.provider == "local_xlsx":
            receipt.update(provider="local_xlsx", path=snapshot.raw["path"], file_sha256=snapshot.raw["file_sha256"], verification="reopened_xlsx_ooxml")
        q.atomic(path, receipt)
    # Receipt-first recovery is idempotent if the process stops during queue moves.
    for key in journal["packet_keys"]:
        pending = base / "queue/pending" / f"{key}.json"
        done = base / "queue/done" / f"{key}.json"
        entry = q.read(pending if pending.exists() else done)
        if entry["packet_sha256"] != journal["packet_hashes"][key]:
            raise q.ProtocolError("Packet changed before receipt installation")
        entry["receipt_id"] = receipt_id
        q.atomic(done, entry)
        if pending.exists():
            pending.unlink()
    journal.update(status="committed", receipt_id=receipt_id, committed_at=q.now())
    q.atomic(_journal_path(base, journal["journal_id"]), journal)
    return receipt


def verify_and_commit(root, journal_id, readback_snapshot):
    with q.locked(root) as base:
        journal = _load(base, journal_id)
        if journal["status"] == "committed":
            return q.read(base / "writer/receipts" / f"{journal_id}.json")
        if journal["status"] != "write_pending":
            raise q.ProtocolError("Record the write attempt before accepting its result")
        view = snapshot_view(readback_snapshot, journal["workbook_id"])
        if view.provider != journal.get("provider", "google_sheets"):
            raise q.ProtocolError("Readback provider differs from journal")
        return _commit(base, journal, view)


def _settled(journal, settlement):
    if settlement is None:
        return False
    evidence = q.read(settlement)
    if not isinstance(evidence, dict) or evidence.get("journal_id") != journal["journal_id"]:
        raise q.ProtocolError("Settlement evidence must bind this journal")
    if not isinstance(journal.get("attempt_id"), str) or not journal["attempt_id"] or evidence.get("attempt_id") != journal["attempt_id"]:
        raise q.ProtocolError("Settlement evidence must bind the current attempt_id")
    checked = q.timestamp(evidence.get("verified_at"))
    if not q.timestamp(journal.get("attempt_recorded_at")) <= checked <= q.timestamp(q.now()):
        raise q.ProtocolError("Settlement time must follow the current attempt and cannot be in the future")
    if evidence.get("kind") == "native_terminal_failure":
        response = q.read(evidence.get("response"))
        if isinstance(response, dict) and "structuredContent" in response:
            response = response["structuredContent"]
        error = response.get("error", {}) if isinstance(response, dict) else {}
        if not isinstance(error, dict) or type(error.get("code")) is not int or error["code"] not in {400, 401, 403, 404, 409, 412, 422}:
            raise q.ProtocolError("Timeouts, 5xx and generic tool errors do not prove the write settled")
        return True
    if evidence.get("kind") == "human_reconciled":
        q.text(evidence.get("human_turn_ref"), "human confirmation reference")
        if evidence.get("confirmation") != "The previous connector operation has ended; no pending call can still apply this batch.":
            raise q.ProtocolError("Explicit settled-operation human confirmation is required")
        return True
    raise q.ProtocolError("Unknown settlement evidence kind")


def reconcile(root, journal_id, snapshot, settlement=None):
    """Inspect actual native cells after uncertain writes; never resend automatically."""
    with q.locked(root) as base:
        journal = _load(base, journal_id)
        if journal["status"] == "committed":
            return q.read(base / "writer/receipts" / f"{journal_id}.json")
        if journal["status"] not in {"write_pending", "conflict", "retryable", "awaiting_settlement"}:
            raise q.ProtocolError("Only an attempted write needs reconciliation")
        snap = Snapshot(snapshot, journal["workbook_id"])
        actual = snap.state()
        geometry = {name: table["rows"] for name, table in snap.tables.items()}
        expected_geometry = {name: rows + journal["insertions"].get(name, {}).get("length", 0) for name, rows in journal.get("before_geometry", {}).items()}
        geometry_matches = journal.get("operation") != "tracking" or geometry == expected_geometry
        if actual == _expected(journal) and geometry_matches:
            return _commit(base, journal, snap)
        if actual == journal["before_state"]:
            if (journal.get("operation") == "tracking" and geometry != journal["before_geometry"]) or any(snap.tables[tab]["rows"] != insertion["before_row_count"] for tab, insertion in journal["insertions"].items()):
                # Blank inserted rows are not ownership evidence. A partial effect
                # or concurrent resize requires explicit repair, not another insert.
                journal["status"] = "conflict"
            else:
                evidence = q.read(settlement) if settlement is not None else journal.get("settlement_evidence")
                journal["status"] = "retryable" if _settled(journal, evidence) else "awaiting_settlement"
                if evidence is not None:
                    journal["settlement_evidence"] = evidence
                    history = journal.setdefault("settled_attempts", [])
                    if not any(item.get("attempt_id") == journal["attempt_id"] for item in history):
                        history.append(copy.deepcopy(evidence))
        else:
            journal["status"] = "conflict"
        journal["reconciled_at"] = q.now()
        q.atomic(_journal_path(base, journal_id), journal)
        actions = {"retryable": "Reauthorize against fresh readback", "awaiting_settlement": "The snapshot is unchanged, but the prior operation may still finish. Supply terminal native failure or explicit human settlement evidence.", "conflict": "Inspect mixed/user-edited cells or changed geometry; no automatic retry or claim takeover"}
        return {"status": journal["status"], "journal_id": journal_id, "attempt_id": journal.get("attempt_id"), "attempt_recorded_at": journal.get("attempt_recorded_at"), "attempts": journal["attempts"], "action": actions[journal["status"]]}


def cancel_unattempted(root, journal_id, owner):
    with q.locked(root) as base:
        journal = _load(base, journal_id)
        if journal["owner"] != owner or journal["status"] != "prepared" or journal["attempts"]:
            raise q.ProtocolError("Only the owner can cancel an unattempted plan")
        journal.update(status="cancelled", cancelled_at=q.now())
        q.atomic(_journal_path(base, journal_id), journal)
        return {"status": "cancelled", "journal_id": journal_id}
