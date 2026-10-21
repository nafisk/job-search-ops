# Find recruiters for named companies

> **Required:** Completed [onboarding](ONBOARDING.md), selected private settings/tracker, an explicit company scope, public research tools and the supported signed-in LinkedIn browser.
> **Runs in:** Codex app; local JSON or selected Google Sheets writes.
> **Computer use:** Required to inspect live LinkedIn profiles. This procedure ends at a roster, without drafting or sending.

Start with a request such as **“Find recruiters at [company] for my saved target roles.”** Read the current settings and [tracker](tracker.md), recover unfinished requested work and record the human request, companies, owner and run ID privately. A report, new application or another agent cannot launch this procedure.

## 1. Establish scope and history

Use the named companies, configured specialties and candidate levels. Ask only for scope that the request does not establish. Keep parents/subsidiaries separate unless both are selected. A standalone recruiter request does not require a submitted application.

If the user selects companies *because they applied there*, verify that selection from their actual application history. When using [Application Workflow](../Application%20Workflow/README.md), consult its accepted role identities and [tracking evidence](../Application%20Workflow/docs/tracking.md); do not infer submission from an open tab. This dependency does not automatically trigger recruiter research or change application records.

Read canonical profile identities, exclusions, opt-outs, replies, prior outreach and existing reservations before adding contacts. Matching names alone cannot merge people. Normalize observed profile URLs by removing tracking parameters and equivalent trailing slashes; merge materially different URLs only with evidence that they identify the same person.

## 2. Search broadly and retain coverage

Use the company's LinkedIn People/current-company filter as a lead finder. Search recruiter/recruiting, sourcer, talent acquisition, talent partner/advisor and staffing families; add the user's specialty terms. Split unsupported long queries. Generic titles may qualify when their current work fits; historical keyword matches do not prove current remit.

Record queries, observed results/pages, cursors and inaccessible scopes in private `state.json`. Pursue the configured research goal without relaxing fit to fill it. A capped or unavailable listing is partial coverage, not proof that no more recruiters exist. Process distinct fresh identities before repeatedly retrying failed profiles.

## 3. Verify employer and recruiting remit

Read each live profile. Current Experience marked Present or a clear first-person current-employment statement can establish employer when no contrary evidence exists. Search filters, snippets and headlines alone cannot. Direct fixed-term employment may qualify; an agency's client assignment does not prove employment at that client.

Inspect title/About first, then the current Experience description when needed. Compare explicit current hiring remit with the user's specialties and candidate levels. A recruiter's own senior title is not the level of candidates they recruit. Broad compatible hiring may have an unspecified candidate level; record that uncertainty. An explicit incompatible remit is an exclusion; unclear evidence stays Needs review.

| Decision | Record |
| --- | --- |
| Employer | `Verified current`, `Unconfirmed` or `Not current`, with source statement, URL and actual check time |
| Fit | `Match`, `Needs review` or `Exclude`, against the user's saved target scope |
| Qualification | `Qualified`, `Hold: employment`, `Hold: specialty` or `Excluded`, using [tracker rules](tracker.md#contact-fields) |

Keep fit, employer and communication history separate. A draft or a formula cannot supply missing evidence. Preserve held contacts for review and excluded identities for history/deduplication. Do not mark someone Do not contact merely because their remit is a mismatch.

## 4. Save and stop at the roster

Only the coordinator saves accepted contact changes through [tracker writes](tracker.md#save-and-recover). Preserve user notes, send dates, replies and existing drafts. Read back affected records before reporting them saved; unavailable sync remains explicitly unsynced.

Parallel workers may research disjoint assigned profiles and return evidence. One operator owns browser controls at a time; only the coordinator changes shared state. At most the configured read attempts apply across methods/workers for one failed operation. On uncertainty, checkpoint the last verified state and continue independent contacts; never reset attempts by opening another tab.

Hand off unique contacts, verified matches, Needs review records, exclusions as aggregate counts, actual coverage and precise gaps. Give links and evidence for retained contacts; distinguish research goals from observed results. Stop here. A separate scoped request and approved copy are needed for [drafting](run.md).
