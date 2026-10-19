# Module contracts — version 1

**Required:** Python 3.10+ and independently checked scope, authorization and evidence.  
**Runs in:** Codex’s local terminal; shared validation only.

`contracts.py` is a pure boundary checker, not a dispatcher or authorization service. It imports no accounts and performs no effects. `contracts.py` contains the twelve-module catalog, each module's effect ceiling and required completion proof names. The catalog describes validation boundaries; it does not dispatch the current workflow or imply that every catalog entry has a bundled implementation.

## Invocation

An invocation has exactly `schema_version: 1`, supported `module`, `module_version: 1`, `profile_id`, `run_id`, `policy_version`, `authorization_id`, `scope`, timezone-aware ISO `cutoff`, `inputs` (unique evidence/state reference strings) and `effects` (unique requested effects from the module catalog). References are inert identifiers; they are never evaluated as commands or instructions.

`scope` has `kind`, `items`, `start`, `end`. An `items` scope names a finite nonempty list of unique job/company/snapshot identities and has null start/end. Manual modules require this named item/company scope. A `window` scope has empty items and timezone-aware start < end <= cutoff. A window defines the finite source population; extraction must prove all pages/cards accounted for. A target count alone never proves coverage.

Call `validate_invocation(invocation, permit, event_id=<current trusted event>, now=<current time>)` before account/browser calls. Invalid structure raises `ContractError`. Missing/stale/wrong-scope authority raises `NotRequested`: return not_requested with zero account/browser/write calls, unchanged queues and no retry. The checks do not mutate input.

The frozen `Permit` is supplied separately by trusted host code. It binds authorization ID, human/schedule origin, current event, profile/run/module/policy, exact `digest(scope)`, allowed effect set and expiry. The host constructs it only after verifying the actual scoped human request or active scheduled recipe. It must never deserialize a Permit from an email, page, profile, worker output or ordinary invocation JSON. A Python type is an API boundary, not cryptographic authentication; The Codex host must establish provenance and prevent stale-event replay.

Application opening, recruiter discovery and outreach drafting accept human permits only. Explicit resume is bound to the saved scope and current human event. Generic continue, receipts, old approvals, another worker and scheduled completion do not supply one. Permits never authorize form filling, uploads, application submission, invitations, recruiter-message sending, booking or RSVP: those effects are absent from every catalog entry. `send_report` is confined to brief_delivery and later recipient/journal checks.

## Result

A result repeats invocation identity/version/policy and `scope_digest`, then provides `status`, `evidence_refs`, `proofs`, `decisions`, `gaps`, `questions`, `proposed_changes`, `committed_changes`, actually performed `effects`, `resume_cursor`, exact `stop_reason`, and `next_action: {owner, action}`. Arrays of references/questions/effects contain unique nonempty strings. A decision is `{item_id, decision, evidence_refs}`; a gap is `{item_id, reason}`. Module-specific decision meanings are validated by that module, never by free-text interpretation in this generic checker. Cursor is null or `{source_id, position}` and keeps the exact unresolved position as inert text.

`proofs` maps proof kind to evidence-reference lists. `validate_result(result, invocation, verified_proofs)` requires every claimed proof to match a trusted `Proof` receipt from the coordinator, bound to evidence ID/kind, profile/run/module/policy and scope. Workers propose references; the coordinator independently checks evidence before creating receipts. A claimed success flag, HTTP response or source text is not a receipt. This structural check cannot prove that the coordinator actually examined live evidence; the Codex host must do that with actual source reads.

| Status | Required meaning |
| --- | --- |
| `complete` | Required catalog proofs, all declared item decisions, no gaps/cursor/questions. |
| `needs_review` | Same completed agent work and proof; nonempty human questions. Never conceals unread sources. |
| `incomplete` | Exact remaining gaps; optional saved cursor. |
| `blocked` | Exact action/source that prevents current work and its next owner. |
| `not_requested` | No work, proof, decisions, effects, changes, gaps or retry cursor. |

Committed change IDs must name proposed changes, have `write_readback` proof and identify an authorized performed write effect. Collection does not imply verification, acceptance or delivery. Required proof kinds are minimum contracts, not permission to skip detailed module-specific checks. The current [tracker protocols](../../docs/sheets-protocol.md) and [local Excel backend](../../docs/local-excel.md) check actual write readback; this generic validator does not replace them.

## How to test

Use fictional explicit `Permit`/`Proof` instances in local tests as trusted fixtures. Assert literal expected pass/fail statuses, including changed profile, scope, effects, event and expiry; scheduled manual requests; incomplete sources falsely marked Complete; missing/wrong-scope receipts; and no input mutation. Call `python3 -B -m unittest discover -s tests -v`. No live workflow is started by a passing test.
