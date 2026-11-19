# Private installation choices

Prepare private JSON from the user's [onboarding](../../ONBOARDING.md) choices. Use Python 3.10+ to review `setup-plan --config <private-file>` before creating resources.

[installation-v2.json](examples/installation-v2.json) and
[profile-v2.json](examples/profile-v2.json) illustrate a local Excel tracker,
portal discovery, chat reporting and manual runs. All paths, people and search
criteria are fictional. These examples are not choices or authorization on the
user's behalf.

Version two makes each branch explicit:

| Setting | Selection |
| --- | --- |
| `tracker.provider` | `google_sheets` or `local_xlsx`. |
| `tracker.path` | Null for Google. Local Excel uses an absolute `.xlsx` path in the private instance or in a separate owner-only workbook folder outside the repo. |
| `discovery.email`, `discovery.portals` | Select email alerts and referral portal research independently. |
| `discovery.coordinated` | Use one search profile for selected Gmail alerts and Blind research. Run selected referral portals on request. |
| `modules.blind` | Choose rated-company discovery separately. |
| `tracking.gmail`, `modules.calendar`, `modules.messages` | Independently choose tracking sources. None is inferred from discovery. |
| `tracker_admission` | Optional [tracker save rule](../../docs/handoffs.md#tracker-admission). Applies the same stated-years and level gate to all selected discovery sources. |
| `modules.main` | True: the central coordinator owns the selected tracker and report. |
| `schedules.main`, `schedules.blind` | Enable only the schedules requested. Disabled times may be null. |
| `report` | Chat by default; self-email requires a named recipient and explicit send opt-in. |

At least one discovery or tracking source is selected. A tracking-only setup has
one central chat and no discovery helpers. Other setups create only their
selected helper chats. Manual runs need no schedule tool.

The `modules.excel_export` compatibility flag selects the spreadsheet runtime
check. The three-tab workbook uses its own [discovery export destination](../../docs/discovery-export.md#switch-the-next-export),
saved in `state/discovery-export.json`. Set `tracker.provider` for the separate
jobs tracker.

`installation.schema.json` is an editor aid. `load_config` is the authoritative
validator for cross-field choices, profile, paths, timezone and permission
boundaries. It reads no resume or referenced correspondence and changes nothing.
The single `execution_plan(config)` derivation controls capability checks,
helper bindings, source policies, staging folders, schedules and generated
prompts. Disabled source evidence is not passed to connection verifiers.

Only selected sources require their queries and company files. A disabled Blind
branch may use null `blind_policy`. Tracking-only version-two profiles can use
empty role-family, level and location lists, null residency and null candidate
experience; selecting discovery requires real search scope and truthful tenure.
Profile version two allows null `account_identity` and `report_recipient` when
unused. Selected Google access requires its account identity, and self-email
requires its recipient. Runtime profiles make unselected integrations inert.

Keep the private runtime instance outside the checkout. Résumés, profile references
and private source lists can live under the checkout's ignored `private/` directory.
The instance parent must already exist. Initialization creates owner-only files
and directories. Symlinks, parent
traversal, substitutions and URLs are not private path syntax. Existing state is
preserved. Change ordinary preferences through [plan/apply](../../docs/preferences.md); replacing accounts, tracker or paths requires a separately reviewed migration.

Initialization saves guarded `config.json` and `profile.json`, an installation
manifest, approved source policies and a private `execution-plan.json` for
version two. After real tracker readback, `runtime-profile.json` contains the
actual Google ID or stable local identity `local:<installation_id>` and verified
column mappings. The local path stays in private installation settings. Use the
runtime profile for reusable toolkit operations; never substitute an example ID.

Google binding requires native metadata/cell readback. Local binding reopens the
actual XLSX and verifies its bytes, schema and hyperlinks; a Google-shaped fake
response is not local proof. Local edits use the verified artifact runtime
and an atomic, journaled save. The private artifact package is not an npm install.
Local first-pass acceptance includes the current `tracker_file_sha256` in both
the captured accepted manifest and its receipt.

`capabilities.json` separates the complete inventory from selected requirements.
Doctor distinguishes installed, connected and operation-verified evidence. A
catalog or `verified: true` flag is not account access. Optional Messages can stay
partial without blocking other work unless explicitly required. Selected Gmail
tracking checks Sent reads; alert-only chat reporting does not require them.

Resource intents precede effects. Unknown outcomes resume the same intent and
must be reconciled before retrying. Only selected schedules can be reserved;
they require actual bindings, current selected capability checks and a verified
pilot. The setup plan describes permissions to review and is not itself proof
that the user granted them.

## Rated-company list

Use the [starter list](<../../Blind Company Research/blind-companies.json>) or the [fictional format example](examples/rated-companies.json) to prepare your own. Bind a reviewed private copy in `sources.rated_companies_path`. `doctor` checks the file exists. Before running, review each entry using [Blind setup](<../../Blind Company Research/run.md#setup>) for rating provenance, dates and packet fields.

## Legacy compatibility only

Version-one files keep their serialized shape and installation digests. Their
existing `main` choice still means email discovery, portal discovery and Gmail
tracking, with a Google tracker. No migration or resource replacement occurs
silently. For a new setup, use version two.

[Version-one installation](legacy/installation.json) and [profile](legacy/profile.json) are retained for compatibility tests. New users start with version two.

## Referral companies

[referral-companies.json](examples/referral-companies.json) is the complete fictional source format. [Referral setup](../../docs/referrals.md) copies it privately, seeds the selected tracker’s watchlist and publishes the private portal registry after readback.
