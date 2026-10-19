# Native evidence and local commands

> **Required:** Python 3.10+, private writable evidence storage and actual responses from each selected tool. Google snapshots require native Drive/Sheets reads.
> **Runs in:** Codex app with connectors and local helpers; [Local Excel](local-excel.md) uses actual file evidence.
> **Computer use:** Only when collecting evidence for a selected browser operation.

This guide applies to connected operations, especially the Google Sheets backend. Local Excel uses actual file verification described in [local Excel](local-excel.md); never label local file evidence as a Google connector response. Read the saved choices first and collect evidence only for selected capabilities.

Local helper commands in this guide run from `Application Workflow/support/` in the permanent checkout.

Codex executes account operations with connected tools. The local helpers retain
requests, validate their returned data, and keep retries consistent. They do not
hold Google credentials or contact accounts themselves.

## Capture the actual response

Save raw native tool results in the private instance directory, with the request
and the time actually observed. Keep the native `structuredContent` object or the
JSON text returned by the tool. For text-only browser or search results, save the
verbatim output as `{"text": "..."}`. Never replace a response with expected data.

A capability observation has this shape. This is fictional syntax documentation,
not evidence that any real account was checked:

```json
{
  "schema_version": 1,
  "observations": [{
    "capability": "gmail_read",
    "stage": "connected",
    "observation_id": "example-profile-read",
    "checked_at": "2026-10-18T12:00:00Z",
    "identity": "alex@example.invalid",
    "resource_id": null,
    "operation": "profile-read",
    "evidence": {
      "installation_id": "alex",
      "operations": ["get_profile"],
      "native_checks": [{
        "operation": "get_profile",
        "tool": "mcp__codex_apps__gmail_get_profile",
        "request": {},
        "response": {"emailAddress": "alex@example.invalid"},
        "assertions": [{"path": "/emailAddress", "equals": "alex@example.invalid"}]
      }]
    }
  }]
}
```

Use the real host tool name and actual returned schema. An assertion's `path` is
a JSON pointer into the unwrapped response. Checks support exact `equals`,
`contains`, `min_items`, or the SHA-256 of a returned text value. Each operation
must have retained native data and an assertion appropriate to that operation.
An empty-list response can prove a successful bounded search, but cannot prove a
message read or full source coverage. A successful HTTP request does not prove
that a job meets the candidate's policy.

`config/capabilities.json` lists the operations needed for each enabled feature.
The doctor distinguishes installed tools, connected accounts, and tested operations.
Local tool presence and a profile read alone do not make a workflow ready. Evidence
expires after 15 minutes for setup/readiness checks; refresh the affected bounded
checks before activation. Historical save and delivery receipts remain durable.

```sh
python3 -m job_search_ops doctor --config /PRIVATE/config.json \
  --evidence /PRIVATE/readiness.json --output /PRIVATE/doctor.json
```

Exit codes are 0 for success/readiness, 2 for a doctor report with missing or failed
requirements, and 1 for invalid input. All commands accept `--output` for private
JSON. They perform no connected operation and do not activate schedules.

These checks operate at a **trusted local agent boundary**. They are not signed
tool attestations: a person who edits the evidence can fabricate it. Their purpose
is to catch missing, stale, mismatched, or internally inconsistent observations.
Do not run setup with evidence received from someone else. Tests use fictional
responses solely to verify the protocol and cannot establish live readiness.

## Assemble a Google Sheets snapshot

Read native metadata and bounded `CellData`, including trailing empty areas. For
each request use the explicit mask from `Application Workflow/sheets/workbook-schema.json`. Store
each cell response with its **actual** request:

```json
[
  {
    "request": {
      "spreadsheet_id": "ACTUAL_RETURNED_ID",
      "ranges": ["'Jobs'!A1:O1000"],
      "cell_fields": "userEnteredValue,effectiveValue,hyperlink,userEnteredFormat(textFormat),effectiveFormat(textFormat),textFormatRuns"
    },
    "response": {"spreadsheetId": "ACTUAL_RETURNED_ID", "sheets": []}
  }
]
```

The example response is intentionally incomplete. Real writes require all four
managed data tabs through their actual grid row counts and Daily Summary A4:B12.
Setup also reads the other header rows and the formatting evidence. Split large reads into
contiguous bounded chunks; use the same complete mask on every chunk. Do not claim
an unread range was empty because Google omitted trailing cells from another range.
Local native payloads have a 128 MiB ceiling; do not truncate history to fit. Stop
for a reviewed archival/migration if a complete snapshot exceeds that ceiling.

