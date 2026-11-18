"""Seed a private referral scope into either tracker, then publish its registry.

The company file is authoritative. This setup-only bridge never replaces a
nonblank watchlist row, clears a hold, or invents observed portal evidence.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import shutil

from . import queue as q, sheets, setup
from .config import execution_plan, no_symlink, read_json, require

TAB = "Referral Watchlist"
OWNER = "referral-setup"


def validate_source(value):
    require(type(value) is dict and set(value) == {"schema_version", "companies"} and type(value["schema_version"]) is int and value["schema_version"] == 1,
            "referrals", "expected schema_version 1 and companies")
    require(type(value["companies"]) is list and bool(value["companies"]), "referrals", "select at least one company or disable portal discovery")
    seen_ids, seen_names = set(), set()
    fields = {"company_id", "company", "referral_contact", "referral_hold", "careers_url", "alert_method", "targeting_notes", "search_scope"}
    for company in value["companies"]:
        require(type(company) is dict and set(company) == fields, "referrals", "use the supplied company example fields")
        q.identifier(company["company_id"], "company_id")
        for field in fields - {"referral_hold"}:
            q.text(company[field], field, empty=field in {"referral_contact", "careers_url", "alert_method", "targeting_notes"})
        require(company["company"] == company["company"].strip(), "referrals", "company name must not have surrounding whitespace")
        require(type(company["referral_hold"]) is bool, "referrals", "referral_hold must be explicit")
        if company["careers_url"]:
            q.url(company["careers_url"])
        key = company["company"].casefold()
        require(company["company_id"] not in seen_ids and key not in seen_names, "referrals", "duplicate company ID or name; reconcile aliases explicitly")
        seen_ids.add(company["company_id"]); seen_names.add(key)
    return copy.deepcopy(value)


def context(config):
    require("portal" in execution_plan(config)["discovery"], "referrals", "portal discovery is not selected")
    manifest = setup.load_instance(config)
    binding = manifest["resources"].get("tracker:tracker", {})
    require(binding.get("status") == "verified", "referrals", "bind and verify the tracker first")
    path = no_symlink(config["sources"]["referral_companies_path"])
    source = validate_source(read_json(path))
    return binding, path, source


def watchlist(snapshot, workbook_id):
    """Read complete native values; local input must be an actual XLSX snapshot."""
    if isinstance(snapshot, sheets.Snapshot) and snapshot.provider == "local_xlsx":
        require(snapshot.raw["workbook_id"] == workbook_id, "referrals", "wrong workbook")
        cells = {tuple(map(int, key.split(":"))): copy.deepcopy(value) for key, value in snapshot.all_cells[TAB].items()}
        # Local OOXML can encode literal text as a constant-string formula.
        for cell in cells.values():
            formula = cell.get("userEnteredValue", {}).get("formulaValue", "")
            match = sheets.re.fullmatch(r'="((?:[^"]|"")*)"', formula)
            if match:
                cell["userEnteredValue"] = sheets.native(match[1].replace('""', '"'))
        sheet_id, row_count = None, max(12, max((r + 1 for r, _ in cells), default=5))
    else:
        raw = sheets.unwrap(snapshot)
        if "metadata" in raw:
            raw = sheets.combine_snapshot(raw["metadata"], raw["cell_responses"], raw["_read_ranges"], raw.get("_cell_fields", ""))
        require(raw.get("spreadsheetId") == workbook_id and "userEnteredValue" in raw.get("_cell_fields", ""), "referrals", "read native workbook identity and userEnteredValue")
        matches = [s for s in raw.get("sheets", []) if s.get("properties", {}).get("title") == TAB]
        require(len(matches) == 1, "referrals", "need exactly one Referral Watchlist tab")
        tab = matches[0]
        sheet_id = tab["properties"]["sheetId"]
        row_count = tab["properties"]["gridProperties"]["rowCount"]
        require(type(sheet_id) is int and type(row_count) is int and row_count >= 5, "referrals", "missing native dimensions")
        sheets.Snapshot._coverage(TAB, range(5), row_count, raw.get("_read_ranges", []))
        cells = {}
        for block in tab.get("data", []):
            for row, data in enumerate(block.get("rowData", []), block.get("startRow", 0)):
                for col, cell in enumerate(data.get("values", []), block.get("startColumn", 0)):
                    require((row, col) not in cells or cells[row, col] == cell, "referrals", "conflicting overlapping readback")
                    cells[row, col] = cell
    require([sheets.cellvalue(cells.get((3, col), {})) for col in range(5)] == sheets.SCHEMAS[TAB], "referrals", "watchlist headers changed")
    rows = []
    for row in range(4, row_count):
        values = [sheets.cellvalue(cells.get((row, col), {})) for col in range(5)]
        if any(value != "" for value in values):
            require(all(type(value) is str and "formulaValue" not in cells.get((row, col), {}).get("userEnteredValue", {}) for col, value in enumerate(values)), "referrals", "watchlist values must be literal text")
            rows.append({"row": row, "values": values})
    return {"sheet_id": sheet_id, "row_count": row_count, "rows": rows}


def _project(company):
    hold = "Referral hold: " + ("yes" if company["referral_hold"] else "no")
    notes = hold + ("\n" + company["targeting_notes"] if company["targeting_notes"] else "")
    return [company["company"], company["referral_contact"], company["careers_url"], company["alert_method"], notes]


def _files(base):
    return no_symlink(base / "writer/referrals/seed.json"), no_symlink(base.parent / "portal-registry.json")


def _release_own_claim(base, workbook_id):
    claim = q.claim_path(base, workbook_id)
    if claim.exists():
        recorded = q.read(claim)
        if recorded.get("owner") == OWNER and recorded.get("workbook_id") == workbook_id:
            claim.unlink()


def prepare(config, snapshot=None):
    binding, source_path, source = context(config)
    if binding["provider"] == "local_xlsx":
        from .local_excel import inspect_workbook
        snapshot = inspect_workbook(binding["path"], binding["resource_id"])
    before = watchlist(snapshot, binding["resource_id"])
    with q.locked(config["instance_root"]) as base:
        journal_path, registry_path = _files(base)
        if journal_path.exists():
            journal = q.read(journal_path)
            require(journal["source_sha256"] == q.digest(source) and journal["workbook_id"] == binding["resource_id"], "referrals", "source changed; preserve history and reconcile the existing seed explicitly")
            require(journal["status"] == "committed" or journal["source_path"] == str(source_path), "referrals", "source path changed")
            if journal["status"] == "committed":
                require(before["rows"] == journal["after_rows"], "referrals", "manual watchlist edit detected; reconcile with the authoritative private list")
                require(registry_path.exists(), "referrals", "accepted portal registry is missing; restore it from the committed seed journal")
                _release_own_claim(base, binding["resource_id"])
            return journal
        q.acquire_claim(base, binding["resource_id"], OWNER)
        try:
            rows = copy.deepcopy(before["rows"])
            known = {}
            for row in rows:
                key = row["values"][0].strip().casefold()
                require(key and key not in known, "referrals", "blank/duplicate watchlist company; reconcile existing rows first")
                known[key] = row
            wanted = {c["company"].casefold() for c in source["companies"]}
            require(set(known) <= wanted, "referrals", "watchlist has companies absent from the private list; reconcile without deleting them")
            changes = []
            registry_companies = []
            for index, company in enumerate(source["companies"]):
                values = _project(company)
                row = known.get(company["company"].casefold())
                if row:
                    require(row["values"] == values, "referrals", "existing contact, hold or notes conflict; reconcile the private list and watchlist explicitly")
                else:
                    row = {"row": max((item["row"] for item in rows), default=3) + 1, "values": values}
                    rows.append(row)
                    for col, value in enumerate(values):
                        changes.append({"tab": TAB, "row": row["row"], "column": col, "before": {}, "after": sheets.native(value)})
                ref = str(source_path) + "#/companies/" + str(index)
                registry_companies.append({"company_id": company["company_id"], "employer_name": company["company"], "referral_hold": company["referral_hold"], "scope_refs": [ref], "watchlist_rows": [row["row"] + 1], "official_urls": [], "historical_evidence": {"source": "user_supplied_unverified", "careers_url": company["careers_url"] or None}, "searches": [{"search_id": "configured-scope", "label": company["search_scope"], "observed_urls": [], "evidence_refs": [ref], "details": {"status": "needs_validation", "scope": company["search_scope"]}}]})
            requests = []
            if before["sheet_id"] is not None:
                if changes:
                    start = min(change["row"] for change in changes)
                    count = len(changes) // 5
                    # Insert instead of overwriting the observed blank rows: a
                    # concurrent manual append survives and fails exact readback.
                    requests.append({"insertDimension": {"range": {"sheetId": before["sheet_id"], "dimension": "ROWS", "startIndex": start, "endIndex": start + count}, "inheritFromBefore": start > 4}})
                for change in changes:
                    requests.append({"updateCells": {"range": {"sheetId": before["sheet_id"], "startRowIndex": change["row"], "endRowIndex": change["row"] + 1, "startColumnIndex": change["column"], "endColumnIndex": change["column"] + 1}, "rows": [{"values": [{"userEnteredValue": change["after"]}]}], "fields": "userEnteredValue"}})
            registry = {"schema_version": 1, "profile_id": config["_profile"]["profile_id"], "scope_evidence": [str(source_path)], "companies": registry_companies}
            journal = {"schema_version": 1, "status": "prepared", "workbook_id": binding["resource_id"], "source_path": str(source_path), "source_sha256": q.digest(source), "before": before, "after_rows": rows, "changes": changes, "requests": requests, "registry": registry, "registry_path": str(registry_path), "provider": binding["provider"]}
            if binding["provider"] == "local_xlsx":
                journal["before_sha256"] = snapshot.raw["file_sha256"]
            q.atomic(journal_path, journal)
            return journal
        except Exception:
            q.claim_path(base, binding["resource_id"]).unlink(missing_ok=True)
            raise


def authorize(config, snapshot):
    binding, _, source = context(config)
    require(binding["provider"] == "google_sheets", "referrals", "use referrals-local for Excel")
    fresh = watchlist(snapshot, binding["resource_id"])
    with q.locked(config["instance_root"]) as base:
        journal_path, _ = _files(base)
        journal = q.read(journal_path)
        require(journal["status"] == "prepared" and fresh == journal["before"] and q.digest(source) == journal["source_sha256"], "referrals", "stale or already attempted seed; read back and reconcile before retrying")
        require(q.read(q.claim_path(base, binding["resource_id"]))["owner"] == OWNER, "referrals", "writer ownership changed")
        journal["status"] = "write_pending"
        journal["attempt"] = journal.get("attempt", 0) + 1
        journal["attempt_id"] = q.digest([journal["workbook_id"], journal["source_sha256"], journal["before"], journal["attempt"]])
        journal["attempted_at"] = q.now()
        q.atomic(journal_path, journal)
        return journal


def commit(config, snapshot=None):
    binding, _, source = context(config)
    if binding["provider"] == "local_xlsx":
        from .local_excel import inspect_workbook
        snapshot = inspect_workbook(binding["path"], binding["resource_id"])
    actual = watchlist(snapshot, binding["resource_id"])
    with q.locked(config["instance_root"]) as base:
        journal_path, registry_path = _files(base)
        journal = q.read(journal_path)
        require(journal["workbook_id"] == binding["resource_id"] and journal["source_sha256"] == q.digest(source), "referrals", "source or workbook changed")
        require(actual["sheet_id"] == journal["before"]["sheet_id"] and actual["rows"] == journal["after_rows"], "referrals", "native watchlist readback differs; registry withheld, do not repeat an uncertain write")
        require(journal["status"] in {"write_pending", "committed"} or not journal["changes"], "referrals", "authorize before writing")
        if journal["status"] == "committed":
            _release_own_claim(base, binding["resource_id"])
            return journal
        claim = q.claim_path(base, binding["resource_id"])
        require(q.read(claim)["owner"] == OWNER, "referrals", "writer ownership changed")
        require(not registry_path.exists() or q.read(registry_path) == journal["registry"], "referrals", "existing registry differs; do not replace research history")
        q.atomic(registry_path, journal["registry"])
        journal.update(status="committed", verified_at=q.now())
        q.atomic(journal_path, journal)
        claim.unlink()
        return journal


def local_seed(config, node, node_modules):
    from . import local_excel as local
    binding, _, _ = context(config)
    require(binding["provider"] == "local_xlsx", "referrals", "local Excel is not selected")
    path = local._path(binding["path"])
    with local._writer_lock(path):
        journal = prepare(config)
        if journal["status"] == "committed":
            return journal
        if journal["status"] == "write_pending" and local.file_hash(path) == journal.get("after_sha256"):
            return commit(config)
        require(local.file_hash(path) == journal["before_sha256"], "referrals", "workbook changed; preserve the seed journal and reconcile")
        before = local.inspect_workbook(path, binding["resource_id"])
        token = q.digest([journal["workbook_id"], journal["source_sha256"]])[:20]
        candidate = no_symlink(path.with_name("." + path.stem + "." + token + ".referrals.xlsx"))
        backup = no_symlink(path.with_name("." + path.stem + "." + token + ".referrals-backup.xlsx"))
        local._artifact(path, candidate, journal["changes"], node, node_modules)
        os.chmod(candidate, 0o600)
        after = local.inspect_workbook(candidate, binding["resource_id"])
        after.validate_layout()
        local._preserved(before, after, journal["changes"])
        require(watchlist(after, binding["resource_id"])["rows"] == journal["after_rows"], "referrals", "candidate readback differs")
        require(local.file_hash(path) == journal["before_sha256"], "referrals", "workbook changed during export")
        if backup.exists():
            require(local.file_hash(backup) == journal["before_sha256"], "referrals", "backup differs")
        else:
            with backup.open("xb") as target, path.open("rb") as original:
                shutil.copyfileobj(original, target)
            os.chmod(backup, 0o600)
            local._sync_file(backup)
        with q.locked(config["instance_root"]) as base:
            journal_path, _ = _files(base)
            require(q.read(q.claim_path(base, binding["resource_id"]))["owner"] == OWNER, "referrals", "writer ownership changed")
            journal.update(status="write_pending", after_sha256=after.raw["file_sha256"], backup=str(backup))
            q.atomic(journal_path, journal)
        local._sync_file(candidate)
        require(local.file_hash(path) == journal["before_sha256"], "referrals", "workbook changed before publication")
        os.replace(candidate, path)
        local._sync_directory(path.parent)
        return commit(config)


def cancel_unattempted(config):
    """Archive an unattempted plan so a corrected source can be prepared safely."""
    manifest = setup.load_instance(config)
    binding = manifest["resources"].get("tracker:tracker", {})
    require(binding.get("status") == "verified", "referrals", "tracker binding missing")
    with q.locked(config["instance_root"]) as base:
        journal_path, _ = _files(base)
        journal = q.read(journal_path)
        require(journal["workbook_id"] == binding["resource_id"] and journal["status"] == "prepared", "referrals", "only an unattempted prepared seed can be cancelled")
        claim = q.claim_path(base, binding["resource_id"])
        require(q.read(claim)["owner"] == OWNER, "referrals", "writer ownership changed")
        journal.update(status="cancelled", cancelled_at=q.now())
        archive = no_symlink(base / "writer/referral-history" / (q.digest(journal) + ".json"))
        q.atomic(archive, journal)
        journal_path.unlink()
        claim.unlink()
        return {"status": "cancelled", "archive": str(archive)}


def require_seed(config):
    """Require accepted setup for a new portal pilot; never writes local state."""
    binding, _, source = context(config)
    journal_path = no_symlink(Path(config["instance_root"]) / "state/writer/referrals/seed.json")
    require(journal_path.is_file(), "referrals", "complete and verify the referral seed before the first portal pilot")
    journal = read_json(journal_path)
    require(journal.get("status") == "committed" and journal.get("workbook_id") == binding["resource_id"] and journal.get("source_sha256") == q.digest(source), "referrals", "first portal pilot needs a committed seed for this tracker and source")
    registry_path = no_symlink(Path(config["instance_root"]) / "portal-registry.json")
    require(registry_path.is_file(), "referrals", "accepted private portal registry is missing")
    registry = read_json(registry_path)
    require(registry.get("schema_version") == 1 and registry.get("profile_id") == config["_profile"]["profile_id"] and type(registry.get("companies")) is list, "referrals", "private portal registry identity differs")
    require(all(type(c) is dict and type(c.get("company_id")) is str for c in registry["companies"]), "referrals", "registry company IDs must be strings")
    companies = {c["company_id"]: c for c in registry["companies"]}
    require(len(companies) == len(registry["companies"]) == len(source["companies"]) and set(companies) == {c["company_id"] for c in source["companies"]}, "referrals", "private portal registry scope differs")
    for company in source["companies"]:
        saved = companies[company["company_id"]]
        require(saved.get("employer_name") == company["company"] and type(saved.get("referral_hold")) is bool and (not company["referral_hold"] or saved["referral_hold"]), "referrals", "registry employer identity or referral hold changed")
    return {"status": "verified", "company_count": len(companies), "registry_path": str(registry_path)}


def retry_google(config, snapshot, settlement):
    """Rearm only an exactly unchanged seed after a terminal native failure."""
    binding, _, source = context(config)
    require(binding["provider"] == "google_sheets", "referrals", "use referrals-local for Excel recovery")
    fresh = watchlist(snapshot, binding["resource_id"])
    with q.locked(config["instance_root"]) as base:
        journal_path, _ = _files(base)
        journal = q.read(journal_path)
        require(journal["status"] == "write_pending" and journal["workbook_id"] == binding["resource_id"] and journal["source_sha256"] == q.digest(source), "referrals", "need the pending seed for this tracker and source")
        require(fresh == journal["before"], "referrals", "watchlist differs from exact before-state; do not repeat inserts")
        require(type(settlement) is dict and settlement.get("kind") == "native_terminal_failure" and settlement.get("attempt_id") == journal.get("attempt_id") and type(journal.get("attempt_id")) is str, "referrals", "terminal failure must bind the exact pending attempt_id")
        checked = q.timestamp(settlement.get("verified_at"))
        require(q.timestamp(journal["attempted_at"]) <= checked <= q.timestamp(q.now()), "referrals", "settlement time must follow the pending attempt")
        response = q.read(settlement.get("response"))
        if type(response) is dict and "structuredContent" in response:
            response = response["structuredContent"]
        error = response.get("error", {}) if type(response) is dict else {}
        require(type(error) is dict and type(error.get("code")) is int and error["code"] in {400, 401, 403, 404, 409, 412, 422}, "referrals", "timeouts, 5xx and generic tool errors do not prove a terminal failure")
        require(q.read(q.claim_path(base, binding["resource_id"]))["owner"] == OWNER, "referrals", "writer ownership changed")
        journal.setdefault("settled_attempts", []).append(copy.deepcopy(settlement))
        journal["status"] = "prepared"
        q.atomic(journal_path, journal)
        return journal
