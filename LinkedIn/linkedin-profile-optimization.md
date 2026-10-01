# Software Engineering LinkedIn Profile Optimization Runbook

Give this file, the current resume, and target software engineering roles to an LLM that can inspect the person's LinkedIn profile. Tailor the review to the person's specialization, level, and career stage. The workflow is deterministic: log in, audit without changing anything, compare LinkedIn with the resume and goals, approve exact changes, apply them in small batches, and verify every saved field.

## Copy-paste starting prompt

```text
Use the Software Engineering LinkedIn Profile Optimization Runbook in the attached file.

I will log into LinkedIn myself in the browser you are authorized to use. Never ask me to paste my password, authentication code, session cookie, or token.

Begin with a read-only audit. Compare my LinkedIn profile with my resume and target roles. Complete every applicable item in the deterministic checklist and label inaccessible items as unavailable.

Do not change anything during the audit. Return:
1. The current value for every checked field.
2. The problem or opportunity.
3. The exact proposed value or action.
4. The evidence from my resume or answers.
5. Any privacy or notification effect.

Group proposed changes into small approval batches. Apply only the batch I explicitly approve. After each batch, reopen every edited field, verify the saved value, and report the result.
```

## What the person must provide

Minimum inputs:

1. Current resume.
2. Target roles and approximate level.
3. Target locations and acceptable work modes.
4. An authenticated LinkedIn session or a profile export/screenshots.

First identify the person's situation: experienced professional, student/new graduate, career changer, or returning professional. Do not apply experienced-candidate assumptions to someone with limited full-time work history.

Ask these short questions before the audit, skipping anything already answered and making career-stage questions conditional:

- Which software engineering job titles and approximate level are you targeting?
- Which primary specialization fits best: frontend, backend, full-stack, mobile, infrastructure/platform, embedded, or another area? Which related roles are acceptable?
- Which locations and remote, hybrid, or onsite arrangements are acceptable?
- What is your earliest truthful start date? If you are a student or recent graduate, what is your graduation month and year?
- Which engineering roles, internships, projects, open-source contributions, research, or technical leadership activities provide relevant evidence? For students and recent graduates, include relevant coursework or student projects where useful.
- Which licenses, exams, certifications, or programs are earned, passed, registered, scheduled, in progress, or merely planned?
- Should Open to Work be visible publicly or only to recruiters?
- Are your current employer and employment dates safe to update publicly?
- Are there metrics, compensation details, job-search signals, or employers that must remain private?
- Are any code, internal architecture, customer data, security details, or unpublished results confidential or restricted from public disclosure?
- May I make live changes after you approve each batch, or should I only prepare recommendations?

If the person supplies no target job descriptions, use the target titles and resume to begin. Do not block the audit.

## Access and safety rules

- The person logs in personally.
- Never request or store credentials or authentication secrets.
- Start read-only.
- Do not change the profile, settings, messages, connections, follows, applications, alerts, or company-interest signals without explicit approval for that action.
- Do not assume authorization for profile edits includes authorization for messages, applications, posts, invitations, or follows.
- Capture the current value before every approved change.
- State whether a change may notify the person's network or expose job-search intent.
- Preserve unrelated fields and settings.
- If LinkedIn behaves unexpectedly, stop the batch and report what was and was not verified.

## Deterministic audit checklist

Complete the checklist in order. For each item record: `current`, `resume/goal comparison`, `recommendation`, `priority`, `approval required`, and `verification status`.

### 1. Identity and profile basics

- [ ] Name matches the resume and professional identity.
- [ ] Profile photo is current, professional, clearly cropped, and safe to display.
- [ ] Background image is legible on desktop and mobile and does not misuse employer/client branding.
- [ ] Profile URL is clean and usable.
- [ ] Location matches the person's real target market.
- [ ] Industry supports the target role.
- [ ] Current-position display is accurate or intentionally preserved.
- [ ] Displayed education is accurate and appropriate to the person's career stage and target roles.
- [ ] Contact information and portfolio links work.
- [ ] Profile language is appropriate for the target market.
- [ ] Optional identity, workplace, or education verification availability and privacy implications were reviewed.

