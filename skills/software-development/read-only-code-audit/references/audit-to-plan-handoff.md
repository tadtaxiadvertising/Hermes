# Audit → Plan Handoff Checklist

Use this checklist when an audit (via `read-only-code-audit`) has produced findings and the user has now said "fix #N" or "do the plan for finding #N".

## From `read-only-code-audit` SKILL.md

> Generating the implementation plan referencing the audit finding ID, exactly the file:lines, and the recommended layer (cursor pagination, guard consolidation, schema migration, etc.).

## Plan writer's checklist (5 items)

1. **Cite the audit Finding ID in plan title**
   - Format: `Finding #N — <one-liner>` (matches the audit's numbering).
   - The implementer should be able to grep the audit transcript for the ID and find the plan.

2. **Reproduce the audit's evidence verbatim in "Current Context"**
   - Copy the file:line, the `git ls-files` output, the `git check-ignore` exit code, the kill-switch code snippet — whatever the audit cited. Do not paraphrase.
   - If the audit said "38 MB apps/api/prisma/client/ committed", the plan says "38 MB apps/api/prisma/client/ committed", not "some generated artifacts leaked".

3. **Honor the audit's recommended layer as architectural contract**
   - Audit said "consolidate into `@RequireActiveSubscription()` guard" → plan implements the guard, NOT a per-route conditional.
   - Audit said "use cursor pagination" → plan uses cursor, NOT `take` slicing.
   - Audit said "delete .gitignore-leaked dir, then `git rm -r --cached`" → plan follows those two steps verbatim, NOT just adding to `.gitignore`.
   - Audit said "recompute in Postgres via groupBy" → plan uses groupBy, NOT business logic in Node after the fetch.
   - If the implementer needs to deviate: surface it explicitly in **Risks** with the reason.

4. **Carry the unchanged invariants forward**
   - List the ✅ findings adjacent to the one being fixed (e.g. "the 15-slot guard is enforced in campaign.service.ts:192; do not regress it").
   - This is the implementer's guardrail: the audit endorsed those, the plan must preserve them.

5. **Flag the unfixed sibling findings**
   - If two findings share a module (e.g. Finding #3 = leak of prisma/client/ and Finding #4 = divergent second schema.prisma), the plan addresses #3 only and explicitly notes #4 is still open.
   - Don't accidentally smuggle fixes for unapproved work into a single plan.

## Common deviations and how to record them

| Deviation from audit | Why it might happen | How to record |
|---|---|---|
| Recommended layer doesn't fit the existing module graph | Refactor cost too high for the scope | Risks: "Audit recommended guard consolidation; plan keeps per-site if checks because consolidating now touches 6 routes not in scope. Track in tech debt." |
| Two findings collapse into one fix | They're the same root cause | Plan notes both Finding IDs and the merged approach explicitly |
| Audit was wrong about a file path | Re-search found a different file | Plan cites the corrected path with git grep evidence |
| Finding has 3+ distinct sub-findings | Audit scoped wide | Split into 2+ plans; link them in each header |

## Quick test: is the plan contractually correct?

Ask: if the implementer executes this plan without re-reading the audit, can they still produce code that:

- (a) Closes Finding #N's risk to the audit's stated severity?
- (b) Doesn't regress any OK finding in the audit transcript?
- (c) Doesn't roll in fixes for adjacent CRITICAL findings without approval?

If "no" to any, walk back to step 3 or 5.
