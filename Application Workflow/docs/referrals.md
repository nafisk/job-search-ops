# Set up referral companies

> **Required when selected:** Portal discovery, Python 3.10+, a verified tracker and a private company file.
> **Runs in:** Codex app; Google uses native Sheets tools, Excel uses the [local runtime](local-excel.md).
> **Computer use:** None for seeding; later portal research may require it.

**One private company list defines scope.** `sources.referral_companies_path` points to that list. Setup projects it into the tracker’s **Referral Watchlist** and writes `<installation>/portal-registry.json` for [toolkit portal checks](../support/toolkit/PORTALS.md). The watchlist is a readable projection; it is not a second independent company list.

## Choose companies

Copy the [fictional example](../support/config/examples/referral-companies.json) outside the repository and replace its company, careers link and search scope. Keep stable `company_id` values. Contacts and notes are optional private text; `referral_hold` is an explicit boolean. Set the absolute file path in the private setup draft before `init`.

The agent validates the exact example fields. A supplied career URL is a starting point, not verified portal evidence. The generated registry has no invented official observations; the helper must validate pages and filters during research.

## Populate the selected tracker

Run commands from `Application Workflow/support/` after the tracker is verified and before the portal pilot. Coordinate with the central writer; seeding uses the exclusive `referral-setup` claim.

**Excel:** close the workbook and use the actual runtime paths returned by Codex:

```sh
python3 -m job_search_ops referrals-prepare --config /absolute/private/config.json
python3 -m job_search_ops referrals-local --config /absolute/private/config.json --node /absolute/bundled/node --node-modules /absolute/bundled/node_modules
```

**Google Sheets:** obtain native workbook metadata and complete `Referral Watchlist!A4:E<allocated-row-count>` CellData with `userEnteredValue`. Retain actual requested ranges in `_read_ranges` and `_cell_fields`; use the [snapshot assembler](native-evidence.md). Capture fresh state again before authorization.

```sh
python3 -m job_search_ops referrals-prepare --config /absolute/private/config.json --snapshot /absolute/private/watchlist-before.json
python3 -m job_search_ops referrals-authorize --config /absolute/private/config.json --snapshot /absolute/private/watchlist-fresh.json --output /absolute/private/referral-write.json
```

Send the returned exact `requests` once through native `batch_update_spreadsheet`, with the returned `workbook_id`. Read back the complete watchlist, then:

```sh
python3 -m job_search_ops referrals-commit --config /absolute/private/config.json --snapshot /absolute/private/watchlist-after.json
```

Only verified rows publish the private registry. Confirm each company’s contact/hold, careers URL, scope and observed watchlist row before the helper runs. No empty watchlist is accepted as successful setup for a nonempty selected list.

## Check before an application handoff

Portal proposals can add a restriction to a role already found through email or rated-company research. Both tracker writers save these source facts in private accepted receipts, separately from manual Notes and Referral Contact cells. Accepted aliases map alternate job IDs and verified URLs to that same role across runs.

Read the merged accepted state before opening application pages:

```sh
python3 -m job_search_ops role-state --root /absolute/private --workbook VERIFIED_WORKBOOK_ID
```

Here `--root` is the installation directory, and `--workbook` is the installed tracker ID (including its `local:` prefix for Excel). The output is private: `aliases` and `alias_urls` resolve the canonical role, and `referral_restrictions` contains holds, discovered contacts and evidence. Check it alongside the current company watchlist and user instructions; the stricter restriction wins.

A later sighting, edited note or blank contact does not release a hold. There is no automatic release command. Resolve the approved route with the user for the named role before proceeding; never delete accepted receipts to bypass a restriction. [Reports](report.md) show new hold/contact-discovered notices without publishing private contacts.

## Preserve edits and recover

Existing matching rows are reused; conflicting contacts, holds, notes or companies stop setup without replacement. A completed identical seed is idempotent. After setup, the helper reads the private scope and checks live manual holds; a stricter hold always wins. Adding/removing companies or reconciling manual edits with the frozen seed is a separate reviewed migration. Do not overwrite the list or delete its journal to force reseeding.

Before an attempt, `python3 -m job_search_ops referrals-cancel --config /absolute/private/config.json` archives a prepared plan and releases its claim so a corrected source can be planned. It refuses attempted writes. After a Google timeout, retain the claim and read back; `referrals-commit` can accept an exact saved result without repeating inserts. Any mismatch remains unresolved for inspection. For Excel, rerun `referrals-local`: the file hashes distinguish a saved result from an unchanged original; unexpected edits stop recovery.

If Google confirms a terminal failed attempt and the complete watchlist is still exactly the before-state, use `python3 -m job_search_ops referrals-retry --config /absolute/private/config.json --snapshot /absolute/private/watchlist-fresh.json --settlement /absolute/private/seed-settlement.json`. The private settlement contains `kind: "native_terminal_failure"`, the exact returned `attempt_id`, a timezone-qualified `verified_at`, and `response` holding the actual native error response (or its saved JSON path). Only terminal codes 400/401/403/404/409/412/422 qualify; timeouts and server errors do not. The helper records settlement and returns the plan to prepared; obtain fresh state and authorize again before any new request. A prior attempt’s settlement cannot authorize a later retry.