Do not invent credentials, suffixes, location flexibility, or current employment.
Treat photos, banners, and verification as trust or conversion choices, not guaranteed search-ranking boosts. Never submit identity documents or connect a third-party verification service without separate explicit approval.

### 2. Headline

- [ ] Contains a recognizable target title.
- [ ] Communicates the person's primary specialty.
- [ ] Includes a small number of supported skills or domains.
- [ ] Does not claim an unearned level, current employer, certification, or specialization.
- [ ] For a student or new graduate, distinguishes a target role from a title already earned.
- [ ] Reads naturally to a recruiter.

Create two or three headline options only when the person must choose between different positioning strategies. Recommend one.

### 3. About section

- [ ] First two lines state who the person is and what roles they fit.
- [ ] Strongest recent evidence appears early.
- [ ] Skills are connected to actual work.
- [ ] Target roles are clear without sounding desperate or generic.
- [ ] Metrics and ownership match the resume evidence.
- [ ] No unsupported keyword list, filler, or private information.

The About section may be broader than the resume, but it must not contradict it.

For a new graduate with limited experience, build the About section from the strongest available engineering evidence: internships, completed projects, open-source contributions, supervised research, coursework with a concrete deliverable, technical leadership, and accurately stated credentials. Describe the person's actual contribution. Do not apologize for limited experience or inflate academic work into professional employment.

### 4. Experience

Review every Experience entry:

- [ ] Employer, title, employment type, location, and dates match the resume or an intentional documented exception.
- [ ] The title uses an accurate, recognizable label.
- [ ] The first lines explain the product, customer, or system context.
- [ ] Descriptions communicate personal ownership and important outcomes.
- [ ] Team outcomes, estimates, goals, and attributed metrics are qualified correctly.
- [ ] Technologies listed for the role were actually used there.
- [ ] Recent relevant work receives more detail than old or unrelated work.
- [ ] Training programs, volunteering, clubs, and accelerators are not incorrectly presented as employment.
- [ ] Internships, part-time work, open-source contributions, research, and personal or class projects are classified accurately.

If the resume bullets are too compressed for LinkedIn, expand their context without changing the underlying claims.

### 5. Skills

- [ ] Audit all profile-wide skills for relevance and truth.
- [ ] Confirm core target-role skills are present using LinkedIn's standardized labels when possible.
- [ ] Check which skills are displayed first.
- [ ] Check skills attached to each Experience entry.
- [ ] Add supported programming languages, frameworks, testing practices, databases, infrastructure, domains, and engineering practices relevant to the target roles.
- [ ] Remove or demote irrelevant skills that distort the person's positioning.
- [ ] Do not add skills solely because they appear in a job description.
- [ ] Every selected skill maps to an Experience, Education, Project, Course, or other defensible evidence item.
- [ ] The final skills list is consistent with the selected profile copy and target software engineering roles.

The goal is not to fill every available slot. The goal is an accurate skills graph that supports recruiter filters and the profile narrative.

Select engineering skills based on the person's actual work and target specialization, rather than a universal technology checklist. Tool familiarity, coursework, project use, and production experience are not interchangeable; describe the real level of use.

### 6. Software engineering experience and evidence

Complete this section when applicable:

