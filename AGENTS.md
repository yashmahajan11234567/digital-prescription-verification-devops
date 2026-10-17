# ChatGPT project context

This directory is a local mirror of the ChatGPT project “(DevOps) Digital Prescription Verification System”.

- Treat every file under `sources/` as read-only reference material.
- Do not edit, rename, move, or delete synced project files.
- These files may be replaced the next time a task is created from this ChatGPT project.


## Project instructions

## Project memory workflow

RxVerify knowledge lives in three local systems; keep them distinct.

- Vault (curated, durable): /Users/yashsiphone/Documents/Obsidian/RxVerify-notes
  Read before a task; write confirmed outcomes back after. (Not the obsidian-skill default path.)
- Session history: recall past decisions/progress with the `session_search` tool — never copy raw conversations into the vault.
- Code graph: inspect relationships/dependencies/impact with the Graphify MCP tools (`mcp__graphify_*`).

### Before a project task (read)
1. Open the vault index `Welcome to RxVerify Notes`, then the relevant curated note(s).
2. If prior progress/decisions matter, recall them via `session_search` (topic query; `sort=newest` for "where did we leave X").
3. If the task touches structure/dependencies/blast radius, confirm with Graphify: `graph_stats` (freshness) then `query_graph` / `get_neighbors` / `shortest_path` for the specific question.

### After a task (write confirmed outcomes)
Append — never overwrite — a dated entry to `Project Outcomes.md` (create if missing).
Each entry: one-line outcome · what changed · [[wikilink]] to the affected curated note · commit hash if code changed. Verified facts only.

### Vault rules
- Path: /Users/yashsiphone/Documents/Obsidian/RxVerify-notes (concrete; ignore the skill default).
- The 5 curated notes are read-only to you: no rewrites/deletes; add via anchored append or a new note.
- NEVER write secret values (API keys, tokens, passwords, connection strings, card data) — reference where a secret lives, not its value.
- One canonical write-target (`Project Outcomes.md`); connect with [[wikilinks]], don't spawn new MOCs.

### Graph freshness
Graphify's graph is a commit snapshot. Read the commit from `graph_stats`; if it lags HEAD, treat structural answers as possibly stale and verify current code with `read_file`.
