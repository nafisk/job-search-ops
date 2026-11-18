# Run Blind company research

Load the reviewed company list and search policy. Follow the [shared operating rules](../docs/operations.md) and run the [source checks](../docs/operations.md#start-a-discovery-source) with the `blind` gate. Use public search and page reads, with browser controls if needed. Supplied ratings require no Blind login.

Run manually or on the selected Blind schedule. Queue results through the [producer handoff](../docs/handoffs.md#producer-handoff). Central saves reviewed targets and provenance to **Rated Companies**, attempts and gaps to **Rated Search Coverage**, and accepted evidence to **Job Sources**. Keep the `blind` source key and generated `prompts/blind.md` filename.

## Setup

Choose the bundled [103-company starter list](blind-companies.json) or supply your own using the [fictional format example](../support/config/examples/rated-companies.json). The starter preserves the original company names, supplied ratings and career URLs; personal notes are removed. **These are historical user-supplied ratings, not freshly verified Blind ratings. Their original rating dates are unknown.** Career URLs are starting points and must be rechecked during research.

During onboarding, copy the selected list outside the repository, review which companies to enable, and set `sources.rated_companies_path` to that absolute private copy. Do not bind the repo file directly, overwrite an existing private list, or enable Blind merely because the starter is present. Add personal notes only to the private copy. An empty selection leaves discovery disabled until targets are chosen. The tracker’s **Rated Companies** tab holds this installation’s reviewed targets and rating provenance.

Keep unknown rating dates explicitly `"unknown"`; never substitute the research date. For central handoff, map the input `url` to `careers_url` and retain `rating_origin: "user_supplied"`. Search only enabled companies.

Configure rating threshold, role families, preferred locations, location priority and experience policy. Classify roles using the installed base/stretch thresholds and excluded titles. These are search preferences, **not statements about the person's actual experience**. Respect the configured replacement policy and retain its version in every sighting.

## Reuse saved portal routes

Use the confirmed company list as the target scope. If `private.refs.blind_search_sources` points to a private CSV, read it in saved priority order. Match rows by the exact reviewed employer. Keep a verified board or first-page filtered URL, a fallback query or browser steps, and the scope each route covers. For a NYC-first search, try the saved NYC route or a company-specific official-site query before the configured remote and other US search scopes.

The existing source-list format can be reused. Relevant columns are `step,company,scope,source_type,url,search_or_filter,instructions`. Use `career_page`, `job_board`, `filtered_portal` and `official_site_search` for research routes. The installed tracker binding supplies the save destination. Review full postings, preserve priority and verified pagination, and account for every enabled company even when a route is missing. Record per-company filter and coverage gaps. Follow the [portal validation checks](../support/toolkit/PORTALS.md#live-recipe-acceptance).

## Every run

1. Freeze run ID, cutoff, company list, saved routes and policy version. Read prior review/seen history and all unresolved sources. Attempt every enabled target; never silently turn a test subset into the scheduled scope.
2. Revalidate observed public careers/ATS sources and full pagination. Prefer official exact postings. Use supported web discovery and public browser fallback for coverage gaps. Existing board metadata and search snippets are leads only. Never extract private cookies or bypass access controls.
3. Follow [screening](../support/toolkit/SCREENING.md) for each full description and any configured applicant facts or search requirements. Distinguish overall minimums from skill-specific years and preferred qualifications. Preserve exact published ranges and available degree alternatives. Ambiguous experience/level is unconfirmed. Record country/region eligibility and work authorization against the configured locations, office attendance, on-call, specialized languages and applied-AI versus ML research/training constraints.
4. Recheck saved roles outside the readable board's actual scope by exact official detail. A supplemental board cannot prove a role disappeared from the main site. Conflicting caches, redirects, partial lists and failed access cannot establish availability or closure.
5. Deduplicate by employer/requisition or observed canonical official URL. Preserve first-seen/last-verified/last-reported dates, prior review evidence and material changes. Fresh users initialize their own baseline; never inherit another user's suppression history.
6. Save each company's scope, check date, source count, verified openings, and gaps. Record where to resume if a board fails.
7. Apply [tracker admission](../docs/handoffs.md#tracker-admission) if set, then use the [shared handoff](../docs/handoffs.md#producer-handoff) for the accepted `blind` packet. Include rating and policy provenance, coverage, and the distinction between new roles, material changes, and relistings.
8. List every newly verified research match directly in the rated chat with company/rating, title, location, published experience, exact official link and important constraints. Include report-only roles and label stretches. State whether eligible jobs are queued, saved or pending sync. A save failure does not suppress the chat list. Stay quiet for routine unchanged runs and surface actionable gaps.

The central coordinator drains ready rated packets during its next merge, writes accepted Jobs/Job Sources rows, and includes the saved receipts in the next brief. If rated discovery finishes after that brief's frozen set, its receipt belongs to the following brief; never lose it or reannounce it from reset state. When central runs manually, queued results wait for that run; explain this timing during onboarding. An optional separate rated schedule does not authorize a second writer, email send, application, recruiter contact or change to the main timer.