- [ ] Target software engineering roles, specialization, and approximate level are documented.
- [ ] Earliest start date, employment type, location, work authorization, and sponsorship answers are consistent across LinkedIn, resume, and saved applications; graduation timing is checked when relevant.
- [ ] Evidence is prioritized by relevance, personal contribution, and demonstrated engineering work, with detail appropriate to the person's career stage.
- [ ] Engineering roles, internships, personal or class projects, open-source contributions, and research demonstrate a concrete contribution or deliverable and accurately distinguish independent, team, and guided work.
- [ ] Relevant coursework is included only when it adds missing evidence and names what the person actually produced or learned.
- [ ] GPA, honors, test scores, and coursework are public only by the person's choice and are factually supported.
- [ ] Engineering skills map to a defensible implementation, design, test, investigation, operational responsibility, or other concrete work; public source code is not required.
- [ ] Descriptions and linked artifacts are safe to share and do not expose proprietary code, internal architecture, customer data, security details, or unpublished results without permission.
- [ ] Claims about reliability, latency, delivery time, cost, usage, or quality include supported scope, measurement context, and personal contribution; team outcomes and goals are distinguished from individual delivered results.
- [ ] Licenses, designations, exams, and certifications use the issuer's accurate status language; planned credentials are not presented as earned or in progress.

Do not force engineering metrics or assume every project ran in production. A truthful description of the problem, implementation, tradeoffs, and observed outcome is stronger than a guessed number. Distinguish prototypes, coursework, pilots, and production systems accurately.

### 7. Open to Work and job preferences

- [ ] Target job-title set is accurate and not excessively broad.
- [ ] Locations and relocation preferences are accurate.
- [ ] Remote, hybrid, and onsite preferences are accurate.
- [ ] Employment types are accurate.
- [ ] Availability/start timing is accurate.
- [ ] Start timing and, where relevant, graduation timing agree with Education, the resume, and saved application answers.
- [ ] Visibility is public or recruiters-only according to the person's choice.
- [ ] Compensation preferences are current and private where applicable.

Explain the visibility choice before changing it. Do not enable a public frame without explicit approval.

### 8. Resume sharing and application data

- [ ] Inspect resumes saved or shared with recruiters.
- [ ] Identify stale, duplicate, or contradictory versions.
- [ ] Confirm which resume should remain current.
- [ ] Check whether resume-data sharing is enabled according to the person's preference.
- [ ] Check saved application answers for outdated contact, salary, location, sponsorship, or work-authorization data.
- [ ] Record the number and last-use date of saved resumes; LinkedIn currently documents up to four, but verify the current account and help page at audit time.
- [ ] Confirm which resume LinkedIn currently preselects for applications.
- [ ] Review the resume-data-sharing control and the setting governing use of application data for product improvement.

Never delete a saved resume or application record without approval.

### 9. Featured and supporting sections

- [ ] Featured items support the target role and all links work.
- [ ] Education fields are accurate.
- [ ] Certifications are current and genuine.
- [ ] Projects demonstrate relevant work rather than unfinished placeholders.
- [ ] Courses, organizations, honors, awards, languages, publications, test scores, volunteering, and recommendations are individually audited when present or useful.
- [ ] Services and Career Break sections are accurate when present and marked not applicable when irrelevant.
- [ ] Recommendations support the target engineering roles and come from people who directly observed the work.
- [ ] Old student or new-graduate content does not dominate an experienced profile.

For a new graduate, relevant student evidence may appropriately carry more weight; remove it only when stronger experience replaces it. Featured controls may vary by account, region, subscription, or rollout. Mark unavailable controls as unavailable rather than forcing a workaround.

Do not require optional sections merely to make the profile look complete.

### 10. Privacy, visibility, and notifications

- [ ] Public-profile visibility matches the person's preference.
- [ ] Network notification settings are understood before edits.
- [ ] Email, phone number, birthday, and other contact data have appropriate visibility.
- [ ] Profile-viewing mode is understood before research or outreach.
- [ ] Company-interest signals and follows are treated as separate actions.
- [ ] No private job-search detail is added to public text.
- [ ] Visible posts, comments, reactions, and other Activity do not disclose confidential information or contradict the target identity.
- [ ] Engineering content and linked artifacts disclose no restricted code, internal architecture, customer data, security details, or unpublished results; performance claims are supported and public-safe.

