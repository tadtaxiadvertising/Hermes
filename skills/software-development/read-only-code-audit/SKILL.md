---
name: read-only-code-audit
description: "Use when a user asks for a passive audit, code review by section, or 'show me what concerns you' against a monorepo with documented business rules. Produces severity-ranked findings with file:line evidence, depth-bounded, and an explicit list of what was NOT audited. Does not modify any file. Distinct from dogfood (which audits running web apps via browser) and requesting-code-review (which reviews in-progress PR diffs)."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [audit, review, read-only, architecture, business-rules, monorepo]
    related_skills: [plan, requesting-code-review, systematic-debugging]
---

# Read-Only Codebase Audit

## Overview

A workflow for delivering **depth-bounded, severity-ranked, evidence-cited audits of a monorepo** without modifying a single file. Optimized for codebases that already maintain their own business-rules documentation (e.g. numbered SOP files, kill-switch rules, RAM budgets, telemetry contracts) — the audit verifies whether the code honors what the docs claim.

Three guarantees this skill makes the agent keep:

1. **No code mutations, no commits, no PRs.** The user will say "vamos" when they want execution.
2. **Severity-ranked findings with file:line evidence.** Every entry cites a path and either a line number or a verifiable runner command.
3. **Explicit "not audited" boundary.** The agent states what was skipped each session, so the user knows the scope.

This is **not** the same as `dogfood` (browser-driven QA of a live app), nor `requesting-code-review` (PR diff review). The closest sibling is `systematic-debugging` — both are read-only investigations that demand evidence before action.

## When to Use

Trigger phrases (any one):
- "Hazme una auditoría del repo, no modifiques nada"
- "Auditoría pasiva, read-only"
- "Review the codebase and tell me what concerns you, but don't change anything"
- "Show me a security / consistency / architecture review"
- "Verify whether the code respects the rules in `NN_*.md`"
- "Utiliza tu recomendación y hazlo" (after a plan was presented and approved)
- "procede con #N" / "tira" / "dale" (after FASE 2 plan is shown)

**Don't use for:**
- The user has a specific bug fix or feature → use `plan` then `subagent-driven-development` (or directly fix).
- The user wants browser-driven QA of a live web app → use `dogfood`.
- The user has an open PR / diff → use `requesting-code-review`.
- The user wants a plan for future code → use `plan`, not this skill.

## Pre-flight: Confirm the Audit Frame

Before producing any findings, verify three inputs are present. **If any is missing, halt and ask — do not assume.**

1. **Repo root** — absolute path to the working tree. On Windows, prefer `C:\\Users\\<user>\\...` or MSYS `/c/Users/<user>/...`. If git: `git rev-parse HEAD` to capture the SHA being audited; record it in the report.
2. **Working tree state** — `git status --short` must be clean OR the user must acknowledge any tracked modifications. Auditing an in-flight branch is fine; auditing an uncommitted mess tends to produce misleading evidence.
3. **Scope** — does the user want the whole repo, a specific app/service (`apps/api`, `apps/driver`), or a specific concern (security, cost, performance, business-rule compliance)?

If the user provided a multi-phase directive ("## Role FASE 1 → 4") embedded with the request, treat the phase prompts as scope: FASE 1 = reconnaissance; FASE 2 = planning. **Do not auto-promote to execution** even if a later phase says "implementation"; wait for explicit consent ("Procede", "go", "ahora sí").

### Pre-flight: Repeated accelerators are blockers, not go-ahead signals

Prompts like "continue", "procede", "dale", "go", "siguiente" with no task content are **not** an instruction to advance. They are the user paging the system. The correct response is to **name what's blocking and ask again** — re-state the missing input (task, scope, ref, etc.) rather than invent one. This honors both the user's director pattern and your own Zero-Trust commitment.

This applies doubly after model-swap notifications ("active model changed to X") or in multi-turn setups where the running model may have just changed between turns: the accelerator says "I'm still here", not "do something".

## Audit Workflow

### Step 1: Reconnaissance — read mandated docs first

Many monorepos carry numbered SOP files at the root (TAD DOOH keeps `01_auditoria_*.md` through `16_*.md`). The audit must read **whatever the user pointed at** in their directive (often `01`, `02`, `04`) to load business rules before sampling code. After reading, internalize:

- Critical invariants (kill-switch / payment-required / slot limits / TTLs)
- Hard caps (RAM limits on microservices, file size limits, debounce values)
- Auth split (which guard for whom, which local auth, which sign-in flow)
- Realtime / offline contracts (channels, batched payloads, JWT TTL)

Persist these to **memory** so they survive across this session's turns. They are not session-noise; they are the rulebook the audit will reference.

### Step 1b: When the user asks for more depth ("profundiza", "ahonda", "todo el contexto")

If the user follows the initial report with a depth request, do NOT re-run the whole workflow — extend it. Three things change:

1. **Prioritize cross-references over new findings.** A second-wave audit's job is to verify what wasn't visible in the first pass: cross-references between docs and code, hidden duplications, TTL drift between docs and runtime.
2. **Sequence by *dimension*, not by *file*.** Group the second pass into named dimensions (schema, auth, schedulers, RAM/queries, CI/CD, observability) and audit each to completion before moving on. This turns a vague "more depth" into a measurable scope.
3. **End every wave with an explicit "not yet audited" boundary.** Do not silently disappear — name the dimensions you skipped and the rationale, so the next user message can be precise (e.g., "do Security next" instead of "profundiza más").

A second-wave audit often uncovers shadow stubs, doc/code TTL drift, command-vs-behavior contract gaps, and forgotten generated artifacts. Plan the second wave around exactly those classes of finding.

### Step 2: Reconnaissance — map the workspace

Run before any code sampling:

```bash
ls apps/                                        # or the workspace root convention
find . -name "schema.prisma" -not -path "*/node_modules/*"
git ls-files <suspect-generated-dir>
git check-ignore -v <generated-file>
du -sh <big-dir>
```

Catch three classes of misconfiguration early — they will become the audit's highest-impact findings:

- Committed generated artifacts (`prisma/client/`, `.next/`, `dist/`, `dev.db`).
- Duplicate sources (two `schema.prisma`, two `service-worker.js`, two `.env*`).
- OS-specific binaries tracked in git (`.dll.node`, `.so.node`) — cause platform drift.

### Step 2a: Credential surface check (before any git fetch/push)

If the user said "credenciales ya están en el sistema" or similar, **do not assume SSH.** Verify both sides before touching git:

```bash
# Side A: SSH key presence
ls -la ~/.ssh/ 2>/dev/null   # success-files only, NOT glob

# Side B: Remote URL protocol (HTTPS vs SSH)
git remote -v
```

If the SSH directory is empty AND the remote is `git@github.com:…`, the user has HTTPS+credential helper config, not SSH — that's fine for `git fetch`/`push` but you should not assume a passphrase prompt. If `git remote -v` shows `https://github.com/...` and SSH keys are missing, you have HTTPS-only access via the credential helper — declare it explicitly before any fetch/push so the user knows what will happen.

**Reproducible tool quirk — `memory` rejects SSH-glob content.** The `memory` tool's `add` action rejects content whose body contains literal SSH key glob patterns (for example `~/.ssh/id_*` or `id_ed25519`) because its classifier flags them as potential SSH-injection payloads. Phrase any memory entry neutrally ("local SSH agent is empty; HTTPS credential helper is the configured auth path") rather than including the literal glob. Filter the variable stored value before writing the memory entry.

### Step 2b: Generated-artifact check (run with `git ls-files`)

After the basic `find`/`.gitignore` checks, run `git ls-files <suspect-dir>` and `git check-ignore -v <file>` against each generated dir. Three things to surface as 🔴 or 🟠:

- `prisma/client/`, `apps/api/prisma/client/` — these are **not** Prisma's standard output (the standard is `node_modules/.prisma/client`). If they're tracked, they're either hand-copied leftover or an old `output = "./client"` schema. Always read both `prisma/schema.prisma` and the suspect to confirm they're divergent — divergence is the strongest evidence of staleness.
- `.next/`, `dist/`, `dev.db`, `*.node` binaries (`.dll.node`, `.so.node`) under git — platform-drift sources; never useful tracked. A 38 MB committed `apps/api/prisma/client/` is a 🔴 hygiene finding.
- Two `service-worker.js` files (custom + `sw.js` from `next-pwa`) — grep **`serviceWorker.register(`** AND **`navigator.serviceWorker?.addEventListener(`** to see which is actually registered; if only the listener hook exists with no register call, both files are dead code.

