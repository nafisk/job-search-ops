# Shared queue and producer handoffs

Run commands from `Application Discovery/support/`. Use the installation directory containing `installation.json` as `--root`. See [state and ownership rules](operations.md#ownership-and-source-boundaries).

Email, portal and rated-company producers propose jobs. Central validates and saves through [local Excel](local-excel.md) or [Google Sheets](sheets-protocol.md), then [reports](report.md) from accepted receipts. Queued, saved and delivered are separate checkpoints.

## 1. Bind the reviewed policy during setup

Setup writes `state/approved-policies.json` only from the user's validated profile, binds its workbook ID after verified resource creation, and declares enabled sources and the profile's IANA timezone. Workers must not edit this file or choose their own thresholds. `queue.configure_policies(root, workbook_id, sources, timezone)` validates a supplied policy mapping when used directly. Disabled sources cannot enqueue packets.

Each source (`email`, `portal`, `blind`) has `id`, `version`, `max_required_years`, `allow_unstated_years`, `allowed_tiers`, and `forbidden_title_patterns`. Blind also has `min_rating` and `base_required_years`: core roles must be at or below that base, and stretch roles must state a minimum above the base and at or below the maximum. IDs are installation choices; the supplied setup uses `core` and `rated-companies`. Coordinated Blind uses the shared role filters and its own rating threshold. A standalone Blind policy can admit a three-year stretch while the main source ceiling is two years. A `QUALIFY` decision still has to pass the bound policy.

The code checks that these bindings match, applies numeric ceilings/title exclusions/tier/rating rules, and requires quoted identity, full-requirements, location and availability evidence. Interpreting full duties, applicable degree branches, skills, geography and actual availability remains the assigned evidence reviewer's responsibility. Code does not claim to have read a posting merely because evidence fields are present. The quoted requirements must support `required_years`; null means a completely read qualification section states no numeric minimum, not missing evidence.

### Tracker admission

An installation can opt into a stricter save rule independently of its research scope. For example, set this top-level field in a version-two configuration:

```json
{
  "tracker_admission": {
    "required_years_below": 3,
    "excluded_levels": ["senior", "sr", "staff", "lead", "principal", "manager", "director"]
  }
}
```

The exclusive ceiling admits a stated 2.5-year minimum and blocks 3 years or an unstated minimum. Review every applicable mandatory overall and specialty clause and the applicant's viable degree branch. Put the highest applicable minimum from the accepted branch in `qualification.required_years`. Use the lower bound of an approved explicit range. Hold unread, unclear or conflicting requirements for review. Compare the configured level exclusions with the reviewed `job.level`. Classify ambiguous and numbered titles from duties and requirements.

Before handoff, leave out any finding that fails this rule. A Blind role can still qualify for its chat report as a three-year stretch. Label it report-only, keep its evidence and seen history, and omit it from save packets and save retries. The queue checks admission again against the bound policy. Existing tracker records, manual fields and historical decisions are preserved.

Confirm the source policies as well. A source ceiling can be more restrictive than admission. An installation that wants to permit a stated 30-month minimum needs its source ceiling to allow 2.5 years. Change the relevant role and Blind policy versions through [preferences](preferences.md) when adopting a new admission rule.

## 2. Enqueue a source-normalized packet

### Producer handoff

First verify where each producer can write and where the central chat can read. If the shared private staging and queue are writable, enqueue there. Otherwise save the packet and its evidence in that producer's verified writable workspace, with a manifest of exact file paths, run/source IDs and SHA-256 hashes; return those paths and mark `archive_pending`. Do not weaken permissions or claim the shared queue accepted it.

The central chat reads the authorized files, copies them into the private durable instance, verifies the copied hashes, validates the packet against the configured source policy, and calls `enqueue` itself. Return the archived paths/hashes and queue receipt through the configured handoff. Retain the producer's staging until that acknowledgement; archive failure alone does not require repeating successful research. If the central chat cannot read the files, retain them and report the access gap until a permitted transfer path exists.

If an assigned helper is busy with unrelated work or cannot start, use an alternate worker only when the saved setup authorizes fallback and the original assignment cannot also execute. Give the fallback the same scope and remaining attempts. A pending approval or archive is a reason to check the existing status and continue independent work.

Setup must exercise the selected handoff path for all enabled producers before scheduling. Archival and queue acceptance remain separate from the later verified Sheet save.

When the approved queue is writable, enqueue the completed packet:

```sh
python3 -m job_search_ops enqueue --root /absolute/private --packet /absolute/private/source-packet.json
```

Return the receipt and coverage gaps to the coordinator.

Call `queue.enqueue(root, packet_or_path)`. Required packet shape:

```json
{
  "schema_version": 1,
  "packet_id": "example-2026-10-18",
  "workbook_id": "the-verified-installed-workbook-id",
  "source": "blind",
  "observed_at": "2026-10-18T08:00:00Z",
  "policy": {"id": "rated-companies", "version": "approved-version", "source": "blind"},
  "jobs": [{
    "job_key": "example:requisition-123",
    "source_job_id": "requisition-123",
    "company": "Example Company",
    "title": "Software Engineer",
    "url": "https://careers.example.com/jobs/123",
    "provider": "Official ATS",
    "location": "New York City",
    "level": "Mid-level",
    "experience": "3+ years",
    "target_fit": "Stretch",
    "fit_reason": "Verified target duties and location; three-year source-policy stretch",
    "rating": 4.0,
    "rating_as_of": "2026-10-01",
    "rating_origin": "user_supplied",
    "qualification": {
      "decision": "QUALIFY",
      "tier": "stretch",
      "required_years": 3,
      "checked_at": "2026-10-18T08:00:00Z",
      "evidence": {
        "identity": {"url": "https://careers.example.com/jobs/123", "quote": "Example Company — Software Engineer — requisition 123"},
        "requirements": {"url": "https://careers.example.com/jobs/123", "quote": "Bachelor's degree and at least three years of professional software engineering experience"},
        "location": {"url": "https://careers.example.com/jobs/123", "quote": "New York City"},
        "availability": {"url": "https://careers.example.com/jobs/123", "quote": "Apply now"}
      }
    },
    "sightings": [{"id": "example-123-2026-10-18", "observed_at": "2026-10-18T08:00:00Z"}]
  }],
  "coverage": [{
    "company_key": "example",
    "company": "Example Company",
    "scope": "NYC and eligible US remote",
    "status": "partial",
    "checked_at": "2026-10-18T08:00:00Z",
    "observed_jobs": 12,
    "qualified_jobs": 1,
    "notes": "Second page was unavailable; remaining extent unknown"
  }]
}
```

Examples are fictional; do not use them as live evidence. Email/portal packets omit rating fields. `provider` is one of `Official ATS`, `LinkedIn`, `Simplify`; Blind is a discovery source, not a new provider value. `tier` is `core`, `stretch` or `senior_exception`, subject to the installed source policy.

`jobs` contains qualified proposals only. Keep unverified or qualification-held/excluded candidates in the producer's private evidence packet; never promote them to Jobs to satisfy a count. A zero-qualified packet can still persist truthful coverage. Optional `companies` entries contain `company_key`, `company`, `rating`, `rating_as_of`, `rating_origin: user_supplied`, `careers_url`, and timezone-qualified `checked_at`.

Stable keys are employer/requisition identities or stable provider IDs. Explicit aliases require `{job_key,evidence_url,quote}` proving the shared identity; include optional `url` only when that alternate role URL is also verified. Exact identical URLs can identify the same saved role; title similarity never merges jobs. The writer restores accepted aliases before each merge and checks both the proposal URL and every verified alias URL, so new IDs can reuse the original row on a later run. It resolves all validated pending aliases before allocating new rows, so connecting evidence may arrive anywhere in the batch. Evidence joining two already-saved rows still requires explicit reconciliation. Conflicting or unevidenced mappings stop the import. Preserve accepted receipts and completed source packets; they carry this history.

Source event IDs must remain stable across replay. An unchanged packet ID must have unchanged bytes. New evidence gets a new packet ID while preserving original sighting IDs; replay does not increment counts or create another new-job report.

A portal proposal can include an optional `referral_contact` for an existing or new role. Verified saves keep contact evidence private and separate from the user's Notes and Referral Contact cells. New contact evidence produces a notice in the [report](report.md). Use [accepted job aliases](referrals.md#check-before-an-application-handoff) for application handoffs.

## Save and report

An enqueue receipt identifies a packet. The coordinator owns verified tracker saves and saved checkpoints. Discovery and tracking save receipts feed the [brief](report.md). Late receipts wait for the next brief.
