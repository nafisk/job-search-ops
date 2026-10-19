# Profile contract — versions 1 and 2

**Required:** Python 3.10+ with IANA timezone data; the selected installation’s private profile.  
**Runs in:** Codex’s local terminal; configuration validation only.

The profile is JSON configuration. Unknown fields, unsupported schema versions, duplicate JSON keys and invalid types fail instead of silently selecting defaults. Missing fields never inherit another profile's values. Errors name the field without printing its contents. Profiles contain connection **names**, never passwords, tokens, cookies, keys or authentication URLs.

Version 1 retains the contract below. Version 2 uses `schema_version: 2` and permits null unused `account_identity`/`report_recipient`, empty discovery families/levels and region lists, and null `residency_region`. These allow tracking-only or local-only installations without unrelated questions. The installation validator still requires actual job criteria when discovery is selected, an account identity for selected Google access, and a recipient for self-email. See the [v2 profile example](../config/examples/profile-v2.json); its fictional choices are not defaults. All other validation and permission boundaries remain unchanged.

## Settings

| Field | Meaning |
| --- | --- |
| `schema_version`, `profile_id` | Integer `1`; stable lowercase identifier containing letters, digits, hyphens or underscores. |
| `identity` | `display_name`, `account_identity`, `report_recipient`. Mail addresses are nonempty address-shaped configuration values; actual ownership requires later live verification. |
| `timezone` | IANA timezone, checked using Python `zoneinfo`. |
| `role_policy` | `version`; nonempty `families` and `preferred_levels`; `excluded_duties`, `excluded_levels`, `excluded_employers`; `experience` settings below. Lists are explicit, with no personal defaults. |
| `locations` | `onsite_regions`, `remote_countries`, `residency_region`, `allow_relocation`. At least one onsite region or remote country is needed. A country name is scope, not proof of remote eligibility. |
| `trackers` | Named destinations, each containing `workbook_id`, `worksheet`, one-based `header_row` and a `columns` map from logical field name to `{index, header}`. No two fields may occupy the same index or header. Saved mapping is an expectation; live metadata must still be checked. Empty map of destinations is allowed for modules that do not use Sheets. |
| `capacity` | Positive integer `application_pages`, `initial_application_total`, `next_application_additional`, `outreach_drafts`, `recruiter_target`, `recruiter_stretch_target`; nonnegative `workers`. Application counts include carryovers and reservations. Target counts are goals, not guaranteed results or proof of coverage. |
| `integrations` | Named entries with boolean `enabled`, boolean `required`, `connection_ref`, `expected_identity`. Required sources must be enabled. Enabled sources need a named connection and expected identity. Disabled sources use null connection/identity and mean Not configured, never Checked. Optional enabled sources still require identity verification when used. |
| `source_access` | `google: connector_only`; `public_portals: [background, builtin_browser]`; external `authenticated_browser` and `email_job_browser`: `chrome` or `edge`; `read_attempts`: positive integer. This does not configure a connector or start a browser. |
| `private` | `state_root` and `refs`, a map of private source names to local paths. References identify existing authoritative ledgers, policy detail, applicant facts, referral scope, approved copy or source-check instructions. They confer no approval. |

Experience fields: numeric `max_required_years`, `preferred_required_years` (nonnegative; preferred cannot exceed maximum); boolean `senior_low_experience_exception`; `unknown_minimum` is `review` or explicit opt-in `include`; `ambiguous_range` is `review` or explicit opt-in `accept_lower_bound`. The opt-ins apply only after independent review of the full qualification inventory; unread content cannot qualify. Policy evaluation belongs to the screening module: applicable qualification branch, all mandatory specialty requirements, preferred versus required, role duties and exclusions must be evaluated together. A configured ceiling alone is not an eligibility decision. Titles and numbered levels alone cannot invent experience requirements.

## Paths and privacy

Relative private paths resolve against the **profile file's parent**, never the current working directory or `state_root`. Absolute paths remain absolute. `~`, environment substitutions and URLs are not path syntax. Use explicit local paths. Symlinks resolve before separation checks. No referenced private file or state root may resolve inside this package; state root must not contain the package either. References may point to existing authoritative locations outside `state_root`; this preserves independent ledgers during migration. Loading does not test their existence or read their contents.

For an integration whose expected identity is stored in an existing private source-check record, `expected_identity` may be `private:<ref-name>` referring to an entry in `private.refs`. This is an unresolved reference, not verified account identity. A later preflight must read that binding, obtain an unambiguous expected identity and compare live evidence; missing/ambiguous identity must block access. This retains required local-message identity checks without copying contacts into configuration or assuming a device account.

The example references intentionally resolve to fictional sibling private directories. A real profile must be stored outside this toolkit. Do not put real names, addresses, resumes, approval records, account IDs, message templates or source histories into examples, tests, package instructions or exports.

## API and verification limits

`load_profile(path)` returns a dictionary after validation. `resolved_private_paths(profile, profile_path)` returns normalized paths with no state creation. `validate_profile(profile, profile_path)` checks the same contract for already parsed JSON. These functions raise `ProfileError` on invalid input; the CLI returns exit code 2 and a bounded error.

The command's `configuration_valid` result proves shape and separation only. It does not attest account login, document existence, destination ownership, current sheet layout, source availability, cross-profile ownership, effect authorization or workflow reliability. These checks must occur at their own later boundaries. No authorization history belongs in a shareable profile fixture.