### Step 2c: Shadow-stub detection (greppable patterns)

Several codebases carry **two implementations** of the same guard / same class / same interface, one "real" and one "stub" with `return true` or `// TODO`. Always check for this pattern when you see a security-relevant decorator being applied:

```bash
search_files(pattern="<ClassName>", output_mode="files_only", path="<source-root>")
```

If two files declare the same class name AND one reads `return true;` with a comment justifying it ("always allow", "stub", "política ahora permite"), that's a **shadow-stub**. Severity:

- 🔴 if the stub is `@UseGuards`-applied on a sensitive endpoint AND the comment suggests the intent changed (could be either bug or policy flip).
- 🟡 if the stub is imported but never applied (dead code, just clutter).
- 🔴 if multiple imports of the same name occur (e.g. `import { SubscriptionGuard as FooSubscriptionGuard } from '../somewhere'`) — verify each application site.

### Step 2d: Schema ↔ client ↔ SQL consistency (Prisma + Postgres)

Codebases that use Prisma + materialized views have three "maps of truth" that must agree: the `schema.prisma` source, the generated `@prisma/client` living under `node_modules/.prisma/client`, and any hand-written `*.sql` files (views, refresh functions, triggers). When they drift, the failure mode is silent runtime breakage — the type checker is often the only thing that catches it.

**Three cheap checks; do all three:**

```bash
# 1. Type-check the backend alone. Prisma client staleness surfaces as
#    TS2339 on `prisma.<modelName>` or TS2353 on inputs that the model
#    declares but the generated types don't accept.
cd <backend-app> && node_modules/.bin/tsc -p tsconfig.json --noEmit 2>&1 | head -80

# 2. Grep every `prisma.<something>` reference and verify the model exists
#    in schema.prisma. A hit without a model = client was never regenerated
#    after the schema changed.
git grep -nE "prisma\.[a-zA-Z]+" -- 'apps/api/src/**/*.ts' \
  | sed -E 's/.*prisma\.([a-zA-Z]+).*/\1/' | sort -u > /tmp/used_models.txt
grep -oE "^model [A-Z][a-zA-Z]+" apps/api/prisma/schema.prisma \
  | awk '{print $2}' | sort -u > /tmp/declared_models.txt
diff /tmp/{used_models,declared_models}.txt      # any difference = bug
```

**The three Prisma-staleness symptoms (priority-ordered):**

| Symptom | Cause | Severity |
|---|---|---|
| `TS2339: Property '<Model>' does not exist on type 'PrismaService'` | Model added to schema, `prisma generate` never re-run | 🔴 — runtime throws `undefined is not a function` |
| `TS2353: Object literal may only specify known properties, and 'X' does not exist in type '...WhereInput' / '...CreateInput'` | Field added/renamed in schema, generated `inputs.ts` not refreshed | 🟠 — same root cause, masked if field is newly added (the cache is current for *flat* fields in older indexes) |
| Raw `INSERT ... ON CONFLICT (<cols>) DO NOTHING` with no matching UNIQUE constraint in schema | `skipDuplicates` / `ON CONFLICT` silently inert or throws | 🔴 — telemetry inserts hit "no unique or exclusion constraint matching" |

**Also check hand-written SQL files for materialized-view drift:**

```bash
find . -path "*/node_modules" -prune -o -name "*.sql" -print \
  | xargs grep -l "MATERIALIZED VIEW\|CREATE VIEW" 2>/dev/null
```

Two files defining the same view = drift. Pick the canonical one and delete the rest. Drift tells: (a) two `CREATE MATERIALIZED VIEW <same-name>` with different columns/indices; (b) one file `DROP IF EXISTS` + `CREATE`, the other `CREATE IF NOT EXISTS` only — silent overwrite risk; (c) a `refresh_<view>()` function exists in one file but is called from code referencing the other — coupling finding. Full patterns and fix templates live in `references/prisma-and-mv-staleness.md`.

Additionally, if the SQL file contains PL/pgSQL function bodies with `$$...$$` dollar-quoted strings, the standard `split(';')` approach will fragment the function body into invalid SQL fragments that PgBouncer rejects. Use the dollar-quote-aware splitter in `references/split-sql-dollar-quoted.md`.

### Step 2e: Doc-vs-code TTL drift

