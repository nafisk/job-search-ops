# Report and delivery

> **Required:** Accepted tracker receipts, Python 3.10+ and the configured Codex chat with readback. Self-email additionally requires explicit send permission, a recipient and native Gmail send/Sent-read tools.
> **Runs in:** Codex app; chat is the default delivery.
> **Computer use:** None.

Local helper commands run from `Application Workflow/support/`. **`--root` is the installation directory containing `installation.json`; never pass its `state/` child.** Follow the shared [operating rules](operations.md).

Read saved report and feature choices before building the report. Build one safe public snapshot from accepted receipts for the selected tracker backend and accepted facts from selected tracking sources. Use the same facts for chat, plain text and optional email/progress views. Use the current `job_search_ops` snapshot and brief journal described below. Preserve incomplete source labels; a prepared report never proves full source coverage or successful delivery.

1. Freeze the receipts for this brief:

```sh
python3 -m job_search_ops brief-prepare --root /absolute/private --brief BRIEF_ID
```

2. Include newly saved jobs from every source, including rated-company packets committed since the prior delivered baseline. Each listed job needs company, title, location, exact official link, published experience, important constraints, referral/fit holds and next action. Label rated three-year minimums as stretch. Keep relistings/material changes separate. Never call queued/unverified jobs saved or newly verified.
3. Include every frozen `tracking_summary` entry: company, title, exact URL and its change labels. Both Excel and Google tracking saves participate in this checkpoint. Status transitions are explicit; Notes and Referral Contact changes use a safe “updated” label, without private contents. Show responses owed, interviews and actual deadlines only when their tracking sources are selected. Omit unselected sections; do not report them as failed or incomplete checks. Derive counts from displayed accepted records. Disclose source gaps and next actions; distinguish `complete_with_exceptions` processing from partial/unavailable source coverage. Missing or stale sources are not “nothing found.”
4. Set the public snapshot’s `tracking_updates` to the brief’s exact `tracking_summary` when tracking changes are present. Review the public projection. Remove raw emails/transcripts, contact handles, private paths, source IDs, resume answers, auth/tracking tokens and internal notes. Escape external text in HTML; observed HTTPS links still require exact-job verification. The brief can describe a gap without exposing private context.
5. Save the public snapshot and exact final body in private files, then freeze delivery with `python3 -m job_search_ops brief-sending --root /absolute/private --brief BRIEF_ID --delivery /absolute/private/delivery-intent.json`. For chat delivery, the intent contains `channel: "chat"`, the configured `thread_id`, `snapshot_path`, and `chat_body_path`. Return that exact frozen body as the final response in the intended chat. On the next invocation (manual or scheduled), read that chat with `mcp__codex_app__read_thread` and save the raw actual response. Set `maxOutputCharsPerItem` high enough for the full frozen body and paginate to its actual completed turn; a truncated result cannot confirm delivery. Confirmation requires the same chat ID and an actual final assistant message whose text exactly matches the frozen body; preparation or a commentary message does not confirm delivery.
6. Only when self-email is selected, verify account/recipient and the user's explicit self-email authorization. Freeze an intent containing `recipient`, `subject`, `snapshot_path`, and `plain_body_path` and/or `html_body_path` before the native Gmail send tool. An uncertain send is not a failed send to retry. Search/read Sent using exact recipient, subject/report identity, time window and body evidence; paginate the relevant scope. Reconcile an existing exact sent message before any retry. A draft or successful tool call alone is not delivery confirmation. Never send recruiter/referrer messages as part of this report.
7. After actual delivery/readback, advance only the frozen receipt set:

```sh
python3 -m job_search_ops brief-delivered --root /absolute/private --brief BRIEF_ID --evidence /absolute/private/delivery-evidence.json
```

For chat, the evidence file contains `verified_at` and `native_chat_readback` pointing to the saved raw chat response. For email, it contains `verified_at` and `native_sent_readback` pointing to the actual native read-email response; the message must have the `SENT` label and exactly match the frozen recipient, subject and decoded body. See [native evidence](native-evidence.md) and the [shared handoff contract](handoffs.md) for output binding. Never turn a fixture, preview, manually asserted success or planned send into a delivery receipt. If delivery cannot be confirmed, preserve the prepared brief and frozen receipts for recovery. Discovery and tracking receipts committed after preparation stay for the next brief. Native readback must include a timestamp at or after the recorded attempt, a completed error-free chat turn or actual Sent message, and a message ID not already acknowledged by another brief. Older identical messages cannot confirm a new attempt.

Manual runs return their requested report; they do not create a schedule to confirm delivery. For scheduled work, notify according to the user's saved preference. Routine unchanged rated runs stay quiet; actionable failures, new matches, material changes and required user decisions are visible. Manual actions remain “not requested” unless separately authorized.
