# Validation and fictional scenarios

## Offline package checks

```sh
python3 scripts/validate_skills.py
python3 -B -m unittest discover -s tests/skills -v
```

The maintainer script checks this project's restricted two-scalar frontmatter,
names, file types, symlinks, and local-link closure. It is not a general YAML
parser. Isolation tests copy each skill alone, remove dependencies, add an
external dependency, and introduce a private-file symlink/binary to verify
failure behavior. They do not execute job screening or simulate an agent.

Also run the installed skill-creator's `scripts/quick_validate.py` for each skill
when available; its YAML parser provides a separate format check. This is a
developer tool, never a basic skill dependency.

## Behavioral review

[Eleven fictional cases](../tests/skills/scenarios.md) cover stale/blocked
postings, misleading support titles, unknown qualifications, missing tools,
duplicate applications, precedence, geography, referral holds, degree branches,
calibration, and uncertain submissions. Evaluate by applying the skill to the
supplied observations without fetching fictional URLs. Compare outputs against
the oracle and record actual results, including failures.

Initial validation includes an author-performed tabletop walkthrough, not an
independent agent run or an automated model benchmark. An expected outcome in a
fixture is not evidence of actual model compliance. See the validation record
below for the exact scope exercised.

## Existing advanced runtime

No advanced runtime code is changed. Its regression suites can run on fictional
data using [existing commands](<../Application Workflow/docs/verification.md>).
Keep the strict reviewed release inventory. A personal file in the working tree
must continue to block whole-repo export. To validate public assets without
moving/deleting that file, copy only the explicitly reviewed inventory into a
temporary directory, run the release check there, and identify that scope in the
report. Never add private inputs to the inventory or weaken the checker.

## Validation record

Pending execution: record format/package results and tabletop outcomes here
before considering this initial implementation complete. No real job research,
accounts, trackers, chats, live browser routes, Simplify behavior, or cross-host
installation will be exercised during this development task.
