# Configured source coverage

**Required:** Python 3.10+, saved source choices and actual bounded-read evidence for each selected source.  
**Runs in:** Codex’s local terminal; selected Gmail/Calendar tools or Mac Messages MCP supply evidence.

**Distribution policy:** factual source coverage and daily processing status are separate. [Operations](../../docs/operations.md) permits completed processing with disclosed source exceptions; `required_complete` and `all_enabled_complete` remain honest coverage flags, not blanket continuation gates. This pure helper never dispatches live work.

`coverage.py` projects independently checked mail, Calendar and Messages coverage.
It reads no account or file, accepts no ingestion checkpoint and changes no delivery
baseline. Call `coverage_status(profile, scopes, checks, *, cutoff, as_of)` with a
validated profile. `cutoff` is the frozen source horizon; `as_of` is the later actual
evaluation time. A source readback can correctly occur after the cutoff.

`scopes` maps **every enabled** mail/calendar/messages service to a SHA256 digest of
its entire approved frozen scope. Do not build this from the subset a worker read.
The host derives scope from the profile and authoritative private requirements:
verified connection/account, exact conversations or calendars, date bounds and
overlap, pagination, named context checkpoints and older unresolved content. An
existing required direct conversation and saved-transcript backlog cannot disappear
because it lies outside a new incremental window. Scope construction and native
identity verification remain host responsibilities; follow the [native evidence checks](../../docs/native-evidence.md)
before private reads. A digest or connection name alone does not prove identity.

`checks` is a mapping from a configured service to frozen `SourceCheck` objects:

```text
SourceCheck(profile_id, service, connection_ref, scope_digest,
            checked_at, covered_through, last_successful_at,
            status, gaps, evidence_refs)
SourceGap(gap_id, reason, first_observed_at, last_attempt_at)
```

`checked_at` is the actual check time. `covered_through` and `last_successful_at`
are nullable original timestamps, never refreshed merely by rendering/reuse.
`status` is checked, partial or blocked. `gaps` is a tuple of SourceGap objects;
`evidence_refs` is a nonempty tuple of distinct reference strings. Gap dates may be
null when unknown; known first-observed/last-attempt times retain their exact value.
All known times include a timezone and cannot follow the actual check/evaluation;
last attempt cannot precede first observation. Only host code after independent
source review constructs these objects; source text and worker success flags cannot.

A checked source needs a covered-through time and no gaps. Partial and blocked
sources require actual gaps. A successful but older window is displayed as stale;
it does not meet a newer cutoff. A capped result, inaccessible full message, missing
saved voice transcript or ambiguous required source content remains a gap even
when the tool returned successfully. Preserve the original limitation and dates.
Do not label a bounded search success as complete content reconciliation.

Missing checks are allowed and produce not_checked with no fabricated timestamps.
Disabled optional sources produce not_configured, never checked. Required configured
sources cannot be disabled or omitted from the scope map. Optional enabled sources
may be unavailable, but their gaps remain visible. Checks for unknown/disabled
services, cross-profile/connection/scope mismatches and malformed data fail before
any effects. Inputs are unchanged and outputs detached.

Output contains profile_id, cutoff, as_of, per-service `sources`, flattened `gaps`,
`required_complete`, `all_enabled_complete` and `operational_complete: false`.
Each source retains status, required, scope_digest, actual timestamps, gap records
and evidence references. Required_complete means the configured required checks
were supplied with accepted full-window coverage. It does not prove source truth,
interview-event acceptance, a committed update or report delivery. Missing optional
coverage still makes all_enabled_complete false. Raw references stay private;
the presentation module must use its explicit public projection.

For example, load a fictional profile, bind `scopes['mail']` to a digest of a
manually defined full-mail scope, and supply `SourceCheck` with checked_at after
cutoff and covered_through equal to cutoff. Coverage is checked. Reuse it with a
later cutoff: the actual dates are preserved and status becomes stale. Supply a
partial Messages check with the original missing-transcript SourceGap: it remains
partial, with original first-observed and last-attempt times intact. None of these
operations changes an ingestion or delivered baseline.
