# Shared queue and producer handoffs

> **Required:** Python 3.10+, the installation’s private settings and shared queue.
> **Runs in:** Codex app; the same contract serves Excel and Google Sheets.
> **Computer use:** None for this handoff; source research may need it.

Follow [operating rules](operations.md). Local commands run from `Application Workflow/support/`.

**Every `--root` is the installation directory containing `installation.json`, not its `state/` child.** The code adds `state/` itself. The name `state` is reserved for this managed child, so choose a different name for your installation directory.

Email, portal and rated-company producers propose jobs. Central validates and saves through [local Excel](local-excel.md) or [Google Sheets](sheets-protocol.md), then [reports](report.md) from accepted receipts. Queued, saved and delivered are separate checkpoints.

## 1. Bind the reviewed policy during setup

Setup writes `state/approved-policies.json` only from the user's validated profile, binds its workbook ID after verified resource creation, and declares enabled sources and the profile's IANA timezone. Workers must not edit this file or choose their own thresholds. `queue.configure_policies(root, workbook_id, sources, timezone)` validates a supplied policy mapping when used directly. Disabled sources cannot enqueue packets.

Each source (`email`, `portal`, `blind`) has `id`, `version`, `max_required_years`, `allow_unstated_years`, `allowed_tiers`, and `forbidden_title_patterns`. Blind also has `min_rating` and `base_required_years`: core roles must be at or below that base, and stretch roles must state a minimum above the base and at or below the maximum. IDs are installation choices; the supplied setup uses `core` and `rated-companies`. Main and Blind remain separate policies. For example, a verified three-year Blind stretch may be accepted while the main source ceiling remains two years. A five-year role cannot bypass that ceiling by supplying `QUALIFY`.

The code checks that these bindings match, applies numeric ceilings/title exclusions/tier/rating rules, and requires quoted identity, full-requirements, location and availability evidence. Interpreting full duties, applicable degree branches, skills, geography and actual availability remains the assigned evidence reviewer's responsibility. Code does not claim to have read a posting merely because evidence fields are present. The quoted requirements must support `required_years`; null means a completely read qualification section states no numeric minimum, not missing evidence.

## 2. Enqueue a source-normalized packet

### Producer handoff

First verify where each producer can write and where the central chat can read. If the shared private staging and queue are writable, enqueue there. Otherwise save the packet and its evidence in that producer's verified writable workspace, with a manifest of exact file paths, run/source IDs and SHA-256 hashes; return those paths and mark `archive_pending`. Do not weaken permissions or claim the shared queue accepted it.

The central chat reads the authorized files, copies them into the private durable instance, verifies the copied hashes, validates the packet against the configured source policy, and calls `enqueue` itself. Return the archived paths/hashes and queue receipt through the configured handoff. Retain the producer's staging until that acknowledgement; archive failure alone does not require repeating successful research. If the central chat cannot read the files, retain them and report the access gap until a permitted transfer path exists.

Setup must exercise the selected handoff path for all enabled producers before scheduling. Archival and queue acceptance remain separate from the later verified Sheet save.

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
    "referral_hold": false,
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

`jobs` contains qualified proposals only. Keep unverified/held/excluded candidates in the producer's private evidence packet and report handoff; never promote them to Jobs to satisfy a count. A zero-qualified packet can still persist truthful coverage. Optional `companies` entries contain `company_key`, `company`, `rating`, `rating_as_of`, `rating_origin: user_supplied`, `careers_url`, and timezone-qualified `checked_at`.

Stable keys are employer/requisition identities or stable provider IDs. Explicit aliases require `{job_key,evidence_url,quote}` mapping evidence. Exact identical URLs can identify the same saved role; title similarity never merges jobs. Source event IDs must remain stable across replay. An unchanged packet ID must have unchanged bytes. New evidence gets a new packet ID while preserving original sighting IDs; replay does not increment counts.

Queued is not saved. The enqueue receipt contains a packet key, not a Sheets write receipt. Producers do not send a connector write or advance their saved checkpoint.

## Save and report

After enqueue, only the central owner runs the chosen tracker writer. A producer's queue receipt does not establish that a row was saved. Source packets and tracking saves both feed the [report checkpoint](report.md); receipts arriving after a brief is frozen wait for the next brief.
