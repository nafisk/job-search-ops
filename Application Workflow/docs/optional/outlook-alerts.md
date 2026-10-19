# Optional Outlook alert organization

> **Required:** An Outlook mailbox and user-approved alert/routing scope.
> **Runs in:** Codex guidance with selected Outlook tools or manual mailbox settings.
> **Computer use:** Needed when using mailbox web settings.

This organizes mail only. The workflow currently ingests Gmail; an Outlook folder does not make email discovery ready. Follow the LinkedIn search and real-delivery checks in [alert setup](../linkedin-alerts.md), then use these mailbox-specific steps.

### Outlook.com / Outlook on the web: move to a folder

1. Create or reuse **Job Alerts** in the mailbox. Open **Settings → Mail → Rules → Add new rule**.
2. Name the rule, add the reviewed sender/subject conditions, and choose **Move to → Job Alerts**. Use exceptions where needed. Review ordering and **Stop processing more rules** against existing rules; do not silently interfere with them.
3. Save and reopen the rule. Verify a new matching alert appears in that folder and is absent from Inbox. A category or the Other tab alone does not establish that move. Handle old messages separately only within the user's chosen scope.

Follow [Microsoft's rules guide](https://support.microsoft.com/en-gb/outlook/mail/manage-email-messages-by-using-rules-in-outlook). Prefer mailbox-side web rules; some classic Outlook rules need the desktop client running. For a Gmail account displayed inside Outlook, configure the rule at Gmail, not in Outlook's rules settings.

## Optional plus address

[Outlook.com supports site-specific addresses](https://support.microsoft.com/en-us/outlook/send-email-from-a-different-address-in-outlook-com), such as `yourname+jobs@outlook.com`. Tags are not separate sign-in identities. For work/school Microsoft mail, [support depends on Exchange configuration](https://learn.microsoft.com/exchange/recipients-in-exchange-online/plus-addressing-in-exchange-online). Keep the ordinary address if unavailable; verify actual LinkedIn delivery before relying on an alias condition.

Keep rules narrow, preserve read state and avoid delete/forward actions. Verify a newly arriving alert reaches Job Alerts outside Inbox; a category or manually moved old message is insufficient. Record the unsupported ingestion path honestly and continue other selected sources.