```sh
python3 -m job_search_ops snapshot --metadata /PRIVATE/metadata.json \
  --reads /PRIVATE/cell-reads.json --output /PRIVATE/snapshot.json
python3 -m job_search_ops bootstrap --snapshot /PRIVATE/snapshot.json \
  --output /PRIVATE/bootstrap-plan.json
```

`bootstrap` applies only to an empty imported template. It emits native requests
for frozen headers, filters, status validation, a hidden key column, date formats,
and open-ended Google summary formulas. Apply its `requests` with the connector,
then read back all settings. Send its `include_spreadsheet_in_response`,
`response_include_grid_data`, and `response_ranges` arguments along with the batch.
Retain the actual returned `updatedSpreadsheet` under a `bootstrap_readback`
native check. This carries column metadata as well as cells, so the verifier can
check hidden O, frozen headers, filters, status choices, date formats, and summary
formulas. Omit the descriptive `readback` key from the actual tool arguments.
It is not a migration tool for an existing tracker.

## Bind new resources

Before creating a workbook/chat/schedule, save its exact intended request using
`resource-intent`. If the returned action is `reconcile_existing_intent`, inspect
the original result and native resource list; do not create again. Use
`resource-uncertain` if the outcome is unknown.

`resource-record` consumes one observation from an evidence bundle. It requires
capability `resource.tracker`, `resource.chat`, or `resource.schedule`, stage
`operation_verified`, the actual returned `resource_id`, and `evidence` containing
the exact `installation_id`, `intent_id`, and `request_digest` from the saved intent.

- A tracker observation includes a matching account profile, metadata and complete
  cell reads, and their assembled `snapshot`. The snapshot must match the retained
  request/response data exactly; a separate expected workbook is rejected. Include
  the `bootstrap_readback` check above; missing structural evidence prevents binding.
- A chat observation retains creation/readback plus a `workspace_probe` from that
  chat. Its actual execution result must contain `workspace_path` and
  `staging_write_readback: true`, backed by a temporary file written and read in that
  workspace. Record the real workspace, even if it differs from the requested one.
- A schedule observation retains the actual saved native view and its returned ID.
  `field_checks` maps each required normalized field to `{check: 0, path: "/..."}`
  in `native_checks`. Fields are `thread_id`, `local_time`, `timezone`, `status`,
  `notification_policy`, `prompt_digest`, and `next_run_at`. The prompt field points
  to the returned prompt text; the adapter hashes it. Supported explicit transforms
  are `rrule_time` for a single BYHOUR/BYMINUTE recurrence,
  `notification_policy` for native null → meaningful changes, and `uppercase` for
  status. Do not fabricate timing fields a host does not return; leave activation
  unverified and document the host limitation until its actual UI/API can verify it.

```sh
python3 -m job_search_ops resource-intent --config /PRIVATE/config.json \
  --kind tracker --key tracker --request /PRIVATE/tracker-request.json \
  --output /PRIVATE/tracker-intent.json
python3 -m job_search_ops resource-record --config /PRIVATE/config.json \
  --kind tracker --key tracker --evidence /PRIVATE/resources.json \
  --observation ACTUAL_OBSERVATION_ID
```

## First-pass acceptance and delivery

For each enabled workflow, retain its real accepted run manifest and native output
readback. `first-pass-record` requires `first_live_pass` capability, identities for
selected connected accounts, actual run ID, bound workbook ID, truthful coverage
status, zero unsynced jobs, and
verified configured delivery. Store `accepted_manifest` and its canonical SHA-256
(sorted JSON keys, compact separators, UTF-8). The manifest must be present in the
actual `accepted_manifest_readback` result, directly or in parsed execution stdout.
A local Excel/public-research/chat installation needs no Google account identity;
retain its actual local workbook and configured chat binding instead.
Include `delivery_readback` from the actual destination. Source gaps may remain
explicit `complete_with_exceptions`; unsaved writes cannot pass acceptance.

For daily report retries and the separate saved-vs-delivered frontier, follow
[the Sheets protocol](sheets-protocol.md) and [report runbook](report.md).
Do not substitute a send acknowledgement or a made-up message reference for actual
delivery readback. Blind's saved result remains eligible for exactly one later
central daily brief; its own result message does not consume that brief frontier.
