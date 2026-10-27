# Growth research: evidence before more skills

*Research checkpoint: 27 October 2026. Scope: only `BarganConstantin/agent-skills`.*

## What the data supports

| Observation | Evidence | Decision for our repository |
| --- | --- | --- |
| Distribution is highly concentrated: about 375 skills (0.04% of the registry) accounted for 62% of installs, and nearly half were installed only once | [Vercel: State of agent skills, 25 Sep 2026](https://vercel.com/blog/state-of-agent-skills) | Adding many near-duplicate `SKILL.md` files is not a viable stand-alone growth strategy |
| General-purpose agent workflows account for about 14.8% of classified installs, while software engineering is an oversupplied category per install/listing | [Vercel category analysis](https://vercel.com/blog/state-of-agent-skills) | Favor portable, differentiated workflows like trustworthy handoffs over another generic debugging checklist |
| The CLI leaderboard is based on aggregated **install telemetry**, not verified successful tasks or unique developers | [Official skills.sh docs](https://skills.sh/docs), [Vercel methodology](https://vercel.com/blog/state-of-agent-skills) | Keep synthetic/CI installs opted out with `DISABLE_TELEMETRY=1`. Track independently confirmed attempts separately from GitHub stars |
| Public repo pages can be customized by `skills.sh.json`, but its updates only appear after **genuine** CLI installs with telemetry enabled | [Official customization reference](https://skills.sh/docs/customize) | Defer registry-page customizations and install-count badges until the public listing is verified. Never simulate adoption |
| Public skills.sh API now requires Vercel OIDC bearer authorization | [Official skills.sh API reference](https://skills.sh/docs/api) | Do not claim registry install counts from unauthenticated requests or invented leaderboard rankings |
| Maintainer inactivity and unresolved social interaction are correlated with OSS project attrition; merely increasing commits does not establish resilience | [2026 research on 3,472 matched OSS projects](https://www.sciencedirect.com/science/article/pii/S0164121226001755) | Prioritize timely feedback and independently reproducible user reports over a large inventory of unvalidated skills |

### A growth case study worth treating skeptically

The [Infrasity MemClaw case study](https://www.infrasity.com/case-studies/github-marketing-case-study) reports that technical demo repositories, genuine Reddit conversations and curated listings accompanied an increase from 17 to 274 stars over six weeks. Those are **agency-reported marketing results**, not a randomized or independently audited causal experiment. We should borrow the *testable hypothesis* (authentic working examples + relevant discovery surfaces), **not copy its claimed growth rates** or spam communities.

## Current state and decision

As measured using GitHub's repository API on 27 Oct 2026: **4 stars, 0 forks, 3 Agent Skills**. These are a snapshot, not a live counter. The maintainer profile, ccdeck and other repositories are out of scope.

Our product catalog is [First User Audit](../skills/first-user-audit/SKILL.md), [Handoff with Receipts](../skills/handoff-with-receipts/SKILL.md), and [API Contract Drift](../skills/api-contract-drift/SKILL.md).

**Focus: help a stranger discover, install, obtain a useful result, and give specific feedback.** Next best change is not automatically a fourth skill.

## Prioritized experiments (one change at a time)

| Order | Hypothesis | Implementation / metric | What counts as failure? |
| --- | --- | --- | --- |
| 1 | Actual GitHub installation may fail although local install smoke passes | Use [public GitHub install smoke](../.github/workflows/public-install.yml) on main and weekly; check discovery + three skills in Codex/Claude Code with exact file match; telemetry disabled | Public install or file integrity fails. Repair before marketing |
| 2 | Unfamiliar users abandon setup before trying any workflow | Invite up to five independent opt-in developers to follow the [practice lab](practice-lab.md) and [feedback form](../.github/ISSUE_TEMPLATE/first-run-feedback.yml). Record all failures, browser prerequisites and first successful runs | No voluntary feedback after outreach; or most attempts stop at installation/browser setup. Improve specific blocker |
| 3 | Proof is more convincing than a speculative slogan | After opt-in user evidence, publish **one** permissioned, safely redacted real-project case study, including missed defects and limitations | No reproducible independent result. Keep controlled fixtures separate and do not market them as validation |
| 4 | More niche skill names increase discovery only if each solves a distinct job | Build another skill **only** after a repeated real request or demonstrated demand and a functional evaluation plan | No validated users, overlapping capability, copied code, unclear license or untestable result → reject candidate |
| 5 | Registry/listings could expand qualified discovery | Check whether the project is listed; submit only to channels where explicitly permitted and track accepted listings, not submitted counts | No acceptance/qualified visits, permissions missing, or listing requires manufactured activity → stop |

### Measurement contract

Record GitHub stars/forks with time and link to source, new user reports (including failed attempts), real verified installs only when reported by independent testers, and first-use feedback. **Do not equate** stars, installs, completed browser checks, qualified user feedback and business conversion. Avoid fabricated testimonials, synthetic CLI leaderboard installs, bought stars, mass unsolicited outreach, or claiming benchmark advantages without controlled runs.

Before changing strategy, ask: (1) what observable user friction are we fixing? (2) what is the cheapest test? (3) which real outcome would make us stop? Avoid repeated README text edits that do not affect usability.

## Review rhythm

At each scheduled review: read current issues and CI; validate current GitHub counts; check recent changes to the official Agent Skills specification, skills CLI, and skills.sh docs **only where relevant**; assess one relevant competitor's concrete feature/installation path and its license; decide one hypothesis and test it. Skip code changes if none would increase real user value. Keep a dated research log rather than re-collecting superficial ideas. Never modify another repository.

No external posts, submissions or messages without separate explicit authorization. The only allowed writable repository is `BarganConstantin/agent-skills`.


## Homepage conversion experiment — 2026-10-27

**Hypothesis:** developers are more likely to try a skill after seeing a reproducible task/result and a clearly separated install choice in the first screen. This is **untested for this repository** and does not imply a measured conversion rate.

**External examples inspected:**

- [Matt Pocock's engineering skills](https://github.com/mattpocock/skills): concise product viewpoint and prominent **30-second installation** rather than opening with exhaustive reference material.
- [Addy Osmani's agent skills](https://github.com/addyosmani/agent-skills): prominently lists installation commands, specific per-skill examples and independent guide references.
- [Superpowers](https://github.com/obra/superpowers): explains what a session *does* before listing many installation options.
- [GitHub Octoverse 2026 analysis](https://github.blog/news-insights/octoverse/what-the-fastest-growing-tools-reveal-about-how-software-is-being-built/): emphasizes lower-friction setup and reproducible results; this is industry context, not proof that shorter README pages generate stars.

**Implemented experiment:** Replaced a ~11.7k-character README heavily dominated by First User Audit with a ~5.3k-character catalog homepage. Above the install section, visitors now see a ready-to-run **synthetic API regression sample** (using fixtures with three verified checks); all detailed browser QA documentation and original controlled imagery remain in [docs/first-user-audit.md](first-user-audit.md). Added test coverage for links, preserved content and real commands.

**What we will measure:** Github stars/forks and independent first-run feedback after publication. Github does not expose traffic views through the connected read-only API available here, so **do not claim view-to-star conversion or impressions**. If actual users report confusion, revisit layout based on specifics rather than repeated copywriting guesses. Do not manufacture visits through bots.