### 11. Optional job-search infrastructure

Treat these as separate actions from profile editing:

- [ ] Target searches use the approved software engineering titles, level, and related roles.
- [ ] Locations, experience level, employment type, industry, and date-posted filters are appropriate.
- [ ] Existing saved searches and job alerts are current and nonduplicative.
- [ ] Proposed new alerts have an exact query, filters, frequency, and notification channel.

Do not create, modify, or delete a job alert or saved search without explicit approval.

### 12. Search and analytics baseline

When available, record before editing:

- [ ] Search appearances and reporting period.
- [ ] All appearances and reporting period.
- [ ] Profile views and reporting window.
- [ ] Recruiter views and reporting window.
- [ ] Job titles the person was found for.
- [ ] Searcher companies and titles.
- [ ] Qualified recruiter outreach.
- [ ] Wrong-role or wrong-location outreach.

Unavailable or paywalled fields stay `unavailable`; never estimate them.

## Resume-to-LinkedIn comparison

Create a compact consistency table:

| Field | Resume | LinkedIn | Decision |
|---|---|---|---|
| Name |  |  |  |
| Target identity |  |  |  |
| Employers and titles |  |  |  |
| Dates |  |  |  |
| Locations |  |  |  |
| Skills |  |  |  |
| Metrics and claims |  |  |  |
| Education and certifications |  |  |  |
| Start timing and graduation timing, if relevant |  |  |  |
| Work authorization and sponsorship answers |  |  |  |
| Portfolio links |  |  |  |

The two assets should agree on facts but do not need identical wording. The resume is compact evidence; LinkedIn can provide more context and structured discovery fields.

## Recommendation format

Return each recommendation as:

```text
ID:
Priority: P0 / P1 / P2
Field:
Current value:
Problem:
Resume or user evidence:
Exact proposed value or action:
Privacy/notification effect:
Approval status: proposed / approved / rejected
Application status: not applied / applied / verified / failed
```

Priorities:

- `P0`: factual inconsistency, important recruiter filter, privacy risk, or stale resume/application data.
- `P1`: headline, About, Experience, skills, or other meaningful discovery/conversion improvement.
- `P2`: optional proof, polish, recommendations, photo, Featured, or supporting sections.

## Apply changes in small batches

Recommended order:

1. Identity, titles, dates, location, industry, and privacy decisions.
2. Open to Work, job preferences, and resume sharing.
3. Skills and Experience-linked skills.
4. Headline, About, and Experience descriptions.
5. Featured, education, projects, recommendations, and optional sections.
6. Optional saved searches and job alerts under their own approval.

Before each batch:

- Show every exact change.
- State anything public or notification-sensitive.
- Obtain explicit approval.

After each batch:

- Reopen each edited field.
- Compare it with the approved value.
- Verify links and formatting.
- Record applied, verified, failed, or unavailable.
- Stop if an unrelated field changed.

## Completion checklist

- [ ] Every applicable audit item has a recorded result.
- [ ] LinkedIn and the resume agree on core facts or document intentional exceptions.
- [ ] Target titles, location, industry, Open to Work, and skills are accurate.
- [ ] Headline and About communicate one clear target identity.
- [ ] Experience descriptions are truthful and understandable.
- [ ] Saved resumes and application data are current.
- [ ] Engineering experience, project contributions, and start timing are accurate; education and graduation timing were checked where relevant to career stage.
- [ ] Engineering confidentiality, performance claims, and credential status were checked where applicable.
- [ ] Privacy and notification choices match the person's instructions.
- [ ] Every approved change was reopened and verified.
- [ ] Analytics baseline and change date were recorded.
- [ ] No messages, applications, invitations, follows, or posts occurred without separate approval.
- [ ] Copy-ready profile text is separated from review notes, questions, and change logs.

Return the completed checklist, before/after values, unresolved items, and the date of the next measurement review.
