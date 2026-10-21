<div align="center">

<h1>💼 job-search-ops</h1>

<p><strong>Your job search. One guided step at a time.</strong></p>

<p>Improve your materials, find relevant jobs, and prepare applications and recruiter messages for your review.</p>

<p>
  <img src="https://img.shields.io/badge/Format-Markdown-475569?style=flat-square&logo=markdown" alt="Format: Markdown">
  <img src="https://img.shields.io/badge/Setup-guided-16a34a?style=flat-square" alt="Guided setup">
</p>

<p><a href="ONBOARDING.md">Start setup</a> · <a href="#-choose-your-workflow">Choose a workflow</a> · <a href="#-follow-the-flow">See the flow</a></p>

</div>

---

## 📚 Choose your workflow

| Workflow | What you get | What you need to start |
| --- | --- | --- |
| [1. Resume](Resume/README.md) | Clearer experience bullets grounded in your work | Your resume and an AI assistant |
| [2. LinkedIn](LinkedIn/README.md) | A profile audit and reviewed improvements | Your resume and profile content; browser access for live changes |
| [3.1 LinkedIn Job Alerts](<Application Workflow/README.md>) | Jobs from your email alerts, plus shared application tracking and reports | Codex on macOS, Python, selected tracker and Gmail alerts |
| [3.2 Blind 3.5+ Companies](<Blind Company Research/README.md>) | Jobs researched from your chosen rated-company list | Shared jobs tracker/setup, reviewed targets and public web access |
| [4. Application Batches](<Application Batches/README.md>) | Eligible application pages opened for you | Completed shared setup/pilot, saved jobs from either source, confirmed criteria and browser access |
| [5. Recruiter Outreach](<Recruiter Outreach/README.md>) | Screened contacts and unsent LinkedIn drafts | Independent Codex setup, browser access and a separate contact tracker |

## 🚀 Get started

1. **Resume or LinkedIn review:** open that folder's README and give your assistant the entire linked runbook. Supplied files are enough for a content review.
2. **Operational workflows:** download the complete repository or reviewed release ZIP, keep it in a permanent folder, and open it in Codex on macOS.
3. Follow [guided onboarding](ONBOARDING.md). Choose what you want; the agent explains and checks only the tools those choices need.

You do not need to edit JSON or install every tool. Personal settings, resumes, contacts and history stay in a separate private location.

## 🧭 Follow the flow

Start with your current goal. Choose **3.1, 3.2 or both**. They share one jobs tracker: the coordinator saves verified findings before Batches can use them. Dotted arrows show suggested order; Outreach works independently.

```mermaid
flowchart TD
    resume["1. Resume<br/>Improve your resume"]
    linkedin["2. LinkedIn<br/>Improve your profile"]
    alerts["3.1 LinkedIn Job Alerts<br/>Find jobs from your alert emails"]
    blind["3.2 Blind 3.5+ Companies<br/>Research jobs at selected companies"]
    batches["4. Application Batches<br/>Open pages; you apply"]
    outreach["5. Recruiter Outreach<br/>Prepare drafts; you send"]

    resume -.-> linkedin
    linkedin -.-> alerts
    linkedin -.-> blind
    alerts -->|"Shared jobs tracker"| batches
    blind -->|"Shared jobs tracker"| batches
    batches -.-> outreach

    classDef prepare fill:#f9f9f9,stroke:#5d5d5d,color:#0d0d0d
    classDef email fill:#e5f3ff,stroke:#004f99,color:#0d0d0d
    classDef rated fill:#d9f4e4,stroke:#008635,color:#0d0d0d
    classDef action fill:#efe5fe,stroke:#6b3ab4,color:#0d0d0d
    class resume,linkedin prepare
    class alerts email
    class blind rated
    class batches,outreach action
```

Colors use the [OpenAI Apps SDK UI palette](https://github.com/openai/apps-sdk-ui/blob/main/src/styles/variables-primitive.css). Blind starter ratings are historical and not freshly verified. Batches requires the shared installation and its completed pilot; choosing Blind alone does not require LinkedIn alerts.

For operational workflows, use the first-run request in your private setup summary. **Request Batches and Outreach separately:** discovery starts neither. Opening an application page does not mark it Applied. Only selected Application Workflow runs can be scheduled, after verification.

Each numbered workflow links to its setup, run instructions and preferences in the [table above](#-choose-your-workflow). The shared Application Workflow [guide catalog](<Application Workflow/docs/source-map.md>) explains its helpers, detailed procedures and support code.
