# Figma Plugin API: recipes and traps

These notes come from building a full design system through `use_figma`. Read them before the first
script.

## How the tool behaves

- **One script runs as one transaction.** If it throws, nothing it did is kept. Write scripts so that
  you can run them again without harm: check whether a node already exists before you create it.
- **A failed transport ("transport dropped") means nothing was committed.** Read the state back,
  then run the script again.
- **Keep return values small.** A return value over about 48 KB fails. Return IDs and short strings.
  Never walk the whole document tree and return it.
- **Switch to one page per call** with `await figma.setCurrentPageAsync(page)` before you read or
  change nodes on it.
- **Fonts:** load every font before you set characters or a text property.
- **Text styles:** use `setTextStyleIdAsync`. The sync setter fails.
- **Components:** `figma.getLocalComponentsAsync` does not exist. Use
  `page.findAllWithCriteria({ types: ['COMPONENT'] })` or `['COMPONENT_SET']`.

## Preamble

```js
await Promise.all([['Inter','Regular'],['Inter','Medium'],['Inter','Semi Bold'],
  ['JetBrains Mono','Regular'],['JetBrains Mono','Medium']]
  .map(([family, style]) => figma.loadFontAsync({ family, style })));
const VARS = await figma.variables.getLocalVariablesAsync();
const V = {}, VI = {}; for (const v of VARS) { V[v.name] = v; VI[v.id] = v; }
const UI = (await figma.variables.getLocalVariableCollectionsAsync()).find(c => c.name === '<UI collection>');
const LM = UI.modes.find(m => m.name === 'Light').modeId;
const DM = UI.modes.find(m => m.name === 'Dark').modeId;
// Resolve an alias chain to a raw colour, for the paint's fallback value.
const rl = v => { let val = v.valuesByMode[LM] ?? Object.values(v.valuesByMode)[0]; let g = 0;
  while (val && val.type === 'VARIABLE_ALIAS' && g++ < 8) { const t = VI[val.id];
    val = t.valuesByMode[LM] ?? Object.values(t.valuesByMode)[0]; } return val; };
// A solid paint bound to a variable: it follows the frame's mode.
const paint = name => { const v = V[name]; const c = rl(v);
  return figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: c.r, g: c.g, b: c.b } }, 'color', v); };
const S = {}; for (const s of await figma.getLocalTextStylesAsync()) S[s.name] = s;
```

Bind padding and radius to dimension variables as well, with `node.setBoundVariable('paddingLeft',
V['space/4'])` and `'topLeftRadius'` and so on.

## Recipes

**Dark copy of a frame.** Make the copy and set the mode. Every bound paint follows it:

```js
const D = L.clone(); page.appendChild(D);
D.name = L.name.replace(/Light$/, 'Dark');
D.setExplicitVariableModeForCollection(UI, DM);
D.x = L.x + 1560; D.y = L.y;
```

**Replace text without losing mixed styling.** For text that has more than one font or style:

```js
for (const fn of t.getRangeAllFontNames(0, t.characters.length)) await figma.loadFontAsync(fn);
const i = t.characters.indexOf(a);
t.insertCharacters(i + a.length, b, 'BEFORE'); t.deleteCharacters(i, i + a.length);
```

To set one span in mono, use `await t.setRangeTextStyleIdAsync(start, end, S['Code/Small'].id)`.

**Dialog over a screen.**

1. Clone a full-frame scrim into the screen. Set it to `layoutPositioning = 'ABSOLUTE'` at 0,0.
2. Add the dialog instance, also ABSOLUTE.
3. Centre it over the content area, not over the whole frame. With a sidebar of width `s`, set
   `x = (W - w) / 2 + s / 2` and `y = (H - h) / 2 - 40`.

For a scrim, use a plain paint with opacity. A paint bound to a variable plus `opacity` rendered
opaque.

**Annotations linked to frames.** Make an instance of the annotation component and fill its text
property. Then link it to its frame, so that an arrange script can move it with the frame:

```js
a.setSharedPluginData('<namespace>', 'for', frame.id);
```

**Screens grid.** Put row `n` at `y = (n - 1) * 1300`. Put state `k` at `x = k * 3120`, with Dark
at `+1560`. Sort state codes as strings: `'' < 'b' < 'c' < 'c2' < 'd' < 'd2'`. When a frame moves,
move its annotations by the same amount. Place annotations in a row under the frame, at
`y + height + 32`, 456 apart.

**Screenshots.**

1. `get_screenshot` returns a short-lived URL. Download it with `curl -fsSL -o file.png "<url>"`.
   Python's urllib failed on these URLs.
2. To compare many frames, tile them into one image with Pillow, for example two columns with an
   8 px gap. Then read that image.
3. Remove the downloads when you are done, because the URLs are private.

## Traps

| Symptom | Cause | Fix |
|---|---|---|
| An icon turns black after a swap or a variant change. | An instance swap or a variant switch drops the colour overrides on nested strokes. | Recolour the icon's vectors after every swap. |
| A nested button keeps its old state after a variant switch. | Overrides from the old variant can survive. | Set the nested instance's own property explicitly. |
| A text collapses to 1 px high. | FILL height in a horizontal row, and the parent became vertical. | Set `layoutSizingVertical = 'HUG'`. |
| `TypeError` from `findAll`. | Called on a TEXT node. | Check `'findAll' in node` first. |
| "Cannot unwrap symbol". | Setting characters on mixed-font text. | Load `getRangeAllFontNames`, then insert and delete ranges. |
| "Unloaded font" on `textAutoResize`. | The node's font was not loaded. | Load all fonts first. |
| A header cell stays FILL after an insert. | The sizing was set before the node had a parent. | Set the sizing and resize after `appendChild` or `insertChild`. |
| A node does not keep a custom property. | `node.__x = …` throws. | Keep state in variables, or in shared plugin data. |
| `variantOptions` is undefined. | A guessed property name. | Read `componentPropertyDefinitions` first; names are exact, such as `Type` or `Label#30:0`. |
| "24 h" breaks across two lines on a narrow card. | A normal space. | Use a non-breaking space (` `). |
| Empty top-level frames pile up at 0,0. | Leftovers from failed clones. | Remove empty, unnamed-purpose frames at the origin during the arrange pass. |
