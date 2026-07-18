# Session Evidence: TAD Driver Dashboard Refactor (2026-07-13)

## Outcome
Status: **code complete, verification partially complete**.

## What passed
- `tsc --noEmit -p tsconfig.json` → exit 0, only pre-existing `TS7016` lucide-react type-declaration warnings (not regressions).
- `next lint` → exit 0 on the real repo (`Documentos\GitHub\tad-dooh-platform\apps\driver`). None of the reported lint violations were in touched files; all are pre-existing in `pages/p/`, `pages/p/[id].tsx`, `pages/register.tsx`, `scratch/*.js`, `tests/e2e/*.spec.ts`.
- Architecture invariants preserved: `useTelemetry()` remains mounted in `pages/driver/dashboard.tsx` at page level; the new `DriverShell` child only swaps `<main>` content via internal `useState` tab switching.

## What blocked full verification
`next build` stalled at `Attempted to load @next/swc-win32-x64-msvc ... is not a valid Win32 application` and did not reach compile completion. This is a native SWC binary mismatch on this Windows host, not a code regression.

## Path-mirror trap (OneDrive duplicate roots)
The same repo is mirrored across two OneDrive paths:
- **Git root:** `...\Documentos\GitHub\tad-dooh-platform`
- **Mirror (non-git):** `...\Escritorio\TAD PLASTFORM\tad-dooh-platform`

`write_file` / `patch` from earlier in this session created new files under the mirror path, requiring an `cp` back to the git root before verification. Future sessions must:
1. Run `git rev-parse --show-toplevel` once and pin that path for all `write_file` / `patch` / `search_files` calls.
2. If `search_files` shows new files but `git status` still shows them as untracked under a non-git mirror, move/copy them into the git root before running `tsc` / `next build`.
3. Treat OneDrive-synced duplicates as untrusted paths; always operate from the git root.

## Changed files (git-root paths, verified present)
- `apps/driver/components/dashboard/BottomNavigationBar.tsx` (new)
- `apps/driver/components/dashboard/BottomNavigation.tsx` (deprecated annotation)
- `apps/driver/components/dashboard/DriverShell.tsx` (new)
- `apps/driver/components/dashboard/RoutesTab.tsx` (new)
- `apps/driver/components/dashboard/SettingsTab.tsx` (new)
- `apps/driver/components/dashboard/WalletTab.tsx` (new)
- `apps/driver/components/dashboard/dashboard-utils.tsx` (new)
- `apps/driver/pages/driver/dashboard.tsx` (refactored to thin wrapper)
- `apps/driver/pages/driver/wallet.tsx` (rewritten to use shared WalletTab)

## Unchanged invariants (zero-touch)
- `hooks/useTelemetry.ts`
- `hooks/useBackgroundTelemetry.ts`
- `hooks/useDriverHub.ts`
- `lib/offlineQueue.ts`
- `store/usePaymentStore.ts`
- `pages/_app.tsx`, `pages/_document.tsx`, `styles/globals.css`
- `components/BankForm.tsx`
- `components/dashboard/KillSwitchOverlay.tsx`

## Commands actually run
```bash
cd C:\Users\Arismendy\OneDrive\Documentos\GitHub\tad-dooh-platform\apps\driver
npx tsc --noEmit -p tsconfig.json   # exit 0
npx next lint --dir .               # exit 0 (pre-existing violations only)
npx next build                       # stalled on SWC native binary, not a code error
```
