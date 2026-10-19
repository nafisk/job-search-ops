"""Idempotent native formatting plan after importing the blank tracker.

Produces requests only. The setup agent applies them with the Google connector
and reads back the real workbook before recording its resource binding.
"""
from .config import require
from .snapshots import unwrap


METRICS = ["Total jobs", "New", "Saved", "Asked for referral", "Applied", "Interviewing", "Rated companies", "Source sightings"]


def plan(snapshot):
    from .sheets import SCHEMAS, STATUSES, Snapshot, cellvalue
    raw = unwrap(snapshot)
    workbook_id = raw.get("spreadsheetId")
    checked = Snapshot(raw, workbook_id)
    tables = {s["properties"]["title"]: s for s in raw["sheets"]}
    require(set(SCHEMAS) <= set(tables), "bootstrap", "all seven workbook tabs are required")
    for name, headers in SCHEMAS.items():
        cells = {}
        for block in tables[name].get("data", []):
            for row, item in enumerate(block.get("rowData", []), block.get("startRow", 0)):
                for col, cell in enumerate(item.get("values", []), block.get("startColumn", 0)):
                    cells[row, col] = cell
        require([cellvalue(cells.get((3, i), {})) for i in range(len(headers))] == headers,
                "bootstrap", "imported headers do not match the shipped template")
    # Bootstrap is a fresh-instance operation. Migration must be reviewed separately.
    require(not any(checked.rows(name) for name in checked.tables), "bootstrap", "use only an empty new tracker")
    requests = []
    for name, headers in SCHEMAS.items():
        sheet_id = tables[name]["properties"]["sheetId"]
        requests += [
            {"updateSheetProperties": {"properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 4}}, "fields": "gridProperties.frozenRowCount"}},
        ]
        if name not in ("How to Use", "Daily Summary"):
            requests.append({"setBasicFilter": {"filter": {"range": {"sheetId": sheet_id, "startRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": len(headers)}}}})
    jobs_id = tables["Jobs"]["properties"]["sheetId"]
    requests += [
        {"updateDimensionProperties": {"range": {"sheetId": jobs_id, "dimension": "COLUMNS", "startIndex": 14, "endIndex": 15}, "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}},
        {"setDataValidation": {"range": {"sheetId": jobs_id, "startRowIndex": 4, "startColumnIndex": 5, "endColumnIndex": 6}, "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": x} for x in STATUSES]}, "strict": True, "showCustomUi": True}}},
        {"repeatCell": {"range": {"sheetId": jobs_id, "startRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 2}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}}, "fields": "userEnteredFormat.numberFormat"}}
    ]
    # Google supports open-ended ranges; replace the bounded Excel preview formulas
    # so tracker growth cannot silently fall outside the summary.
    formulas = ["=COUNTA(Jobs!C5:C)"] + [f'=COUNTIF(Jobs!F5:F,"{name}")' for name in METRICS[1:6]] + ["=COUNTA('Rated Companies'!A5:A)", "=COUNTA('Job Sources'!A5:A)"]
    requests.append({"updateCells": {"range": {"sheetId": tables["Daily Summary"]["properties"]["sheetId"], "startRowIndex": 4, "endRowIndex": 12, "startColumnIndex": 0, "endColumnIndex": 2}, "rows": [{"values": [{"userEnteredValue": {"stringValue": name}}, {"userEnteredValue": {"formulaValue": formula}}]} for name, formula in zip(METRICS, formulas)], "fields": "userEnteredValue"}})
    from .sheets import colname
    return {"spreadsheet_id": workbook_id, "requests": requests,
            "include_spreadsheet_in_response": True, "response_include_grid_data": True,
            "response_ranges": [f"'{name}'!A4:{colname(len(headers)-1)}12" for name, headers in SCHEMAS.items()],
            "readback": "Verify all seven headers, frozen rows, Jobs status validation, hidden Job Key, and Daily Summary formulas before resource-record."}


def verify_structure(response, workbook_id):
    """Validate actual updatedSpreadsheet returned by the bootstrap native batch."""
    from .sheets import SCHEMAS, STATUSES
    native = unwrap(response)
    raw = native.get("updatedSpreadsheet", {})
    require(raw.get("spreadsheetId") == workbook_id, "bootstrap readback", "wrong workbook")
    tabs = {s["properties"]["title"]: s for s in raw.get("sheets", [])}
    require(set(SCHEMAS) <= set(tabs), "bootstrap readback", "missing native tabs")
    def cell(name, row, col):
        for block in tabs[name].get("data", []):
            ri, ci = row - block.get("startRow", 0), col - block.get("startColumn", 0)
            rows = block.get("rowData", [])
            if 0 <= ri < len(rows) and 0 <= ci < len(rows[ri].get("values", [])):
                return rows[ri]["values"][ci]
        return {}
    for name, headers in SCHEMAS.items():
        props = tabs[name]["properties"]
        require(props.get("gridProperties", {}).get("frozenRowCount") == 4, "bootstrap readback", "headers are not frozen")
        if name not in ("Daily Summary", "How to Use"):
            bounds = tabs[name].get("basicFilter", {}).get("range", {})
            require(bounds.get("sheetId") == props["sheetId"] and bounds.get("startRowIndex") == 3 and bounds.get("startColumnIndex", 0) == 0 and bounds.get("endColumnIndex") == len(headers), "bootstrap readback", "filter does not cover the data range")
    hidden = []
    for block in tabs["Jobs"].get("data", []):
        index = 14 - block.get("startColumn", 0)
        columns = block.get("columnMetadata", [])
        if 0 <= index < len(columns): hidden.append(columns[index].get("hiddenByUser"))
    require(True in hidden and False not in hidden, "bootstrap readback", "Job Key hiding was not observed")
    rule = cell("Jobs", 4, 5).get("dataValidation", {})
    require(rule.get("strict") is True and rule.get("condition", {}).get("type") == "ONE_OF_LIST" and
            [v.get("userEnteredValue") for v in rule["condition"].get("values", [])] == STATUSES,
            "bootstrap readback", "status choices do not match the schema")
    for col in (0, 1):
        require(cell("Jobs", 4, col).get("userEnteredFormat", {}).get("numberFormat", {}).get("type") == "DATE", "bootstrap readback", "date format is missing")
    formulas = ["=COUNTA(Jobs!C5:C)"] + [f'=COUNTIF(Jobs!F5:F,"{name}")' for name in METRICS[1:6]] + ["=COUNTA('Rated Companies'!A5:A)", "=COUNTA('Job Sources'!A5:A)"]
    for row, formula in enumerate(formulas, 4):
        require(cell("Daily Summary", row, 1).get("userEnteredValue", {}).get("formulaValue") == formula,
                "bootstrap readback", "summary formula mismatch")
    return True
