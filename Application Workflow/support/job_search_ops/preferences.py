"""Reviewed, recoverable local preference updates; never changes connected resources."""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import asdict
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .config import execution_plan, load_config, no_symlink, public_settings, read_json, require
from . import setup
from .doctor import required_capabilities, validate_receipt


def _snapshot(config):
    return {"config": public_settings(config), "profile": copy.deepcopy(config["_profile"])}


def preferences_digest(config):
    return setup.digest(_snapshot(config))


def _validated(snapshot):
    """Reuse the full config validator; temporary files contain no credentials."""
    require(type(snapshot) is dict and set(snapshot) == {"config", "profile"}, "preferences", "invalid snapshot")
    with tempfile.TemporaryDirectory(prefix="job-ops-preferences-") as temporary:
        root = Path(temporary).resolve()
        settings = copy.deepcopy(snapshot["config"])
        settings["profile_path"] = str(root / "profile.json")
        setup._atomic_json(root / "profile.json", snapshot["profile"])
        setup._atomic_json(root / "config.json", settings)
        config = load_config(root / "config.json")
    require(_snapshot(config) == snapshot, "preferences", "snapshot is not canonical")
    return config


def _changes(before, after, prefix=""):
    result = []
    if type(before) is dict and type(after) is dict:
        for key in sorted(set(before) | set(after)):
            result.extend(_changes(before.get(key), after.get(key), prefix + ("." if prefix else "") + key))
    elif before != after:
        result.append({"field": prefix, "before": before, "after": after})
    return result


def _check_scope(old, new):
    require(old["schema_version"] == new["schema_version"] == 2, "preferences", "only version 2 supports this update; legacy installations need a separately reviewed migration")
    for key in ("installation_id", "instance_root", "profile_path", "tracker"):
        require(old[key] == new[key], "preferences", "installation identity, private root and tracker cannot be replaced; use a separately reviewed migration")
    for key in ("schema_version", "profile_id", "private", "trackers"):
        require(old["_profile"][key] == new["_profile"][key], "preferences", "private paths and tracker references cannot be replaced")
    require(old["_profile"]["identity"]["account_identity"] == new["_profile"]["identity"]["account_identity"], "preferences", "account replacement needs explicit resource migration")
    for name, entry in old["_profile"]["integrations"].items():
        selected = new["_profile"]["integrations"][name]
        # Disabled profile entries require null refs; the backup retains the old
        # binding while active connections may not silently switch accounts.
        if selected["enabled"]:
            for key in ("connection_ref", "expected_identity"):
                require(entry[key] == selected[key], "preferences", "active connection and identity bindings must be retained; new bindings need separate verified setup")
    old_policy, new_policy = old["_profile"]["role_policy"], new["_profile"]["role_policy"]
    criteria_changed = (any(old_policy[key] != new_policy[key] for key in old_policy if key != "version") or
                        old["_profile"]["locations"] != new["_profile"]["locations"] or old["candidate"] != new["candidate"])
    if criteria_changed and execution_plan(new)["discovery"]:
        require(old_policy["version"] != new_policy["version"], "preferences", "changing search criteria requires a new role_policy.version so old producer packets cannot be reused")
        if new["modules"]["blind"] and old["blind_policy"] is not None:
            require(old["blind_policy"]["version"] != new["blind_policy"]["version"], "preferences", "shared criteria changes also require a new blind_policy.version for selected rated-company discovery")
    if new["modules"]["blind"] and old["blind_policy"] != new["blind_policy"] and old["blind_policy"] is not None:
        require(old["blind_policy"]["version"] != new["blind_policy"]["version"], "preferences", "changing rated-company rules requires a new blind_policy.version")
    for name in ("referral_companies_path", "rated_companies_path"):
        require(old["sources"][name] == new["sources"][name], "preferences", "retain existing private company-list paths; update their reviewed contents separately")