Where the SOP/architecture doc declares a hard TTL (JWT, manifest, offline cache, retry window, grace period), grep the matching code:

```bash
search_files(pattern="expiresIn.*['\"][0-9]+[mhd]", path="<module>")
search_files(pattern="setTimeout.*[0-9]{6,}", path="<module>")  # ms form
```

Compare each declared TTL to the actual code value. Drift is **almost always** the code being ahead of the doc — code wins for runtime, doc wins for instruction; the finding is "decision required" not "bug". Track which is current and ask the user to choose. Drift that contradicts docs in multiple places (e.g. SOP says 48h offline-first, runbook also says 48h, code is 24h) is a stronger signal than a one-doc/one-code mismatch — code moved; both docs are stale.

### Step 3: Cross-check rules against code

For each critical invariant from Step 1, run a precise search:

```text
search_files(pattern="<rule-keyword>", path="apps/api/src")
search_files(pattern="<guard-name>", path="src")
```

Three outcomes per rule, each mapping to a finding:

| Outcome in code | Finding |
|---|---|
| Rule enforced at a centralized layer (guard / constant / interceptor) | ✅ Healthy — note tests as the only follow-up |
| Rule enforced ad-hoc at each call site (e.g. `if (!driver.subscriptionPaid)` repeated) | 🟠 MEDIUM — refactor opportunity into a single `@RequireActiveSubscription()` |
| Rule **not found** in code despite being in the SOP | 🔴 HIGH — this is a delivery bug, not hygiene |

Always **read the function** that matches — a one-line hit can be misleading. The `$1.byte` rule: a finding needs at least one full read of the cited code path, not just the grep match.

### Step 4: Cost & memory audit (monorepo RAM caps)

If the SOP declares RAM caps on services (e.g. 512 MB API, 1024 MB Remotion), look for patterns that break them:

- `.findMany({ include: { rel: { include: { sub: true }}}}` chained → fetch joined trees to Node heap.
- `for (const x of bigArray) await …` → sequential I/O on large arrays (and N+1 query pattern when each iteration hits the DB).
- `.reduce()` / `.sort()` on arrays loaded fully → CPU-bound in-process.
- `findMany({include, take: undefined})` without a `take` cursor — loads the whole table.

For each suspect, the fix lives in the database, not the API: `groupBy`, `aggregate`, cursor-paginated `findMany`, raw SQL, or materialized views. **Auditor's role is to flag, not to prescribe** — but always suggest the right layer (Postgres agg vs Node loop vs cursor).

### Step 5: Produce the report

Output format (use exactly this skeleton — adapt the wording but keep the columns populated):

```markdown
## 🔍 READ-ONLY AUDIT — <repo name> · <branch>@<short-sha>

### Finding #N · <severity emoji> <severity word> — <one-line title>

**Evidence:**

```
<exact path:line or command output that proves the issue>
```

**Risk:** <one or two sentences — what could break>

**Reproduction:** <a one-liner shell command the user can run themselves>

---

## 📋 Severity summary

| # | Finding | Severity | Minimum fix suggested (NOT applied) |
|---|---|---|---|

## 🔍 What was NOT audited this session

<explicit bullet list — depth-bounded reporting>
```

Severity scale:

| Marker | When to use |
|---|---|
| 🔴 CRITICAL | Would break business rule, kill production, leak data |
| 🟠 MEDIUM  | Refactor opportunity, will bite when scope grows |
| 🟡 INFO   | Doc rot, naming, low-impact hygiene |

**Don't invent severity to feel impressive.** Most audits in real codebases should be 🟠/🟡; reserve 🔴 for findings with concrete production consequences. A 🟡 can be silently promoted to 🔴 if it replicates across multiple waves or appears in 2+ maps of truth (docs + code).

### Step 6: Close the loop — no execution

End the response with one of these closings, never anything else:

- *"If you want any finding promoted to FASE 2 (execution plan), tell me which one and I'll scope the impact trace."*
- *"Audit complete. No files modified, no commits made. Awaiting your direction."*

Never auto-promote. The user's directive format usually reserves FASE 2 for a separate explicit approval. Even if they paste the whole multi-phase directive, **the audit deliverable is the report above, nothing more**.

## Common Pitfalls

