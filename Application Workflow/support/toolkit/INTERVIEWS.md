# Interview facts

**Required:** Python 3.10+, exact application/process identities and independently checked interview evidence. Mac Messages MCP is required only when Messages is selected.  
**Runs in:** Codex’s local terminal after selected source reads; this helper connects no accounts.

`interviews.py` reconciles accepted interview facts for exact application, process
and stage identities. It preserves original application source records and opaque legacy
interview history. It makes proposals only, with no booking, RSVP, sending, file,
Sheets or delivered-baseline changes. The ponytail simplification is deliberate:
small supplied snapshots and explicit host interpretations, no parser or datastore.

## Input and trust boundary

Call `reconcile_interviews(payload, events=None, legacy_records=None, *,
submission_acceptances=None, excluded_process_keys=None,
excluded_application_keys=None, profile=None, source_scopes=None,
source_checks=None, cutoff=None)`. The original packet and submission receipts use
APPLICATIONS.md. Legacy records are finite JSON dictionaries in a list, copied
unchanged: labels, dates, stage outlines, exclusions, unknown fields and historical
evidence are retained. Legacy labels alone never establish a normalized process.
The integration adapter must independently reconcile current/manual facts and
exclusions; omitting them is not permission to overwrite a real tracker.

Use trusted frozen receipts constructed by the host after reading complete source
content and verifying exact employer, role, process, stage and evidence meaning:

```text
InterviewAcceptance(profile_id,event_id,source_event_id,source_digest,
 application_key,process_id,stage_id,kind,effective_at,reviewed_at,
 evidence_ref,match_basis,full_source_read,evidence_kind,data)

evidence_kind: employer_email | calendar | user_confirmation |
               user_voice_transcript | advice
match_basis: exact_role | exact_requisition | exact_application_ref |
             independent_exact_role
data by kind:
 invitation: {label}
 booking: {booking_id,starts_at,ends_at,timezone}
 rsvp: {booking_id,response:accepted|tentative|declined|needs_action}
 attendance: {attended:bool}
 outcome: {status:ACTIVE|REJECTED|PAUSED|WITHDRAWN|OFFER|HIRED|CLOSED}
 cancellation: {booking_id}
 user_process/reopen: {}
 availability_sent/registration/reschedule: {request_id}
 outline: {stages:list of unique labels,total_stages:null|positive integer}
 advice: {note}
```

`stage_id` is required for stage-specific facts; it is nullable for outcome,
user_process, reopen, outline and advice. Process and stage IDs are canonical native
identities, never employer-only keys or inferred titles. Public `process_key(app,
process)` and `stage_key(process,stage)` hash their exact identity pairs. Different
roles, processes and stages stay separate even at the same employer.

Receipts bind the entire original source wrapper by digest and profile. User
confirmation/voice requires `manual_history` origin and actual reviewed user words;
advice cannot be relabeled as an invitation, attendance or employer outcome.
Calendar/email evidence uses original supplied correspondence or unresolved-source
wrappers, preserving full payloads and real URLs. Calendar cannot prove attendance
or an outcome. No URL tokens, role aliases, audio transcripts or missing facts are
invented. A worker flag, inbox unread state or UI demonstration is not evidence.

## Independent facts and chronology

An actual invitation, booking, confirmed positive attendance or explicit user confirmation
can establish a process. Employer application-only rejection, receipt, referral,
RSVP, generic lead, advice and future outline cannot. Such records remain in source
history or unresolved accepted events. An outcome alone, including user-reported
rejection, does not prove an interview; supply a separate explicit `user_process`
fact if the user actually confirms interviewing. Nonattendance or reopening alone
cannot establish a previously unproven interview process.

Invitation, availability sent, registration, booking, RSVP, attendance, cancellation
and process outcome remain separate. Acceptance requires a matching current booking
ID; old RSVP/cancellation for known prior bookings remains valid history, while an
unknown booking reference is a gap. Neither applies to a replacement booking. A past start
time does not imply attendance. Cancellation does not imply rejection, and an
explicit reschedule request does not invent a new booking. Outlines retain their
reported denominator, including null; they never create fictional invited rounds.
Older attendance cannot complete a replacement booking or precede its actual
scheduled start; conflicting evidence stays history with a precise gap.