def _schedule_actions(old, new, manifest, prompts):
    actions = []
    for name in ("main", "blind"):
        before, after = old["schedules"][name], new["schedules"][name]
        bound = manifest["resources"].get("schedule:" + name)
        if not bound:
            if after["enabled"]:
                actions.append({"workflow": name, "action": "create_after_doctor_and_pilot", "resource_id": None,
                                "local_time": after["local_time"], "timezone": new["_profile"]["timezone"],
                                "instruction": "Use schedule-plan and the Codex automation tool after doctor and the selected pilot pass; reserve and verify the real binding. No schedule has been activated."})
            continue
        require(bound.get("status") == "verified", "preferences", "reconcile the existing uncertain schedule intent before updating preferences")
        desired = copy.deepcopy(bound["request"])
        require(all(key in desired for key in ("thread_id", "cadence", "local_time", "timezone", "status", "notification_policy", "prompt_digest")), "preferences", "existing schedule lacks verified timing/status; inspect and reconcile its native binding first")
        require(desired["cadence"] == "daily", "preferences", "existing schedule cadence needs explicit native reconciliation")
        if before["local_time"] != after["local_time"] and after["local_time"] is not None:
            desired["local_time"] = after["local_time"]
        if old["_profile"]["timezone"] != new["_profile"]["timezone"]:
            desired["timezone"] = new["_profile"]["timezone"]
        if before["notifications"] != after["notifications"]:
            desired["notification_policy"] = after["notifications"]
        if before["enabled"] != after["enabled"]:
            desired["status"] = "ACTIVE" if after["enabled"] else "PAUSED"
        body = prompts.get(name, "This workflow is disabled in the saved preferences. Do not research, access accounts, dispatch helpers, or write the tracker. Report that its schedule needs to remain paused.\n")
        desired["prompt_digest"] = hashlib.sha256(body.encode()).hexdigest()
        if desired != bound["request"]:
            actions.append({"workflow": name, "action": "update_existing", "resource_id": bound["resource_id"],
                            "before_request": copy.deepcopy(bound["request"]), "request": desired, "prompt": body,
                            "instruction": "Read this exact existing automation with the Codex tool. Reconcile any drift before changing it. Preserve its ID and all unrequested fields; update only the reviewed changes, then save native readback and use preferences-schedule-record. Never delete or recreate it."})
    return actions


def _build_plan(old, new, manifest):
    require(type(manifest) is dict and type(manifest.get("resources")) is dict and type(manifest.get("prompts")) is dict, "preferences", "invalid installation snapshot")
    _check_scope(old, new)
    require(not manifest.get("preferences_update", {}).get("pending_schedules"), "preferences", "finish the pending schedule reconciliation before another preference update")
    old_plan, new_plan = execution_plan(old), execution_plan(new)
    missing = [key for key in setup._needed_bindings(new) if manifest["resources"].get(key, {}).get("status") != "verified"]
    # ponytail: new connections/chats still use the existing verified setup flow.
    # This updater handles established installations, not resource migration.
    require(not missing, "preferences", "complete verified tracker and selected chat bindings before updating; new unbound helpers require separate reviewed setup")
    prompts = setup.render_prompts(new, manifest)
    workbook = manifest["resources"]["tracker:tracker"]["resource_id"]
    changes = _changes(_snapshot(old), _snapshot(new))
    require(bool(changes), "preferences", "no changes selected")
    actions = _schedule_actions(old, new, manifest, prompts)
    # Timing-only updates can reuse their accepted pilot. Operational changes
    # retain historical acceptance but need a pilot for the new selected scope.
    operational = [item["field"] for item in changes if not item["field"].startswith("config.schedules.")]
    pilots = list(manifest.get("preferences_update", {}).get("pilot_required", []))
    main_fields = [field for field in operational if not field.startswith(("config.blind_policy", "config.modules.blind"))]
    if main_fields and "main" not in pilots:
        pilots.append("main")
    blind_fields = ("config.blind_policy", "config.candidate", "config.modules.blind", "profile.role_policy", "profile.locations", "profile.timezone")
    if new["modules"]["blind"] and any(field.startswith(blind_fields) for field in operational) and "blind" not in pilots:
        pilots.append("blind")
    pilots = [name for name in pilots if name == "main" or new["modules"]["blind"]]
    plan = {"schema_version": 1, "installation_id": old["installation_id"], "instance_root": old["instance_root"],
            "expected_digest": preferences_digest(old), "new_digest": preferences_digest(new),
            "before": _snapshot(old), "after": _snapshot(new), "manifest_before": copy.deepcopy(manifest),
            "changes": changes, "schedule_actions": actions, "pilot_required": pilots,
            "requirements": [{"capability": item["id"], "setup": item["setup"]} for item in required_capabilities(new)],
            "disabled_discovery": sorted(set(old_plan["discovery"]) - set(new_plan["discovery"])),
            "disabled_tracking": sorted(set(old_plan["tracking"]) - set(new_plan["tracking"])),
            "old_policies": setup._approved_policies(old, workbook), "new_policies": setup._approved_policies(new, workbook),
            "effects": ["Update private preferences, execution plan, runtime profile and selected prompts; preserve tracker, history, receipts and resource bindings."],
            "connected_effects": [],
            "next_action": "Review changes, finish in-flight runs and deliveries, then apply with the exact expected digest. Follow returned schedule actions separately; local apply never changes a schedule."}
    plan["update_id"] = setup.digest(plan)
    return plan


