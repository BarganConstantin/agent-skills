# States every screen family needs

Use this as the starting list in the research brief. Remove what the product does not have, and add
what it needs. Draw every state that stays in both Light and Dark.

## Every data page

- Loading: a skeleton in the final layout, never a lone spinner.
- Empty on first use: what this page will show, and the one action that fills it.
- Filtered with no results: the active filters, and a way to clear them.
- Error: what failed, what to do, and a request ID that can be copied.
- Populated, at real density.
- Stale or degraded: a banner that says what is late and since when. It must not block reading.
- Not found (404) and no access (403). Say who can grant access, without blaming the person.

## Lists and tables

- Hover, focus, and selection; selection only where a bulk action exists.
- A bulk bar, a confirmation that names the objects and the count, and the result.
- Live updates: new items wait behind a "New items" pill. Rows never move while someone reads them.
- An item that is open in a drawer is marked in the list.
- IDs are mono, cut in the middle (`evt_0193…9e07`), and can be copied. Numbers use tabular figures.

## Forms

- Pristine, invalid after the field is left, a server error mapped to its field, submitting, and
  success.
- A counter or a rule shown before the person fails it, for example "12 to go".

## Sign-in and accounts

- Sign in. A wrong email or a wrong password gives one message, so the form does not show which
  part was wrong.
- Too many attempts: say when the person can try again.
- Session ended: sign in again in place, and keep the page and the unsaved input.
- Set a password from an invitation. A link that expired and a link already used are two states,
  each with its own next step.

## Secrets and keys

- The key is shown once. Offer Copy, and Copy as an environment line (`NAME=value`).
- Done stays disabled until the person confirms that they stored the key.
- Closing before the key was copied asks first. Make "Keep it open" the default.
- After that, show only the key's prefix, so keys can be told apart.
- Rotation: two keys are active, the new one is marked, and the next step is said.
- Revoke: a confirmation names the key. In production, the person types the name to confirm.

## Destructive actions

- The confirmation names the object, says what is lost, and says whether it can be undone.
- The safe action is the default. The destructive button has the destructive style and a verb, such
  as "Revoke key", never "OK".

## First run

- A few steps with a visible count ("1 of 3").
- A waiting state. After a short time, show what each failure would look like and what it means.
- A success moment: one line, plus the next step.
- A checklist before production, shown until the first real use. Its steps tick themselves from
  facts the system already has.

## Environments (test and production)

- The two never look alike. Test has a persistent marker; production has none.
- Nothing from one environment appears on a screen of the other.
- A search that misses in one environment can offer the other one, without showing its data.

## Phone

- Navigation in a drawer, cards instead of tables, and targets of at least 44 × 44.
- No keyboard hints, such as "/" or Ctrl+K, on touch layouts.
- The same labels as on desktop.

## Checks across all screens

- One sample dataset, so the same numbers appear everywhere.
- One time range per page, stated once.
- One label for one thing, everywhere: in the navigation, in the titles, in the buttons and on the
  phone.
- Status is never shown by colour alone: it always has an icon and a word.
- A focus ring on every interactive element.
- A contrast check on every text and control token, in both modes.
