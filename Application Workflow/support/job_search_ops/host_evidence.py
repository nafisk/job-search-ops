"""Check saved native tool observations at the local trusted-agent boundary.

This does not authenticate JSON or replace connector authorization. It preserves
the actual request/response and checks explicit observations against those bytes.
Never construct a response from an expected value or use synthetic test evidence
for a live installation. See Application Workflow/docs/native-evidence.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from dataclasses import fields

from .config import require
from .doctor import HostReceipt
from .snapshots import assemble, unwrap, read_data


def pointer(value, path):
    require(isinstance(path, str) and (path == "" or path.startswith("/")), "evidence path", "use a JSON pointer")
    for part in path.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def assertions_pass(response, assertions):
    if not isinstance(assertions, list) or not assertions:
        return False
    for assertion in assertions:
        if not isinstance(assertion, dict) or "path" not in assertion:
            return False
        actual = pointer(response, assertion["path"])
        if set(assertion) == {"path", "equals"}:
            if type(actual) is not type(assertion["equals"]) or actual != assertion["equals"]:
                return False
        elif set(assertion) == {"path", "contains"}:
            if not isinstance(actual, (str, list)) or assertion["contains"] not in actual:
                return False
        elif set(assertion) == {"path", "min_items"}:
            minimum = assertion["min_items"]
            if type(minimum) is not int or minimum < 0 or not isinstance(actual, (list, dict)) or len(actual) < minimum:
                return False
        elif set(assertion) == {"path", "sha256"}:
            if not isinstance(actual, str) or hashlib.sha256(actual.encode()).hexdigest() != assertion["sha256"]:
                return False
        else:
            return False
    return True


def daily_recurrence(value):
    """Accept only an unbounded daily rule at one exact local time."""
    require(isinstance(value, str), "schedule", "native recurrence must be a full RRULE string")
    value = value.strip().removeprefix("RRULE:")
    parts = value.split(";")
    require(parts and all(part.count("=") == 1 for part in parts), "schedule", "invalid recurrence")
    pairs = [part.split("=", 1) for part in parts]
    rule = dict(pairs)
    require(len(rule) == len(pairs) and set(rule) <= {"FREQ", "INTERVAL", "BYHOUR", "BYMINUTE", "BYSECOND"},
            "schedule", "recurrence includes unsupported limits, selectors or duplicate fields")
    require(rule.get("FREQ") == "DAILY" and rule.get("INTERVAL", "1") == "1", "schedule", "expected every-day recurrence")
    require(all(re.fullmatch(r"\d{1,2}", rule.get(key, "")) for key in ("BYHOUR", "BYMINUTE")), "schedule", "expected one daily time")
    hour, minute = int(rule["BYHOUR"]), int(rule["BYMINUTE"])
    require(0 <= hour <= 23 and 0 <= minute <= 59 and rule.get("BYSECOND", "0") == "0", "schedule", "invalid daily time")
    return f"{hour:02d}:{minute:02d}"


def _named_values(value, names):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in names:
                yield item
            yield from _named_values(item, names)
    elif isinstance(value, list):
        for item in value:
            yield from _named_values(item, names)


def _provider_ok(capability, operation, tool):
    # Tool prefixes differ across host releases (one vs two underscores). Bind
    # logical operations to their real provider, not to cached personal tool IDs.
    normalized = tool.lower().replace("__", "_")
    exact_operations = {
        "get_profile": ("get_profile",), "list_labels": ("list_labels",),
        "search_email_ids": ("search_email_ids",),
        "read_email": ("read_email", "batch_read_email", "batch_read_email_threads"),
        "send_email": ("send_email",),
        "sent_readback": ("read_email", "batch_read_email", "search_emails", "batch_read_email_threads"),
        "get_spreadsheet_metadata": ("get_spreadsheet_metadata",),
        "get_spreadsheet_cells": ("get_spreadsheet_cells",),
        "effective_link_readback": ("get_spreadsheet_cells",),
        "batch_update_spreadsheet": ("batch_update_spreadsheet",),
        "bootstrap_readback": ("batch_update_spreadsheet",),
        "schema_readback": ("get_spreadsheet_cells",),
        "native_workbook_create_or_import": ("import_spreadsheet", "duplicate_sheet_in_new_spreadsheet"),
        "list_calendars": ("list_calendars",), "search_events": ("search_events",),
        "read_event": ("read_event", "batch_read_event"),
        "thread_read": ("read_thread",), "workspace_probe": ("exec_command",),
        "private_state_probe": ("exec_command",),
        "authorized_handoff": ("send_message_to_thread", "wait_threads"),
    }
    if operation in exact_operations and not normalized.endswith(exact_operations[operation]):
        return False
    if capability.startswith("gmail"):
        return "gmail" in normalized
    if capability in {"google_sheets", "drive_setup", "resource.tracker"}:
        return "google_drive" in normalized or "google_sheets" in normalized
    if capability == "calendar":
        return "google_calendar" in normalized
    if capability in {"schedule_management", "resource.schedule"}:
        return "automation_update" in normalized or (operation == "tool_catalog" and tool == "host.tool_catalog")
    if capability in {"chat_coordination", "chat_delegation", "resource.chat"}:
        return "codex_app" in normalized or (operation == "workspace_probe" and "exec_command" in normalized)
    if capability == "collaboration":
        return tool == "host.tool_catalog" or "collaboration" in normalized
    if capability in {"public_browser", "authenticated_browser"}:
        return "cua_repl" in normalized
    if capability == "public_research":
        return any(name in normalized for name in ("web_run", "search_service", "exec_command"))
    if capability == "messages":
        return "mac_messages" in normalized or "exec_command" in normalized
    if capability == "host_filesystem":
        return "exec_command" in normalized
    if capability == "artifact_tool":
        return any(name in normalized for name in ("load_workspace_dependencies", "node_repl", "exec_command", "view_image"))
    if capability == "node":
        return "load_workspace_dependencies" in normalized or "exec_command" in normalized
    if capability == "manual_outreach":
        return tool == "host.tool_catalog"
    if capability == "first_live_pass":
        return any(name in normalized for name in ("exec_command", "gmail", "codex_app", "google_drive"))
    return False


def verify(receipt):
    """Reject a bare success flag; validate retained raw outputs and key bindings."""
    try:
        if type(receipt) is not HostReceipt:
            return False
        evidence = receipt.evidence
        checks = evidence.get("native_checks")
        if not isinstance(checks, list) or not checks:
            return False
        responses, observed = [], set()
        for check in checks:
            if not isinstance(check, dict) or not {"operation", "tool", "request", "response", "assertions"} <= set(check):
                return False
            operation, tool = check["operation"], check["tool"]
            if not isinstance(operation, str) or not isinstance(tool, str) or not _provider_ok(receipt.capability, operation, tool):
                return False
            raw = check["response"]
            # Raw text-only browser/search output is retained verbatim as {text:...}.
            response = unwrap(raw)
            if not assertions_pass(response, check["assertions"]):
                return False
            if "exec_command" in tool and response.get("exit_code") != 0:
                return False
            observed.add(operation)
            responses.append(response)
        if set(evidence.get("operations", [])) != observed:
            return False
        if receipt.identity is not None:
            identities = list(_named_values(responses, {"email", "emailAddress", "email_address", "account_identity", "identity"}))
            explicit_identity_assertion = any(a.get("equals", a.get("contains")) == receipt.identity for c in checks for a in c["assertions"])
            if receipt.identity not in identities and not explicit_identity_assertion:
                return False
        if "identity_binding" in evidence:
            binding = evidence["identity_binding"]
            path = Path(binding["path"])
            if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)) or path.stat().st_size > 2_000_000:
                return False
            content = path.read_text(encoding="utf-8").strip()
            if content != binding.get("identity"):
                parsed = json.loads(content)
                if binding.get("identity") not in _named_values(parsed, {"email", "emailAddress", "email_address", "account_identity", "identity", "phone"}):
                    return False
            if binding.get("identity") != receipt.identity:
                return False
        if receipt.capability.startswith("resource."):
            names = {"resource.tracker": {"spreadsheetId", "id"}, "resource.chat": {"threadId", "thread_id"}, "resource.schedule": {"id", "automationId"}}[receipt.capability]
            if receipt.resource_id not in _named_values(responses, names):
                return False
        if receipt.capability == "resource.tracker":
            from .sheets import SCHEMAS, Snapshot, cellvalue
            snapshot = evidence.get("snapshot")
            metadata_checks = [c for c in checks if c["operation"] == "get_spreadsheet_metadata"]
            cell_checks = [c for c in checks if c["operation"] in {"get_spreadsheet_cells", "schema_readback"}]
            if len(metadata_checks) != 1 or not cell_checks:
                return False
            observed_snapshot = assemble(metadata_checks[0]["response"],
                                         [{"request": c["request"], "response": c["response"]} for c in cell_checks])
            if unwrap(snapshot) != observed_snapshot:
                return False
            from .bootstrap import verify_structure
            bootstrap_checks = [c for c in checks if c["operation"] == "bootstrap_readback"]
            if len(bootstrap_checks) != 1 or not verify_structure(bootstrap_checks[0]["response"], receipt.resource_id):
                return False
            Snapshot(snapshot, receipt.resource_id).state()
            raw = unwrap(snapshot)
            for name, headers in SCHEMAS.items():
                sheets = [s for s in raw["sheets"] if s["properties"]["title"] == name]
                if len(sheets) != 1:
                    return False
                cells = {}
                for block in sheets[0].get("data", []):
                    for row, item in enumerate(block.get("rowData", []), block.get("startRow", 0)):
                        for col, cell in enumerate(item.get("values", []), block.get("startColumn", 0)):
                            cells[row, col] = cell
                if [cellvalue(cells.get((3, i), {})) for i in range(len(headers))] != headers:
                    return False
        if receipt.capability == "resource.chat":
            # Probe output is JSON produced in the actual destination chat, saved
            # inside the exec tool's raw output. Its values are checked by pointers.
            probe_checks = [c for c in checks if c["operation"] == "workspace_probe"]
            if not probe_checks:
                return False
            for field in ("workspace_path", "staging_write_readback"):
                if evidence.get(field) not in _named_values(responses, {field}):
                    # exec JSON stdout can be parsed by an explicit assertion on
                    # the exact output string; require both fields in that string.
                    outputs = list(_named_values(responses, {"output"}))
                    parsed = []
                    for output in outputs:
                        try:
                            parsed.append(json.loads(output))
                        except (TypeError, ValueError):
                            continue
                    if evidence.get(field) not in _named_values(parsed, {field}):
                        return False
        if receipt.capability == "resource.schedule":
            # The agent retains the saved native view and its explicit checked
            # normalization. Exact view fields are verified by JSON pointers.
            for key in ("thread_id", "cadence", "local_time", "timezone", "status", "notification_policy", "prompt_digest", "next_run_at"):
                bindings = evidence.get("field_checks", {})
                binding = bindings.get(key, {})
                index = binding.get("check")
                if type(index) is not int or not 0 <= index < len(responses):
                    return False
                actual = pointer(responses[index], binding.get("path"))
                if key == "prompt_digest":
                    actual = hashlib.sha256(actual.encode()).hexdigest()
                elif key == "cadence":
                    if binding.get("transform") != "rrule_daily":
                        return False
                    if daily_recurrence(actual) != evidence.get("local_time"):
                        return False
                    actual = "daily"
                elif binding.get("transform") == "rrule_time":
                    actual = daily_recurrence(actual)
                elif binding.get("transform") == "notification_policy":
                    actual = "meaningful_changes" if actual is None else actual
                elif binding.get("transform") == "uppercase":
                    actual = actual.upper()
                elif "transform" in binding:
                    return False
                if actual != evidence.get(key):
                    return False
        if receipt.capability == "first_live_pass":
            manifest = evidence.get("accepted_manifest")
            if not isinstance(manifest, dict):
                return False
            encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
            if hashlib.sha256(encoded).hexdigest() != evidence.get("accepted_manifest_sha256"):
                return False
            captured = []
            for index, check in enumerate(checks):
                if check["operation"] != "accepted_manifest_readback":
                    continue
                response = responses[index]
                captured.append(response)
                captured.extend(_named_values(response, {"manifest", "accepted_manifest"}))
                if isinstance(response.get("output"), str):
                    try:
                        captured.append(json.loads(response["output"]))
                    except ValueError:
                        pass
            if manifest not in captured:
                return False
            for field in ("workflow", "status", "unsynced_count", "workbook_id", "delivery"):
                if manifest.get(field) != evidence.get(field):
                    return False
            if str(evidence.get("workbook_id", "")).startswith("local:"):
                value = evidence.get("tracker_file_sha256")
                if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) or manifest.get("tracker_file_sha256") != value:
                    return False
            if "preferences_update_id" in evidence and manifest.get("preferences_update_id") != evidence["preferences_update_id"]:
                return False
            if manifest.get("run_id") != receipt.resource_id or not {"accepted_manifest_readback", "delivery_readback"} <= observed:
                return False
        return True
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OSError):
        return False


def load_evidence(path):
    value = read_data(path)
    require(isinstance(value, dict) and value.get("schema_version") == 1 and isinstance(value.get("observations"), list), "evidence", "expected version-one observations bundle")
    names = {x.name for x in fields(HostReceipt)}
    result = []
    for item in value["observations"]:
        require(isinstance(item, dict) and set(item) == names, "evidence", "invalid observation fields")
        result.append(HostReceipt(**item))
    return result
