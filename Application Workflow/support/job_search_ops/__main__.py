"""Local command entrypoint. Connected operations are performed by Codex tools."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .config import ConfigError, execution_plan, load_config, no_symlink, read_json, require
from .host_evidence import load_evidence, verify


def parser():
    root = argparse.ArgumentParser(description="Local setup, queue, and tracker write helpers. No network calls or schedule activation.")
    commands = root.add_subparsers(dest="command", required=True)
    def command(name, description, fields=()):
        p = commands.add_parser(name, help=description)
        p.add_argument("--output", help="Save JSON to this private path instead of stdout")
        if name in {"run-check", "enqueue", "prepare", "tracking-prepare", "authorize-write", "local-sync", "local-update", "brief-prepare", "brief-sending"}:
            p.add_argument("--pilot-update-id", help="Only for an explicitly requested manual replacement pilot; never save this flag in schedules")
        for field in fields:
            p.add_argument("--" + field, required=True)
        return p
    command("run-check", "Check whether the selected workflow may run before accessing sources", ("config", "workflow"))
    command("role-state", "Read accepted aliases and private referral restrictions before manual actions", ("root", "workbook"))
    command("preferences-plan", "Review a same-installation settings change", ("config", "candidate"))
    command("preferences-apply", "Apply or resume the exact reviewed local settings change", ("config", "plan", "expected-digest"))
    command("preferences-schedule-record", "Record native readback of an existing schedule update", ("config", "update", "workflow", "evidence", "observation"))
    p = command("referrals-prepare", "Plan selected companies into the watchlist and portal registry", ("config",))
    p.add_argument("--snapshot", help="Required native readback for Google; local reads its bound workbook")
    command("referrals-retry", "Rearm a settled failed Google seed after exact unchanged readback", ("config", "snapshot", "settlement"))
    command("referrals-cancel", "Archive an unattempted referral seed for replanning", ("config",))
    command("referrals-authorize", "Check fresh Google watchlist before the exact seed write", ("config", "snapshot"))
    p = command("referrals-commit", "Verify saved referral rows before publishing their registry", ("config",))
    p.add_argument("--snapshot", help="Required native Google readback; local reads its bound workbook")
    command("referrals-local", "Seed and verify the selected private Excel watchlist", ("config", "node", "node-modules"))
    command("tracking-review", "Review exact Google job identities and current manual fields", ("workbook", "snapshot"))
    p = command("tracking-prepare", "Prepare an evidence-backed Google tracking change journal", ("root", "workbook", "snapshot", "plan"))
    p.add_argument("--owner", default="central")
    command("init", "Initialize a private instance without connecting accounts", ("config",))
    command("setup-plan", "Review selected storage, sources, chats, permissions and schedules without effects", ("config",))
    p = command("doctor", "Check installed tools and current native evidence", ("config",))
    p.add_argument("--evidence"); p.add_argument("--check-staging", action="store_true")
    p.add_argument("--workflow", choices=("main", "blind"), help="Check only this workflow’s dependencies")
    command("prompts", "Write prompts using verified real resource bindings", ("config",))
    command("runtime-profile", "Resolve the strict toolkit profile with actual resource bindings", ("config",))
    p = command("schedule-plan", "Prepare only selected schedules after verified first passes", ("config",))
    p.add_argument("--evidence")
    p.add_argument("--workflow", choices=("main", "blind"), help="Prepare only this workflow’s schedule")
    for name, description in (("local-init", "Create and verify the selected private Excel tracker"),
                              ("local-sync", "Merge queued discoveries into the selected private Excel tracker"),
                              ("local-update", "Apply an evidence-backed tracking update to the selected private Excel tracker")):
        p = command(name, description, ("config", "node", "node-modules"))
        if name == "local-update": p.add_argument("--plan", required=True)
    command("resource-intent", "Reserve a resource effect before invoking a native tool", ("config", "kind", "key", "request"))
    command("resource-uncertain", "Record an unknown creation outcome", ("config", "kind", "key"))
    command("resource-record", "Record a native resource readback", ("config", "kind", "key", "evidence", "observation"))
    command("first-pass-record", "Record acceptance of an actual live initial run", ("config", "workflow", "evidence", "observation"))
    command("snapshot", "Assemble native metadata and request/CellData response pairs", ("metadata", "reads"))
    command("bootstrap", "Prepare native formatting for an empty imported tracker", ("snapshot",))
    command("enqueue", "Validate and queue a source packet", ("root", "packet"))
    command("pending", "List queued imports", ("root",))
    command("prepare", "Prepare the sole-writer native batch", ("root", "workbook", "snapshot", "owner"))
    for name in ("authorize-write", "commit", "reconcile"):
        p = command(name, "Check fresh native state against the durable write journal", ("root", "journal", "snapshot"))
        if name == "reconcile": p.add_argument("--settlement", help="Saved evidence that an uncertain native operation has terminated")
    command("cancel-unattempted", "Cancel an unattempted journal after inspection", ("root", "journal", "owner"))
    command("release-claim", "Release a resolved workbook writer claim", ("root", "workbook", "owner"))
    command("brief-prepare", "Reserve newly saved roles for one brief", ("root", "brief"))
    command("brief-sending", "Record an intended delivery before sending", ("root", "brief", "delivery"))
    command("brief-delivered", "Commit exact successful delivery evidence", ("root", "brief", "evidence"))
    return root


def one_observation(args):
    observations = [r for r in load_evidence(args.evidence) if r.observation_id == args.observation]
    if len(observations) != 1:
        raise ConfigError("evidence: choose one unique observation ID")
    return observations[0]


def run(args):
    from .setup import execution_context
    with execution_context(pilot_update_id=getattr(args, "pilot_update_id", None)):
        return run_command(args)


def run_command(args):
    name = args.command
    if name == "preferences-apply":
        from .preferences import apply_preferences
        return apply_preferences(args.config, read_json(args.plan), args.expected_digest), 0
    config = load_config(args.config) if hasattr(args, "config") else None
    if name == "doctor":
        from .doctor import run_doctor
        result = run_doctor(config, load_evidence(args.evidence) if args.evidence else (), verify,
                            check_staging=args.check_staging, workflow=args.workflow)
        return result, 0 if result["ready"] else 2
    if config is not None:
        from . import setup
        if name == "run-check": result = setup.run_check(config, args.workflow)
        elif name.startswith("preferences-"):
            from . import preferences
            if name == "preferences-plan":
                result = preferences.preference_plan(config, load_config(args.candidate))
            else:
                result = preferences.record_schedule_reconciliation(config, args.update, args.workflow, one_observation(args), verify)
        elif name.startswith("referrals-"):
            from . import referrals
            from .snapshots import read_data
            snapshot = read_data(args.snapshot) if getattr(args, "snapshot", None) else None
            if name == "referrals-retry": result = referrals.retry_google(config, snapshot, read_json(args.settlement))
            elif name == "referrals-cancel": result = referrals.cancel_unattempted(config)
            elif name == "referrals-prepare": result = referrals.prepare(config, snapshot)
            elif name == "referrals-authorize": result = referrals.authorize(config, snapshot)
            elif name == "referrals-commit": result = referrals.commit(config, snapshot)
            else: result = referrals.local_seed(config, args.node, args.node_modules)
        elif name == "setup-plan": result = setup.setup_plan(config)
        elif name == "init": result = setup.init_instance(config)
        elif name == "prompts": result = setup.prepare_prompts(config)
        elif name == "runtime-profile": result = setup.runtime_profile(config)
        elif name == "schedule-plan": result = setup.prepare_schedules(config, load_evidence(args.evidence) if args.evidence else (), verify, workflow=args.workflow)
        elif name in {"local-init", "local-sync", "local-update"}:
            require(execution_plan(config)["tracker"]["provider"] == "local_xlsx", "tracker", "local Excel is not selected")
            from . import local_excel
            if name == "local-init":
                intent = setup.prepare_resource(config, "tracker", "tracker", {"provider": "local_xlsx", "path": config["tracker"]["path"]})
                if intent["action"] == "reuse_verified":
                    local_excel.inspect_workbook(config["tracker"]["path"], intent["resource_id"])
                    result = intent
                else:
                    result = setup.record_local_tracker(config, local_excel.initialize(config, args.node, args.node_modules))
            else:
                workbook = setup.runtime_profile(config)["trackers"]["jobs"]["workbook_id"]
                if name == "local-sync":
                    result = local_excel.merge(config["instance_root"], workbook, config["tracker"]["path"], args.node, args.node_modules)
                else:
                    require(bool(execution_plan(config)["tracking"]), "tracking", "tracking is not selected")
                    result = local_excel.update_tracking(config["instance_root"], workbook, config["tracker"]["path"], read_json(args.plan), args.node, args.node_modules)
        elif name == "resource-intent": result = setup.prepare_resource(config, args.kind, args.key, read_json(args.request))
        elif name == "resource-uncertain": result = setup.mark_resource_uncertain(config, args.kind, args.key)
        elif name == "resource-record": result = setup.record_resource(config, args.kind, args.key, one_observation(args), verify)
        elif name == "first-pass-record": result = setup.record_first_pass(config, args.workflow, one_observation(args), verify)
        else: raise ConfigError("command: unsupported setup operation")
        return result, 0
    if name == "snapshot":
        from .snapshots import assemble, read_data
        return assemble(read_data(args.metadata), read_data(args.reads)), 0
    if name == "bootstrap":
        from .bootstrap import plan
        from .snapshots import read_data
        return plan(read_data(args.snapshot)), 0
    from . import queue, sheets
    if name in {"prepare", "tracking-prepare", "authorize-write", "commit", "reconcile"}:
        # Match the queue's existing root normalization (including macOS /var).
        # Installation config validation still rejects user-configured symlinks.
        manifest_path = no_symlink(Path(args.root).expanduser().resolve() / "installation.json")
        if manifest_path.exists():
            binding = read_json(manifest_path).get("resources", {}).get("tracker:tracker", {})
            require(binding.get("provider") != "local_xlsx", "tracker", "use local-sync or local-update for this installation")
    if name == "tracking-review":
        from .google_tracking import review
        from .snapshots import read_data
        return review(read_data(args.snapshot), args.workbook), 0
    if name == "tracking-prepare":
        from . import setup
        from .google_tracking import prepare
        from .snapshots import read_data
        installed = load_config(no_symlink(Path(args.root).expanduser().resolve() / "config.json"))
        require(Path(installed["instance_root"]) == Path(args.root).expanduser().resolve(), "instance", "use the installed root")
        require(bool(execution_plan(installed)["tracking"]), "tracking", "tracking is not selected")
        require(execution_plan(installed)["tracker"]["provider"] == "google_sheets", "tracker", "Google Sheets is not selected")
        binding = setup.load_instance(installed)["resources"].get("tracker:tracker", {})
        require(binding.get("status") == "verified" and binding.get("resource_id") == args.workbook,
                "tracker", "tracking must use the verified installed workbook")
        return prepare(args.root, args.workbook, read_data(args.snapshot), read_json(args.plan), args.owner), 0
    if name == "role-state": result = sheets.role_state(args.root, args.workbook)
    elif name == "enqueue": result = queue.enqueue(args.root, args.packet)
    elif name == "pending": result = queue.pending(args.root)
    elif name == "prepare": result = sheets.prepare(args.root, args.workbook, args.snapshot, args.owner)
    elif name == "authorize-write": result = sheets.authorize_write(args.root, args.journal, args.snapshot)
    elif name == "commit": result = sheets.verify_and_commit(args.root, args.journal, args.snapshot)
    elif name == "reconcile": result = sheets.reconcile(args.root, args.journal, args.snapshot, settlement=read_json(args.settlement) if args.settlement else None)
    elif name == "cancel-unattempted": result = sheets.cancel_unattempted(args.root, args.journal, args.owner)
    elif name == "release-claim": result = queue.release_claim(args.root, args.workbook, args.owner)
    elif name == "brief-prepare": result = queue.prepare_brief(args.root, args.brief)
    elif name == "brief-sending": result = queue.mark_brief_sending(args.root, args.brief, read_json(args.delivery))
    elif name == "brief-delivered": result = queue.confirm_brief_delivery(args.root, args.brief, read_json(args.evidence))
    else: raise ConfigError("command: unsupported operation")
    return result, 0


def emit(result, output):
    body = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if not output:
        print(body, end="")
        return
    target = Path(output).absolute()
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ConfigError("output: symlink paths are not supported")
    fd, tmp = tempfile.mkstemp(prefix=".result-", dir=target.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(body); stream.flush(); os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result, code = run(args)
        emit(result, args.output)
        return code
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error), "effects": "No connected operation was performed by this CLI."}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
