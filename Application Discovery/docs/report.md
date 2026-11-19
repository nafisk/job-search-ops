# Report and delivery

Use the saved notification and delivery choices. Chat is the default. Select `report.delivery: "email"` for self-email or `report.delivery: "both"` for chat and self-email. Either email choice requires `report.send_opt_in: true`, the saved report recipient, and native Gmail send and Sent readback.

## Prepare the report

Run the CLI from `Application Discovery/support/`. Pass the private directory containing `installation.json` as `--root`.

1. **Freeze the receipts.** Prepare one brief for all selected channels.

   ```sh
   python3 -m job_search_ops brief-prepare --root /absolute/private --brief BRIEF_ID
   ```

2. **Use the saved public job pages.** Reopen the tracker and take the exact role-specific destination from **Jobs → Job Link**. Verify that it opens the human-facing posting for that role and matches the saved receipt. Keep API routes, JSON, board listings and supporting URLs in source evidence. Choose the public canonical URL before [enqueueing](handoffs.md#2-enqueue-a-source-normalized-packet) so it survives deduplication and readback.
3. **Build the public snapshot and compact body.** Start discovery reports with **Filters:** and short bullets in plain language. Summarize the applicable role and level policy, location and residency rules, required experience and tracker admission, and any source-specific constraint such as a Blind rating threshold. Derive the words from that run's installed policies. Group saved jobs under **Gmail alerts**, **Blind company research** or **Referral portals**. Skip empty groups. List each role once as company, middle dot and linked title. Add `[Referral available]` only after the tracker verifies **Available**. Label relistings and material changes when reported. Keep counts, coverage, attempts and elapsed time in private evidence. Surface actionable failures or decisions separately.
4. **Keep selected updates.** Copy the frozen `tracking_summary` and `referral_summary` to `tracking_updates` and `referral_updates` in the snapshot. Render their company, title, exact URL and safe change label when present. Keep contact names, handles, raw messages, transcripts, private paths and IDs, résumé answers, tokens and internal notes out of the public snapshot and email. Include interview actions only for selected tracking sources.

## Freeze and deliver

Save the exact snapshot and rendered bodies privately before recording the intent.

```sh
python3 -m job_search_ops brief-sending --root /absolute/private --brief BRIEF_ID --delivery /absolute/private/delivery-intent.json
```

Use `snapshot_path` for every intent. For `channel: "chat"`, add the configured `thread_id` and `chat_body_path`. For `channel: "email"`, add `recipient`, `subject` and `plain_body_path` and/or `html_body_path`. For `channel: "both"`, put all selected chat and email fields in the same intent. Each copy uses the same roles, public posting links and order.

- **Email.** Verify the connected Gmail identity and the sole saved recipient, then send the frozen bodies once through native Gmail. Read the full message from Sent, checking the label, exact recipient, subject, attempt time and decoded bodies. Use the native message ID when known. Search Sent by the exact report identity, recipient and attempt window if the send outcome is uncertain.
- **Chat.** Return the frozen body as the final response in the configured chat. On the next invocation, read the actual completed native turn and compare its full final message and timestamp with the intent.

Record each verified result using a `verified_at` timestamp and the respective `native_chat_readback` or `native_sent_readback` field pointing to the retained native response. For a dual-channel brief, either channel can be confirmed first. Check `delivery_receipts` for the verified channels. The baseline advances when both channels are confirmed. Retain the frozen brief and reconcile pending delivery before retrying. New receipts wait for the next brief.

```sh
python3 -m job_search_ops brief-delivered --root /absolute/private --brief BRIEF_ID --evidence /absolute/private/delivery-evidence.json
```

## Job Search email template

Use `Job Search {Month} {ordinal day}` based on the run date in the configured timezone. Use the full month name and `th` for days 11, 12 and 13.

```html
<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.55">
  <p><strong>Filters:</strong></p>
  <ul>{{applied_filter_bullets}}</ul>
  {{nonempty_source_sections}}
</div>
```

For each nonempty source, use a bold source name followed by a list of company and linked job title. Escape external text and URLs in HTML. Use the same filters and source sections in plain text with the exact URL on each role's line. Use inline badges for verified referrals.

## Stay quiet without blocking later reports

Use the saved notification choice for unchanged runs. Release an unattempted, unwanted brief with `brief-cancel --root /absolute/private --brief BRIEF_ID` and use a fresh ID for the next brief. Cancellation preserves receipts for later delivery. Reconcile any send attempt first.
