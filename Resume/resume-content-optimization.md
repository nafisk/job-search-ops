# Resume Content Optimization Runbook

Give this file and the current resume to an LLM. The goal is to improve the resume's existing content, especially experience bullets. Do not redesign the resume, replace its structure, or rewrite everything unless the person explicitly requests that work.

## Copy-paste starting prompt

```text
Use the Resume Content Optimization Runbook in the attached file.

Start by reading my resume. Assume the existing structure and formatting should remain unless I explicitly ask for a broader overhaul.

Help me improve the content iteratively:
1. Identify the bullets with the greatest opportunity.
2. Ask me short, simple questions to uncover missing ownership, context, technical detail, scale, and impact.
3. Rewrite only the bullets we are currently reviewing.
4. Give me two or three strong options when the wording involves a meaningful tradeoff.
5. Explain the difference briefly and wait for my selection or correction.
6. Never invent experience, metrics, technologies, ownership, or results.

Tell me upfront that reaching the right wording may require multiple iterations. Do not edit the resume file until I approve the wording.
```

### Optional evidence-pack prompt

Use this variation only when the person provides verified supporting material and explicitly authorizes an offline draft:

```text
Use the Resume Content Optimization Runbook in the attached file in EVIDENCE-PACK DRAFT mode.

Read my current resume and the supplied evidence. Produce a complete candidate rewrite and a decision log without waiting for approval between bullets. Do not edit or overwrite my actual resume file.

Label the rewrite CANDIDATE — NOT YET PERSON-APPROVED. For every material change, record the supporting source, important qualifier, unresolved conflict, and reason for the change. Omit unsupported claims. End with the short questions I must answer before any wording can be considered final.
```

## Default behavior

The person may provide only a resume. That is enough to begin.

When evidence is limited:

- Treat the resume as an initial description, not proof of every implication.
- Ask simple questions instead of demanding a large evidence packet.
- Improve one role or small group of bullets at a time.
- Preserve facts the person confirms.
- Mark estimates as estimates.
- Omit unsupported claims.

Tell the person:

> Strong resume wording usually takes a few passes. We can review one role or a few bullets at a time, correct anything that sounds inaccurate, and refine the language until it sounds like you and supports the roles you want.

## Minimal intake

Ask only what is not already clear from the resume:

1. What role and approximate level are you targeting?
2. Which job or section should we improve first?
3. Is there a specific job description, or should this remain generally targeted?
4. Are there any facts, metrics, technologies, or wording that must remain private?

Do not block the work because the person lacks a job description. A target role is helpful, but the LLM can still improve clarity, specificity, and impact.

## Working modes

Use the smallest mode that matches the person's request:

1. **INTERACTIVE REVIEW — default:** Ask targeted questions, rewrite a small set of bullets, and wait for selection or correction. Do not apply wording to the resume file before approval.
2. **EVIDENCE-PACK DRAFT — explicit authorization required:** When the person supplies reliable evidence and asks for an autonomous pass, produce a complete candidate rewrite plus a decision log. Do not change the actual resume file or describe the draft as approved.
3. **APPLY APPROVED WORDING:** Update a new copy of the resume only after the person approves the wording. Preserve the original and validate the result.

Keep these states visibly distinct:

- `CANDIDATE — NOT YET PERSON-APPROVED`
- `PERSON-APPROVED WORDING`
- `APPLIED FINAL`

An evidence-rich autonomous draft skips conversational pauses, not factual verification or human approval of the final wording.

## Bullet-by-bullet method

For each bullet, identify the information already present:

| Element | Question the bullet should answer |
|---|---|
| Action | What did the person personally do? |
| Object | What system, feature, process, customer problem, or deliverable changed? |
| Mechanism | How was it built, improved, analyzed, or delivered? |
| Scope | How large, frequent, complex, or widely used was it? |
| Impact | What became faster, safer, cheaper, clearer, more reliable, or more valuable? |
| Evidence | How does the person know the result occurred? |

Do not force all six elements into every bullet. Use the smallest combination that makes the work clear and credible.

### Ask targeted questions

Ask one to three questions for the current bullet. Prefer questions that unlock several improvements at once.

Examples:

- What did you personally own versus what the team delivered?
- What problem did this solve for the user, business, or engineering team?
- What technologies mattered to how it worked?
- Was there a measurable change in time, cost, reliability, usage, revenue, quality, or scale?
- If there was no formal metric, what observable difference did the work make?
- Who did you work with, and what decision or result came from that collaboration?
- Was this launched, tested, piloted, or left incomplete?

Do not ask the person to guess a metric. A truthful nonnumeric bullet is better than an invented number.

### Generate options only when useful

Provide two or three alternatives when the person must choose between meaningful emphases:

- Technical depth
- Product or customer impact
- Ownership and leadership
- Concision and scanability

