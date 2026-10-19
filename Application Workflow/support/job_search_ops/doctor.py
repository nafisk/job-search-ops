"""Dependency inventory and checks over validated native host observations.

Local probes never prove account access. Host evidence is checked by the native
response adapter supplied by the caller, not by a JSON `verified` flag.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import copy
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
from zoneinfo import ZoneInfo

from .config import ConfigError, SUPPORT_ROOT, execution_plan, no_symlink, read_json, require


STAGES = {"installed": 0, "connected": 1, "operation_verified": 2}


@dataclass(frozen=True)
class HostReceipt:
    capability: str
    stage: str
    observation_id: str
    checked_at: str
    identity: str | None
    resource_id: str | None
    operation: str
    evidence: dict


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None and parsed.utcoffset() is not None,
                "timestamp", "timezone required")
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ConfigError("timestamp: expected timezone-aware ISO time") from None


def now_utc(now=None):
    return timestamp(now) if now is not None else datetime.now(timezone.utc)


def validate_receipt(receipt, verify, *, now=None, max_age_seconds=900, expected_identity=None):
    require(type(receipt) is HostReceipt, "receipt", "native response adapter must construct a HostReceipt")
    require(receipt.stage in STAGES and type(receipt.evidence) is dict, "receipt", "invalid observation")
    for value in (receipt.capability, receipt.observation_id, receipt.operation):
        require(type(value) is str and value.strip() and not any(ord(c) < 32 for c in value), "receipt", "missing bounded identity")
    age = (now_utc(now) - timestamp(receipt.checked_at)).total_seconds()
    require(type(max_age_seconds) is int and 1 <= max_age_seconds <= 86400,
            "receipt", "invalid freshness limit")
    require(0 <= age <= max_age_seconds, "receipt", "observation is stale or future-dated")
    if expected_identity is not None:
        require(receipt.identity == expected_identity, "receipt", "wrong account identity")
    require(callable(verify), "receipt", "native evidence verifier is required")
    try:
        accepted = verify(receipt)
    except Exception:
        accepted = False
    require(accepted is True, "receipt", "native evidence did not verify")
    return receipt


def capability_manifest():
    return read_json(SUPPORT_ROOT / "config" / "capabilities.json")


def _selected(config, selector):
    return execution_plan(config)["selectors"].get(selector, False)


def required_capabilities(config):
    selected = execution_plan(config)["selectors"]
    result = []
    for original in capability_manifest()["capabilities"]:
        if original["classification"] != "runtime" or not any(selected.get(name, False) for name in original["required_when"]):
            continue
        capability = copy.deepcopy(original)
        for name, operations in capability.get("conditional_verification_operations", {}).items():
            if selected.get(name, False):
                capability["verification_operations"] += operations
        result.append(capability)
    return result


def local_probes(config):
    """Read executable/package metadata; do not import account adapters or install."""
    posix_ready = os.name == "posix" and importlib.util.find_spec("fcntl") is not None
    result = {"python": {"installed": sys.version_info >= (3, 10) and posix_ready,
                         "posix_locking_available": posix_ready,
                         "version": platform.python_version(), "path": sys.executable}}
    try:
        ZoneInfo(config["_profile"]["timezone"])
        result["python"]["timezone_available"] = True
    except Exception:
        result["python"].update(installed=False, timezone_available=False)
    for name in (["node"] if execution_plan(config)["selectors"]["artifact_tool"] else []):
        path = shutil.which(name)
        result[name] = {"installed": path is not None, "path": path, "version": None}
    return result


def _expected_identity(config, capability):
    service = {"gmail_read": "mail", "gmail_send": "mail", "google_sheets": "sheets",
               "drive_setup": "sheets", "calendar": "calendar", "messages": "messages",
               "authenticated_browser": "browser"}.get(capability)
    if service:
        return config["_profile"]["integrations"][service]["expected_identity"]
    return None


def check_staging(config):
    """Explicitly requested local write/read test; does not attest child-chat grants."""
    root = no_symlink(config["instance_root"])
    results = []
    for relative in execution_plan(config)["staging"]:
        path = no_symlink(root / relative)
        try:
            require(path.is_dir(), "staging", "initialize private instance first")
            with tempfile.NamedTemporaryFile(prefix=".doctor-", dir=path) as handle:
                handle.write(b"job-search-ops-private-staging-check\n")
                handle.flush()
                os.fsync(handle.fileno())
                handle.seek(0)
                require(handle.read() == b"job-search-ops-private-staging-check\n", "staging", "readback mismatch")
            results.append({"path": str(path), "local_write_readback": True, "child_access_verified": False})
        except (OSError, ConfigError):
            results.append({"path": str(path), "local_write_readback": False, "child_access_verified": False})
    return results


def run_doctor(config, observations=(), verify=None, now=None, check_staging=False):
    """Report installed/connected/verified separately; never create live readiness."""
    probes = local_probes(config)
    requirements = required_capabilities(config)
    selected = {x["id"] for x in requirements}
    messages_required = config["_profile"]["integrations"].get("messages", {}).get("required", False)
    blocking = selected - ({"messages"} if not messages_required else set())
    evidence = {}
    rejected = []
    not_requested = []
    blocking_rejections = []
    seen = set()
    manifest_path = Path(config["instance_root"]) / "installation.json"
    tracker = None
    binding = {}
    if manifest_path.exists():
        no_symlink(manifest_path)
        manifest = read_json(manifest_path)
        require(manifest.get("installation_id") == config["installation_id"], "installation", "wrong manifest")
        binding = manifest.get("resources", {}).get("tracker:tracker", {})
        if binding.get("status") == "verified":
            tracker = binding.get("resource_id")
    for receipt in observations:
        try:
            if type(receipt) is HostReceipt and receipt.capability not in selected:
                not_requested.append(receipt.capability)
                continue
            require(type(receipt) is HostReceipt and receipt.observation_id not in seen, "receipt", "duplicate or malformed observation")
            seen.add(receipt.observation_id)
            expected_identity = _expected_identity(config, receipt.capability)
            if expected_identity and expected_identity.startswith("private:"):
                reference = expected_identity.removeprefix("private:")
                identity_binding = receipt.evidence.get("identity_binding", {})
                require(type(identity_binding) is dict and identity_binding.get("reference") == reference and
                        identity_binding.get("path") == config["_private_paths"].get(reference) and
                        type(identity_binding.get("identity")) is str and identity_binding["identity"] and
                        not identity_binding["identity"].startswith("private:"),
                        "identity", "configured private identity binding is unresolved")
                expected_identity = identity_binding["identity"]
            validate_receipt(receipt, verify, now=now, expected_identity=expected_identity)
            if receipt.capability == "google_sheets" and receipt.stage == "operation_verified" and tracker:
                require(receipt.resource_id == tracker, "receipt", "wrong shared workbook")
            require(receipt.evidence.get("installation_id") == config["installation_id"], "receipt", "cross-installation evidence")
            previous = evidence.get(receipt.capability)
            if previous is None or STAGES[receipt.stage] > STAGES[previous.stage]:
                evidence[receipt.capability] = receipt
        except ConfigError as error:
            rejected.append(str(error))
            if type(receipt) is not HostReceipt or receipt.capability in blocking:
                blocking_rejections.append(str(error))
    checks = []
    for capability in requirements:
        name = capability["id"]
        receipt = evidence.get(name)
        state = "missing"
        reason = "No current validated native host observation."
        if name in probes and probes[name]["installed"]:
            state = "installed"
            reason = "Local dependency found; account/network operations are not implied."
        if receipt:
            state = receipt.stage
            required_ops = set(capability["verification_operations"])
            observed_ops = receipt.evidence.get("operations", [])
            if state == "operation_verified" and (type(observed_ops) is not list or not required_ops <= set(x for x in observed_ops if type(x) is str)):
                state = "connected"
                reason = "Native evidence does not cover every required operation."
            else:
                reason = "Native response adapter verified this scoped observation."
        if name == "local_workbook":
            state = "missing"
            reason = "Create or adopt and verify the selected local workbook first."
            if binding.get("status") == "verified" and binding.get("provider") == "local_xlsx" and binding.get("path") == execution_plan(config)["tracker"]["path"] and tracker == "local:" + config["installation_id"]:
                try:
                    from .local_excel import inspect_workbook
                    inspect_workbook(binding["path"], tracker).validate_layout()
                    state = "operation_verified"
                    reason = "Current local XLSX bytes, schema, identities and role hyperlink targets were read and checked."
                except Exception:
                    reason = "The bound local workbook could not pass current file readback; inspect it before continuing."
        ready = state in STAGES and STAGES[state] >= STAGES[capability["required_stage"]]
        checks.append({"capability": name, "state": state, "required_stage": capability["required_stage"],
                       "ready": ready, "blocking": name in blocking, "reason": reason})
    for source in execution_plan(config)["source_files"]:
        path = config["sources"][source]
        available = path is not None and Path(path).is_file() and not Path(path).is_symlink()
        checks.append({"capability": source, "state": "configured" if available else "missing",
                       "required_stage": "configured", "ready": bool(available), "blocking": True,
                       "reason": "Source choices must exist; source content is validated by its workflow."})
    messages_check = next((x for x in checks if x["capability"] == "messages"), None)
    messages_status = "disabled" if messages_check is None else "available" if messages_check["ready"] else "partial"
    report = {"schema_version": 1, "installation_id": config["installation_id"],
              "checked_at": now_utc(now).isoformat(), "local_probes": probes,
              "checks": checks, "rejected_observations": rejected, "not_requested_observations": not_requested,
              "ready": all(x["ready"] for x in checks if x["blocking"]) and not blocking_rejections,
              "optional_modules": {"messages": {"status": messages_status, "required": messages_required}},
              "effects": [], "note": "Tool catalog presence alone is not live readiness."}
    if check_staging:
        report["staging"] = globals()["check_staging"](config)
        report["effects"] = ["temporary local staging read/write probes"]
        report["ready"] = report["ready"] and all(x["local_write_readback"] for x in report["staging"])
    return report
