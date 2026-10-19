# Set up LinkedIn alerts and keep them out of your inbox

> **Required when selected:** A LinkedIn account, access to the receiving mailbox and the supported signed-in browser. Automated discovery additionally requires native Gmail search/full-message reads.
> **Runs in:** Codex app plus LinkedIn browser setup. Outlook steps organize mail only; they do not enable ingestion.
> **Computer use:** Required for LinkedIn alerts. You handle login and mailbox-rule settings when native tools cannot manage them.

**Use this step when choosing LinkedIn email discovery in [onboarding](../ONBOARDING.md).** You need active email alerts for the jobs you want before the workflow can discover those jobs from mail. Skip this step for portal-only, Blind-only or tracking-only setups.

Recommended: keep your existing email address, create a **Job Alerts** label/folder, and route only job-alert emails there. A `+jobs` address is optional; it does not create a folder or rule by itself.

**Current reader support:** the shipped Email Discovery helper reads Gmail. The [optional Outlook instructions](optional/outlook-alerts.md) organize alerts in Outlook, but an Outlook folder is not yet an automated input to this package. Record that reader gap explicitly; do not put Outlook searches into `sources.gmail_queries` or claim full email-discovery setup. Other selected sources can still run.

## 1. Check what is already set up

The setup assistant reads saved choices first, then checks the selected LinkedIn account, mailbox provider, existing alerts and routing rules. Reuse a matching setup instead of creating duplicate alerts or filters. Ask only for missing choices: target searches, daily/weekly frequency, mailbox, destination label/folder and whether to organize existing matching messages too. Default to future mail only. Save these choices and the proposed rule in a private draft note before external changes; retain pending evidence there until initialization creates the installation's evidence directory.

Use the supported signed-in browser for LinkedIn. For Gmail, use native tools for account identity, message/label reads and any available label/filter management. Discover actual capabilities: a label-creation tool is not a filter-creation tool. If native filter management is unavailable, give the user the exact Gmail settings steps below, then verify the resulting messages through native reads. Preserve the repo's connector-only Google access; do not add a CLI, alternate credentials or browser Google access. Outlook rule setup may use a selected, authorized native tool or supported browser; otherwise guide the user through it.

Show the concrete search and routing rule before saving. The user's request to set up these chosen alerts/routing authorizes those actions; do not add another blanket confirmation. New connections/permissions and changes to an existing LinkedIn primary address need their own user choice. Leave sign-in and verification challenges to the user. These are setup actions, never daily producer actions; no additional permanent chat or schedule is needed.

## 2. Create email alerts for the desired jobs

1. In LinkedIn Jobs, search the selected title/keywords and location. Set the relevant experience, work arrangement and other available filters. Review results against the user's actual search intent.
2. Turn on the job-alert switch for that search. Reuse an existing equivalent alert where possible.
3. Open **Manage alerts**, choose the user's daily/weekly frequency and enable **email** delivery. App notifications alone do not supply this workflow. Recommend daily for a daily discovery run; the user can choose weekly.
4. Reopen the alert to verify its saved criteria and delivery settings. Save its search URL or visible identity privately. Repeat for the distinct searches the user selected.

