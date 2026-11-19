# Set up referral matching and portal searches

Set `sources.referral_companies_path` to your private company list. Coordinated discovery matches employers after deduplication. Targeted portal searches use the same list.

## Choose companies

Reuse the user's referral companies. Ask for missing decisions. A contact name is optional. Confirm which names may go in the selected tracker and keep any others in private notes.

Copy the [fictional example](../support/config/examples/referral-companies.json) into the ignored `private/` folder or a separate private location. Confirm each employer and its stable `company_id` with the user. Add an optional `aliases` array of confirmed employer names. Include a subsidiary only when the user confirms that their referral covers it. Leave unknown contacts and careers links blank.

The Jobs **Referral** column shows **Available** for a unique employer match and is blank otherwise. A match means the employer is on your list. If a name points to more than one company, review it before adding an alias. Use **Application Status** or **Notes** to track your next step.

## Populate the selected tracker

For referral matching alone, the private list and the Jobs **Referral** column are enough. To enable portal searches, follow the steps below to populate **Referral Watchlist** and create `portal-registry.json`.

Run commands from `Application Discovery/support/` after verifying the tracker and before the portal pilot. Coordinate with the central writer for the `referral-setup` claim.

**Excel:** close the workbook and use the verified Node and package paths:

```sh
python3 -m job_search_ops referrals-prepare --config /absolute/private/config.json
python3 -m job_search_ops referrals-local --config /absolute/private/config.json --node /absolute/runtime/node --node-modules /absolute/runtime/node_modules
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

Only verified rows publish the private registry. Confirm each company’s contact, careers URL, scope and observed watchlist row before the helper runs. No empty watchlist is accepted as successful setup for a nonempty selected list.

## Build links for repeat runs

During the first [portal pilot](agent-setup.md#5-pilot-the-selected-path), open each official career board in scope. Apply the approved role, employment type and location filters the portal supports. Use separate searches for distinct scopes when needed, such as NYC and eligible US remote. Screen requirements like years of experience from the full job descriptions when the board lacks a reliable filter.

For each search, confirm the employer, selected filters and complete pagination. Reopen the exact first-page URL in a clean tab. Save it as a reusable link only if it restores the intended filters. If filters do not survive reopening, save the board URL and the ordered controls to apply. Record unavailable routes and untested scopes as pending. Follow the [portal validation checks](../support/toolkit/PORTALS.md#live-recipe-acceptance).

Save checked searches to the existing private `portal-registry.json`. Keep company IDs, scope and prior evidence. Record each search's scope, checked date and evidence references. Use these fields to identify the entry point:

| Route | Registry entry |
| --- | --- |
| Direct link | Add the exact filtered URL to `observed_urls`. Set `details.route_kind` to `url` and `details.entry_url` to that URL. |
| Browser steps | Set `details.route_kind` to `browser_steps`. Record the observed board URL as `details.entry_url` and the ordered controls as `details.steps`. |
| Pending | Keep `details.status` as `needs_validation` and record the gap. |

The coordinator [validates the registry](../support/toolkit/PORTALS.md#build-the-registry) before updating it atomically. Include the link, steps or pending gap for each scope in the private setup summary. If an export is selected, copy links or steps to **Referral Portals** Targets, keeping contacts private. Recheck scope each run.

## Check before an application handoff

Accepted aliases map alternate job IDs and verified URLs to the same role across runs. The writer keeps any contacts found during portal research in private receipts, separately from your Notes and Referral Contact cells.

Read the merged accepted state before opening application pages:

```sh
python3 -m job_search_ops role-state --root /absolute/private --workbook VERIFIED_WORKBOOK_ID
```

Here `--root` is the installation directory, and `--workbook` is the installed tracker ID (including its `local:` prefix for Excel). The output is private. Use `aliases` and `alias_urls` to resolve the canonical role. The legacy `referral_restrictions` field preserves contact evidence and any old referral holds as history. [Reports](report.md) can note a newly discovered contact without publishing the name.

## Preserve edits and recover

Existing matching rows are reused; conflicting contacts, notes or companies stop setup without replacement. A completed identical seed is idempotent. After setup, the helper reads the private scope and accepted search routes. Adding/removing companies or reconciling manual edits with the frozen seed is a separate reviewed migration. Do not overwrite the list or delete its journal to force reseeding.

Before an attempt, `python3 -m job_search_ops referrals-cancel --config /absolute/private/config.json` archives a prepared plan and releases its claim so a corrected source can be planned. It refuses attempted writes. After a Google timeout, retain the claim and read back; `referrals-commit` can accept an exact saved result without repeating inserts. Any mismatch remains unresolved for inspection. For Excel, rerun `referrals-local`: the file hashes distinguish a saved result from an unchanged original; unexpected edits stop recovery.

If Google confirms a terminal failed attempt and the complete watchlist is still exactly the before-state, use `python3 -m job_search_ops referrals-retry --config /absolute/private/config.json --snapshot /absolute/private/watchlist-fresh.json --settlement /absolute/private/seed-settlement.json`. The private settlement contains `kind: "native_terminal_failure"`, the exact returned `attempt_id`, a timezone-qualified `verified_at`, and `response` holding the actual native error response (or its saved JSON path). Only terminal codes 400/401/403/404/409/412/422 qualify; timeouts and server errors do not. The helper records settlement and returns the plan to prepared; obtain fresh state and authorize again before any new request. A prior attempt’s settlement cannot authorize a later retry.
