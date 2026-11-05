# Records and hand-off

The Figma file is the design. These files and issues let people review it and build from it. Get
the counts from the file with a script; never write them from memory.

## Summary report

Save it as `reports/<date>-<topic>-design-system.md`, with the status **draft** until the owner
approves.

1. **What changed since the last version:** foundations, components, screens and prototype, with
   counts.
2. **How to review it:** where to start, how the Screens page reads, the prototype flows, and the
   annotation kinds.
3. **The file, page by page:** a table of each page, what it holds, and its node ID.
4. **Foundations:** the variable collections with their counts; the derived steps and why each is
   needed; type; effects; icons.
5. **Components:** the groups, and the rules the library keeps.
6. **Page anatomy:** measurements for developers.
7. **Screens:** a table of each flow and its states, using the frame names.
8. **Motion:** the signature moments, durations, easing, what never animates, and reduced motion.
9. **What the design does not decide:** pending decisions with the screens they affect, the
   proposals, and the questions for the designer.
10. **How it was checked:** the visual passes, the critique (findings, fixed, open), the copy checked
    against the documents, and the sweeps (no hard-coded colour, every text on a style).
11. **After approval:** export to `design/`, build from tokens and components, and build the
    screens that wait on decisions last.

## Review issue for the owner

```markdown
The <product> UI is designed in Figma: <URL>. It is a draft; nothing is built until you approve it.
Summary: <link to the report>.

## How to review (about 20 minutes)
1. Open the Cover page.
2. On Screens, each row is one flow: Light on the left, Dark on the right. Blue notes are proposals;
   red notes are questions for you.
3. Press Play to click through the flows.

## Questions only you can answer
- [ ] **Q-O1.** <question, what it changes, and the screen it affects>

## Proposals to accept or reject
- <proposal> (<screen>)

## When you approve
The frames are exported to `design/` and the build starts. Screens that wait on an answer are built
last.
```

Label it as an owner task. Link it from the file's Cover page.

## Issue for the brand designer

List each question (Q-D1…) with its evidence, such as hue angles, contrast ratios or the surfaces
where it fails. Then list the derived steps, with their hex values and the need each one meets. Ask
the designer to confirm, replace or name each step, and to add it to the kit's tokens in the next
release.

## Notes to keep for the next session

When the agent has a memory, save:

- the file key;
- the page IDs, and the IDs of the most used components;
- the screens grid rule;
- any new Plugin API trap.

Never save the screenshot URLs: they are private and expire.
