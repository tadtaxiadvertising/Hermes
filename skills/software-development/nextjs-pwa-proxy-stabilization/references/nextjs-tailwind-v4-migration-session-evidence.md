# Next.js Tailwind v4 Migration — Session Evidence

Session: 2026-07-12 — TAD DOOH "Advertiser UI/Assets Recovery"

## The Bug

**Symptom (production):** `tad-advertiser` portal renders raw, unstyled HTML. Tailwind CSS does not load. Browser shows no `/static/css/*.css` requests.

**Local discovery:** A clean `npx next build` of `apps/advertiser` produced `.next/static/` with all JS chunks but **no `css/` directory at all** — Tailwind never ran its PostCSS plugin. The sibling portals (`apps/admin`, `apps/driver`) rendered correctly in prod.

## Root Cause

`apps/advertiser` was left in Tailwind **v3** shape while the rest of the monorepo migrated to **v4**:

| Aspect | `apps/admin` (works) | `apps/advertiser` (broken) |
|---|---|---|
| `postcss.config.mjs` | ✅ `{"@tailwindcss/postcss": {}}` | ❌ **ABSSENT** |
| `tailwind.config.js` | ❌ None (CSS-first v4) | ✅ v3 shape (`content: [...]` + `module.exports`) |
| `styles/globals.css` | ✅ `@import "tailwindcss"; @theme {...}` | ❌ `@tailwind base/components/utilities` (v3, ignored by v4) |
| Tailwind/PostCSS deps in `package.json` | ✅ `tailwindcss@^4`, `postcss`, `@tailwindcss/postcss`, `autoprefixer` | ❌ **NONE** (relied on npm hoisting from monorepo root) |

Effect: v4 runtime ignores the v3 directives + JS config → Tailwind's PostCSS plugin never registered (no `postcss.config.*`) → zero CSS generated → unstyled HTML.

The Dockerfile compounded this: `RUN rm -rf package-lock.json node_modules && npm install` made each Docker build non-reproducible and could resolve different Tailwind/PostCSS versions locally vs in-container.

## Fix Applied — 5 files

1. **`apps/advertiser/postcss.config.mjs`** (NEW) — registers `@tailwindcss/postcss` (v4):
   ```js
   const config = { plugins: { "@tailwindcss/postcss": {} } };
   export default config;
   ```

2. **`apps/advertiser/styles/globals.css`** (REWRITTEN) — migrated from v3 directives to v4 CSS-first. Moved the custom TAD colors (`tad-bg`, `tad-surface`, `tad-accent`, `tad-accent-hover`, `tad-text`, `tad-text-muted`) and animations (`spin-slow`, `scan`) from the deleted `tailwind.config.js` into a `@theme { ... }` block. Preserved `@layer base` body styling + custom scrollbar directives.

3. **`apps/advertiser/tailwind.config.js`** (DELETED) — v4 is CSS-first; the v3 JS config was silently ignored and is dead weight.

4. **`apps/advertiser/package.json`** (+4 deps) — added `tailwindcss@^4.0.0`, `postcss@^8.5.8`, `@tailwindcss/postcss@^4.2.1`, `autoprefixer@^10.4.0` explicitly. No longer relying on root-workspace hoisting.

5. **`Dockerfile.advertiser`** (REPAIRED) — replaced `COPY package.json ./` with `COPY package.json package-lock.json ./`, and removed `rm -rf package-lock.json` from the install line. Now: `RUN npm install` (honors lockfile, reproducible).

6. **`package-lock.json`** (synced) — `npm install` at monorepo root added 16 packages / removed 4 / changed 1 to reflect the new deps in the advertiser workspace.

## Diff Stat

```
 Dockerfile.advertiser              |  8 +++++---
 apps/advertiser/package.json       |  6 +++++-
 apps/advertiser/styles/globals.css  | 38 +++++++++++++++++++----------------
 apps/advertiser/tailwind.config.js | 39 --------------------------------------
 package-lock.json                  | 30 ++++++++++++++---------------
 5 files changed, 58 insertions(+), 63 deletions(-)
```

Plus new file: `apps/advertiser/postcss.config.mjs` (untracked).

