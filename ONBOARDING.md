# Set up your job-search workflows

Choose the workflows you need. Ask the agent to reuse confirmed answers and follow each selected guide.

| Goal | Guide |
| --- | --- |
| Review a resume | [Resume](Resume/README.md) |
| Audit or edit a LinkedIn profile | [LinkedIn](LinkedIn/README.md) |
| Find jobs from alerts, referral portals or Blind company research | [Application Discovery](<Application Discovery/ONBOARDING.md>) |

Use supplied files for resume and LinkedIn content reviews. For operational workflows, keep the complete repo or reviewed release ZIP contents in a permanent folder the agent can access.

Alerts, referral portals and Blind research share one tracker and central writer. Choose the sources you need.

## Ask your agent to guide setup

```text
Read ONBOARDING.md and guide me through the workflows I choose. Reuse my
setup and confirmed answers. Explain the tools and permissions I need.

I authorize the documented setup for my choices, including the required
trackers, selected chats and delegation. Ask before installing software,
adding connections or expanding access. Preserve unrelated workflows.
Keep discovery and tracking within the selected scope.
Save my private setup summary with any blockers and the exact next request.
```

## Tools for your choices

| Tool | When to use it |
| --- | --- |
| Local files and [Python 3.10+](https://www.python.org/downloads/) | Operational workflows. The shared runtime requires POSIX file locking through `fcntl` and IANA timezone data. |
| Public search and page reads | Job research. |
| Browser controls | Live LinkedIn work and interactive career sites. Sign in yourself. The agent verifies the selected session and preserves existing tabs and edits. |
| Google Drive and Sheets connector | A Google tracker or Sheets discovery export. Verify the account, workbook and permitted operations. |
| [Excel runtime](<Application Discovery/docs/local-excel.md>) | Local Excel writes require Node and `@oai/artifact-tool`. |
| Gmail or Calendar connectors | Gmail for selected discovery, tracking or report email. Calendar for selected interview tracking. |
| [Mac Messages MCP](https://github.com/carterlasalle/mac_messages_mcp) | Selected Messages tracking. Follow the [Messages setup guide](<Application Discovery/docs/messages.md>). |

Use the selected guide's access checks and report any missing access that affects the requested work. See [Application Discovery tools](<Application Discovery/docs/tools.md>).

## Reuse an existing setup

Provide the private configuration or ledger path. Read its choices and verification records before asking for missing information. Preserve active settings, trackers and history.

Keep private data outside the repo and shared exports. Check resolved paths, including symlinks and case aliases, and follow the guide's permissions. Keep one authoritative configuration per workflow.

## Your setup summary

Update `setup-summary.md` in the private setup folder. Preserve unrelated entries. For supplied-content reviews, return the handoff in chat.

Include these items:

1. Selected workflows, verified setup, actual pilot results and outstanding gaps.
2. The actual tracker file path or verified workbook link.
3. Absolute links to the canonical settings, ledger and runbook. Keep credentials and private correspondence out of the summary.
4. Assigned chats, ownership and manual mode or verified schedules.
5. One copyable next request with actual paths and scope, or the step needed to unblock setup.

Read the linked records when resuming. Follow the current verification state and holds. A summary grants no permission.