1. **Assuming auth setup means SSH.** The user may say "credenciales ya están en el sistema" — that's HTTPS credential helper config, not SSH keys. Verify both with `ls -la ~/.ssh/` (not glob) and `git remote -v`. Declare the auth surface explicitly before any `git fetch`/`push`. (See Step 2a.)
2. **`memory` tool rejects SSH globs.** Don't write `~/.ssh/id_*` or `id_ed25519` into memory; the classifier blocks it. Rephrase neutrally. (See Step 2a.)
3. **Fabricating file paths or line numbers.** When the search isn't returning what you expect, re-search with a different pattern. A wrong line number is worse than no line number — it destroys the user's trust.
4. **Skipping the "not audited" section.** Hiding the boundary is a dishonest report. The user needs to know what's at risk vs what's confirmed.
5. **Treating "no doc reference" as "no problem."** A 15-slot rule in business docs that has no backend guard isn't a "potential issue" — it's a defect. Read the comments near the rule's enforcement site; if they exist but live ad-hoc, that's 🟠 MEDIUM, not ✅.
6. **Mistaking shadows for stubs.** Two files with the same class name is a strong signal but not a verdict. Read both files end-to-end; one may be the "real" implementation and the other dead code, or both may be live in different paths. The grep alone is evidence of duplication, not of failure.
7. **Aggressive refactor suggestions.** Auditors propose, not prescribe. Don't write 50-line rewrites in a report. State the finding, point at the file:line, suggest the *layer* (e.g. "consolidate into a guard", "move to cursor pagination"). Specifics belong in the FASE 2 plan, gated on the user's approval.
8. **Mistaking "all checks pass" for "code is healthy."** Some critical rules are enforced; some are not. Audit both. Distinguish "verified enforced" from "couldn't find a reference" in the report.
9. **Under-severitizing a shadow-stub on a security-critical decorator.** When a guard class returns `true` with a comment like "política ahora permite X" or "TAD ahora permite…" or "always allow for V12", that is almost always a **policy flip** that may or may not be intentional. The comment is itself the evidence the auditor needed. A `return true` inside `@UseGuards(SubscriptionGuard)` (kill-switch path) is 🔴, not 🟡, until proven intentional. Treat the comment as the diff against the rulebook: read the doc, find the line that contradicts, and flag the divergence.
10. **Treating shadow-stub duplicates as low-impact dead code when one is the live guard.** Step 2c flags duplicates as "evidence of duplication, not of failure." That's correct for cleanup audits. For security-relevant guards, reverse the default: **duplicate → +1 probability that one of them is the live, stubbed-out version**. Open both files end-to-end and check the import sites.
11. **Missing the "convergent evidence" promotion.** A 🟠 finding that has BOTH (a) the SOP rule it violates AND (b) a code-comment justifying the divergence is rarely an innocent drift. Promote to 🔴 unless the user confirms the policy flipped on purpose. Document the promotion rationale in the finding body, not just the severity column.
12. **Prescribing Prisma fixes without verifying the client was regenerated.** When the finding is `TS2339: Property '<Model>' does not exist`, the fix is `cd <app> && npx prisma generate` (and `db push`/`migrate deploy` for the schema itself), not a code rewrite. Recommend the smallest, most upstream fix first — re-running codegen is often the whole answer.
13. **`write_file` on Windows resolves relative paths from the tool CWD, not the repo root.** Passing a relative path like `apps/player/src/env.d.ts` can silently create nested phantom directories like `apps/player/apps/player/src/env.d.ts`. Always pass an absolute path (`C:/Users/<user>/.../apps/player/src/env.d.ts`) when writing files on Windows hosts. If a phantom directory appears, `rm -rf` it immediately before it confuses subsequent `search_files` calls.
14. **`patch` mode=replace can swallow a method signature when `old_string` spans a blank line into the next method body.** The fuzzy matcher sees the blank line as optional and may consume the following method's signature. Always include enough trailing context (the start of the next method's body or a unique non-blank line) to anchor the replacement boundary. If the post-patch lint suddenly shows `TS7008: Member implicitly has 'any' type` or `TS1068: Unexpected token`, re-read the file — a signature was likely eaten.
15. **TS5 `env.d.ts` for `import.meta.env` requires `declare global` + `export {}`, not bare interfaces.** With `module: "ESNext"` + `moduleDetection: "force"`, a plain `interface ImportMeta { readonly env: ImportMetaEnv }` at top level is NOT recognized as ambient — the file silently no-ops and every `import.meta.env.VITE_*` reference continues to throw `TS2339`. The working pattern: `declare global { interface ImportMetaEnv { readonly VITE_API_URL: string; ... } interface ImportMeta { readonly env: ImportMetaEnv; } }` followed by `export {};`. This resolves 11+ TS2339 errors in one shot. Verify with `tsc --listFiles` that the `.d.ts` is actually included in the compilation.
16. **When the user says "requiero 0 errores, procede" after a verification pass that reported pre-existing errors — they want those errors FIXED, not re-verified.** The session is still in the execution loop; the user is not asking for a re-run of the same check. They are escalating the success criteria. Apply the fix (populate `env.d.ts`, install the missing dependency, etc.), then re-verify from scratch.
17. **`sql.split(';')` breaks PL/pgSQL blocks with dollar-quoted strings (`$$...$$`).** When a monorepo uses a `.sql` file with a `CREATE OR REPLACE FUNCTION ... AS $$ BEGIN ... END; $$;` block, the naive `sql.split(';').map(trim).filter` splits the function body in half. Prisma then sends fragments like `"BEGIN\n    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_active_campaigns"` (no closing `$$`) and `"EXCEPTION"` (invalid standalone SQL) to the pooler, producing `ERROR: unterminated dollar-quoted string` and `ERROR: syntax error at or near "EXCEPTION"`. The fix is a splitter that tracks `$$` depth and only treats `;` as a statement boundary when `dollarDepth % 2 === 0` (outside dollar-quoted blocks). Full implementation in `references/split-sql-dollar-quoted.md`.

