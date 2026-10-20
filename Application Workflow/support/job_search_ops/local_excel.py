"""One local XLSX tracker, edited by the bundled artifact-tool only.

OOXML verifies the actual saved file. A narrowly scoped post-export fallback
restores native hyperlinks and the hidden key column, unsupported by the bundled
artifact API. Ordinary cells/formulas are authored only by artifact-tool.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import fcntl
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr
import zipfile

from . import queue as q, sheets, google_tracking

SUPPORT = Path(__file__).resolve().parents[1]
TEMPLATE = SUPPORT.parent / "sheets/job-search-tracker.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"


def _path(value, *, exists=True):
    path = Path(value).expanduser()
    if not path.is_absolute() or path.suffix.lower() != ".xlsx":
        raise q.ProtocolError("Local tracker must be an absolute .xlsx path")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise q.ProtocolError("Local tracker path must not contain symlinks")
    if exists and (not path.is_file() or path.stat().st_nlink != 1):
        raise q.ProtocolError("Local tracker must be a regular unlinked file")
    if path.with_name("~$" + path.name).exists() or path.with_name(".~lock." + path.name + "#").exists():
        raise q.ProtocolError("Workbook appears open in Excel/LibreOffice; close it before syncing")
    return path


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _part(base, target):
    if target.startswith("/"):
        result = target.lstrip("/")
    else:
        result = str(PurePosixPath(base).parent / target)
    if ".." in PurePosixPath(result).parts:
        raise q.ProtocolError("Unsupported relative workbook relationship")
    return result


def _rels(archive, part):
    name = str(PurePosixPath(part).parent / "_rels" / (PurePosixPath(part).name + ".rels"))
    if name not in archive.namelist():
        return {}
    return {r.attrib["Id"]: dict(r.attrib) for r in ET.fromstring(archive.read(name)).findall(REL)}


def _coordinate(value):
    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", value)
    if not match:
        raise q.ProtocolError("Malformed XLSX cell coordinate")
    return int(match[2]) - 1, sheets.colnum(match[1])


def _entered(cell, strings):
    formula, value = cell.find("m:f", NS), cell.find("m:v", NS)
    if cell.get("t") == "e":
        raise q.ProtocolError("Saved workbook contains a formula error")
    if formula is not None:
        if formula.attrib:
            raise q.ProtocolError("Shared/array formulas require explicit workbook migration")
        literal = re.fullmatch(r'"((?:[^"]|"")*)"', formula.text or "")
        if literal and (value.text if value is not None and value.text is not None else "") != literal[1].replace('""', '"'):
            raise q.ProtocolError("Saved constant-text formula cache differs from its exact text")
        return {"formulaValue": "=" + (formula.text or "")}
    text = value.text if value is not None and value.text is not None else ""
    kind = cell.get("t")
    if kind == "s":
        return sheets.native(strings[int(text)])
    if kind == "inlineStr":
        return sheets.native("".join(n.text or "" for n in cell.findall(".//m:t", NS)))
    if kind in {"str", "d"}:
        return sheets.native(text)
    if kind == "b":
        return sheets.native(text == "1")
    if text:
        number = float(text)
        return sheets.native(int(number) if number.is_integer() else number)
    return {}


class LocalSnapshot(sheets.Snapshot):
    """Explicit local readback with the same normalized merge view as Sheets."""
    provider = "local_xlsx"

    def __init__(self, path, workbook_id):
        path = _path(path)
        q.identifier(workbook_id)
        if not workbook_id.startswith("local:"):
            raise q.ProtocolError("Local tracker identity must start with local:")
        before_hash = file_hash(path)
        self.tables, self.summary, self.all_cells, self.structures, self.styles, self.validations, self.caches = {}, None, {}, {}, {}, {}, {}
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) > 5000 or sum(i.file_size for i in archive.infolist()) > 150_000_000:
                raise q.ProtocolError("Workbook exceeds the supported local tracker size")
            if any(x.startswith(("xl/externalLinks/", "xl/activeX/", "xl/embeddings/", "xl/drawings/", "xl/charts/", "xl/pivot")) or x.endswith("vbaProject.bin") for x in names):
                raise q.ProtocolError("Unsupported workbook feature; use the supplied tracker template")
            book = ET.fromstring(archive.read("xl/workbook.xml"))
            props = book.find("m:workbookPr", NS)
            if props is not None and props.get("date1904") in {"1", "true"}:
                raise q.ProtocolError("1904-date workbooks require explicit migration")
            if book.find("m:workbookProtection", NS) is not None:
                raise q.ProtocolError("Protected workbooks require explicit migration")
            strings = []
            if "xl/sharedStrings.xml" in names:
                strings = ["".join(n.text or "" for n in item.findall(".//m:t", NS)) for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
            relations = _rels(archive, "xl/workbook.xml")
            style_xml = ET.fromstring(archive.read("xl/styles.xml"))
            def node_value(node):
                return [node.tag.rsplit("}", 1)[-1], dict(node.attrib), node.text or "", [node_value(child) for child in node]]
            style_groups = {kind: list(style_xml.find("m:" + kind, NS) or []) for kind in ("cellXfs", "fonts", "fills", "borders")}
            num_formats = {x.get("numFmtId"): x.get("formatCode") for x in style_xml.findall("m:numFmts/m:numFmt", NS)}
            def style_value(index):
                xf = copy.deepcopy(style_groups["cellXfs"][index])
                refs = {}
                for key, group in (("fontId", "fonts"), ("fillId", "fills"), ("borderId", "borders")):
                    refs[group] = node_value(style_groups[group][int(xf.attrib.pop(key, "0"))])
                fmt = xf.attrib.pop("numFmtId", "0")
                refs["numberFormat"] = num_formats.get(fmt, fmt)
                refs["xf"] = node_value(xf)
                return refs
            style_cache = {i: style_value(i) for i in range(len(style_groups["cellXfs"]))}
            listed = book.findall("m:sheets/m:sheet", NS)
            tab_names = [tab.attrib["name"] for tab in listed]
            if len(set(tab_names)) != len(tab_names) or not set(sheets.SCHEMAS).issubset(tab_names):
                raise q.ProtocolError("Local workbook is missing the seven tracker tabs")
            for tab in listed:
                name = tab.attrib["name"]
                relation = relations[tab.attrib["{" + NS["r"] + "}id"]]
                if relation.get("TargetMode") == "External":
                    raise q.ProtocolError("External sheet relationship")
                part = _part("xl/workbook.xml", relation["Target"])
                xml = ET.fromstring(archive.read(part))
                if xml.find("m:sheetProtection", NS) is not None:
                    raise q.ProtocolError("Protected sheets require explicit migration")
                cells = {}
                styles = {}
                caches = {}
                for item in xml.findall("m:sheetData/m:row/m:c", NS):
                    coord = _coordinate(item.attrib["r"])
                    styles[f"{coord[0]}:{coord[1]}"] = style_cache[int(item.get("s", "0"))]
                    value = _entered(item, strings)
                    if value:
                        cells[coord] = {"userEnteredValue": value}
                    if "formulaValue" in value:
                        cache = item.find("m:v", NS)
                        caches[f"{coord[0]}:{coord[1]}"] = cache.text if cache is not None else None
                sheet_rels = _rels(archive, part)
                for link in xml.findall("m:hyperlinks/m:hyperlink", NS):
                    ref = link.attrib["ref"]
                    if ":" in ref:
                        raise q.ProtocolError("Range hyperlinks require explicit workbook migration")
                    coord = _coordinate(ref)
                    rid = link.get("{" + NS["r"] + "}id")
                    if rid:
                        relation = sheet_rels[rid]
                        if relation.get("Type") != NS["r"] + "/hyperlink" or relation.get("TargetMode") != "External":
                            raise q.ProtocolError("Workbook hyperlink needs an actual external hyperlink relationship")
                        target = relation["Target"]
                    else:
                        target = "#" + link.get("location", "")
                    cells.setdefault(coord, {})["xlsx_relationship_target"] = target
                self.all_cells[name] = {f"{r}:{c}": copy.deepcopy(value) for (r, c), value in cells.items()}
                for cell in cells.values():
                    formula = cell.get("userEnteredValue", {}).get("formulaValue", "")
                    literal = re.fullmatch(r'="((?:[^"]|"")*)"', formula)
                    if literal:
                        cell["userEnteredValue"] = {"stringValue": literal[1].replace('""', '"')}
                self.styles[name] = styles
                self.caches[name] = caches
                self.validations[name] = [{"range": x.get("sqref", ""), "type": x.get("type"), "formula": x.findtext("m:formula1", "", NS)} for x in xml.findall("m:dataValidations/m:dataValidation", NS)]
                self.structures[name] = {
                    "merged": sorted(x.attrib["ref"] for x in xml.findall("m:mergeCells/m:mergeCell", NS)),
                    "frozen": [dict(x.attrib) for x in xml.findall("m:sheetViews/m:sheetView/m:pane", NS)],
                    "columns": [dict(x.attrib) for x in xml.findall("m:cols/m:col", NS)],
                    "validations": [node_value(x) for x in xml.findall("m:dataValidations/m:dataValidation", NS)],
                }
                if name not in sheets.SCHEMAS:
                    continue
                headers = {}
                for (r, c), value in cells.items():
                    label = sheets.cellvalue(value)
                    if r == 3 and label in sheets.SCHEMAS[name]:
                        if label in headers:
                            raise q.ProtocolError("Duplicate managed header")
                        headers[label] = c
                if set(headers) != set(sheets.SCHEMAS[name]):
                    raise q.ProtocolError(f"Missing/changed {name} headers")
                table = {"name": name, "id": int(tab.attrib["sheetId"]), "rows": max(12, max((r + 1 for r, _ in cells), default=5)), "columns": max((c + 1 for _, c in cells), default=1), "headers": headers, "cells": cells}
                if name == "Jobs":
                    # The shared planner uses a canonical logical formula. The
                    # actual Excel file uses a native relationship and text label.
                    for (row, col), cell in cells.items():
                        if row >= 4 and col == headers["Job Link"] and sheets.cellvalue(cell) != "":
                            target = self.link_target(cell)
                            cell["userEnteredValue"] = sheets.hyperlink(target)
                if name == "Daily Summary":
                    self.summary = table
                elif name in sheets.MANAGED:
                    self.tables[name] = table
        if file_hash(path) != before_hash:
            raise q.ProtocolError("Workbook changed during readback")
        self.raw = {"provider": self.provider, "workbook_id": workbook_id, "path": str(path), "file_sha256": before_hash, "cells": self.all_cells, "structures": self.structures}
        # Run identity/link validation immediately, including during setup.
        self.state()

    def validate_layout(self):
        for name in sheets.SCHEMAS:
            panes = self.structures[name]["frozen"]
            if not any(float(p.get("ySplit", "0")) == 4 and p.get("state") == "frozen" for p in panes):
                raise q.ProtocolError("Tracker headers must remain frozen at row 4")
        headers = self.tables["Jobs"]["headers"]
        key = headers["Job Key"] + 1
        if not any(int(col["min"]) <= key <= int(col["max"]) and col.get("hidden") in {"1", "true"} for col in self.structures["Jobs"]["columns"]):
            raise q.ProtocolError("The local Job Key column must remain hidden")
        rows = {4, *(row for row, _ in self.rows("Jobs"))}
        for row in rows:
            for field in ("First Seen", "Last Seen"):
                if self.styles["Jobs"].get(f"{row}:{headers[field]}", {}).get("numberFormat") != "yyyy-mm-dd":
                    raise q.ProtocolError("Local job dates need the yyyy-mm-dd number format")
            covered = False
            for rule in self.validations["Jobs"]:
                if rule["type"] != "list" or rule["formula"].strip('"').split(",") != sheets.STATUSES:
                    continue
                for span in rule["range"].split():
                    ends = span.replace("$", "").split(":")
                    start, end = _coordinate(ends[0]), _coordinate(ends[-1])
                    covered |= start[0] <= row <= end[0] and start[1] <= headers["Application Status"] <= end[1]
            if not covered:
                raise q.ProtocolError("Local status dropdown is missing or changed")
        jobs = self.rows("Jobs")
        totals = [len(jobs)] + [sum(values["Application Status"] == status for _, values in jobs) for status in ("New", "Saved", "Asked for referral", "Applied", "Interviewing")] + [len(self.rows("Rated Companies")), len(self.rows("Job Sources"))]
        for row, expected in enumerate(totals, 4):
            cached = self.caches["Daily Summary"].get(f"{row}:{self.summary['headers']['Value']}")
            if cached is None or float(cached) != expected:
                raise q.ProtocolError("Saved summary formula cache does not match actual tracker rows")
        return True

    @staticmethod
    def link_target(cell):
        relationship = cell.get("xlsx_relationship_target")
        if cell.get("userEnteredValue") == {"stringValue": "Open job"} and relationship:
            return q.url(relationship)
        formula = cell.get("userEnteredValue", {}).get("formulaValue", "")
        match = re.fullmatch(r'=HYPERLINK\("((?:[^"]|"")*)","Open job"\)', formula)
        if not match:
            raise q.ProtocolError("Local Job Link must be the canonical role-specific HYPERLINK formula")
        url = q.url(match[1].replace('""', '"'))
        # A formula target is Excel's clickable target unless a stored hyperlink
        # overrides it. Read and compare the actual OOXML relationship too.
        if relationship != url:
            raise q.ProtocolError("XLSX hyperlink relationship conflicts with role formula")
        return url


def inspect_workbook(path, workbook_id):
    return LocalSnapshot(path, workbook_id)


def _repair_literal_caches(xml):
    """Repair only a strict constant-string formula's wrongly typed cache.

    Artifact exports ISO-looking string constants with numeric date caches.
    The formula is untouched; no function, reference or expression is evaluated.
    """
    root = ET.fromstring(xml)
    match = re.search(r"<((?:[A-Za-z_][\w.-]*:)?)worksheet\b", xml)
    prefix = match[1] if match else ""
    fixes = {}
    for cell in root.findall("m:sheetData/m:row/m:c", NS):
        formula = cell.find("m:f", NS)
        if formula is None or formula.attrib:
            continue
        literal = re.fullmatch(r'"((?:[^"]|"")*)"', formula.text or "")
        if not literal:
            continue
        expected = literal[1].replace('""', '"')
        cache = cell.find("m:v", NS)
        if cell.get("t") != "str" or (cache.text if cache is not None and cache.text is not None else "") != expected:
            fixes[cell.attrib["r"]] = expected
    pattern = r"<" + re.escape(prefix) + r"c\b[^>]*(?<!/)>.*?</" + re.escape(prefix) + r"c>"
    def repair(match):
        body = match[0]
        opening = body[:body.index(">") + 1]
        ref = re.search(r'\br=["\']([^"\']+)["\']', opening)
        if not ref or ref[1] not in fixes:
            return body
        changed = re.sub(r'\s+t=["\'][^"\']*["\']', "", opening)
        changed = changed[:-1] + ' t="str">'
        body = changed + body[len(opening):]
        value = "<" + prefix + "v>" + escape(fixes[ref[1]]) + "</" + prefix + "v>"
        cache_pattern = r"<" + re.escape(prefix) + r"v(?:\s[^>]*)?(?:\s*/>|>.*?</" + re.escape(prefix) + r"v>)"
        if re.search(cache_pattern, body, re.S):
            return re.sub(cache_pattern, lambda _: value, body, count=1, flags=re.S)
        close = "</" + prefix + "c>"
        return body[:-len(close)] + value + close
    return re.sub(pattern, repair, xml, flags=re.S)


def _patch_native_features(destination, source, changes):
    """Missing-capability fallback: links, hidden key, literal-text caches.

    The public artifact runtime emits an error cache for HYPERLINK and exposes
    neither native hyperlinks nor column hiding. It also mis-types ISO string
    formula caches. Preserve every other ZIP part and worksheet byte.
    """
    source_view = LocalSnapshot(source, "local:feature-transfer")
    headers = source_view.tables["Jobs"]["headers"]
    links = {}
    for row, _ in source_view.rows("Jobs"):
        cell = source_view.tables["Jobs"]["cells"][(row, headers["Job Link"])]
        links[f"{sheets.colname(headers['Job Link'])}{row + 1}"] = source_view.link_target(cell)
    for change in changes:
        if change["tab"] == "Jobs" and change["column"] == headers["Job Link"]:
            formula = change["after"].get("formulaValue", "")
            match = re.fullmatch(r'=HYPERLINK\("((?:[^"]|"")*)","Open job"\)', formula)
            if not match:
                raise q.ProtocolError("Only canonical job link changes can use the native-link fallback")
            links[f"{sheets.colname(change['column'])}{change['row'] + 1}"] = q.url(match[1].replace('""', '"'))
    with zipfile.ZipFile(destination) as archive:
        entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        tab = next(x for x in book.findall("m:sheets/m:sheet", NS) if x.get("name") == "Jobs")
        relation = _rels(archive, "xl/workbook.xml")[tab.attrib["{" + NS["r"] + "}id"]]
        part = _part("xl/workbook.xml", relation["Target"])
        xml = archive.read(part).decode("utf-8")
        root = ET.fromstring(xml)
        root_match = re.search(r"<((?:[A-Za-z_][\w.-]*:)?)worksheet\b", xml)
        if not root_match:
            raise q.ProtocolError("Unsupported worksheet XML serialization")
        prefix = root_match[1]
        escaped_prefix = re.escape(prefix)
        rel_part = str(PurePosixPath(part).parent / "_rels" / (PurePosixPath(part).name + ".rels"))
        rel_xml = archive.read(rel_part).decode("utf-8") if rel_part in archive.namelist() else '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
        rel_root = ET.fromstring(rel_xml)
        old_ids = {x.get("{" + NS["r"] + "}id") for x in root.findall("m:hyperlinks/m:hyperlink", NS)}
        old_relationships = {r.get("Id"): r for r in rel_root.findall(REL)}
        # Preserve any hyperlink outside the managed Job Link cells.
        kept_links = [x for x in root.findall("m:hyperlinks/m:hyperlink", NS) if x.get("ref") not in links]
        kept_ids = {x.get("{" + NS["r"] + "}id") for x in kept_links}
        for rid in old_ids - kept_ids:
            if rid in old_relationships:
                rel_root.remove(old_relationships[rid])
        used = {r.get("Id") for r in rel_root}
        native_links = []
        for index, (cell, target) in enumerate(sorted(links.items()), 1):
            rid = "jobSearchLink" + str(index)
            while rid in used:
                rid += "x"
            used.add(rid)
            ET.SubElement(rel_root, REL, {"Id": rid, "Type": NS["r"] + "/hyperlink", "Target": target, "TargetMode": "External"})
            native_links.append(f'<{prefix}hyperlink ref={quoteattr(cell)} r:id={quoteattr(rid)}/>')
        kept_text = []
        for item in kept_links:
            attrs = []
            for key, value in item.attrib.items():
                attrs.append(("r:id" if key == "{" + NS["r"] + "}id" else key) + "=" + quoteattr(value))
            kept_text.append("<" + prefix + "hyperlink " + " ".join(attrs) + "/>")
        replacement = '<' + prefix + 'hyperlinks xmlns:r="' + NS["r"] + '">' + "".join(kept_text + native_links) + "</" + prefix + "hyperlinks>" if kept_text or native_links else ""
        if re.search(r"<" + escaped_prefix + r"hyperlinks(?:\s[^>]*)?>", xml):
            xml = re.sub(r"<" + escaped_prefix + r"hyperlinks(?:\s[^>]*)?>.*?</" + escaped_prefix + r"hyperlinks>", lambda _: replacement, xml, count=1, flags=re.S)
        elif replacement:
            # CT_Worksheet places hyperlinks after data validations and before
            # print/page settings. Insert before the first following child.
            match = re.search(r"<" + escaped_prefix + r"(?:printOptions|pageMargins|pageSetup|headerFooter|rowBreaks|colBreaks|customProperties|cellWatches|ignoredErrors|smartTags|drawing|legacyDrawing|picture|oleObjects|controls|webPublishItems|tableParts|extLst)\b", xml)
            offset = match.start() if match else xml.rfind("</" + prefix + "worksheet>")
            if offset < 0:
                raise q.ProtocolError("Unsupported worksheet XML serialization")
            xml = xml[:offset] + replacement + xml[offset:]
        cols_match = re.search(r"<" + escaped_prefix + r"cols(?:\s[^>]*)?>.*?</" + escaped_prefix + r"cols>", xml, re.S)
        if not cols_match:
            raise q.ProtocolError("Template column metadata is missing")
        cols = root.find("m:cols", NS)
        key = headers["Job Key"] + 1
        result = []
        found = False
        for col in cols:
            low, high = int(col.get("min")), int(col.get("max"))
            if low <= key <= high:
                found = True
                if low < key:
                    result.append({**col.attrib, "max": str(key - 1)})
                result.append({**col.attrib, "min": str(key), "max": str(key), "hidden": "1"})
                if key < high:
                    result.append({**col.attrib, "min": str(key + 1)})
            else:
                result.append(dict(col.attrib))
        if not found:
            result.append({"min": str(key), "max": str(key), "hidden": "1"})
        replacement_cols = "<" + prefix + "cols>" + "".join("<" + prefix + "col " + " ".join(k + "=" + quoteattr(v) for k, v in attrs.items()) + "/>" for attrs in sorted(result, key=lambda x: int(x["min"]))) + "</" + prefix + "cols>"
        xml = xml[:cols_match.start()] + replacement_cols + xml[cols_match.end():]
        patches = {part: xml.encode(), rel_part: ET.tostring(rel_root, encoding="utf-8", xml_declaration=True)}
        for info, data in entries:
            if re.fullmatch(r"xl/worksheets/[^/]+\.xml", info.filename):
                prior = patches.get(info.filename, data)
                repaired = _repair_literal_caches(prior.decode("utf-8")).encode("utf-8")
                if repaired != prior:
                    patches[info.filename] = repaired
    temporary = Path(destination).with_suffix(".native.xlsx")
    if temporary.exists():
        raise q.ProtocolError("Unresolved native-feature candidate exists")
    with zipfile.ZipFile(temporary, "w") as output:
        for info, data in entries:
            output.writestr(info, patches.pop(info.filename, data))
        for name, data in patches.items():
            output.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    os.replace(temporary, destination)


def _artifact(source, destination, changes, node, node_modules, *, initialize=False):
    node, modules = Path(node), Path(node_modules)
    if not node.is_absolute() or not node.is_file() or not modules.is_absolute() or not (modules / "@oai/artifact-tool").is_dir():
        raise q.ProtocolError("Use Node and node_modules paths returned by load_workspace_dependencies")
    with tempfile.TemporaryDirectory(prefix="job-search-artifact-") as scratch:
        scratch = Path(scratch)
        shutil.copyfile(SUPPORT / "scripts/local_artifact.mjs", scratch / "local_artifact.mjs")
        (scratch / "node_modules").symlink_to(modules, target_is_directory=True)
        q.atomic(scratch / "plan.json", {"source": str(source), "destination": str(destination), "changes": changes, "initialize": initialize, "statuses": sheets.STATUSES})
        result = subprocess.run([str(node), str(scratch / "local_artifact.mjs"), str(scratch / "plan.json")], capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise q.ProtocolError("Artifact XLSX edit failed; original is unchanged: " + result.stderr[-2500:])
        _patch_native_features(destination, source, changes)
        q.atomic(scratch / "plan.json", {"source": str(destination), "changes": changes, "verify_only": True})
        verified = subprocess.run([str(node), str(scratch / "local_artifact.mjs"), str(scratch / "plan.json")], capture_output=True, text=True, timeout=240)
        if verified.returncode:
            raise q.ProtocolError("Patched XLSX could not be reopened by artifact-tool: " + verified.stderr[-2500:])
        return result.stdout.strip()


@contextmanager
def _writer_lock(path):
    # ponytail: this serializes this package's writers, not an interactive Excel
    # process. The user must close the workbook; hashes catch outside changes.
    lock = path.with_name("." + path.name + ".job-search.lock")
    if lock.is_symlink():
        raise q.ProtocolError("Local workbook lock must not be a symlink")
    with lock.open("a+") as stream:
        os.chmod(lock, 0o600)
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise q.ProtocolError("Another local workbook writer is running") from error
        yield


def _sync_file(path):
    with Path(path).open("rb") as stream:
        os.fsync(stream.fileno())


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _preserved(before, after, changes):
    expected = copy.deepcopy(before.all_cells)
    for change in changes:
        key = f"{change['row']}:{change['column']}"
        prior = expected[change["tab"]].get(key, {})
        updated = {**prior, "userEnteredValue": change["after"]}
        if not change["after"]:
            updated.pop("userEnteredValue", None)
        if updated:
            expected[change["tab"]][key] = updated
        else:
            expected[change["tab"]].pop(key, None)
    # Exporters may add an explicit relationship for a HYPERLINK formula.
    # Validate its actual destination, then compare values and all other links.
    def normalized(all_cells):
        result = copy.deepcopy(all_cells)
        for table in result.values():
            for cell in table.values():
                formula = cell.get("userEnteredValue", {}).get("formulaValue", "")
                literal = re.fullmatch(r'="((?:[^"]|"")*)"', formula)
                if literal:
                    cell["userEnteredValue"] = {"stringValue": literal[1].replace('""', '"')}
        for cell in result.get("Jobs", {}).values():
            if cell.get("userEnteredValue", {}).get("formulaValue", "").startswith('=HYPERLINK('):
                formula = cell["userEnteredValue"]["formulaValue"]
                match = re.fullmatch(r'=HYPERLINK\("((?:[^"]|"")*)","Open job"\)', formula)
                if not match:
                    raise q.ProtocolError("Noncanonical planned Job Link")
                cell["userEnteredValue"] = {"stringValue": "Open job"}
                cell["xlsx_relationship_target"] = match[1].replace('""', '"')
        return result
    if normalized(expected) != normalized(after.all_cells):
        raise q.ProtocolError("Artifact readback changed an unplanned cell, sheet, formula, or hyperlink")
    for name in before.structures:
        if before.structures[name]["merged"] != after.structures[name]["merged"]:
            raise q.ProtocolError("Artifact readback changed merged cells")
        if before.structures[name]["frozen"] != after.structures[name]["frozen"]:
            raise q.ProtocolError("Artifact readback changed frozen panes")
        if before.structures[name]["columns"] != after.structures[name]["columns"]:
            raise q.ProtocolError("Artifact readback changed column widths or hidden columns")
        changed = {f"{c['row']}:{c['column']}" for c in changes if c["tab"] == name}
        for key, style in before.styles[name].items():
            if key not in changed and after.styles[name].get(key) != style:
                raise q.ProtocolError("Artifact readback changed formatting of an untouched cell")


def _config(config):
    if config.get("tracker", {}).get("provider") != "local_xlsx":
        raise q.ProtocolError("Local Excel command requires tracker.provider local_xlsx")
    root = Path(config["instance_root"])
    path = _path(config["tracker"]["path"], exists=False)
    if not root.is_absolute() or not root.is_dir():
        raise q.ProtocolError("Initialize the private installation first")
    return root, path, "local:" + config["installation_id"]


def initialize(config, node, node_modules):
    """Create once from the shipped template; recover only our own prior result."""
    root, path, workbook_id = _config(config)
    manifest = q.read(root / "installation.json")
    intent = manifest.get("resources", {}).get("tracker:tracker", {})
    if intent.get("request") != {"provider": "local_xlsx", "path": str(path)}:
        raise q.ProtocolError("Reserve the matching local tracker setup intent first")
    path.parent.mkdir(parents=True, exist_ok=True)
    _path(path, exists=False)
    evidence_path = root / "evidence/local-tracker.json"
    with _writer_lock(path):
        if path.exists():
            if not evidence_path.exists():
                raise q.ProtocolError("Existing workbook has no local setup evidence; explicit adoption is required")
            evidence = q.read(evidence_path)
            verify_binding(config, evidence)
            return evidence
        candidate = path.with_name("." + path.stem + ".initial.xlsx")
        if candidate.exists():
            raise q.ProtocolError("Interrupted initial candidate exists; inspect it before retrying")
        _artifact(TEMPLATE, candidate, [], node, node_modules, initialize=True)
        os.chmod(candidate, 0o600)
        snapshot = LocalSnapshot(candidate, workbook_id)
        snapshot.validate_layout()
        if any(snapshot.rows(tab) for tab in sheets.MANAGED):
            raise q.ProtocolError("Initial workbook is not blank")
        evidence = {"provider": "local_xlsx", "installation_id": config["installation_id"], "intent_id": intent["intent_id"], "request_digest": intent["request_digest"], "resource_id": workbook_id, "workbook_id": workbook_id, "path": str(path), "file_sha256": snapshot.raw["file_sha256"], "checked_at": q.now(), "verification": "reopened_xlsx_ooxml", "engine": "@oai/artifact-tool"}
        # Persist recovery evidence before the atomic no-clobber publication.
        q.atomic(evidence_path, evidence)
        _sync_file(candidate)
        os.link(candidate, path)
        candidate.unlink()
        _sync_directory(path.parent)
        verify_binding(config, evidence)
        return evidence


def verify_binding(config, evidence):
    _, path, workbook_id = _config(config)
    evidence = q.read(evidence)
    if evidence.get("provider") != "local_xlsx" or evidence.get("resource_id") != workbook_id or evidence.get("path") != str(path):
        raise q.ProtocolError("Local tracker evidence does not bind the configured file")
    actual = LocalSnapshot(path, workbook_id)
    actual.validate_layout()
    if evidence.get("file_sha256") != actual.raw["file_sha256"]:
        raise q.ProtocolError("Local tracker bytes differ from setup readback")
    return True


def merge(root, workbook_id, path, node, node_modules, owner="central"):
    """Save pending packets, or recover a published journal without a second edit."""
    if owner != "central":
        raise q.ProtocolError("Only the central coordinator writes the local workbook")
    path = _path(path)
    if not workbook_id.startswith("local:"):
        raise q.ProtocolError("Local sync requires a local workbook identity")
    with _writer_lock(path):
        for record in (q.storage(root) / "writer/local-tracking").glob("*.json"):
            if q.read(record).get("status") != "committed":
                raise q.ProtocolError("An interrupted local tracking update needs local-update with its original plan")
        before = LocalSnapshot(path, workbook_id)
        before.validate_layout()
        recovered = None
        with q.locked(root) as base:
            for saved in (base / "writer/journals").glob("*.json"):
                prior = q.read(saved)
                if prior.get("workbook_id") != workbook_id or prior.get("status") != "write_pending":
                    continue
                transaction = prior.get("local_transaction", {})
                if (prior.get("provider") == "local_xlsx" and transaction.get("path") == str(path) and
                        transaction.get("after_sha256") == before.raw["file_sha256"]):
                    prior = sheets._load(base, prior["journal_id"])
                    if prior["owner"] != owner:
                        raise q.ProtocolError("Local recovery does not own the existing journal")
                    recovered = prior["journal_id"]
                    break
        if recovered is not None:
            # Readback-only settlement stays available while new work is held.
            return sheets.verify_and_commit(root, recovered, before)
        journal = sheets.prepare(root, workbook_id, before, owner)
        if journal["status"] == "empty":
            return journal
        if journal.get("provider") != "local_xlsx":
            raise q.ProtocolError("Cannot apply a Google journal to a local workbook")
        base = q.storage(root)
        journal_path = sheets._journal_path(base, journal["journal_id"])
        transaction = journal.get("local_transaction")
        if transaction and str(path) != transaction["path"]:
            raise q.ProtocolError("Local journal path differs from configured workbook")
        if journal["status"] == "write_pending":
            if not transaction:
                raise q.ProtocolError("Missing local recovery evidence")
            if before.raw["file_sha256"] == transaction["after_sha256"]:
                return sheets.verify_and_commit(root, journal["journal_id"], before)
            if before.raw["file_sha256"] != transaction["before_sha256"]:
                raise q.ProtocolError("Workbook changed after an interrupted write; inspect before retrying")
            # All artifact subprocesses finish before authorization; no pending
            # exporter can publish. A new process holds the exclusive writer lock.
            journal.update(status="retryable")
            q.atomic(journal_path, journal)
        if journal["status"] not in {"prepared", "retryable"}:
            raise q.ProtocolError("Local journal requires explicit reconciliation")
        if before.state() != journal["before_state"]:
            raise q.ProtocolError("Workbook changed since planning; cancel the unattempted plan and retry")
        candidate = path.with_name("." + path.stem + "." + journal["journal_id"] + ".candidate.xlsx")
        if candidate.is_symlink():
            raise q.ProtocolError("Candidate path must not be a symlink")
        _artifact(path, candidate, journal["changes"], node, node_modules)
        os.chmod(candidate, 0o600)
        after = LocalSnapshot(candidate, workbook_id)
        after.validate_layout()
        _preserved(before, after, journal["changes"])
        if after.state() != sheets._expected(journal):
            raise q.ProtocolError("Candidate workbook differs from the planned merge")
        _path(path)
        if file_hash(path) != before.raw["file_sha256"]:
            raise q.ProtocolError("Workbook changed while preparing; original was not replaced")
        backup = path.with_name("." + path.stem + "." + journal["journal_id"] + ".backup.xlsx")
        if backup.is_symlink() or (backup.exists() and file_hash(backup) != before.raw["file_sha256"]):
            raise q.ProtocolError("Existing backup differs from the planned original")
        if not backup.exists():
            with backup.open("xb") as target, path.open("rb") as source:
                shutil.copyfileobj(source, target)
            os.chmod(backup, 0o600)
            _sync_file(backup)
        journal["local_transaction"] = {"path": str(path), "candidate": str(candidate), "backup": str(backup), "before_sha256": before.raw["file_sha256"], "after_sha256": after.raw["file_sha256"], "verified_at": q.now()}
        q.atomic(journal_path, journal)
        sheets.authorize_write(root, journal["journal_id"], LocalSnapshot(path, workbook_id))
        _sync_file(candidate)
        _path(path)
        if file_hash(path) != before.raw["file_sha256"]:
            raise q.ProtocolError("Workbook changed before publication; original was not replaced")
        os.replace(candidate, path)
        _sync_directory(path.parent)
        final = LocalSnapshot(path, workbook_id)
        if final.raw["file_sha256"] != after.raw["file_sha256"]:
            raise q.ProtocolError("Workbook changed after publication; receipt withheld")
        return sheets.verify_and_commit(root, journal["journal_id"], final)


def _tracking_receipt(record_path, record, snapshot):
    receipt_path = record_path.parent.parent / "receipts" / (record["update_id"] + ".json")
    receipt = q.read(receipt_path) if receipt_path.exists() else record.get("receipt")
    if receipt is None:
        receipt = {"status": "saved", "provider": "local_xlsx", "operation": "tracking", "receipt_id": record["update_id"], "workbook_id": record["workbook_id"], "path": snapshot.raw["path"], "file_sha256": snapshot.raw["file_sha256"], "verified_at": q.now(), "verification": "reopened_xlsx_ooxml", "updates": record["plan"]["updates"], "new_records": record["plan"].get("new_records", []), "new_jobs": []}
    if "tracking_changes" not in receipt:
        receipt["tracking_changes"] = record.get("tracking_changes", google_tracking.describe_updates(snapshot, record["plan"]["updates"]))
    # Receipt first: a stopped process can replay the journal without writing
    # the workbook or reporting the same update twice.
    q.atomic(receipt_path, receipt)
    record.update(status="committed", receipt=receipt)
    q.atomic(record_path, record)
    return receipt


def update_tracking(root, workbook_id, path, plan, node, node_modules, owner="central"):
    """Apply reviewed status/contact/note edits, preserving every other cell.

    Source evidence is supplied by the coordinator after its tracking review;
    this local file adapter never reads mail or infers an application status.
    """
    if owner != "central" or not workbook_id.startswith("local:"):
        raise q.ProtocolError("Only the central coordinator updates a local tracker")
    plan = google_tracking.validate_plan(plan, workbook_id, "expected_file_sha256")
    additions = plan.get("new_records", [])
    path = _path(path)
    with _writer_lock(path):
        update_id = q.digest(plan)
        with q.locked(root) as base:
            from .setup import require_execution
            record_path = base / "writer/local-tracking" / (update_id + ".json")
            for pending in record_path.parent.glob("*.json"):
                if pending != record_path and q.read(pending).get("status") != "committed":
                    raise q.ProtocolError("Reconcile the prior local tracking plan first")
            record = q.read(record_path) if record_path.exists() else None
            if record:
                if (record.get("update_id") != update_id or record.get("workbook_id") != workbook_id or
                        record.get("path") != str(path) or record.get("plan") != plan):
                    raise q.ProtocolError("Tracking recovery differs from the exact journaled plan/path")
                claim = q.claim_path(base, workbook_id)
                if record.get("status") != "committed" and (not claim.exists() or q.read(claim)["owner"] != owner):
                    raise q.ProtocolError("Tracking recovery no longer owns the workbook")
                if record["status"] == "committed":
                    if "tracking_changes" in record["receipt"]:
                        return record["receipt"]
                    # Adopt old receipts only with independent role-link evidence.
                    current = LocalSnapshot(path, workbook_id)
                    accepted = sheets._accepted_links(base, workbook_id)
                    for item in google_tracking.describe_updates(current, record["plan"]["updates"]):
                        if accepted.get(item["job_key"]) != item["url"]:
                            raise q.ProtocolError("Historical tracking receipt needs role identity review")
                    return _tracking_receipt(record_path, record, current)
            before = LocalSnapshot(path, workbook_id)
            before.validate_layout()
            if record and record.get("status") == "write_pending" and before.raw["file_sha256"] == record["after_sha256"]:
                return _tracking_receipt(record_path, record, before)
            require_execution(root, "main")
            q.acquire_claim(base, workbook_id, owner)
            for pending in (base / "writer/journals").glob("*.json"):
                other = q.read(pending)
                if other["workbook_id"] == workbook_id and other["status"] not in {"committed", "cancelled"}:
                    raise q.ProtocolError("Reconcile the outstanding discovery import before tracking edits")
        if before.raw["file_sha256"] != plan["expected_file_sha256"]:
            raise q.ProtocolError("Workbook bytes changed since tracking review; review fresh values")
        jobs = sheets._index(before, "Jobs", "Job Key")
        accepted = sheets._accepted_links(base, workbook_id)
        destinations = set()
        for entry in before.state()["Jobs"]["rows"]:
            key, url = entry["values"]["Job Key"], entry["url"]
            if accepted.get(key) != url or url in destinations:
                raise q.ProtocolError("Tracking requires independent accepted role URLs and unique destinations")
            destinations.add(url)
        google_tracking.validate_identities(base, workbook_id, before, plan, accepted)
        changes, coordinates = [], set()
        for item in plan["updates"]:
            if item["job_key"] not in jobs:
                raise q.ProtocolError("Tracking job key is missing")
            row, values = jobs[item["job_key"]]
            column = before.tables["Jobs"]["headers"][item["field"]]
            if (row, column) in coordinates or values[item["field"]] != item["old_value"]:
                raise q.ProtocolError("Duplicate tracking target or changed old value")
            coordinates.add((row, column))
            changes.append({"tab": "Jobs", "row": row, "column": column, "before": sheets.native(item["old_value"]), "after": sheets.native(item["new_value"])})
        next_rows = {name: max((row for row, _ in before.rows(name)), default=3) + 1 for name in ("Jobs", "Job Sources")}
        policy = q.read(base / "approved-policies.json")
        for item in additions:
            date = sheets.serial(item["observed_at"], policy["timezone"])
            fields = dict(zip(sheets.JOBS, [date, date, item["company"], item["title"], sheets.hyperlink(item["url"]), item["status"], "Tracking evidence", "", "", "", "", "Application evidence; discovery screening not evaluated", 1, "Tracked application: " + item["evidence_ref"], item["job_key"]]))
            event = q.digest(["tracking", item["job_key"], item["evidence_ref"]])
            source_fields = dict(zip(sheets.SOURCES, [event, item["job_key"], "Tracking evidence", item["job_key"], "tracking", "v1", "not_screened", "", "", item["observed_at"], q.now(), item["url"], "TRACKED_APPLICATION", item["role_evidence_ref"]]))
            for tab, values in (("Jobs", fields), ("Job Sources", source_fields)):
                row = next_rows[tab]
                next_rows[tab] += 1
                for field, value in values.items():
                    col = before.tables[tab]["headers"][field]
                    if sheets.cellvalue(before.tables[tab]["cells"].get((row, col), {})) != "":
                        raise q.ProtocolError("New tracking target is not blank")
                    entered = value if isinstance(value, dict) else sheets.native(value)
                    changes.append({"tab": tab, "row": row, "column": col, "before": {}, "after": entered})
        if additions:
            # Extend the template's bounded summary when an append grows past it.
            for row, values in before.rows("Daily Summary"):
                formula = values["Value"]
                bound = max(1000, max(next_rows.values()) + 100)
                formula = re.sub(r"(:[A-Z]+)[0-9]+", lambda m: m[1] + str(bound), formula)
                col = before.summary["headers"]["Value"]
                changes.append({"tab": "Daily Summary", "row": row, "column": col, "before": {"formulaValue": values["Value"]}, "after": {"formulaValue": formula}})
        candidate = path.with_name("." + path.stem + "." + update_id + ".tracking.xlsx")
        if candidate.is_symlink():
            raise q.ProtocolError("Tracking candidate must not be a symlink")
        _artifact(path, candidate, changes, node, node_modules)
        os.chmod(candidate, 0o600)
        after = LocalSnapshot(candidate, workbook_id)
        after.validate_layout()
        _preserved(before, after, changes)
        _path(path)
        if file_hash(path) != plan["expected_file_sha256"]:
            raise q.ProtocolError("Workbook changed during tracking export; original was not replaced")
        backup = path.with_name("." + path.stem + "." + update_id + ".backup.xlsx")
        if backup.is_symlink() or (backup.exists() and file_hash(backup) != plan["expected_file_sha256"]):
            raise q.ProtocolError("Tracking backup is not the reviewed original")
        if not backup.exists():
            with backup.open("xb") as target, path.open("rb") as source:
                shutil.copyfileobj(source, target)
            os.chmod(backup, 0o600)
            _sync_file(backup)
        record = {"update_id": update_id, "workbook_id": workbook_id, "status": "write_pending", "path": str(path), "plan": plan, "before_sha256": before.raw["file_sha256"], "after_sha256": after.raw["file_sha256"], "candidate": str(candidate), "backup": str(backup), "tracking_changes": google_tracking.describe_updates(before, plan["updates"])}
        q.atomic(record_path, record)
        _sync_file(candidate)
        _path(path)
        if file_hash(path) != plan["expected_file_sha256"]:
            raise q.ProtocolError("Workbook changed before tracking publication")
        with q.locked(root) as locked_base:
            require_execution(root, "main")
            claim = q.claim_path(locked_base, workbook_id)
            if not claim.exists() or q.read(claim)["owner"] != owner:
                raise q.ProtocolError("Tracking journal no longer owns the workbook")
            os.replace(candidate, path)
            _sync_directory(path.parent)
        final = LocalSnapshot(path, workbook_id)
        if final.raw["file_sha256"] != after.raw["file_sha256"]:
            raise q.ProtocolError("Workbook changed after tracking publication; receipt withheld")
        return _tracking_receipt(record_path, record, final)
