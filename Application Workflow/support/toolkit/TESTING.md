# Local helper verification

**Required:** Python 3.10+ with IANA timezone data. Test inputs are fictional.  
**Runs in:** Codex’s local terminal; no account access, browser or computer use.

Run from this directory:

```sh
python3 -B verify_offline.py
```

This checks the exact inventory against `SHAREABLE_FILES.txt`, rejects symlinks and missing/unlisted files, copies the helpers into a temporary workspace, runs their tests, and removes the temporary copy. It installs nothing and reads no personal settings or accounts.

## What the checks cover

- Profiles: explicit criteria, selected integrations, private paths and configuration-only loading.
- Discovery: full-message extraction, local Simplify link decoding, independent card review, exact-role qualification and portal evidence binding.
- Recovery: shared attempt limits, retained cursors and honest completion/coverage decisions.
- Tracking: exact application identity, submission evidence, lifecycle conflicts, response obligations and separate interview facts.
- Shared boundaries: scoped authority, evidence bindings, strict input validation and unchanged inputs.

Tests protect retained behavior. Their fixtures are not current job evidence or permission to run anything. Test expectations are independently specified; a helper must not generate its own expected answer.

## What they do not prove

These pure helpers do not test a live Gmail reader, portal browser, account permission, tracker writer or report send. The current [workflow verification](../../docs/verification.md) covers the separate setup, queue, tracker and native-evidence tests and records remaining live checks.

The previous standalone importer, simulated commit/delivery adapters, migration experiments, backlog/delta helpers and optional report renderer were removed because current runbooks use the workflow support CLI for those responsibilities or do not select them. Their dedicated tests and historical fixtures were removed with them; tests for retained helpers remain.

Use `python3 -B -m unittest discover -s tests -p test_alerts.py -v` for a focused check, replacing the filename as needed. Update the inventory only after reviewing exact file changes. Keep real-source evidence and results in private deployment state.
