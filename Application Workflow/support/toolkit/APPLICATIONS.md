# Application evidence reconciliation

**Required:** Python 3.10+, private runtime profile and independently read exact-role application evidence.  
**Runs in:** Codex’s local terminal after selected source reads; this helper connects no accounts.

`applications.py` unions supplied application sources and returns submission-fact
proposals. It has no account, file, browser, Sheets, checkpoint or dispatch effects.
It performs no NLP, title similarity, URL parsing or time-based matching. Full
original source records and all origins remain available for later reconciliation.
[Lifecycle](LIFECYCLE.md) handles replies/outcomes and [interviews](INTERVIEWS.md) handles interview stages separately; this module changes
no lifecycle status, notes, referral hold, exclusion or outreach/application action.

## Supply the whole known universe

Call `reconcile(payload, acceptances=None)` with these exact wrapper fields:

```text
schema_version: 1
profile_id: explicit host profile
as_of: timezone-aware ISO evaluation time
sources: [
  {
    event_id: stable immutable source-event ID,
    origin: sheet | manual_history | batch_manifest | unresolved_association | correspondence,
    source_item_id: exact native event identity,
    observed_at: actual timezone-aware source-capture time OR null if unknown,
    employer_id: verified canonical employer ID OR null,
    role_id: verified exact canonical role ID OR null,
    requisition_id: verified exact employer-bound requisition identity OR null,
    application_ref: verified exact native application identity OR null,
    evidence_refs: [nonempty distinct references],
    payload: {complete original finite JSON record, unknown fields retained}
  }
]
```

Supply the union of sheet rows, manual application history, all registered batches,
unresolved associations and full newly relevant correspondence. A batch is not the
population, and eligibility exclusions do not remove previously known applications.
The host must independently retrieve every relevant Inbox/Archive/Spam/Sent page
and read full relevant message bodies/conversations with overlap and older pending
associations preserved. This helper cannot establish that retrieval coverage.
Email native event identity is a message ID, not thread ID, subject or role title.

Wrapper identities are source-backed host normalization, not facts parsed from
free text here. Keep employer/source namespaces distinct. Do not infer requisitions
from URL tails: public posting IDs, ATS requisitions and application IDs may differ.
Only independently verified canonical bindings belong in the wrapper; retain raw
URL/title/requisition values unchanged in `payload`. No fuzzy alias merge occurs.

`observed_at` describes a real capture/observation, not a fabricated precise legacy
timestamp. Original date-only, unknown, assumed and submission dates remain raw in
the original payload. Use null for genuinely unknown wrapper time. A current source
snapshot may have a real new capture time while retaining old original dates in
its payload; that never refreshes historical submission/receipt facts. A reused
event retains its original wrapper. Receipt arrival is not the submission click time.

`sheet`, `manual_history` and `batch_manifest` establish registered applications
only when employer and exact role/requisition are known. Employer+canonical role
defines `application_key(profile_id, employer_id, role_id)`, a SHA256 digest.
Requisition-only baseline records join an existing unique exact employer-bound
requisition; otherwise a new exact requisition-backed target uses role ID
`requisition:<requisition_id>`. A native application reference alone cannot invent
an unregistered role. `correspondence` and `unresolved_association` never create new
targets: an unknown named role remains unresolved until registered identity exists.

Exact role IDs take precedence. Requisition/application-reference-only matches must
be unique within the exact employer. Same-title roles with different requisitions
stay distinct. Competing canonical roles for one employer's requisition/application
reference, contradictory references or several requisitions for one canonical role
produce explicit conflicts and block affected submission proposals. Different
employers sharing a requisition string remain distinct.

## Confirm only independently reviewed facts

Pass a mapping `event_id -> SubmissionAcceptance` using the frozen dataclass:

```text
profile_id, event_id, source_digest: digest of complete source wrapper,
application_key: one registered target,
match_basis: exact_role | exact_requisition | exact_application_ref | independent_exact_role,
evidence_kind: email_receipt | confirmation_page | user_report,
submission_at: actual timezone-aware submission time OR null,
reviewed_at: actual timezone-aware independent review time,
evidence_ref: exact accepted association/confirmation proof,
full_source_read: true, established by the trusted host
```

