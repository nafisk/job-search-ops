# Lifecycle and response evidence

**Required:** Python 3.10+, reconciled application identities and independently checked event/reply evidence.  
**Runs in:** Codex’s local terminal after selected source reads; this helper connects no accounts.

`lifecycle.py` layers independently accepted events over the original application source
packet through `applications.reconcile`. Confirmed submission remains a separate
fact when a role is rejected, paused, withdrawn, interviewed, offered or hired.
An old receipt cannot downgrade a newer outcome. This module performs no external
or file actions. Actual interview
process/booking evidence belongs to [interviews](INTERVIEWS.md); an INTERVIEWING label does not create one.

## Supply exact accepted events

Call `reconcile_lifecycle(payload, submission_acceptances=None, events=None,
sent_coverage=None, excluded_application_keys=None, *, sent_cutoff=None)`. `payload` and submission
receipts use the complete [application contract](APPLICATIONS.md). The host supplies all
relevant source history, including existing manual/current statuses and exclusions;
omitting an old status is not proof it never existed. Raw source payloads and
submission facts remain unchanged in output `reconciliation`.

`events` is a list of frozen trusted-host `EventAcceptance` objects:

```text
profile_id, event_id: immutable interpretation ID,
source_event_id: existing application source event,
source_digest: digest of its complete wrapper,
application_key: exact registered employer/role,
kind: outcome | manual_status | reopen | request | reply,
effective_at: actual event/request/Sent time OR null,
reviewed_at: actual independent review time,
evidence_ref, match_basis, full_source_read: true,
data: exact kind-specific object

outcome/manual_status/reopen: {stage}
request: {request_id, response_owner, deadline_at, suggested_followup_at}
reply: {request_id}
```

Response owners are `applicant`, `user` (both mean the profile owner), or `employer`
(waiting on employer, never a user reply-due claim).

Match bases are `exact_role`, `exact_requisition`, `exact_application_ref` and
`independent_exact_role`, with the application contract’s exact-role/full-source host proof boundary.
Never infer identity from similar titles, timestamps or URL tails. Accepted stages
are ACTIVE, INTERVIEWING, REJECTED, WITHDRAWN, PAUSED, OFFER, HIRED, REFERRED and
CLOSED; APPLIED is permitted only for a manual status and cannot confirm submission.
`manual_status` means confirmed current/manual state; ordinary old sheet labels
remain raw unless explicitly reviewed.
Reopen events require an active nonsuppressed stage and explicit exact user
instruction from `manual_history`; employer correspondence cannot authorize reopening.
Cancellation is not rejection; do not normalize it into REJECTED.

The host verifies full messages, direction and exact association.
Worker flags, mailbox labels and read markers are not proof.
Replies require correspondence origin and actual verified Sent evidence. Request
IDs identify the exact native obligation/process, including stage when needed:
availability, registration and booking may differ. Original action/thread URLs remain raw.

Unknown effective time remains null. Date-only legacy decisions remain raw;
manual confirmation dates are not rejection dates. Effective/review timestamps cannot be future or precede
required source chronology. Actual employer deadlines and suggested followups may
be future; both are independently supplied nullable timestamps. A five-business-day
suggestion never becomes an employer deadline, overdue finding or incoming request.

## Conservative projections and response checks

Known event chronology determines the current stage. Simultaneous incompatible
outcomes, differing current source/manual states and unknown times that prevent
ordering create explicit conflicts and hold lifecycle proposals. Raw manual labels
and history remain unchanged. An explicit later reopening resolves earlier known-time
lifecycle conflicts; unknown-time state and identity conflicts remain held. Ordinary
new outcomes cannot erase a current/manual conflict. The host must normalize known current/manual state
as accepted events and reread the actual destination status before any later write;
missing baseline evidence is a writer preflight blocker, not permission to overwrite.
Proposals never authorize reapplication.