Effective time is the actual fact time or null, never capture/review time. Actual
future booking start/end times are allowed; future fact/review times and naive
timestamps fail. Unknown times and simultaneous incompatible facts stay explicit
gaps/conflicts and hold affected proposals. Full history remains immutable.
Process status is explicitly `last_known_evidence`, separate from current source
freshness. Default ACTIVE retains the latest known actual establishment time; an
unknown establishment time remains null/unknown. Rendering never refreshes it.
Terminal/paused outcomes suppress reminders until an explicit user reopening;
current supplied exclusions always remain excluded. Neither new employer mail nor
historical user reopening clears a current exclusion. `action_required` remains null:
response obligations are unevaluated here; use [lifecycle’s exact request analysis](LIFECYCLE.md).
Excluded process facts remain history, with no interview proposal. Other proposals
retain the suppression/exclusion boundary alongside independently known facts.

## Coverage, output and replay

When provided, the full matching profile and exact configured source scopes/checks
are passed directly to `coverage.coverage_status`, using `cutoff` (default `as_of`)
and the actual packet evaluation time. Required mail, Calendar and private Messages
checks are host-configured, not fabricated by this module. Missing coverage is an
explicit gap; partial/failed checks retain real timestamps and unresolved content.
Independently verified positive facts can remain proposals during partial coverage,
but cannot claim a complete update or change a delivery baseline.

Output contains `reconciliation`, `legacy_records`, `processes`, `unresolved_events`,
`gaps`, `coverage` and `interview_proposals`. Each process retains its exact key,
application/process IDs, process status, known/unknown/conflicted confidence,
stages, outlines, full history, exclusions and conflicts. Each stage has its key,
ID/label, invited flag, nullable booking/RSVP/attendance, cancellation, independent
availability/registration IDs, reschedule flag, status, history and conflicts.
Stage labels distinguish pending_schedule, availability_sent (waiting on employer), booked, invite_accepted, completed,
not_attended, canceled, reschedule_requested, not_invited and unknown; they authorize
no action. `operational_complete` and `delivered_baseline_changed` are always false.

Identical replay is a no-op. Changed event-ID content and duplicate native
interpretations under different IDs fail. Malformed fields/data/times and invalid
profile/source digests fail; unresolved exact targets remain gaps, never fuzzy
matches. Outputs are deterministic and detached from caller inputs.

## Fictional runnable check

```sh
python3 -B - <<'PY'
from applications import application_key
from contracts import digest
from interviews import InterviewAcceptance, reconcile_interviews
now='2026-10-06T12:00:00Z'
row={'event_id':'row','origin':'sheet','source_item_id':'sheet:1','observed_at':None,
 'employer_id':'northwind','role_id':'job:1','requisition_id':'REQ-1',
 'application_ref':None,'evidence_refs':['fictional:row'],'payload':{'status':'Applied'}}
mail={**row,'event_id':'invite','origin':'correspondence','source_item_id':'mail:1',
 'payload':{'body':'Invitation to the exact technical interview.'}}
packet={'schema_version':1,'profile_id':'demo','as_of':now,'sources':[row,mail]}
event=InterviewAcceptance('demo','accepted:invite','invite',digest(mail),
 application_key('demo','northwind','job:1'),'process:1','technical','invitation',
 '2026-10-06T10:00:00Z',now,'fictional:full-invite','exact_role',True,
 'employer_email',{'label':'Technical interview'})
result=reconcile_interviews(packet,[event],legacy_records=[{'old_date':'2026-09-01'}])
stage=result['processes'][0]['stages'][0]
assert stage['invited'] and stage['attendance'] is None and stage['booking'] is None
assert not result['operational_complete'] and not result['delivered_baseline_changed']
assert result['legacy_records']==[{'old_date':'2026-09-01'}]
print('interview fact boundary check passed')
PY
```
