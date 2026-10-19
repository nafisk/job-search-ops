# Reusable official-portal search registry

**Required:** Python 3.10+, the user’s private employer scope, and observed official search evidence.  
**Runs in:** Codex with public research tools; browser/computer use when filters, login or rendering require it.

Keep employer scope, referral contacts/holds and observed searches in a **private** registry. Share this guide and `portals.py`, never a personal company list or account history. The registry seeds future portal validation; it does not fetch jobs or prove current coverage. Saved successful counts and terminal pages are historical evidence only.

## Build the registry

Read the current authoritative company/watchlist scope and saved portal evidence. Reconcile combined labels against explicit earlier scope before creating employer IDs. Shared ownership or a common recruiting site is not permission to merge separate employers. Preserve nonblank referral contacts in the private authoritative scope record, and company-wide hold state in the registry; do not clear holds as part of search setup. Do not infer an employer was removed solely from a row-count difference.

Registry shape (unknown fields/version fail):

```text
schema_version: 1
profile_id: matching private profile ID
scope_evidence: [private evidence references]
companies: [
  company_id, employer_name, referral_hold,
  scope_refs: [private row/history evidence references],
  watchlist_rows: [observed one-based row numbers],
  official_urls: [{url, evidence_ref}],
  historical_evidence: {source-preserved portal family, identity fields,
                        successor routing evidence, hazards and citations},
  searches: [{search_id, label, observed_urls: [exact observed URLs],
              evidence_refs: [private file/pointer references],
              details: {observed filter labels/IDs, location/role scope,
                        sort, pagination, terminal evidence and hazards}}]
]
```

`historical_evidence` and `details` are finite JSON metadata, not an executable adapter or a fixed vocabulary of imagined portal fields. Preserve source terminology and evidence pointers. Unknown metadata remains null/unknown, and an unknown observed search URL is an empty list with a cited unresolved scope. Never invent filter IDs, normalize a terminal URL into an unobserved first page or fabricate a successor link. Root/watchlist URLs and actual filtered search URLs are separate records. Keep source observations/dates, selected-job `pid` and pagination `start`/`page` values in historical evidence, with hazards. They are not reusable entry defaults.

Label selected metadata as a projection. When claiming an inventory scope is preserved “as saved,” retain the complete original object alongside that projection, including nested page ledgers/counts. A resolving citation alone does not prove a copied record is complete.

Use `validate_registry(registry)` for shape, unique employer/search identity, explicit holds, source references and safe observed URLs. Company IDs are unique across the registry; search IDs are unique within their company, so two employers can both use `nyc` without merging their searches. It returns a copy and performs no file/network access. The host independently checks every source pointer and confirms that each URL/metadata actually appears in its cited artifact; a valid-looking URL is not proof of observation.

## Validate before reuse

For each declared search, establish the official employer/board and minimal working inventory query. Add location, remote, role and other filters individually; inspect displayed values and actual returned jobs. Verify Boolean syntax rather than assuming support. Avoid exclusive seniority filters that hide allowed low-experience or numbered-role exceptions. Preserve broad scope where keywords cannot be trusted. Verify native pagination, lazy-loaded cards, a changed active page and terminal evidence. Reopen the proposed entry URL and check it starts at the intended first page with the same filters. A selected job, redirected landing page, ignored facet, transient empty result or loading shell cannot pass.

After independently checking that evidence, the host may provide typed `SearchValidation(profile_digest=digest(profile), company_digest=digest(company), search_id, entry_url, checked_at, first_page_verified, filters_verified, pagination_verified, evidence_ref)` to `prepare_search(profile, registry, company_id, search_id, as_of=..., max_age_days=..., proof=...)`. All three booleans require observed evidence, not worker claims. The proof's entry URL must be observed during that current validation; the function checks binding/freshness but cannot authenticate the semantic evidence. Trusted provenance stays at the host boundary.

No proof, dictionary-shaped proof, changed profile/company data, false verification flags or stale/future evidence returns a usable URL. The result is explicit `needs_validation`, never no-match/complete. Valid proof returns `ready` with its exact validated entry URL and unchanged referral hold. `discovery_complete` is always false: an entry point's readiness does not establish today's inventory, detail screening or verified sheet sync. Disjoint company evidence work may run in parallel, while shared browser/Sheets/state controls remain exclusive.

The [portal runbook](../../helpers/referral-portals.md) owns actual retrieval, browser fallback, retries and terminal scope acceptance. Reuse the configured background-first/built-in-browser fallback and shared three-attempt budget when those adapters are connected. Do not activate a new route from this registry alone.

## Live recipe acceptance

Validate one small representative search before expanding to a new portal family. Keep the recipe and its live evidence outside this package. A recipe is the exact request and extraction procedure, not necessarily a bookmark: some sites need an observed read-only POST body as well as a URL. Never present a POST endpoint alone as a working saved search. `prepare_search` currently returns only a URL; it does not execute or attest to POST recipes.

The worker records these five checks; a separate reviewer reads the actual evidence before the host accepts a proof:

1. **Baseline:** confirm employer/board identity, current requested and final URLs, first page, actual job cards and displayed total. A broad working inventory is the positive control before narrowing. Save observation times and exact response artifacts.
2. **Filters:** add each location/remote/role filter separately. Record the observed option label and ID, selected readback, and the returned jobs that show its effect. Follow multi-location detail links when a card's primary city appears to contradict the filter. If Boolean syntax is not supported or there is no keyword control, retrieve a broad inventory and screen it locally. Do not invent URL parameters or exclude all senior/numbered roles.
3. **Traversal:** record every actual page/cursor, source IDs, count, next control/cursor and terminal evidence. Confirm that pages change and reconcile the union of distinct IDs with the displayed total. A full single-page inventory still needs an observed end and count reconciliation. A repeated page, missing cards or interrupted page is unfinished coverage.
4. **Reopen:** load the exact saved recipe again, starting at page one with the intended filters. Compare identities, not only totals; explain actual changes with timestamps. Open one observed detail link and confirm it identifies the same role. A selected-job URL or terminal-page URL is not the reusable entry.
5. **Empty/layout guard:** no-match requires a healthy inventory, applied filters, an explicit settled empty state and a working broad positive control. Missing selectors, a JavaScript shell, generic missing-page template or changed data shape mean needs-validation. Never turn a parser exception into an empty list.

Keep a compact private record with: company/search scope, method and exact URL/body, observed field definitions, extraction path, stable identity field, page ledger, reopen evidence, raw response hashes, attempts and failures, reviewer outcome, and remaining gaps. Bind its accepted report to the current profile/company digests. `first_page_verified` includes baseline and clean reopen; `filters_verified` includes control and result checks; `pagination_verified` includes the full declared scope and terminal evidence. A worker's five checked boxes alone are not independently accepted proof.

Prefer the broadest cheap, complete inventory when narrowing risks losing matching roles. Department labels are not job-family truth: a backend role may sit outside an employer's Software department. Geography absent from one dropdown does not by itself prove the entire employer has no eligible role. Recipe validation establishes a retrieval route; description screening and verified tracker writes remain separate required work.

## Retrieval patterns to validate per deployment

- **Hosted boards with embedded JSON:** a text extractor may show only a JavaScript warning while the public HTML contains the complete job list. Parse the observed inert JSON using the standard library; never execute downloaded script. Check employer/board identity, expected shape and stable job IDs against the rendered board before reusing the extraction path. Missing or changed shape is unknown, never zero. Retain all locations and departments when that is the complete cheap inventory.
- **Paginated boards:** keep the public posting ID distinct from internal display/requisition IDs. Record actual current pagination controls and the unique-ID union. A matching count alone cannot detect repeated pages or replacement jobs. Reopen the first-page query and verify its facet controls and results.
- **Form-backed searches:** retain the exact observed endpoint, method, nonsecret form fields, facet IDs and response extraction path together. A filter's name or requested payload does not prove it was applied. Check response facet state and representative full-location details, traverse the native pagination, and repeat the same first-page recipe. Do not share private account/session fields or derive credentials from the browser.

Use the configured background-first access policy. If the response is incomplete or conflicts with the visible board, request the exclusively owned browser fallback with the remaining shared attempt count. Do not reset failed-operation budgets when a worker or method changes. A tool-wide connectivity failure is recorded once as a capability gap; it is not evidence that every company's portal was visited.

Workers may expose different browser capabilities and cannot assume a coordinator's tab ID is accessible in their session. Keep interactive ownership with one agent, preserve its observed controls/ID arrays/times as evidence, and let independent workers audit captured source records. Distinguish an independent source audit from a second live UI execution; an unavailable worker browser is not a company-portal failure.

## Full-scope validation

Map every configured historical search to its current recipe, a verified broader inventory, or a named unresolved gap. Keep the old search intact; record the replacement and its evidence separately. A complete broader inventory can replace overlapping keyword searches, but its jobs still need individual screening. Avoid expanding into a large global walk when a verified location/remote facet can cover the same declared scope cheaply. A local-only success cannot clear an unresolved remote search.

Some native searches preserve filters during page-button navigation but omit them from the URL. Save a short interaction recipe: clean entry, sort, selected filters, full page traversal, then clean reopen and reapply. Label these as interaction recipes, never URL-only ready searches. Check settled controls after asynchronous rerenders before retrying an apparently failed action.

Record actual visible results separately from recommendation links and hidden duplicate cards. Preserve compound posting/location IDs when the board treats them as distinct. Reconcile distinct identities across all pages: an endpoint may ignore a cursor, overlap pages or change totals during collection even when the final page and first-page reopen look correct. Retain the failed capture; a new stable traversal or native browser recovery may supersede it, but matching counts alone cannot repair it.

The private acceptance index should bind each company/search mapping to the current profile and company digests, cite source and audit files with their hashes, preserve original observation times for reused evidence, and name any superseded worker outcome. A validation task can account for every company with verified coverage or explicit blockers; that does not make blocked coverage complete, prove individual eligibility, or advance operational discovery. Keep recipe validation, executable adapter readiness and verified tracker sync separate.
