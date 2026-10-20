# Report and delivery

> **Required:** Accepted tracker receipts for saved changes, Python 3.10+ and the configured Codex chat with readback. Self-email additionally requires explicit send permission, a recipient and native Gmail send/Sent-read tools.
> **Runs in:** Codex app; chat is the default delivery.
> **Computer use:** None.

Local helper commands run from `Application Workflow/support/`. **`--root` is the installation directory containing `installation.json`; never pass its `state/` child.** Follow the shared [operating rules](operations.md).

Read saved report and feature choices before building the report. Build one safe public snapshot from accepted receipts for the selected tracker backend and accepted facts from selected tracking sources. Use the same facts for chat, plain text and optional email/progress views. Use the current `job_search_ops` snapshot and brief journal described below. Preserve incomplete source labels; a prepared report never proves full source coverage or successful delivery.

1. Check the saved notification preference. A scheduled run with no new matches, material changes, actionable failures or required decisions can stay quiet without reserving a brief. An actionable source failure still needs a report even when there are no new jobs or receipts. When reporting is warranted, freeze the receipts for this brief:

```sh
python3 -m job_search_ops brief-prepare --root /absolute/private --brief BRIEF_ID
```

2. Include newly saved jobs from every source, including rated-company packets committed since the prior delivered baseline. Each listed job needs company, title, location, exact official link, published experience, important constraints, referral/fit holds and next action. Use each accepted job receipt’s `tier` and source policy to label `core`, `stretch` or `senior_exception`; do not infer a tier from a fixed number of years. For example, a three-year role may be core when the configured base allows three years. Keep relistings/material changes separate. Never call queued/unverified jobs saved or newly verified.
3. Include every frozen `tracking_summary` and `referral_summary` entry: company, title, exact URL and its change label. Both Excel and Google saves participate. Status transitions are explicit; Notes and Referral Contact changes use safe “updated” labels. Referral updates report newly learned holds or a contact-discovered notice, including for an existing job; they never expose the contact itself or count the role as new again. Show responses owed, interviews and deadlines only when their tracking sources are selected. Derive counts from displayed accepted records. Disclose source gaps and next actions; missing or stale sources are not “nothing found.”
4. When present, set public `tracking_updates` to the brief’s exact `tracking_summary`, and public `referral_updates` to its exact `referral_summary`. The delivery check requires these facts in both the snapshot and rendered body. Review the public projection: remove raw emails/transcripts, contact handles, private paths, source IDs, resume answers, auth/tracking tokens and internal notes. Keep private `referral_restrictions` out of the public snapshot. Escape external text in HTML; observed HTTPS links still require exact-job verification. The brief can describe a gap without exposing private context.
5. Save the public snapshot and exact final body in private files, then freeze delivery with `python3 -m job_search_ops brief-sending --root /absolute/private --brief BRIEF_ID --delivery /absolute/private/delivery-intent.json`. For chat delivery, the intent contains `channel: "chat"`, the configured `thread_id`, `snapshot_path`, and `chat_body_path`. Return that exact frozen body as the final response in the intended chat. On the next invocation (manual or scheduled), read that chat with `mcp__codex_app__read_thread` and save the raw actual response. Set `maxOutputCharsPerItem` high enough for the full frozen body and paginate to its actual completed turn; a truncated result cannot confirm delivery. Confirmation requires the same chat ID and an actual final assistant message whose text exactly matches the frozen body; preparation or a commentary message does not confirm delivery.
6. Only when self-email is selected, verify account/recipient and the user's explicit self-email authorization. Freeze an intent containing `recipient`, `subject`, `snapshot_path`, and `plain_body_path` and/or `html_body_path` before the native Gmail send tool. An uncertain send is not a failed send to retry. Search/read Sent using exact recipient, subject/report identity, time window and body evidence; paginate the relevant scope. Reconcile an existing exact sent message before any retry. A draft or successful tool call alone is not delivery confirmation. Never send recruiter/referrer messages as part of this report.
7. After actual delivery/readback, advance only the frozen receipt set:

```sh
python3 -m job_search_ops brief-delivered --root /absolute/private --brief BRIEF_ID --evidence /absolute/private/delivery-evidence.json
```

For chat, the evidence file contains `verified_at` and `native_chat_readback` pointing to the saved raw chat response. For email, it contains `verified_at` and `native_sent_readback` pointing to the actual native read-email response; the message must have the `SENT` label and exactly match the frozen recipient, subject and decoded body. See [native evidence](native-evidence.md) and the [shared handoff contract](handoffs.md) for output binding. Never turn a fixture, preview, manually asserted success or planned send into a delivery receipt. If delivery cannot be confirmed, preserve the prepared brief and frozen receipts for recovery. Discovery, tracking and referral updates committed after preparation stay for the next brief; delivered receipts are not reported again. Native readback must include a timestamp at or after the recorded attempt, a completed error-free chat turn or actual Sent message, and a message ID not already acknowledged by another brief. Older identical messages cannot confirm a new attempt.

## Stay quiet without blocking later reports

If a brief was already prepared and the completed review finds nothing that warrants notification, release the reservation before stopping:

```sh
python3 -m job_search_ops brief-cancel --root /absolute/private --brief BRIEF_ID
```

Cancellation is only for an unattempted `prepared` brief. It preserves all receipts for the next report and does not mark anything delivered. Use a fresh brief ID next time; a cancelled ID remains cancelled. Never cancel after `brief-sending`, a timeout or an uncertain send: reconcile the existing delivery instead. Do not suppress an empty brief with an actionable source failure or required user decision.

Manual runs return their requested report; they do not create a schedule to confirm delivery. For scheduled work, notify according to the user's saved preference. Routine unchanged rated runs stay quiet; actionable failures, new matches, material changes and required user decisions are visible. Manual actions remain “not requested” unless separately authorized.
