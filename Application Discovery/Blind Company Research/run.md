# Run Blind company research

Run the [source checks](../docs/operations.md#start-a-discovery-source) with the `blind` gate. Use public company sources and your saved policy. Supplied ratings require no Blind login. Use the `blind` source key and generated `prompts/blind.md` filename.

## Setup

Review the [starter list](blind-companies.json) or use the [example format](../support/config/examples/rated-companies.json) for your own list. Bind the reviewed private copy to `sources.rated_companies_path`. Research enabled companies only.

In the handoff, use `rating_origin: "user_supplied"`, set `rating_as_of` to the supplied date or `"unknown"`, and map `url` to `careers_url`. Verify careers URLs during research.

In coordinated mode, use the main search profile plus Blind's rating threshold and bound policy version. A standalone run uses its saved base and stretch thresholds.

## Reuse saved portal routes

If `private.refs.blind_search_sources` points to a private CSV, match routes by reviewed employer and read them in order. Use the assigned location scope. The CSV fields are `step,company,scope,source_type,url,search_or_filter,instructions`. Route types are `career_page`, `job_board`, `filtered_portal` and `official_site_search`. Follow the [portal validation checks](../support/toolkit/PORTALS.md#live-recipe-acceptance) before relying on a saved route.

## Every run

1. **Freeze the assignment.** Record the run ID, cutoff, enabled companies, routes and policy version. Load seen history and unresolved sources. Account for each enabled company in the assigned scope.
2. **Read official sources.** Verify the public boards, filters and pagination. Use exact official postings for decisions and the browser fallback for coverage gaps. Recheck saved jobs outside the board's readable scope on the official detail page. Use the [source coverage rules](../docs/operations.md#completion-and-source-gaps) for gaps and closures.
3. **Screen and deduplicate.** Follow [screening](../support/toolkit/SCREENING.md) using the full posting and saved criteria. Deduplicate by employer and requisition or verified canonical URL. Keep rating provenance and first-seen, last-verified and last-reported dates. Preserve material changes and relistings.
4. **Queue the results.** Record scope, check date, counts, gaps and resume cursor per company. Apply any [tracker admission rule](../docs/handoffs.md#tracker-admission), then send the `blind` packet through the [producer handoff](../docs/handoffs.md#producer-handoff). For a coordinator assignment, return the receipt and gaps to the coordinator. For a standalone run, list new verified matches with company/rating, title, location, years, exact link and whether the job is queued or saved. Label any stretch.

The coordinator imports ready packets. **Rated Companies** holds targets and ratings, **Rated Search Coverage** records attempts and gaps, and **Job Sources** stores accepted sightings. For a separate Blind schedule or manual run, explain when central will import the queue.
