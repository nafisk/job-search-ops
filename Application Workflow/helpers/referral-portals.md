# Referral portal producer

> **Required when selected:** Your private company list, accepted portal registry, Referral Watchlist, search policy, Python 3.10+, public search/page reads, the supported Codex browser and a [producer handoff](../docs/handoffs.md#producer-handoff).
> **Runs in:** Codex app; the central chat saves results.
> **Computer use:** Dynamic pages need browser interaction. Restricted pages additionally need an authorized signed-in browser and your login.

Start with the [shared source checks](../docs/operations.md#start-a-discovery-source). Use the `main` gate.

Read the authoritative file at `sources.referral_companies_path`, the accepted `<installation>/portal-registry.json`, the live Referral Watchlist and [toolkit portals](../support/toolkit/PORTALS.md). [Referral setup](../docs/referrals.md) creates these projections; missing seed/registry is a setup gap, not an empty search. Freeze scope from the private list and overlay stricter live contact/referral holds. Never clear a hold from weaker registry data. Manual scope or contact conflicts require reconciliation. Group verified employer aliases while keeping distinct subsidiaries separate unless explicitly approved.

1. Freeze every configured company in scope; partition disjoint companies among workers. Preserve contact/referral holds and exact company keys. A held application route does not prevent public job discovery.
2. Use official public careers pages and observed ATS endpoints first. A saved URL/endpoint is a starting point, not proof its filters or board identity still work. Verify employer identity, location/filter effects, complete pagination/traversal, clean reopen and layout/empty-result safeguards before treating a portal recipe as validated.
3. Background retrieval may use `curl`/Python standard-library helpers or supported web tools. Preserve TLS checks. Do not extract private cookies, export browser credentials or call private authenticated endpoints. Greenhouse, Lever, Ashby and Workday routes must come from current observed evidence.
4. Use the supported Codex built-in browser for JavaScript shells, partial text, filters, pagination or contradictory templates. Other authenticated interactive work uses the user's authorized external browser. Google mail/sheets remain connector-only. Inventory owned tabs and preserve existing user tabs and handoffs.
5. Enumerate the entire declared scope unless a verified incremental adapter proves equivalence. Record query/filter/page coverage, terminal pagination evidence and original check dates. No result from a partial page is a verified zero. Absence is Closed only with positive closure evidence or a complete authoritative comparison covering that specific role.
6. Verify exact official descriptions and all matching criteria; keep overall minimums separate from specialty/degree alternatives. Label target and stretch based on configured search policy, without rewriting factual tenure. Unread/ambiguous descriptions remain unresolved. Every candidate gets a decision and evidence.
7. Reserve browser fallback for incomplete retrieval. Record the exact URL and resume cursor if it fails.
8. Use the [shared handoff](../docs/handoffs.md#producer-handoff) for the `portal` packet. Include referral facts, verified identities, screening decisions, and coverage.
