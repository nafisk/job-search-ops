"""Assemble saved native Google Sheets reads without inventing read coverage."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .config import ConfigError, require, unique_object


CELL_FIELDS = ("userEnteredValue,effectiveValue,hyperlink,"
               "userEnteredFormat(textFormat),effectiveFormat(textFormat),textFormatRuns")


def read_data(path):
    """Native payloads have a separate ceiling from small installation settings.

    ponytail: 128 MiB per local payload is the single-host v1 ceiling. Split native
    requests, or stop for reviewed archival/migration when full coverage exceeds it.
    """
    source = Path(path)
    require(source.stat().st_size <= 128 * 1024 * 1024, "native data", "payload exceeds 128 MiB; review archival/migration")
    return json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ConfigError("native data: nonfinite number")))


def unwrap(value):
    """Accept raw JSON or a normal MCP structured/text-content response wrapper."""
    if isinstance(value, (str, Path)):
        value = read_data(value)
    for _ in range(5):
        require(isinstance(value, dict), "native response", "expected a JSON object")
        require(not value.get("isError") and not value.get("error"), "native response", "tool reported an error")
        if isinstance(value.get("structuredContent"), dict):
            value = value["structuredContent"]
            continue
        if "content" in value and not any(k in value for k in ("sheets", "spreadsheetId", "id")):
            blocks = [x.get("text") for x in value["content"]
                      if isinstance(x, dict) and x.get("type") == "text"]
            require(len(blocks) == 1, "native response", "save the native JSON text result separately")
            try:
                value = json.loads(blocks[0])
            except (ValueError, TypeError):
                raise ConfigError("native response: text is not JSON") from None
            continue
        return value
    raise ConfigError("native response: too many wrappers")


def assemble(metadata, cell_reads):
    """Combine actual metadata with saved {request, response} CellData reads.

    Read ranges come from the requests the agent executed, never from the cells
    returned (Google omits trailing empty cells). Empty ranges are still meaningful
    only when their native request succeeded. This is evidence preservation, not
    cryptographic attestation of a tool invocation.
    """
    meta = unwrap(metadata)
    require(isinstance(meta.get("spreadsheetId"), str), "metadata", "missing native spreadsheetId")
    require(isinstance(meta.get("sheets"), list) and meta["sheets"], "metadata", "missing sheets")
    result = copy.deepcopy(meta)
    by_id = {}
    for sheet in result["sheets"]:
        props = sheet.get("properties", {})
        require(type(props.get("sheetId")) is int and isinstance(props.get("title"), str),
                "metadata", "sheetId/title required")
        require(props["sheetId"] not in by_id, "metadata", "duplicate sheetId")
        sheet["data"] = []
        by_id[props["sheetId"]] = sheet
    require(isinstance(cell_reads, list) and cell_reads, "reads", "at least one native read required")
    ranges, masks = [], []
    for read in cell_reads:
        require(isinstance(read, dict) and set(read) == {"request", "response"}, "read", "expected request and response")
        request = read["request"]
        require(isinstance(request, dict), "read request", "expected object")
        requested = request.get("ranges")
        mask = request.get("cell_fields")
        require(isinstance(requested, list) and requested and all(isinstance(x, str) and "!" in x for x in requested),
                "read request", "preserve actual bounded A1 ranges")
        require(isinstance(mask, str) and mask, "read request", "preserve explicit cell_fields")
        request_id = request.get("spreadsheet_id", meta["spreadsheetId"])
        require(request_id == meta["spreadsheetId"], "read request", "workbook mismatch")
        native = unwrap(read["response"])
        require(native.get("spreadsheetId") == meta["spreadsheetId"], "read response", "workbook mismatch")
        require(isinstance(native.get("sheets"), list), "read response", "missing native sheets")
        for sheet in native["sheets"]:
            props = sheet.get("properties", {})
            sheet_id = props.get("sheetId")
            require(sheet_id in by_id, "read response", "unknown sheetId")
            if "title" in props:
                require(props["title"] == by_id[sheet_id]["properties"]["title"], "read response", "sheet title changed")
            require(isinstance(sheet.get("data", []), list), "read response", "missing grid data array")
            by_id[sheet_id]["data"].extend(copy.deepcopy(sheet.get("data", [])))
        ranges.extend(requested)
        masks.append(mask)
    # Each range must have the complete mask, so don't union complementary masks.
    require(len(set(masks)) == 1, "reads", "use one complete CellData mask for every range")
    result["_read_ranges"] = ranges
    result["_cell_fields"] = masks[0]
    return result