REJECTED, PAUSED, WITHDRAWN, HIRED and CLOSED suppress outstanding response reminders
until an explicit, chronologically supported reopening. New requests, replies,
silence or an OFFER alone do not reopen a process or create scheduling actions.
User-excluded applications always remain suppressed here. The host removes a current
exclusion only after independently reviewing the user's explicit current scoped
instruction; historical manual reopenings and employer mail cannot remove it.

Each request preserves its explicit owner, original requested time and separate
deadline/followup values. An exact accepted reply resolves only the same application
and request, with known Sent time at or after the known request time, yielding
`waiting_on_employer`. Another role's Sent message or unknown chronology cannot
resolve it. An actual positive reply can resolve its request without claiming that
the overall Sent retrieval is complete.

Before claiming `reply_due`, the host must independently accept complete relevant
Sent coverage through the frozen evaluation horizon using:

```text
SentCoverage(profile_id, scope_digest, request_keys: frozenset,
             through, checked_at, evidence_ref, complete: bool)
request_key = digest([application_key, request_id])
scope_digest = digest({profile_id, request_keys: sorted(all declared request keys)})
```

Coverage binds the complete current request set/profile, not a successful subset.
`sent_cutoff` defaults to `payload.as_of`; an explicit earlier cutoff allows actual
readback after the frozen search horizon. `through` must equal that cutoff; checked
time must be at or after it and no later than `as_of`. A request after cutoff cannot
be due. Output `sent_cutoff` and request `due_as_of` keep the horizon explicit.
Missing, stale or incomplete Sent yields `status_unchecked`
and a gap, never due. Unknown request chronology or conflicts yield `held`; terminal
state/exclusion yields `suppressed`. Silence cannot become rejection. Deadline
state is unknown/upcoming/overdue solely from the actual employer deadline.

## Output and replay

Output retains application `reconciliation`, per-application `submission_confirmed`, full
`submission_facts`, `current_stage`, nullable `effective_at`, `status` (known/unknown/
conflicted), `manual_status_events`, complete accepted `history`, requests and
conflict reasons. Requests contain their exact key/ID/event/owner/times, status,
matching reply event IDs and deadline state. Global `gaps` identify application,
event and reason. `lifecycle_proposals` contain application/stage/effective time/
supporting event IDs only. `operational_complete` remains false.

Identical event replay is a no-op; changed content under one event ID or duplicate
native interpretation under another ID fails. Unknown fields, malformed JSON,
cross-profile/source-content bindings and invalid dates fail before modifying input.
Unregistered or mismatched exact application targets remain gaps without projections.
All outputs are detached and deterministic; original histories remain immutable.

## Fictional runnable check

```sh
python3 -B - <<'PY'
from contracts import digest
from applications import application_key
from lifecycle import EventAcceptance, reconcile_lifecycle
now = '2026-10-06T12:00:00Z'
row = {'event_id':'row','origin':'sheet','source_item_id':'sheet:1','observed_at':None,
       'employer_id':'northwind','role_id':'job:1','requisition_id':'REQ-1',
       'application_ref':None,'evidence_refs':['fictional:row'],'payload':{'status':'Applied'}}
mail = {**row,'event_id':'mail','origin':'correspondence','source_item_id':'mail:1',
        'payload':{'full_body':'Please provide availability for REQ-1.'}}
packet = {'schema_version':1,'profile_id':'demo','as_of':now,'sources':[row,mail]}
key = application_key('demo','northwind','job:1')
request = EventAcceptance('demo','request-event','mail',digest(mail),key,'request',
                         '2026-10-06T10:00:00Z',now,'fictional:full-request-proof',
                         'exact_role',True,{'request_id':'availability:1','response_owner':'user',
                         'deadline_at':None,'suggested_followup_at':'2026-10-13T12:00:00Z'})
result = reconcile_lifecycle(packet,events=[request])
app = result['applications'][0]
assert app['requests'][0]['status'] == 'status_unchecked'
assert app['requests'][0]['deadline_at'] is None and not app['submission_confirmed']
assert not result['operational_complete'] and packet['sources'][0]['payload']['status']=='Applied'
print('lifecycle response boundary check passed')
PY
```