The host constructs this receipt only after full-source review and exact employer/
role association. Dictionaries, source text and worker success flags cannot mint
acceptance. Exact bases must match the supplied corresponding identity. Email
receipts require `correspondence` origin. `independent_exact_role` supports a receipt
whose raw requisition is absent when the host independently verifies its exact
unique role/title against the native official role and registered row. Its evidence
reference must cite that actual role proof; a generic company receipt plus nearby
referral invitation, context or timing cannot establish it. Raw missing requisition
stays null. One source event has one receipt and one target; it cannot confirm
several applications. Unknown accepted targets remain unresolved.

Opened/closed tabs, prepared forms, old sheet Applied labels and legacy
`assumed_closed_tab` entries never confirm submission. Preserve them and their
labels without upgrading their evidence or implying permission to reapply.
Confirmation pages and explicit role-specific user reports require genuine source
proof; missing email does not waive required mail coverage. Unknown actual
submission time stays null, even when receipt capture/review time is known.

Unknown/missing wrapper fields, nonfinite/non-JSON payloads, naive/future dates,
duplicate native events under different IDs, conflicting event-ID content and
malformed/cross-profile/unbound acceptances raise `contracts.ContractError` without
modifying input. Identical source-event replay is a no-op. Unknown original payload
fields are retained, not interpreted as authorization or executable instructions.

## Proposal output

Output contains `profile_id`, sorted `applications`, `unresolved`, `conflicts`,
`proposals`, all deduplicated complete `source_events`, and
`operational_complete: false`. Each application contains its key/employer/role,
`requisition_ids`, `application_refs`, all `origins` and complete `source_events`,
accepted `submission_facts`, `confirmation_status: confirmed|unconfirmed`, and
conflict reasons. Unconfirmed means no accepted submission fact, never permission
to reapply or proof that submission did not occur.

Unresolved entries preserve `{source_event, reason}`. Conflicts identify
`{application_keys, event_ids, reason}`. Every submission fact retains event ID,
application key, evidence kind/reference, original observed time, nullable actual
submission time, review time and match basis. Proposals have exactly
`{kind: confirm_submission, application_key, fact}`. They never propose Applied or
overwrite newer/manual Rejected/Interviewing/Referred/status/notes/hold data.
The host separately journals, verifies and commits any allowed fact projection.
All outputs are detached and deterministic; keep original source ledgers immutable.

## Fictional runnable check

Run from the package directory:

```sh
python3 -B - <<'PY'
from copy import deepcopy
from contracts import digest
from applications import SubmissionAcceptance, application_key, reconcile
now = '2026-10-06T12:00:00Z'
def source(event, origin, role, req, data):
    return {'event_id': event, 'origin': origin, 'source_item_id': origin+':'+event,
            'observed_at': None, 'employer_id': 'northwind', 'role_id': role,
            'requisition_id': req, 'application_ref': None,
            'evidence_refs': ['fictional:'+event], 'payload': data}
sources = [
    source('row', 'sheet', 'job:1', 'REQ-1', {'status': 'Applied', 'manual_note': 'keep'}),
    source('history', 'manual_history', 'job:2', 'REQ-2', {'status': 'Rejected', 'date': '2026-09-01'}),
    source('batch', 'batch_manifest', 'job:1', 'REQ-1', {'tab': 'closed', 'submitted': 'unknown'}),
    source('pending', 'unresolved_association', None, None, {'company_receipt': 'generic'}),
    source('mail', 'correspondence', None, 'REQ-1', {'full_body': 'We received your application for REQ-1.'})]
payload = {'schema_version': 1, 'profile_id': 'demo', 'as_of': now, 'sources': sources}
before = deepcopy(payload)
unconfirmed = reconcile(payload)
assert len(unconfirmed['applications']) == 2 and not unconfirmed['proposals']
target = application_key('demo', 'northwind', 'job:1')
accepted = SubmissionAcceptance('demo', 'mail', digest(sources[-1]), target,
                               'exact_requisition', 'email_receipt', None, now,
                               'fictional:full-source-and-exact-role-review', True)
result = reconcile(payload, {'mail': accepted})
assert len(result['proposals']) == 1 and result['proposals'][0]['fact']['submission_at'] is None
assert result['proposals'][0]['application_key'] == target
assert any(x['source_event']['event_id'] == 'pending' for x in result['unresolved'])
assert payload == before and not result['operational_complete']
assert reconcile(payload, {'mail': accepted}) == result
print('exact application reconciliation checks passed')
PY
```