These controls are described in [LinkedIn's job-alert instructions](https://www.linkedin.com/help/linkedin/answer/a511279/job-alerts-on-linkedin). Verify the actual destination mailbox from received mail; do not assume every alert offers a separate recipient-address field.

## 3. Route job alerts into a label or folder

First inspect real alert messages. Build a narrow condition from their actual sender and, where needed, stable job-alert subject text. Test that it includes the selected alert types and excludes sampled recruiter messages, application receipts, interview messages and account-security emails. Do not archive every message from LinkedIn or everything containing “job.” If no sample exists yet, record that gap and finish the rule when one arrives; do not invent a sender.

### Gmail: label and archive

1. Create or reuse **Job Alerts**. Open a genuine alert and choose **Filter messages like these**, or enter the reviewed criteria through the search options. Preview the matching messages.
2. Create the filter with **Apply the label → Job Alerts** and **Skip the Inbox (Archive it)**. Applying a label alone leaves mail in the inbox. Leave delete, mark-as-read and forwarding off. Apply to existing matches only if the user chose that scope.
3. Reopen **Settings → See all settings → Filters and Blocked Addresses** and verify the saved conditions/actions. With the manual fallback, the user performs this step and reports the saved criteria/actions; record them as **user-confirmed**, not native tool readback. Independently confirm through native message reads that an arriving match has the label and lacks the Inbox label, while remaining readable.

Use [Gmail's filter instructions](https://support.google.com/mail/answer/6579?hl=en) and Google's [label-and-skip-inbox example](https://workspace.google.com/blog/productivity-collaboration/g-suite-pro-tips-declutter-your-inbox-with-gmail-filters). Categories such as Updates or Promotions are not a substitute for a verified routing rule.

For Outlook organization only, use the separate [optional Outlook guide](optional/outlook-alerts.md). It does not enable this package’s Gmail reader.

## 4. Optional: use an address such as `name+jobs@…`

[Gmail supports address variations](https://gmail.googleblog.com/2008/03/2-hidden-ways-to-get-more-from-your.html), such as `yourname+jobs@gmail.com`. Mail still reaches the original mailbox. Combine a verified recipient-address condition with the alert-specific conditions above; the tag alone could also receive important non-alert mail.

LinkedIn uses a verified primary address for notifications; changing it can affect more than job alerts. See [LinkedIn's email-address settings](https://www.linkedin.com/help/linkedin/answer/a518975). Do not change the primary address just to get a tidy inbox. If the user chooses a tagged address, verify LinkedIn accepts it and a real alert reaches it before relying on the recipient condition. A self-sent test cannot prove LinkedIn delivery.

## 5. Verify delivery and hand off to discovery

The assistant performs a separate alert-readiness check; `doctor` checks tool readiness, not LinkedIn subscriptions or inbox routing.

| Check | Evidence needed |
| --- | --- |
| Alerts configured | Actual saved searches, email enabled, frequency and selected account. |
| Routing configured | Saved conditions/actions and label/folder; distinguish tool-observed settings from user-confirmed settings when rule-read tools are absent. Reuse equivalent rules. |
| Delivery and routing observed | A real post-rule LinkedIn alert in the destination, outside Inbox, with full body/cards readable. Check selected alert types; disclose any still unobserved. |
| Reader ready | Gmail identity matches, bounded query returns the routed message, and full-message read succeeds. Outlook remains a reader gap in this release. |

After initialization, transfer/reference the private draft in `evidence/linkedin-alerts-setup.md`. Record choices, rule/label identities, evidence provenance, received message ID/date, checked time and gaps. Keep planned and tested queries distinct. Store references rather than raw correspondence. Set `sources.gmail_queries` from the chosen label (for example, `label:"Job Alerts"`) and observed sender/subject conditions before freezing config; never invent a sender or silently rewrite an initialized config. A label query may be planned while awaiting delivery, but is not verified until it retrieves a real alert. Retain separate sender/subject queries for missed-label reconciliation once observed. The producer adds bounded time windows. Do not require `in:inbox` or `is:unread`: archived/read alerts must remain discoverable.

An existing deployment may already have equivalent private proof under another name; reuse it and consolidate on the next authorized setup/review. The absence of this new filename alone is not grounds to recreate alerts or change existing schedules. Tool-observed delivery proves routing behavior; it does not turn user-confirmed rule settings into independently read settings.

If no alert has arrived, record **awaiting_first_alert**, with the selected cadence and next check, rather than claiming a verified zero-match source. Check the selected email settings, destination and spam/junk when troubleshooting; do not broaden the filter or disable security controls. Continue independent setup, retain the gap and do not enable a schedule that depends on this unfinished email pilot. Scheduling a follow-up still requires the user's choice.

Hand the evidence path and queries to [Email Discovery](../helpers/email-discovery.md). Daily runs read only; they do not recreate alerts, rules or labels. Finish with the saved searches, destination, routing status, ingestion status and the next action if delivery is pending.

*Official guidance checked October 19, 2026. Inspect current controls and tool schemas during setup; names and capabilities can change.*
