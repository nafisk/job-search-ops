"""Offline distribution checks: no installs, credentials, accounts, or live state."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

SUPPORT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = SUPPORT_ROOT.parent
REPO_ROOT = WORKFLOW_ROOT.parent
INVENTORY = "Application Workflow/support/RELEASE_FILES.txt"


def has_private_binding(text):
    if re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", text, re.I):
        return True
    pattern = r"/(?:Users|home)/(?!example(?:/|\b)|fictional(?:/|\b)|yourname(?:/|\b)|USER(?:/|\b)|<)[A-Za-z0-9_.-]+/"
    for match in re.finditer(pattern, text, re.I):
        # Public career paths can resemble local folders; query values remain checked.
        prefix = re.search(r"https?://[^\s<>\"'?#\\()\[\]{}]*$", text[:match.start()], re.I)
        if prefix:
            try:
                url = urlsplit(prefix.group())
            except ValueError:
                return True
            if url.hostname and not (url.username or url.password):
                continue
        return True
    return False


def generated_file(path):
    """Only normal interpreter caches and Finder metadata may be unlisted."""
    return path.name == ".DS_Store" or (path.parent.name == "__pycache__" and path.suffix == ".pyc")


def files(root=None):
    root = Path(root) if root is not None else REPO_ROOT
    manifest = root / INVENTORY
    entries = manifest.read_text(encoding="utf-8").splitlines()
    if not entries or len(entries) != len(set(entries)):
        raise ValueError("release inventory is empty or contains duplicates")
    for entry in entries:
        path = Path(entry)
        if not entry or path.is_absolute() or ".." in path.parts or path.as_posix() != entry:
            raise ValueError("release inventory contains an unsafe path")
        if path.parts[0] == ".git" or generated_file(path):
            raise ValueError("release inventory includes generated or Git files")
    observed = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts[0] == ".git":
            continue
        if path.is_symlink():
            raise ValueError("distributed symlink: " + relative.as_posix())
        if path.is_file() and not generated_file(path):
            observed.add(relative.as_posix())
    if observed != set(entries):
        missing, extra = sorted(set(entries) - observed), sorted(observed - set(entries))
        raise ValueError(f"release inventory differs; missing={missing}; unreviewed={extra}")
    return [root / entry for entry in sorted(entries)]


def workbook_check():
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    schema = json.loads((WORKFLOW_ROOT / "sheets/workbook-schema.json").read_text())
    with zipfile.ZipFile(WORKFLOW_ROOT / "sheets/job-search-tracker.xlsx") as z:
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        names = [s.attrib["name"] for s in workbook.findall("m:sheets/m:sheet", ns)]
        assert names == [t["name"] for t in schema["tabs"]], "Workbook tabs differ from schema"
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(si.itertext()) for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        for index, tab in enumerate(schema["tabs"], 1):
            sheet = ET.fromstring(z.read(f"xl/worksheets/sheet{index}.xml"))
            def value(c):
                v = c.find("m:v", ns)
                if c.get("t") == "s": return shared[int(v.text)]
                if c.get("t") == "inlineStr": return "".join(c.find("m:is", ns).itertext())
                return v.text if v is not None else ""
            cells = sheet.findall("m:sheetData/m:row/m:c", ns)
            headers = [value(c) for c in cells if re.fullmatch(r"[A-Z]+4", c.attrib["r"])]
            assert headers == tab["headers"], f"{tab['name']} header mismatch"
            assert not any(c.get("t") == "e" for c in cells), "Workbook contains formula error"
            if tab["name"] not in ("Daily Summary", "How to Use"):
                assert not any(value(c) for c in cells if int(re.search(r"\d+", c.attrib["r"])[0]) >= 5), "Template contains private/sample rows"
    sys.path.insert(0, str(SUPPORT_ROOT))
    from job_search_ops.sheets import workbook_schema
    assert schema == workbook_schema(), "Python and template schemas differ"


def main():
    try:
        paths = files()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    failures = []
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        if path.is_symlink(): failures.append(relative + ": distributed symlink")
        if path.suffix not in {".py", ".json", ".md", ".txt", ".mjs", ".gs", ".swift", ".lock"}: continue
        text = path.read_text(encoding="utf-8")
        # Literal signatures of local private bindings must never ship.
        if has_private_binding(text):
            failures.append(relative + ": private binding or key signature")
        if path.suffix == ".md":
            targets = re.findall(r'(?<!!)\[[^\]\n]+\]\((<[^>\n]+>|[^)\s]+)(?:\s+"[^"\n]*")?\)', text)
            targets += re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', text, re.I)
            for target in targets:
                target = target.strip("<>")
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"): continue
                target = unquote(urlsplit(target).path)
                if target and not (path.parent / target).exists(): failures.append(relative + ": broken local link " + target)
    try: workbook_check()
    except (AssertionError, KeyError, ValueError, OSError, zipfile.BadZipFile) as error: failures.append(str(error))
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"Distribution verified: {len(paths)} files; reviewed inventory; blank seven-tab workbook; local links; private-binding scan.")
    return 0


if __name__ == "__main__": sys.exit(main())
