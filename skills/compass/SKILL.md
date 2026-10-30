---
name: compass
description: Short orientation at the start or in the middle of a coding session. It says where we are, what we have and what comes next, and the user does not have to explain anything. It reads the conversation first, then live read-only state - the git branch and its commits against the target, the open merge or pull request with its checks and unresolved threads, the Jira ticket with its subtasks, and any background job that still runs. It answers in about 150 words in a fixed shape (Where we are / What we have / What I propose next, plus one question that starts the next step), in the user's language, with Simplified Technical English rules. Strictly read-only. Use when the user says "/compass", "where are we", "status", "recap", "what's next", "where did we stop", "in short words", "unde suntem", "ce avem", "ce urmează", "unde am rămas", or opens a session and asks for orientation.
---

# compass: where we are, what we have, what comes next

This skill replaces the question "so where are we, what do we have and what do we do next, in short
words". The user usually gives no argument. Answer at once. Do not ask the user anything before the
answer.

## Hard rules

- **Read-only.** No commit, stage, stash, checkout, push, `git fetch`, build, test or file edit. No
  write to the merge or pull request, and no write to the tracker. Do not start, stop or wait for a
  background job. Report and propose, nothing else.
- **Never print a token.** `scripts/state.py` reads them from the environment and never prints them.
- **Scoped commands only.** Do not run a search over the whole repository; on a large one it times out.
- **Skip silently.** When a token is missing or a call fails, drop that source. Do not mention the
  failure.
- **Style override.** This answer ignores every compression style the session uses.

## 1. Sources, in this order

1. **The conversation is the main source.** Collect what we did in this session, what is still open,
   what the user decided and what the user refused. The conversation wins, except where live state
   proves a fact: a commit exists, a pipeline is red.
2. **Git**, in the current directory, and in every worktree the conversation names.
3. **The merge or pull request** of the branch: GitLab through its REST API, GitHub through `gh`.
4. **The Jira ticket** of the branch, with its subtasks. When the branch names a subtask, the script
   shows the subtask's parent.
5. **Background jobs of this session.** Take them from the conversation. A background shell or agent
   with no completion notice yet still runs. A notice that shows a failure or a stop is a blocker.

Read sources 2 to 4 with one call, where `<skill-dir>` is the directory that holds this file:

```bash
python3 <skill-dir>/scripts/state.py [<worktree path> ...]
```

The script finds everything else itself:

| Source | How the script finds it |
|---|---|
| Target branch | The target of the open merge or pull request, else `origin/HEAD`, else `main`. |
| GitLab | The host and project path of `origin`, with `GITLAB_TOKEN`. |
| GitHub | `gh pr list` and `gh api graphql`, with the `gh` login. |
| Jira ticket | A key in the branch name (`feature/ABC-12`). Else the branch's trailing number with the project prefix found in its commits or in the request title (`feature/me/12` and a commit `ABC-13 ...` give `ABC-12`). Else the first key in the commits. |
| Jira access | `JIRA_BASE` with `JIRA_TOKEN` (Server or Data Center, Bearer), or `JIRA_EMAIL` with `JIRA_TOKEN` (Cloud, Basic). `JIRA_TOKEN_CMD`, when set, is a command that prints a fresh token. |

Read the output with these rules:

- `WARNING: the upstream is the target branch` is a blocker: a bare `git push` would land on the
  target branch.
- Mention uncommitted files only when they belong to the current work. Ignore build caches and
  crash dumps.
- Failed or cancelled checks are a blocker. Running checks are a fact for "Where we are".
- Unresolved threads are a next step, not a blocker.

## 2. Output

Write in the user's language. Name the three parts in that language too; in Romanian they are
"Unde suntem", "Ce avem" and "Ce propun mai departe". Use exactly this shape:

1. **Blocker first, only if one exists.** A red pipeline, a failing test, a stopped background job, or
   a decision only the user can take. One or two sentences, before "Where we are".
2. **Fresh session.** If the conversation has no earlier work, add one short line: "New session: I
   read the state from git, the request and the tracker."
3. **Where we are.** One or two sentences. Name the ticket and the branch, and say how far the work is.
4. **What we have.** Three to five bullets, one short sentence each. Describe behaviour in plain
   words: what the user or the product now does. Ticket keys are fine. Class names and file names
   are not.
5. **What I propose next.** A numbered list of one to three steps. Put the recommended step first.
6. **Last line.** One question that asks to start step 1, for example "Shall I open the merge request?".

## 3. Style

Apply the ASD-STE100 (Simplified Technical English) rules, in any language:

- One idea per sentence. At most 20 words per sentence.
- Active voice, with the actor named. Simple words and simple tenses.
- No filler, no pleasantries, no recap of the answer at the end.
- No file paths or class names, unless one is load-bearing.
- About 150 words in total.
- Use the language's correct diacritics.

## 4. Reference: the target tone

Copy the tone and the density of this answer, not its content.

> **Where we are.** SHOP-412 is in `main`. SHOP-420 is on the branch `feature/420`, with three of its
> four subtasks done, tested and pushed.
>
> **What we have.**
> - **421:** a customer can reset a forgotten password from the sign-in page.
> - **422:** the reset link works once and expires after 30 minutes.
> - **423:** the customer gets an email when the password changes, with a link to undo it.
> - A support user cannot start a reset in a customer's name.
>
> **What I propose next:**
> 1. I open the merge request for 420.
> 2. We do 424, the live check, together. You try the reset in the browser; I give you 3 short scenarios.
> 3. After the live check, I adjust the email texts if they read badly.
>
> Shall I open the merge request?

What makes it work: each bullet says what the product now does, and nothing names a class. Each step
is one action the user can approve. The last line asks for a single yes.
