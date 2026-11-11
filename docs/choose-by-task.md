# Choose by task

[Installable skills](../README.md#installable-skills) · [Saved references](library.md)

Start with the job you want done. Use one focused skill or reference first;
adding every available workflow usually adds work without answering the question.

## I want my agent to do something

These skills are included in this repository. Install the one you need using
the [README commands](../README.md#install), then name it in your request.
Tools such as browsers and Figma must be connected separately where required.

| Your task | Skill | Example request |
|---|---|---|
| Resume work and understand the current state | [compass](../skills/compass/SKILL.md) | “Use compass: where did we stop and what is next?” |
| Check whether a new user can reach a useful result | [first-user-audit](../skills/first-user-audit/SKILL.md) | “Use first-user-audit on this isolated local preview.” |
| Identify tests that can safely be removed | [prune-tests](../skills/prune-tests/SKILL.md) | “Use prune-tests on this branch’s new tests. Show evidence before deleting anything.” |
| Design the UI in Figma before implementation | [figma-design-system](../skills/figma-design-system/SKILL.md) | “Use figma-design-system for this product’s components, states and themes.” |
| Learn a topic through questions and practice | [socratic-tutor](../skills/socratic-tutor/SKILL.md) | “Use socratic-tutor to teach me SQL joins.” |
| Find a useful project already saved in the library | [reference-library](../skills/reference-library/SKILL.md) | “Use reference-library: show saved React UI resources and explain when each helps. Do not install them.” |

Installing a skill adds instructions. It does not provide missing tools or
permission to change accounts, publish code or run tests against production.

## I want a component, tool or reference

The [Reference Library](library.md) contains external sources you can investigate.
They are not included as installed dependencies in this repository.

| Decision | Use | Why / boundary |
|---|---|---|
| Choose a React component system | [Astryx](https://astryx.atmeta.com/components), [HeroUI](https://heroui.com/en/docs/react/getting-started/agent-skills) | Evaluate components, themes and framework compatibility before adopting one. |
| Own and customize component source | [shadcn/ui](https://ui.shadcn.com/docs/components) | Build your own component system from editable source; maintain local changes and review upstream updates deliberately. |
| Find a visual example or template | [21st.dev](https://21st.dev/) | Browse for a specific interaction or page; check each item’s rights and dependencies before copying. |
| Improve visual direction and page composition | [Hallmark](https://github.com/Nutlope/hallmark), [AI Design Skills](https://github.com/elayadesign/ai-design-skills) | Design guidance and workflows, rather than a replacement for your existing component API. |
| Compose and inspect local services | [Aspire](https://github.com/microsoft/aspire) | Distributed app development and observability. |
| Build backend agent workflows | [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | Agent orchestration and hosting; check the current runtime and API. |
| Review API compatibility | [oasdiff](https://github.com/oasdiff/oasdiff) | Compare OpenAPI specifications for breaking changes. |
| Drive a browser for testing | [Playwright MCP](https://github.com/microsoft/playwright-mcp), [Playwright CLI](https://github.com/microsoft/playwright-cli) | Browser tooling; use a safe local or isolated environment. |
| Structure planning, implementation and verification | [Superpowers](https://github.com/obra/superpowers), [Spec Kit](https://github.com/github/spec-kit) | Development workflows; choose according to task and host capabilities. |

For detailed prerequisites, review dates and cautions, use the
[categorized library](library.md) or its offline explorer.

## Find something quickly

On GitHub, use the category links in [the library](library.md#browse-by-area).
For interactive search, clone this repository and open
`docs/library-explorer.html` in your browser. It works offline; category filters
and text search combine. Press `/` to focus search, or use Tab to reach controls.

From the repository root, the offline CLI also works without installation:

```bash
python3 skills/reference-library/scripts/library.py browse ui-ux
python3 skills/reference-library/scripts/library.py search "React components" --category ui-ux
python3 skills/reference-library/scripts/library.py show astryx
python3 skills/reference-library/scripts/library.py show 21st-dev
```

## Keep it useful

Save new discoveries once in the canonical catalog, with the original URL,
the job they help with, prerequisites, cautions and the review date. Regenerate
both library views using `python3 scripts/render_library.py --write`.
The [curation rules](../skills/reference-library/references/curation.md) explain
the fields. Installed copies do not sync automatically; update them deliberately.

Source notes are not a guarantee of current behavior. Before adopting a project,
read its official documentation and license again. A saved link alone does not
authorize installation or reuse of its assets.
