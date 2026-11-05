---
name: figma-design-system
description: Designs a product's UI in Figma before any code, the way a senior product designer would. It works through the Figma MCP in one file. Research first, then foundations (variables for Light and Dark, type, icons), a component library with every state, measured page anatomy, every screen and state in both themes, motion, an independent design critique, fixes, a visual check of every frame, and a written record with the open questions for the owner. Use when the user says "design it in Figma first", "build a design system in Figma", "every screen in light and dark", "do the UI before we code", "design review in Figma", "fă design system în Figma", "construim UI-ul în Figma", or gives a Figma file and asks for a product's screens.
compatibility: Needs the Figma MCP server with edit access to one Figma file (use_figma, get_screenshot, create_session). Optional - an agent tool for the independent critique, curl and Pillow to tile screenshots.
---

# figma-design-system: design the whole UI in Figma first

The output is a Figma file that a developer can build from without guessing, and a short written
record in the project's repository. The file holds:

- the foundations;
- the component library;
- every screen and state in Light and Dark;
- the motion.

Work in phases. Finish each phase's exit check before you start the next one. Do not ask the user
to confirm between phases. Ask only for decisions that are theirs.

## Hard rules

1. **Design first, code later.** Write no product code until the owner approves the design.
2. **One Figma file.** Use only the file the user gives. Never publish it to the Community or share
   it by a public link. Every other deliverable is a local file in the repository.
3. **Never invent a product decision.** Draw a value that no project document records as an
   annotation of kind *Proposal* or *Pending decision*, and put the question to the owner. Screen
   copy keeps to the project's documented facts: status codes, limits, durations, retention, roles.
4. **Use the brand kit exactly as delivered.** Never recolour or re-trace a logo, mascot or icon.
   When the kit has no token for a need, derive a step from its own ramps and mark it *derived*.
   Then ask the designer to confirm or replace it.
5. **All colour is a variable.** No screen holds a hard-coded colour. Light and Dark come from the
   same frames through variable modes.
6. **Check by looking.** After every change, take a screenshot of each frame it touched and look at
   it. A script that succeeded proves nothing about how the frame looks.
7. **Annotations are review notes, not product UI.** They sit under the frames as a component with
   three kinds: Note, Proposal, Pending decision.

## Session setup

1. Get the file key from the URL. Call `create_session` once and pass its ID on every call.
2. Before the first `use_figma` call, load the Figma MCP's `figma-use` skill. Load
   `figma-generate-library` too when you build the library.
3. Read [references/plugin-api.md](references/plugin-api.md). It has the script preamble, the
   recipes, and the traps that cost hours.
4. Read the project's product notes, decisions and brand kit. List the facts the copy must keep to.

## Phases

### 1. Research

Study five to eight products that solve the same job. Look at their layout, density, states, copy
and motion. Use a screen archive MCP when you have one. Write a brief in the repository, in
`reports/<date>-<topic>-design-research.md`, with:

- principles, each with the evidence behind it;
- the states that each screen family needs (start from [references/states.md](references/states.md));
- the questions for the owner, numbered (Q-O1…);
- the questions for the brand designer (Q-D1…).

*Exit:* every later design choice can point to a line in the brief.

### 2. Foundations

Make these collections, in this order:

1. Primitives: the kit's colours, with derived steps marked.
2. Semantic UI tokens with Light and Dark modes: `bg`, `border`, `text`, `action`, `status`,
   `chart`, `overlay`.
3. Dimensions: spacing and radius.
4. Motion: durations and easings.

Then add text styles (UI and mono, tabular numbers), effect styles (elevation and focus ring), and
one icon set in one line style.

Check the work:

- contrast for text and controls, in both modes;
- chart palettes with a colour-vision validator, in both modes;
- that status hues never double as chart series.

*Exit:* the Foundations page documents every token, and no value outside the variables is needed.

### 3. Components

Build each component with all its states as variants. That means default, hover, pressed, focus,
disabled, loading, error and selected, as they apply. Bind everything to tokens, so each component
works in both modes. Group the library: status and identity, actions, inputs, navigation, feedback
and overlays, data.

*Exit:* every repeated element on a screen is an instance. A one-off frame on a screen is a defect:
make it a component or reuse one.

### 4. Page anatomy

On a Patterns page, measure the shell for developers:

- gutters, sidebar and bar heights, content padding;
- table row heights;
- overlay widths and the stacking order;
- focus rings and target sizes;
- breakpoints, as a proposal.

*Exit:* a developer can lay out a page from this page alone.

### 5. Screens

- Give each flow one row on the Screens page, numbered 01, 02 and so on. Number its states 01b,
  01c, then 03c2 for a state inserted later. Light sits on the left of each pair and Dark on the
  right.
- Draw every state the brief lists: empty, loading, error, filtered with no results, success,
  confirmations, permission denied, not found, first run, and the phone layout.
- Use **one sample dataset** across all screens, so the numbers on an overview, a list and a detail
  page agree.
- Build and check the Light frame first. Then make the Dark copy by setting the frame's variable
  mode (see the recipe).
- Put an annotation under any frame that needs a reason, a proposal or a pending decision.

*Exit:* every flow is clickable as a prototype, and every state from the brief has a frame in both
themes.

### 6. Motion

- Storyboard the few signature moments. Put every other transition in one table: trigger, property,
  duration, easing.
- Entering elements use a strong ease-out. Elements that move on screen use ease-in-out. Never use
  ease-in.
- Never animate an action started from the keyboard.
- Never move rows while someone reads them: new items wait behind a pill.
- Give each moment a reduced-motion version.

*Exit:* every animation has a written purpose.

### 7. Independent critique

Start a reviewer with a fresh context: another agent, or a person. Give it the file, the list of
frames and the project's facts, and never your own conclusions. Use the brief in
[references/critique.md](references/critique.md).

Sort the findings into batches:

- A, copy and facts;
- B, sample data and tables;
- C, structure and new states.

Fix one batch at a time. Record what the reviewer said to keep, and keep it.

*Exit:* every finding is fixed, or written down as open with a reason.

### 8. Visual check

For each frame you touched, take a screenshot in Light and in Dark. Tile the screenshots when there
are many, then read them as a designer would. Look for:

- clipped or wrapped labels;
- misaligned rows across cards;
- one-off styles;
- leaks between environments;
- stale numbers;
- overlapping frames on the canvas.

Fix what you find, then take the screenshots again.

*Exit:* a full pass finds nothing new.

### 9. Record and hand-off

Use the templates in [references/records.md](references/records.md):

- **A summary report in the repository:** counts, the screens table, what the design does not
  decide, how it was checked, and what happens after approval.
- **A review issue for the owner:** how to review in about 20 minutes, the questions as checkboxes,
  and the proposals to accept or reject.
- **An issue for the brand designer:** the missing tokens and the derived steps.
- **On approval:** export the approved frames as PNG to the repository's `design/` folder. Then
  build from the tokens and the components.

## Working style

- Long work continues without a pause between phases. Send a short status line from time to time.
  When the user asked for notifications, also send one at each milestone and whenever you need them.
- Before you build something you think the product does not need, say so, even when it was asked
  for.
- Write all copy in plain, short sentences: one idea per sentence, active voice, no filler.
