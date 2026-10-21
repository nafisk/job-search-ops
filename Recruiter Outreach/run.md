# Prepare recruiter drafts for review

> **Required:** Completed [onboarding](ONBOARDING.md), private tracker/state, approved copy, a scoped human drafting request and the supported signed-in LinkedIn browser. Google tools are required only for a Google tracker.
> **Runs in:** Codex app. One coordinator owns state; one operator controls the browser at a time.
> **Computer use:** Required. The user reviews drafts, attaches the resume and performs every final send.

Request **“Prepare up to two unsent drafts for [company / selected contacts] using my approved copy.”** A completed roster, timer, receipt or old approval does not start a batch. Record the current request and exact scope privately. An explicit continuation may resume its saved scope without asking for the same permission again.

## 1. Recover before allocating

Read `settings.json`, the current tracker and unfinished `state.json` batches using [tracker rules](tracker.md). Check selected account identity. Inspect existing draft tabs without reloading or changing user content. Reconcile earlier uncertain writes before new writes to those contacts.

Count outstanding draft-backed reservations plus genuinely active preparation slots against the configured ceiling, normally **20**. Aggregate by canonical contact identity and accepted aliases across every unfinished/resumed batch: one contact occupies at most one slot, even when several historical records refer to its draft. Identity locks for unprepared/held contacts prevent duplicate work but do not consume draft capacity. Missing tabs do not prove a send or free a draft-backed slot. If ownership is uncertain, hold that slot and continue only within proven remaining capacity.

Reserve only the explicitly requested contacts/count. Store the approved copy snapshot and current request in the batch before opening composers. A smaller pilot or shortfall does not change the overall ceiling. Preserve every existing user edit and attachment; never replace a different draft to reach the target count.

## 2. Recheck each selected contact

Read current tracker history and inspect the live profile before a first new draft. Apply [employer and remit checks](research.md#3-verify-employer-and-recruiting-remit). Check visible prior conversation/invitation state. Skip exclusions, opt-outs, prior outreach/replies, pending invitations, cooldowns and another owner's active draft. An explicit follow-up request needs its own reviewed contacts and copy; it does not erase earlier history.

Normally only Qualified contacts enter drafting. If `allow_needs_review_drafts` was explicitly enabled, retained uncertain contacts may receive review drafts, with their holds/evidence unchanged. Keep `needs_review` distinct from a qualified ready draft, and report both counts. This setting cannot override a clear exclusion or suppression.

Do not infer an open vacancy or application from a recruiter's title. Use only the approved message facts and allowed name/company substitutions. If a name is unclear, preserve the observed name or ask for the greeting rather than guessing.

## 3. Prepare one draft at a time

1. Prefer a visible InMail composer; use ordinary LinkedIn messaging when that is the available selected channel. Confirm the recipient/profile before typing and preserve existing conversation content. A direct message may have no subject field.
2. If those routes are unavailable, use a connection note only when selected and a safe draft-only entry is established in the current UI. Never click a speculative Connect/Invite control that could send immediately. Ask the user to open the note editor if needed, and continue other eligible contacts.
3. Read the visible character limit and check the personalized approved note against it. If it does not fit, hold for a copy revision. No silent truncation, invented attachment claim, credit purchase or invitation withdrawal.
4. Fill or paste into explicitly identified fields; do not press Enter in a message editor or a send shortcut. Refresh UI references after controls change. Never click Send, Send invitation, a paper-plane submit control or upload the resume.
5. Read back recipient, subject where applicable, full text, spacing and unsent state. Save the live tab/link and narrowly scoped evidence privately; exclude unrelated conversations from any screenshot. Local text or an image alone is not a live draft.

Before proceeding beyond the first two drafts, return to each **without reloading** and verify its own recipient/text is intact. Separate tabs may share messaging overlays. If a draft was replaced or a note dialog did not persist, stop scaling, preserve remaining work and report the limitation. A one-draft request stops after that one; it never authorizes a second just for checking persistence.

## 4. Save and hand control back

Re-read each draft's live UI and current tracker immediately before handoff. Preserve changes the user made during the run. Use [narrow verified saves](tracker.md#save-and-recover) to record the actual channel, draft state and batch reference; do not set Sent or a send date because a draft exists.

Report **“X qualified drafts and Y review drafts ready; nothing sent”** only when supported by the current UI. List contact, channel, live profile/tab link and attachment/review action. Separate blocked attempts and reserved-but-unverified drafts. Keep completed draft tabs open and release browser control so the user can review, attach and send.

Stop after the requested handoff. Do not start another batch, discovery run, reminder or recurring outreach.

## 5. Record sends and resume safely

Update sent history only for the contacts the user actually confirms, or from direct sent evidence gathered within authorized access. Record the evidence/request reference and known send time. If only a confirmation date is known, retain that precision and timezone; do not invent an exact time. Preserve any earlier initial Sent date. Google API writes need explicit dates; no date-stamping script is assumed.

By default, **“next batch” does not confirm previous sends**. If `next_batch_confirms_previous_sent` was explicitly enabled, apply that convention only to the immediately preceding handed-off ready batch, including any review drafts actually handed over as ready. Record the user turn as confirmation; exclude blocked contacts and unrelated older reservations. Then allocate the newly requested scope within remaining capacity.

A lost tab, attachment, reply notification or closed composer alone does not prove sending. On an uncertain browser mutation, inspect the actual state before any retry; never blindly repeat draft creation. If the UI unexpectedly sends, stop, disclose the exact observed outcome and preserve evidence. Do not conceal it or withdraw an invitation without authorization.

## Agent coordination

Subagents may inspect disjoint assigned records or prepare text. Only the coordinator assigns replacements and writes tracker/batch state. Grant browser ownership to one operator at a time, including the coordinator; other workers cannot use another tab as a workaround. Share browser name and preserved tab references, then resolve runtime-specific identities through current tool documentation.

Each worker returns canonical contact ID/profile, evidence and check times, chosen channel, preparation state, verified text match, live tab/link, blocker and whether browser ownership is released. Preserve every unresolved draft-backed reservation until actual state is reconciled. A worker report does not replace the coordinator's final live verification.
