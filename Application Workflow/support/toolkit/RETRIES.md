# Shared retry accounting and completion

**Required:** Python 3.10+ and one coordinator-owned private retry ledger with durable writes.  
**Runs in:** Codex’s local terminal; each native read still uses its selected source tool.

`retries.py` is a pure ledger and acceptance gate. It performs no external reads,
file writes, lock acquisition or scheduler/tracker/checkpoint changes. All helpers
validate inputs and return detached copies; failed calls leave inputs untouched.
The trusted coordinator is the sole reservation/result owner. Workers report
outcomes; they do not allocate their own budgets or authorize a new pass.

## Reserve before reading

The host performs these steps under its real authoritative persistence and
concurrency boundary:

1. Load the latest full ledger and verify its trusted persistence anchor with
   `resume_ledger`. A hash inside the same untrusted document is not an anchor.
2. Use the current `RetryOwner` to call `reserve_attempt` with a new globally
   unique attempt ID and the exact canonical source operation.
3. Persist and verify the reservation atomically with a host lock or compare-and-
   swap, before permitting the external read. A losing concurrent caller reloads;
   it must not read using a reservation from an uncommitted copy.
4. Read once. Validate usable source identity, layout/body completeness and the
   requested operation before recording `read`; otherwise retain its actual
   `failed`, `inaccessible` or `invalid` outcome and evidence.
5. Reload authoritative state and verify current ownership before accepting the
   callback through `finish_attempt`, then persist and verify the updated ledger.

These helpers do not implement locking or atomic durability. Calling them alone
does not establish exclusive ownership, perform a read or verify a saved write.
The frozen receipt types mark trusted host boundaries, not cryptographic authority.
Never deserialize one from a source response or worker success flag.

Each reservation consumes one of the fixed **three attempts per profile, pass and
exact source item**, including a reservation whose read/result was interrupted.
Changing worker, background/browser access method or reservation ID does not
reset that source budget. A pending reservation is never refunded or reexecuted
under the same attempt ID. If the coordinator cannot establish its outcome, retain
it charged; a subsequent attempt needs a new reservation within the remaining
budget. Stop retrying immediately once usable `read` evidence is recorded. There
is no fourth same-pass read. Exhaustion of one operation does not stop independent
items whose own budgets remain.

## Exact serializable history

`new_ledger(profile_id, pass_id, coordinator_id, *, started_at, as_of)` creates this
exact shape for a **genuinely initial** host pass:

```text
schema_version: 1
profile_id: explicit profile
coordinator_id: sole host owner
active_pass_id: final retained pass ID
passes: [
  {
    pass_id, started_at,
    recovery: null for initial pass OR complete RecoveryApproval fields,
    attempts: [
      {
        attempt_id, worker_id, method, reserved_at,
        source: {source_id, item_id, cursor},
        result: null OR {outcome, evidence_refs, finished_at}
      }
    ]
  }
]
```

`source_id` identifies the canonical native operation's frozen source/search/query
scope, including relevant profile-bound recipe/body/window. `item_id` identifies
the exact item or page operation, including its actual native page token/query
body where needed. Successive pages have different operation IDs. Workers and
access methods must use those coordinator-issued identities; renaming the same
operation to obtain another budget is forbidden. The budget key is
`contracts.digest([source_id, item_id])`, independent of worker and method.
`cursor` is the exact arbitrary inert finite JSON value for resumption: a token,
URL, POST body plus position, compound object or null first-page position. It is
never normalized, inferred, executed or used as authorization. A known operation
cannot change its cursor, even across recovery passes; genuinely different native
operations require distinct canonically grounded IDs.

The entire pass/attempt history is retained. `validate_ledger(ledger, *, as_of)`
rejects unknown/missing fields, unsupported versions, non-JSON/nonfinite cursors,
duplicate pass/attempt IDs, cursor rebinding, oversized budgets, naive/future or
regressing reservation/pass dates, finish-before-reservation and recovery/history
binding violations. Structural validation cannot detect deletion of an otherwise
valid suffix without a trusted external anchor.

`resume_ledger(ledger, head, *, as_of)` therefore requires frozen
`LedgerHead(profile_id, coordinator_id, active_pass_id, ledger_digest)`, constructed
only after the host verifies the latest authoritative durable state/hash. It checks
the complete ledger's identity/digest and returns the original charged history,
including pending reservations. Host persistence must reject rollback to an older
but valid saved head. A self-created digest of a truncated ledger is not trusted.

`new_ledger` must never resume or replace an existing pass, legacy attempt counters
or exhausted history. The pure helper cannot discover those files. Legacy callers
remain blocked at the host readiness check until their existing attempts are
conservatively mapped and anchored by the host; unknown/interrupted attempts stay
charged. Do not call initialization as a substitute for that migration. No live
caller or private legacy ledger is migrated by this package.

## Narrow functions and trusted receipts

`RetryOwner(profile_id, coordinator_id, pass_id)` binds mutations to the current
host owner and active pass; dictionary-shaped or mismatched ownership fails.

