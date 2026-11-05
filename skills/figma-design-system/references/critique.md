# Independent critique

A reviewer who did not build the screens finds what the builder no longer sees. Give the reviewer
the work, not your view of it.

## Brief for the reviewer

Fill the angle brackets. Do not add your own assessment.

```text
You are a senior product designer reviewing a UI design before any code is written.

File: <Figma URL>, page "Screens". Use get_screenshot on each frame below, Light and Dark.
Frames: <list of frame names and node IDs>
Product facts the copy must keep to: <bullets from the project's decisions: limits, status codes,
durations, roles, what is stored>
Brief the design follows: <path to the research brief>

Check, for every frame:
1. Hierarchy: what the eye reads first, and whether that is the most important thing.
2. Truth: copy that contradicts the product facts, or promises behaviour nobody decided.
3. Consistency: the same numbers, labels, names, IDs and time ranges across screens.
4. States: missing or contradictory states (empty, loading, error, permission, phone).
5. Dark mode: contrast, colours that change meaning, surfaces that merge.
6. Density and alignment: clipped text, wrapped labels, rows that do not line up.
7. Accessibility: status shown by colour alone, focus, target size.
8. Motion notes: animations without a purpose, keyboard actions that animate.

Return numbered findings. For each one give:
- the screen (frame name);
- the problem, in one sentence;
- why it matters;
- the fix, concrete;
- the severity: high, medium or low.
Then list, separately, what must be kept and why.
Do not edit the file.
```

## Triage

1. Check each finding on the screen itself. A finding that you cannot see on the screen is a
   question, not a fix.
2. Sort the findings into batches, so that fixes do not fight each other:
   - **A, copy and facts:** wrong claims, numbers and terms.
   - **B, sample data and tables:** the dataset, columns, IDs, time ranges.
   - **C, structure and new states:** missing frames, component changes, layout.
3. Fix a batch in the component first, so that every instance gets the fix. Then fix the screens.
4. After each batch, take screenshots of the touched frames in both themes and look at them.
5. Record the result: the number of findings, the number fixed, and what stays open and why. Also
   record what the reviewer said to keep. Do not "improve" those parts later by accident.