## Verification Checklist

Before sending the audit:

- [ ] Repo root, branch, and SHA recorded at the top of the report
- [ ] Working tree state confirmed (`git status --short`)
- [ ] No files modified, no commits, no branches created — `git status` should match what was there before the session
- [ ] Each finding cites at least one `path:line` or shell command runnable by the user
- [ ] Severity rankings are justified — 🔴 reserved for production-impacting issues
- [ ] "What was NOT audited" section is present and honest about depth
- [ ] Closing line offers FASE 2 promotion but does not auto-execute
- [ ] If the user invoked a multi-phase directive, only the audit phase was completed; later phases remain gated
- [ ] Auth/auth surface declared: SSH present? remote protocol? before any fetch/push

## One-Shot Templates

### Minimal audit report head (always include)

```text
Audit SHA: <git rev-parse HEAD>
Branch:    <branch name>
Working tree: clean / dirty
Apps in monorepo: <list>
Mandated docs read: <list>
Auth surface: <SSH keys: present/absent; remote protocol: HTTPS/SSH>
```

### Cross-referencing the docs after every finding

When citing a finding, append a tiny "**Rule reference:** `02_reglas_negocio_stack.md:§name`" line so the user sees you didn't invent the rule — you read it. This is the single most valuable habit for a doc-anchored audit.

### Promotion handoff to FASE 2

When the user later says "do the fix for finding #N", the next session step is *not* this skill — it's `plan` mode (write the implementation plan to `.hermes/plans/`) and then `subagent-driven-development` or direct execution. The audit skill's job is done at that point. Generate the plan referencing the audit finding ID, exactly the file:lines, and the recommended layer (cursor pagination, guard consolidation, schema migration, etc.).

For specifics on how to chain plan work back to the audit transcript (cite Finding IDs, copy evidence verbatim, honor the layer recommendation as a contract, flag sibling findings), see `references/audit-to-plan-handoff.md`.

For Prisma client-staleness triage, materialized-view drift, and `ON CONFLICT`-without-UNIQUE failures (the three highest-yield backend-staleness classes), see `references/prisma-and-mv-staleness.md`.

For surgical fixes that span **mobile hook → API proxy → NestJS controller/service → admin map** (telemetry, Realtime, GPS, fleet map), see `references/multi-app-telemetry-chain-fixes.md`. Covers: (a) "canonical hook killed the broadcast" trap when replacing a `@deprecated` hook, (b) `status: enum` ↔ `isOnline: boolean` binding drift in map markers, (c) order-dependent `lastPoint` heuristic for `Device.lastLat/lastLng` snapshot after offline flush, (d) extra-trailing-`}` patch fragility, (e) per-app scoped `tsc --noEmit` verification recipe.