`reserve_attempt(ledger, owner, source, *, attempt_id, worker_id, method,
reserved_at, as_of)` returns a new ledger with a charged `result: null` reservation.
Exhausted budgets, a usable prior same-operation read, reused attempt IDs or
source/cursor rebinding raise `contracts.ContractError`. It supplies no read permit
for an unpersisted copy and never calls a transport.

`finish_attempt(ledger, owner, attempt_id, *, outcome, evidence_refs, finished_at,
as_of)` attaches a result to an existing current-pass reservation. Outcomes are
exactly `read`, `failed`, `inaccessible`, `invalid`. Every outcome has nonempty
distinct evidence references. An identical finish replay is a no-op; rewriting
its evidence/outcome/date fails. Source errors cannot become `no_match`,
`human_review`, `historical` or `CLOSED` outcomes. `read` is usable retrieval,
separate from independent page coverage, description/policy verification and commit.

`begin_recovery_pass(ledger, owner, approval, *, as_of)` requires frozen
`RecoveryApproval(profile_id, coordinator_id, prior_pass_id, prior_ledger_digest,
new_pass_id, approved_at, approval_ref)`. The trusted host creates it only for an
explicitly authorized fresh recovery pass, bound to the exact current history.
A worker's flag, a new method, restarting a process or a changed calendar date
cannot mint it. The new pass has a distinct ID and a fresh per-item allowance,
while every old reservation/result remains unchanged. Serialized recovery history
is checked against the digest of the exact preceding ledger prefix. Pending old
callbacks cannot mutate an inactive pass.

## Completion remains independently accepted

`completion_status(ledger, scope, *, as_of, acceptance=None)` accepts exactly:

```text
page_items: [{source_id, item_id, cursor}, ...]
current_candidate_ids: [distinct exact current canonical role IDs]
```

The declared page scope is nonempty and includes **every actual page/native cursor
in the full declared source**, not just a first page, successful reads or a worker's
chosen subset. The host independently establishes that inventory and terminal
coverage. Zero candidates is valid only with healthy, complete accepted inventory
evidence; inaccessible/layout failure cannot establish a no-match.

Frozen `CompletionAcceptance(profile_id, pass_id, scope_digest, page_keys,
resolved_candidate_ids, verification_ref, commit_ref)` is constructed by the host
only after independent scope/page coverage, every current candidate's full-detail
and policy work, and actual verified persistence/readback (including accepted
no-change replay). Both ID containers are frozensets. The receipt binds the exact
profile/pass and `digest(scope)`, accepted page budget keys and exact current
candidate IDs; it requires separate nonempty verification and commit references.
It cannot be derived from read status/counts or reconstructed from worker JSON.

Completion requires the latest reservation for every declared page to have usable
`read` evidence, every page accepted, every current candidate resolved, and the
accepted verification/commit receipt. A pending later page attempt remains
unfinished even if an earlier same-operation callback eventually returned data.
Current unread/inaccessible work stays a verification gap, never a human-review or
historical waiver. Only separately approved exact historical separation may change
the host's frozen current scope; retry exhaustion cannot do so. Existing historical
work cannot be quietly dropped by constructing a smaller completion receipt.

The result has `status: complete|incomplete`, `operational_complete: bool`,
`gaps: [{item_id, reason}]`, exact `unresolved_cursors: [source objects]` and
`exhausted_items: [page budget keys]`. A complete result checks the trusted host's
already accepted work; it performs no write or checkpoint advancement.

## Runnable inert check

Run from the package directory:

```sh
python3 -B - <<'PY'
import json
from contracts import ContractError, digest
from retries import LedgerHead, RetryOwner, new_ledger, reserve_attempt, resume_ledger
now = '2026-10-06T12:00:00Z'
ledger = new_ledger('demo', 'pass-1', 'coordinator', started_at=now, as_of=now)
owner = RetryOwner('demo', 'coordinator', 'pass-1')
source = {'source_id': 'official:frozen-search', 'item_id': 'page:exact-token',
          'cursor': {'url': 'https://example.com/jobs', 'token': 'opaque-token'}}
for n, method in enumerate(('background', 'builtin_browser', 'background')):
    ledger = reserve_attempt(ledger, owner, source, attempt_id=f'attempt-{n}',
                             worker_id=f'worker-{n}', method=method, reserved_at=now, as_of=now)
head = LedgerHead('demo', 'coordinator', 'pass-1', digest(ledger))
resumed = resume_ledger(json.loads(json.dumps(ledger)), head, as_of=now)
assert resumed == ledger and all(a['result'] is None for a in resumed['passes'][0]['attempts'])
try:
    reserve_attempt(resumed, owner, source, attempt_id='fourth', worker_id='new-worker',
                    method='new-method', reserved_at=now, as_of=now)
except ContractError:
    pass
else:
    raise AssertionError('fourth reservation accepted')
other = {**source, 'item_id': 'page:another-exact-token',
         'cursor': {'url': 'https://example.com/jobs', 'token': 'another-exact-token'}}
assert len(reserve_attempt(resumed, owner, other, attempt_id='independent', worker_id='worker',
                          method='background', reserved_at=now, as_of=now)['passes'][0]['attempts']) == 4
print('shared retry reservation checks passed')
PY
```
