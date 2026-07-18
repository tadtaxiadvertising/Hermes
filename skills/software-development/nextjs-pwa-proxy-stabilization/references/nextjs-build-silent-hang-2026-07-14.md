# Session Evidence: Next.js Build Silent Hang on Windows/OneDrive Monorepo

## Date
2026-07-14

## Affected Project
TAD DOOH Platform — `apps/admin`, `apps/advertiser`, possibly all Next.js portals

## Symptom
`npm run build` (i.e. `next build`) produces **zero stdout** and eventually times out after the terminal timeout limit (300s), returning exit 124. No error messages, no compilation output, no ENOENT — just complete silence until the process is killed by timeout.

## Commands That Reproduced It
```bash
cd apps/admin && npm run build        # hangs, no output
cd apps/admin && npx tsc --noEmit    # passes clean (exit 0)
npx next info                        # passes clean, shows Next 15.2.6 / React 19 / Node 22
```

## Root Cause
Environmental filesystem contention on **Windows + OneDrive-synced working tree**. Not a code regression. `tsc --noEmit` passes, `next info` works, but `next build` (which performs SWC transforms, file tracing, and writes thousands of small files to `.next/`) is sensitive to OneDrive's opportunistic file locking and path-resolution overhead. The process blocks silently during the compilation/write phase.

## Workarounds (in order of preference)
1. Build from a **non-OneDrive working tree** (e.g. clone to `C:\repos\tad-dooh-platform` instead of `C:\Users\...\OneDrive\...`)
2. Let **EasyPanel/CI** run the build remotely — push to a branch and let the container builder handle it
3. Accept `tsc --noEmit` as the local verification gate when `next build` is unusable; treat it as the "compilation correctness" signal and rely on CI for "full bundle integrity"

## Key Distinction
This is **not** the Pattern 6 `ENOENT _app.js.nft.json` issue (which has a clear error message and is fixed by `rm -rf .next`). This is a stricter failure mode: **no error message at all, just a hang**.

## Skill Update
The pitfall was patched into `nextjs-pwa-proxy-stabilization` Pattern 6 under "Pitfalls" with the heading:
> **`next build` can silently hang on Windows/OneDrive monorepos with no output at all**
