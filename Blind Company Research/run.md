# Run Blind company research

> **Required when selected:** Your reviewed company list and search policy, Python 3.10+, public search/page reads, browser controls for interactive pages and a working [producer handoff](<../Application Workflow/docs/handoffs.md#producer-handoff>).
> **Writes:** The central chat saves results to the selected tracker.
> **Computer use:** Browser interaction when career pages need it. Supplied ratings do not require a Blind login.

Read the shared [operating rules](<../Application Workflow/docs/operations.md>) before setup or execution. Use [onboarding](ONBOARDING.md) for new choices. This folder owns the company-research instructions and starter; the existing Application Workflow runtime owns setup, queueing and tracker writes.

Start with the [shared source checks](<../Application Workflow/docs/operations.md#start-a-discovery-source>). Use the `blind` gate.

This optional producer, run manually or on its own selected schedule, updates the **same configured tracker (local Excel or Google Sheets)** through the central queue and writer. It does not directly mutate Sheets or maintain a competing authoritative workbook. Rated Companies stores the user's target list/provenance; Rated Search Coverage stores current per-company attempts/gaps; Job Sources preserves rated policy evidence alongside email/referral sightings. Local JSON/evidence are durable working state, not a separate master tracker.

The technical source key and saved filename remain `blind` for compatibility. The optional starter comes from a historical Blind 3.5+ list.

## Setup

Choose the bundled [103-company starter list](blind-companies.json) or supply your own using the [fictional format example](<../Application Workflow/support/config/examples/rated-companies.json>). The starter preserves the original company names, supplied ratings and career URLs; personal notes are removed. **These are historical user-supplied ratings, not freshly verified Blind ratings. Their original rating dates are unknown.** Career URLs are starting points and must be rechecked during research.

During onboarding, copy the selected list outside the repository, review which companies to enable, and set `sources.rated_companies_path` to that absolute private copy. Do not bind the repo file directly, overwrite an existing private list, or enable Blind merely because the starter is present. Add personal notes only to the private copy. An empty selection leaves discovery disabled until targets are chosen. The tracker’s **Rated Companies** tab holds this installation’s reviewed targets and rating provenance.

Keep unknown rating dates explicitly `"unknown"`; never substitute the research date. For central handoff, map the input `url` to `careers_url` and retain `rating_origin: "user_supplied"`. Search only enabled companies.

Configure rating threshold, role families, preferred locations, location priority and experience policy. Classify roles using the installed base/stretch thresholds and excluded titles. These are search preferences, **not statements about the person's actual experience**. Respect the configured replacement policy and retain its version in every sighting.

## Every run

1. Freeze run ID, cutoff, company list and policy version. Read prior review/seen history and all unresolved sources. Attempt every enabled target; never silently turn a test subset into the scheduled scope.
2. Revalidate observed public careers/ATS sources and full pagination. Prefer official exact postings. Use supported web discovery and public browser fallback for coverage gaps. Existing board metadata and search snippets are leads only. Never extract private cookies or bypass access controls.
3. Read each full description; distinguish overall minimums from skill-specific years and preferred qualifications. Preserve exact published ranges and available degree alternatives. Ambiguous experience/level is unconfirmed. Record country/region eligibility and work authorization against the configured locations, office attendance, on-call, specialized languages and applied-AI versus ML research/training constraints.
4. Recheck saved roles outside the readable board's actual scope by exact official detail. A supplemental board cannot prove a role disappeared from the main site. Conflicting caches, redirects, partial lists and failed access cannot establish availability or closure.
5. Deduplicate by employer/requisition or observed canonical official URL. Preserve first-seen/last-verified/last-reported dates, prior review evidence and material changes. Fresh users initialize their own baseline; never inherit another user's suppression history.
6. Save each company's scope, check date, source count, verified openings, and gaps. Record where to resume if a board fails.
7. Use the [shared handoff](<../Application Workflow/docs/handoffs.md#producer-handoff>) for the `blind` packet. Include rating and policy provenance, coverage, and the distinction between new roles, material changes, and relistings.
8. Return every newly verified qualifying role in the rated chat when configured: company/rating, title, location, exact published experience, official link and important constraints. Clearly label stretches and say whether the packet is queued or has a central saved receipt. No matches/changes means quiet unless there is an actionable failure or user decision.

The central coordinator drains ready rated packets during its next merge, writes accepted Jobs/Job Sources rows, and includes the saved receipts in the next brief. If rated discovery finishes after that brief's frozen set, its receipt belongs to the following brief; never lose it or reannounce it from reset state. When central runs manually, queued results wait for that run; explain this timing during onboarding. An optional separate rated schedule does not authorize a second writer, email send, application, recruiter contact or change to the main timer.
