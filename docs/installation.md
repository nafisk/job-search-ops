# Installation and host support

## Package format

Each `.agents/skills/<name>/` has YAML `name` and `description` frontmatter, concise instructions, a conditional reference, and a fictional optional preferences example. Names match directory names. Packages have no required scripts, connectors, sibling skills, or root-repository references.

The [Agent Skills specification](https://agentskills.io/specification) defines this structure. Format compatibility does not prove any host's discovery or browser behavior.

## Codex instructions checked October 30, 2026

The [official skill guide](https://learn.chatgpt.com/docs/build-skills) documents repository discovery at `.agents/skills` from the working directory through the repository root, explicit invocation, automatic change detection, and `$skill-installer` for other repositories. Restart if a skill does not appear.

For clone-and-open, use the README command after publication. For a local trial before publication, explicitly read the entrypoint in this checkout if it is not discovered.

For individual GitHub installation, give the built-in installer these separate values:

```text
Repository: RaymondRJones/job-search-ops
Ref: codex/ray-updates
Path: .agents/skills/job-search
Install only this directory and its contents; preserve existing skills.
```

Change the path for another skill. The installed Codex helper's instructions were inspected: it supports separate `--repo`, `--ref`, and `--path`, avoiding slash-containing branch ambiguity. No installation/download was run. Availability and authentication depend on the host. Resolve existing destinations before overwriting them.

For manual installation, copy the entire selected directory into the skill location documented by your host, not just its entrypoint. Keep applicant inputs/preferences elsewhere. The local Codex helper commonly uses `$CODEX_HOME/skills`; use its actual destination, not assumptions about another host. No new installer, plugin, or server is bundled.

## Capability and evidence limits

| Capability | Fallback | Status for this redesign |
| --- | --- | --- |
| Native discovery/install | Explicitly read the local skill and references | Codex docs checked; fresh discovery/install not tested |
| Resume attachment reader | Supplied resume text/career facts | Fictional text review only; PDF/DOCX readers not tested |
| Search/full-page reader | Supplied descriptions and search guidance, availability unverified | No real job research or adapters tested |
| Browser | Draft packet, route unverified | No live application handoff tested |
| Simplify | User's manual browser/extension workflow | No adapter; behavior untested |
| CSV/file write | Chat table | Export not exercised; protect formula prefixes if requested |
| Tracker connection | Chat output | No live accounts/trackers exercised |

Local validation uses Python on macOS; basic skills require neither that OS nor Python. No cross-agent, Windows/Linux, native fresh-install, or live integration success is claimed. Other Agent Skills hosts need independently checked host-specific install paths and capability tests.

These changes are local and uncommitted. GitHub installation is unavailable until this version is published.
