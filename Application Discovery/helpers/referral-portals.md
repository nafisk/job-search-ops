# Run a referral portal search

Use the `main` gate in the [shared source checks](../docs/operations.md#start-a-discovery-source). Central saves results through the [producer handoff](../docs/handoffs.md#producer-handoff). Use a supported browser for dynamic pages. Restricted pages need an authorized session and user sign-in.

In coordinated mode, start this run only for the companies named in the user's request. Confirm portal setup for those companies. Use the saved company scope when an existing installation assigns a recurring portal run.

Load `sources.referral_companies_path`, the accepted `<installation>/portal-registry.json` and the live **Referral Watchlist**. Follow [portal checks](../support/toolkit/PORTALS.md). Treat missing seeds or registry as a [setup gap](../docs/referrals.md). Freeze the private scope, reconcile conflicting scope or contacts. Merge verified aliases only within the same employer unless the user approved combining subsidiaries.

1. Freeze the assigned companies and use their saved company keys. Keep contact evidence private.
2. Start from the saved [filtered links or browser steps](../docs/referrals.md#build-links-for-repeat-runs). Verify the employer, active filters, current inventory and complete pagination. If filters changed or the saved route fails, revalidate on the official board and record the new route or a coverage gap. Use the [portal checks](../support/toolkit/PORTALS.md#validate-before-reuse) before relying on a saved search.
3. Background retrieval may use `curl`/Python standard-library helpers or supported web tools. Preserve TLS checks. Do not extract private cookies, export browser credentials or call private authenticated endpoints. Greenhouse, Lever, Ashby and Workday routes must come from current observed evidence.
4. Use the public browser reader for JavaScript shells, partial text, filters, pagination or contradictory templates. Other authenticated interactive work uses the user's authorized external browser. Google mail/sheets remain connector-only. Inventory owned tabs and preserve existing user tabs and handoffs.
5. Enumerate the entire declared scope unless a verified incremental adapter proves equivalence. Record query/filter/page coverage, terminal pagination evidence and original check dates. No result from a partial page is a verified zero. Absence is Closed only with positive closure evidence or a complete authoritative comparison covering that specific role.
6. Use [screening](../support/toolkit/SCREENING.md) with the exact official descriptions, configured applicant facts and hard search requirements. Keep overall minimums separate from specialty and degree alternatives. Label target and stretch based on search policy. Leave unread or ambiguous descriptions unresolved. Record each candidate's decision and evidence.
7. Reserve browser fallback for incomplete retrieval. Record the exact URL and resume cursor if it fails.
8. Use the [shared handoff](../docs/handoffs.md#producer-handoff) for the `portal` packet. Include referral facts, verified identities, screening decisions, and coverage.
