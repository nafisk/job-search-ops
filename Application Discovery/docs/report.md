# Report and delivery

Use the saved channel and notification choice. Chat is the default. Self-email requires the configured recipient, explicit send authorization and native Gmail send and Sent reads.

Run commands from `Application Discovery/support/`. Pass the private directory containing `installation.json` as `--root`.

1. **Freeze the receipts.** Report new matches, material changes, actionable failures or required decisions. Use the saved preference for unchanged scheduled runs.

   ```sh
   python3 -m job_search_ops brief-prepare --root /absolute/private --brief BRIEF_ID
   ```

2. **Build the public snapshot and brief.** Group new saved jobs under **Gmail alerts**, **Blind company research** or **Referral portals** for each source run. List each role once and name any additional verified sources on the same line. For a source with zero saves, state the count and any coverage gap. Include company, title, exact posting link, location, published experience and relevant constraints. Add `[Referral available]` when tracker readback confirms **Available**. In private chat, use `[Referral available · Name]` only for a verified contact the user has approved for that role or employer. Keep relistings and material changes distinct from new roles.
3. **Include frozen updates.** Copy exact `tracking_summary` and `referral_summary` entries into `tracking_updates` and `referral_updates` respectively when present. Render their company, title, exact URL and safe change label. Use status transitions and safe “updated” labels for Notes or Referral Contact. Keep contact names out of the public snapshot and email. Keep handles, raw messages, transcripts, private paths and IDs, résumé answers, tokens, internal notes and `referral_restrictions` private. Include interview actions only for selected tracking sources. Derive counts from the displayed records and escape external text in HTML.
4. **Save the exact snapshot and body privately, then freeze delivery.**

   ```sh
   python3 -m job_search_ops brief-sending --root /absolute/private --brief BRIEF_ID --delivery /absolute/private/delivery-intent.json
   ```

   For **chat**, the intent uses `channel: "chat"`, the configured `thread_id`, `snapshot_path` and `chat_body_path`. Return the frozen body as the final response in that chat. On the next invocation, read and save the native history through the completed turn. Match the actual final message and full body to the intent.

   For **self-email**, use `recipient`, `subject` and `plain_body_path` and/or `html_body_path` in the intent, then send through authorized native Gmail after verifying the account and recipient. Read Sent by exact report identity, recipient and time window. Read the full matching email and confirm the `SENT` label and decoded body. Reconcile uncertainty before any retry. Outreach requires its own request.
5. **Record delivery from readback.** The evidence file includes `verified_at` and either `native_chat_readback` or `native_sent_readback`, pointing to the retained native response. Require a complete error-free final chat message or actual Sent message at or after the attempt, with a message ID that no other brief acknowledged.

   ```sh
   python3 -m job_search_ops brief-delivered --root /absolute/private --brief BRIEF_ID --evidence /absolute/private/delivery-evidence.json
   ```

Keep the brief and its frozen set pending while delivery is uncertain. Newly saved receipts wait for the next brief. See [native evidence](native-evidence.md#first-pass-acceptance-and-delivery) for the binding checks.

## Stay quiet without blocking later reports

If a routine scheduled run has nothing to report and an unattempted brief is already prepared, release it:

```sh
python3 -m job_search_ops brief-cancel --root /absolute/private --brief BRIEF_ID
```

Use a fresh ID for the next brief. Cancellation preserves receipts for later delivery. Reconcile any send attempt first. Return requested manual reports and leave confirmation to the next invocation.

## Compact phase brief

Put newly saved jobs first, followed by prospects pending review or save, then selected application and interview actions. Group exceptions by source or company. Keep tool diagnostics in private evidence or optional Details. Use the same facts in chat, plain text and HTML.