def _check_idle(root, plan):
    for folder in ("writer/journals", "writer/local-tracking", "writer/referrals"):
        for path in sorted((root / "state" / folder).glob("*.json")):
            require(read_json(no_symlink(path)).get("status") in {"committed", "cancelled"}, "preferences", "reconcile unfinished tracker writes before changing preferences")
    for path in sorted((root / "state/delivery").glob("*.json")):
        require(read_json(no_symlink(path)).get("status") in {"delivered", "cancelled"}, "preferences", "finish or reconcile outstanding briefs, or cancel an unattempted brief, before changing preferences")
    # Pending source evidence remains attached to the exact old screening rules.
    # Drain first instead of silently reinterpreting it under new criteria.
    criteria = ("config.discovery", "config.modules.blind", "config.blind_policy", "config.sources", "profile.role_policy", "profile.locations", "config.candidate")
    if any(change["field"].startswith(criteria) for change in plan["changes"]):
        require(not list((root / "state/queue/pending").glob("*.json")), "preferences", "save and report queued discoveries under the current policy before changing search criteria or discovery sources; queued packets and their policy remain untouched")


def preference_plan(current, candidate):
    """Read-only review using canonical current settings and a separate draft."""
    root = setup._root(current)
    require(Path(current["_config_path"]) == root / "config.json", "preferences", "use the installed config.json as --config; keep edited settings in a separate draft")
    plan = _build_plan(current, candidate, setup.load_instance(current))
    _check_idle(root, plan)
    return plan