Do not generate many cosmetic variations. Recommend one option and explain the tradeoff in one sentence.

Example:

```text
Recommended — emphasizes ownership and measurable impact:
• Migrated two weekly Spark pipelines to AWS EMR, reducing processing time from 48–72 hours to approximately six hours.

Alternative — emphasizes implementation depth:
• Rebuilt two weekly data pipelines in Scala/Spark on AWS EMR and Step Functions, cutting tens-of-terabytes processing to approximately six hours.
```

Then ask the person to select, combine, or correct the options.

## Real before-and-after examples

The following examples are copied from an actual resume optimization process. The company name is omitted because the method should work for anyone. “After” reflects the downloaded final resume, not a guarantee that every remaining word is perfect. The notes explain both the improvement and any issue that still deserved another pass.

### 1. Replace a compressed claim with ownership, mechanism, scale, and a corrected result

**Before**

> Migrated jobs from legacy tooling to AWS EMR, Step Functions, and CDK, cutting runtime from >48h to <5h

**After**

> Migrated 2 weekly Python/Spark data jobs end-to-end from a legacy platform to Scala/Spark on AWS EMR, Step Functions & CDK; cut runtime from 48-72h to ~6h while processing tens of TB

**Why it improved:** The revised bullet identifies the number and frequency of jobs, personal ownership, language migration, orchestration stack, data scale, and the corrected six-hour result.

### 2. Replace personal revenue causality with experiment attribution

**Before**

> Delivered embedding strategy, batching retrieval to cut latency >200ms to ~160ms; recorded $900K in sales

**After**

> Owned end-to-end Java/Spring design of a homepage embedding strategy; batched retrieval + concurrent dot-product scoring cut latency from >200ms to ~160ms; experiment attributed $900K sales + 3.91M clicks

**Why it improved:** The new wording explains the engineering mechanism and uses `experiment attributed` instead of implying the candidate's code independently generated all sales.

### 3. Split two projects that were incorrectly merged

**Before**

> Designed response-audit tooling and AWS CDK automation for 90+ dataset dashboards, cutting ops tickets 20%

This sentence combined an interactive debugging tool with a separate dataset-monitoring system. The final resume split them:

**After A — dataset monitoring**

> Automated on-call monitoring for TPS, Size & Freshness across 90+ dataset across 23 marketplaces; surfaced recurring upstream failures, improving reliability and helping cut active ops tickets by ~15%

**After B — response audit**

> Redesigned a React response-audit tool to visualize recommendation sourcing, filtering & ranking per request across 30+ processors; enabled engineers/scientists to view responses, test changes & debug on-call escalations

**Why it improved:** Each project now has its own mechanism and outcome. The final PDF still contains the grammatical phrase `90+ dataset`; a last proofreading pass should change it to `90+ datasets` without altering the approved substance.

### 4. Bound ownership inside a larger, unfinished cross-team system

**Before**

> Partnered with Customer Insights to build an SQS trigger for next-gen LLM-driven Shopping Guides generation

**After**

> Owned the upstream Java/Guice + CDK publisher for a cross-team, event-driven SQS workflow triggered after async Bedrock classification to support dynamic, LLM-generated Shopping Guides

**Why it improved:** The rewrite identifies the exact owned component, technologies, event sequence, and intended downstream use without claiming ownership of the entire product or saying it launched.

### 5. Distinguish personal work from a team expansion result

**Before**

> Expanded the product catalog from 304 to 453 guides contributing to a 39.7% immediate traffic increase

**After**

> Implemented AWS Lambda category/product allowlists, blocklists & quality checks, supporting the team's expansion from 304 to 453 guides; guide-page traffic rose 39.7% after launch

**Why it improved:** The final wording names the candidate's actual implementation and clearly assigns the broader expansion to the team.

### 6. Add a high-level opener when individual bullets lack product context

**Before**

> No role-level opener. The section started immediately with an evaluation-pipeline bullet.

**After**

> Built foundations for a recursively improving recommendation-ranking model on a distributed service handling 7K TPS: data pipelines, tracing & generative AI evaluation supporting a goal to cut irrelevance 50% by EOY

**Why it improved:** A recruiter can understand the system and how the following projects fit together before reading implementation details. `By EOY` is time-sensitive and should be removed once the date is stale; `supporting a goal` must remain so the target is not presented as a delivered result.

### 7. Improve causality and prompt ownership, then keep validating

**Before**

> Built Bedrock evaluation pipeline for 10K users/week, cutting irrelevance 15%+ via heuristic evaluation prompts

**After from the final PDF**

> Productionized Java/Spark LLM evaluation workflow for 10K users/mo via Bedrock, Step Functions + EMR; integrated 6 scientist-defined prompts to flag an issue in a new experiment and verify a ~15% irrelevance drop