## Verification Evidence

### Build (fresh, never reuse prior results)

```
$ cd apps/advertiser && npx next build
   ▲ Next.js 15.2.6
   ✓ Compiled successfully
   ✓ Generating static pages (4/4)
   Finalizing page optimization ...
   Collecting build traces ...
   exit_code: 0
```

Build manifest output included the CSS line that was **absent before the fix**:

```
+ First Load JS shared by all               261 kB
  ├ chunks/framework-b476adb177a4b864.js   57.5 kB
  ├ chunks/main-95ec841fbbcfcae4.js        32.1 kB
  ├ chunks/pages/_app-312d2672fb8ca8e6.js  154 kB
  ├ css/e8b8fe1aba192c9b.css               16.1 kB   ← NEW: CSS generated
  └ other shared chunks (total)            1.85 kB
```

### CSS file inspection (after build)

```
$ ls -la .next/static/css/
-rw-r--r-- 1 Arismendy  105174 Jul 12 18:36 e8b8fe1aba192c9b.css
$ wc -c .next/static/css/*.css
105174 .next/static/css/e8b8fe1aba192c9b.css
$ head -c 300 .next/static/css/*.css
/*! tailwindcss v4.2.4 | MIT License | https://tailwindcss.com */
@layer properties{...}
```

105 KB of Tailwind v4 CSS generated. Header confirms v4.2.4 ran.

### Type check

```
$ cd apps/advertiser && npx tsc --noEmit
exit_code: 0  (no output = no errors)
```

### Standalone server (the artifact Docker copies)

```
$ ls .next/standalone/apps/advertiser/server.js
.next/standalone/apps/advertiser/server.js   ← present
```

The Dockerfile's `CMD ["node", "apps/advertiser/server.js"]` references this exact path.

### Dockerfile final state (the relevant section)

```dockerfile
COPY package.json package-lock.json ./
COPY packages ./packages
COPY apps/advertiser ./apps/advertiser
RUN npm install
```

The `rm -rf package-lock.json` antipattern is gone.

## Pitfalls Hit During the Fix

- **`npm run build --workspace advertiser` failed** with `No workspaces found: --workspace=advertiser`. The workspace name is `@tad/advertiser` (scoped), not `advertiser`. Workaround: `npx next build` from inside `apps/advertiser`. Also `npm run build --workspace apps/advertiser` (using the directory path) works.
- **`grep -rn apps/advertiser` timed out on `node_modules`.** Use `search_files` (ripgrep, which filters `node_modules`) instead of bare `grep -r`.
- **`read_file` failed on relative paths** because the session's logical cwd (`apps/advertiser`) didn't match the snapshot cwd. `terminal` (bash) worked with relative paths, but `read_file` needed paths relative to the snapshot cwd. Workaround: use absolute paths for `read_file`, or `cat` via `terminal`.
- **`app/layout.tsx` (App Router) does NOT import `globals.css`** in this portal — only `pages/_app.tsx` does (`import '../styles/globals.css'`). Since most advertiser routes are Pages Router pages, styling works. If a pure App Router route is added later, it would need to import the CSS itself or via the shared Layout component.

## What the Admin/Driver Siblings Look Like (v4 reference)

`apps/admin` and `apps/driver` use the correct v4 pattern:

```
apps/admin/postcss.config.mjs:
  const config = { plugins: { "@tailwindcss/postcss": {} } };
  export default config;

apps/admin/styles/globals.css (head):
  @import "tailwindcss";
  @theme {
    --color-tad-yellow: #FFD400;
    --color-tad-accent: #ffae00;
    --font-sans: "Inter", ui-sans-serif, system-ui;
    ...
  }
```

No `tailwind.config.js` in either. Their `package.json` explicitly lists `tailwindcss@^4`, `@tailwindcss/postcss`, `postcss`, `autoprefixer`.

## If Mistake Recurs in Another Portal

The same v3→v4 migration gap could still exist in `apps/driver` or `apps/admin` if someone reverts. The 5-step recipe in the SKILL.md "Pattern 5" section is the canonical fix. Always diff against a known-working sibling first.