@contextmanager
def _protocol_lock(root):
    path = no_symlink(root / "state/.protocol.lock")
    if path.exists():
        require(path.is_file() and path.stat().st_uid == os.getuid(), "preferences", "invalid protocol lock owner/type")
    with path.open("a+") as stream:
        os.chmod(path, 0o600)
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            require(False, "preferences", "another queue or writer operation is active; retry after it finishes")
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _json_body(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _writes(new, plan):
    root = Path(new["instance_root"])
    manifest = copy.deepcopy(plan["manifest_before"])
    prompts = setup.render_prompts(new, manifest)
    values = {"config.json": public_settings(new), "profile.json": new["_profile"],
              "state/approved-policies.json": plan["new_policies"],
              "execution-plan.json": execution_plan(new), "runtime-profile.json": setup._runtime_profile(new, manifest)}
    writes = {name: _json_body(value) for name, value in values.items()}
    manifest["prompts"] = {}
    for name, body in prompts.items():
        relative = "prompts/" + name + ".md"
        writes[relative] = body
        manifest["prompts"][name] = {"path": str(root / relative), "sha256": hashlib.sha256(body.encode()).hexdigest()}
    for name in set(plan["manifest_before"].get("prompts", {})) - set(prompts):
        writes["prompts/" + name + ".md"] = "This source is disabled in execution-plan.json. Do not run it or use its accounts. Existing evidence and bindings are retained for history.\n"
    manifest.update(config_digest=setup.digest(public_settings(new)), profile_digest=setup.digest(new["_profile"]))
    manifest["preferences_update"] = {"update_id": plan["update_id"], "digest": plan["new_digest"],
                                      "pilot_required": list(plan["pilot_required"]), "pilot_passes": {},
                                      "pending_schedules": [a for a in plan["schedule_actions"] if a["action"] == "update_existing"]}
    writes["installation.json"] = _json_body(manifest)
    return writes


def apply_preferences(config_path, plan, expected_digest):
    """Apply or resume the exact reviewed plan; no connected operation is invoked."""
    require(type(plan) is dict and plan.get("schema_version") == 1, "preferences", "invalid update plan")
    old, new = _validated(plan.get("before")), _validated(plan.get("after"))
    root = setup._root(old)
    require(no_symlink(Path(config_path).absolute()) == root / "config.json", "preferences", "use the installed config.json path")
    require(expected_digest == plan.get("expected_digest") == preferences_digest(old), "preferences", "expected old digest differs from the reviewed plan")
    require(_build_plan(old, new, plan.get("manifest_before")) == plan, "preferences", "update plan was changed; generate and review a new plan")
    journal_path = no_symlink(root / "state/preferences-update.json")
    from .local_excel import _writer_lock
    workbook_lock = _writer_lock(Path(new["tracker"]["path"])) if new["tracker"]["provider"] == "local_xlsx" else nullcontext()
    with setup._locked(old), workbook_lock, _protocol_lock(root):
        journal = read_json(journal_path) if journal_path.exists() else None
        if journal and journal.get("status") == "applying":
            require(journal.get("update_id") == plan["update_id"] and journal.get("plan") == plan, "preferences", "resume the exact unfinished update plan first")
        elif journal and journal.get("update_id") == plan["update_id"]:
            require(journal.get("status") == "committed" and read_json(root / "installation.json").get("preferences_update", {}).get("update_id") == plan["update_id"], "preferences", "this plan is stale")
            require(preferences_digest(load_config(root / "config.json")) == plan["new_digest"], "preferences", "saved preferences differ from completed update")
            return {"status": "already_applied", "update_id": plan["update_id"], "schedule_actions": plan["schedule_actions"], "connected_effects": []}
        else:
            current = load_config(root / "config.json")
            require(preferences_digest(current) == expected_digest, "preferences", "stale plan; current preferences changed")
            require(setup.load_instance(current) == plan["manifest_before"], "preferences", "installation bindings or acceptance changed; regenerate the plan")
            require(read_json(root / "state/approved-policies.json") == plan["old_policies"], "preferences", "current approved policy differs; reconcile it before updating")
            _check_idle(root, plan)
            history = no_symlink(root / "state/preferences-history")
            history.mkdir(mode=0o700, exist_ok=True)
            require(history.stat().st_uid == os.getuid() and not history.stat().st_mode & 0o077, "preferences", "history requires owner-only permissions")
            if journal:
                setup._atomic_json(history / (journal["update_id"] + ".json"), journal)
            writes = _writes(new, plan)
            before = {}
            for name in writes:
                path = no_symlink(root / name)
                setup._check_private_file(path)
                before[name] = path.read_text() if path.exists() else None
            journal = {"schema_version": 1, "update_id": plan["update_id"], "status": "applying", "plan": plan,
                       "before": before, "after": writes}
            # The immutable backup precedes publication of any changed settings.
            setup._atomic_json(history / (plan["update_id"] + ".backup.json"), journal)
            setup._atomic_json(journal_path, journal)
        require(journal["after"] == _writes(new, plan), "preferences", "recovery targets differ from reviewed plan")
        require(set(journal["before"]) == set(journal["after"]), "preferences", "incomplete recovery backup")
        _check_idle(root, plan)
        for name, after in journal["after"].items():
            path = no_symlink(root / name)
            setup._check_private_file(path)
            actual = path.read_text() if path.exists() else None
            require(actual in (journal["before"][name], after), "preferences", "managed file changed during interrupted update; inspect backup instead of overwriting it")
        for name, after in journal["after"].items():
            path = root / name
            if not path.exists() or path.read_text() != after:
                setup._atomic_text(path, after)
        require(all((root / name).read_text() == body for name, body in journal["after"].items()), "preferences", "saved update failed readback")
        verified = load_config(root / "config.json")
        manifest = read_json(root / "installation.json")
        require(preferences_digest(verified) == plan["new_digest"] and manifest["config_digest"] == setup.digest(public_settings(verified)) and manifest["profile_digest"] == setup.digest(verified["_profile"]), "preferences", "updated config and manifest failed readback")
        journal["status"] = "committed"
        setup._atomic_json(journal_path, journal)
        return {"status": "applied", "update_id": plan["update_id"], "backup": str(root / "state/preferences-history" / (plan["update_id"] + ".backup.json")),
                "schedule_actions": plan["schedule_actions"], "connected_effects": [],
                "pilot_required": list(plan["pilot_required"]),
                "execution_gate": "Affected scheduled and ordinary operations are held until an explicitly requested replacement pilot is verified. Use run-check; only the manual pilot may supply --pilot-update-id.",
                "next_action": "Use the updated config.json. Run each required manual pilot with this update ID, record first-pass evidence, and complete listed scheduler reconciliation through Codex tools. Local apply never changes live schedules."}


def record_schedule_reconciliation(config, update_id, workflow, receipt, verify, *, now=None):
    """Record exact native readback for a reviewed existing automation update."""
    validate_receipt(receipt, verify, now=now)
    require(receipt.capability == "resource.schedule" and receipt.stage == "operation_verified", "preferences", "expected verified native schedule readback")
    with setup._locked(config) as root:
        manifest = setup._manifest(root, config)
        update = manifest.get("preferences_update", {})
        require(update.get("update_id") == update_id, "preferences", "schedule readback belongs to another update")
        matches = [item for item in update.get("pending_schedules", []) if item["workflow"] == workflow]
        prior = update.get("verified_schedules", {}).get(workflow)
        if not matches and prior:
            require(prior["resource_id"] == receipt.resource_id and prior["receipt_digest"] == setup.digest(asdict(receipt)), "preferences", "schedule reconciliation was already recorded with different evidence")
            return {"status": "already_verified", "workflow": workflow, "resource_id": receipt.resource_id, "connected_effects": []}
        require(len(matches) == 1, "preferences", "no pending schedule reconciliation for this workflow")
        action = matches[0]
        require(workflow not in update.get("pilot_required", []) or action["request"]["status"] == "PAUSED", "preferences", "record a live pilot bound to this preference update before accepting an active changed schedule")
        require(receipt.resource_id == action["resource_id"], "preferences", "preserve the existing automation ID")
        require(receipt.evidence.get("installation_id") == config["installation_id"] and receipt.evidence.get("preferences_update_id") == update_id, "preferences", "schedule evidence is not bound to this preference update")
        for key in ("thread_id", "cadence", "local_time", "timezone", "status", "notification_policy", "prompt_digest"):
            require(receipt.evidence.get(key) == action["request"].get(key), "preferences", "saved schedule differs from the reviewed request")
        require(type(receipt.evidence.get("next_run_at")) is str or (action["request"]["status"] == "PAUSED" and "next_run_at" in receipt.evidence and receipt.evidence["next_run_at"] is None), "preferences", "schedule next-run readback is missing")
        binding = manifest["resources"]["schedule:" + workflow]
        require(binding["request"] == action["before_request"], "preferences", "prior schedule binding changed; inspect native drift")
        binding.update(request=copy.deepcopy(action["request"]), request_digest=setup.digest(action["request"]),
                       observation_id=receipt.observation_id, checked_at=receipt.checked_at,
                       receipt_digest=setup.digest(asdict(receipt)), next_run_at=receipt.evidence["next_run_at"])
        update["pending_schedules"].remove(action)
        update.setdefault("verified_schedules", {})[workflow] = {"resource_id": receipt.resource_id, "receipt_digest": setup.digest(asdict(receipt))}
        setup._atomic_json(root / "installation.json", manifest)
        return {"status": "verified", "workflow": workflow, "resource_id": receipt.resource_id, "connected_effects": []}