**Why it improved:** The rewrite names the workflow, stack, scientist ownership of the prompts, diagnostic role, and verification mechanism instead of claiming the pipeline directly caused the result.

**Why another iteration was still needed:** The source history conflicted between `10K users/mo` and approximately `10K unique customers per weekly run`. A movement from roughly 20% to 5–6% is about a 14–15 percentage-point drop, not automatically a 15% relative drop. The LLM should ask the person to resolve both facts before treating the bullet as final.

These examples show the intended process: improve the bullet, ask the person to correct the interpretation, revise again, and perform one final factual and proofreading pass after the wording appears finished.

## Writing rules

- Begin with a clear action when the person genuinely owned that action.
- Prefer concrete nouns and mechanisms over adjectives.
- Explain what the work was before stacking technologies.
- Put the strongest differentiating information early.
- Use target-role language only when the experience supports it.
- Separate different projects when combining them would blur ownership or metrics.
- Keep team results, personal actions, goals, estimates, and experiment-attributed outcomes grammatically distinct.
- Preserve the person's natural level of confidence; do not make every bullet sound like sole leadership.
- Optimize for quick comprehension, not a universal word or character limit.
- Translate, expand, or remove company-internal acronyms, dataset names, and tool names unless the intended external audience will recognize them. Explain the capability before naming an obscure internal system.
- Treat more than approximately 30 words or 220 characters as a scanability review trigger, not an automatic failure. Try a shorter version and keep the longer wording only when every retained detail materially improves the target-role signal.
- Prefer one primary technical signal and one primary result or scale signal per bullet. Move secondary defensible details to interview notes when they make the resume harder to scan.

Useful claim language:

| Situation | Safer wording |
|---|---|
| Direct measured result | `reduced`, `increased`, `cut`, `eliminated` |
| Contributed to a larger result | `supported`, `contributed to`, `helped improve` |
| Team delivered the result | `built X supporting the team's Y` |
| Tool detected the change | `identified`, `measured`, `verified` |
| Work enabled measurement | `enabled attribution of`, `standardized measurement for` |
| Experiment reported the result | `experiment attributed`, `treatment recorded` |
| Number is approximate | `approximately`, `about`, `~` |
| Number was a goal | `supporting a goal to`, `targeting` |
| Product was not launched | Describe the completed component and intended use |

## Iteration loop

Repeat this loop until the person approves the section:

```text
Read current bullet
→ identify the biggest missing signal
→ ask short questions
→ draft one recommended rewrite
→ provide alternatives only if useful
→ receive corrections
→ revise
→ obtain approval
→ move to the next bullet
```

After each round, preserve decisions that should carry forward:

- Confirmed facts and metrics
- Preferred terminology
- Rejected wording
- Privacy constraints
- Target-role priorities
- Approved final bullets

Do not make the person repeat those decisions later.

### Evidence-pack draft loop

When explicitly operating in EVIDENCE-PACK DRAFT mode:

```text
Read resume and evidence
→ build a claim and conflict ledger
→ select the strongest target-relevant evidence
→ draft a clearly labeled candidate version
→ run factual, causal, external-language, and scanability checks
→ create a decision log
→ list unresolved questions and meaningful alternatives
→ stop before applying changes
```

The decision log must identify each material change, its evidence, its qualifier or ownership boundary, any excluded unsupported claim, and why the change improves the resume.

## Scope boundaries

Unless explicitly requested, do not:

- Replace the resume template.
- Reorder every section.
- Add a summary, projects, certifications, or other sections.
- Change official titles or employment dates.
- Force the resume to one page.
- Rewrite approved bullets while editing unrelated content.
- Apply changes to the file before approval.

The LLM may flag a structural or formatting concern separately, but it should continue with the requested content work.

## Final content check

Before applying approved wording, verify:

- Every bullet is supported by the person's answers.
- Ownership is clear.
- Metrics have the correct qualifier and scope.
- Technologies are connected to real work.
- Different projects do not accidentally share one result.
- Repeated words and bullet openings are controlled.
- Tense is consistent.
- The strongest recent work receives the clearest explanation.
- The person can comfortably explain every bullet in an interview.
- Internal terminology is translated or justified for the target audience.
- Bullets above approximately 30 words or 220 characters received an explicit compression review.
- Every artifact is labeled as candidate, person-approved wording, or applied final.

If editing a document file, save a new version, preserve the original, render the result, and confirm that the revised bullets still fit the existing layout.

## Completion message

Return:

1. The current state: candidate, person-approved wording, or applied final.
2. Rewritten bullets appropriate to that state.
3. A short list of facts that remain uncertain.
4. Optional next bullets or variants to review.
5. In EVIDENCE-PACK DRAFT mode, a decision log mapping material changes to evidence.
6. The updated file only if the person authorized file editing after approving the wording.
