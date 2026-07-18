---
name: tad-portal-dev
description: "TAD DOOH Platform portal development: auth integration, portal-specific login pages, and Tailwind v4 conventions for Next.js Pages Router apps."
version: 1.0.0
author: Hermes Agent
platforms: [windows, linux]
tags: [nextjs, tailwind-v4, auth, tad, monorepo]
---

# TAD Portal Development

## Scope

Building or modifying portal login pages and auth integration in the TAD DOOH monorepo (`apps/admin`, `apps/advertiser`, `apps/driver`). Covers the full stack: visual spec compliance, auth backend integration, and portal-specific conventions.

---

## Auth Integration Pattern (MANDATORY)

Every portal login page MUST integrate with the backend — a visual-only submit that only `console.log`s is broken. Use this exact pattern:

```tsx
// 1. State
const [email, setEmail] = useState('admin@tad.do');
const [password, setPassword] = useState('');
const [error, setError] = useState<string | null>(null);
const [submitting, setSubmitting] = useState(false);
const router = useRouter();

// 2. API base — use env, fallback to production
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  'https://proyecto-ia-tad-api.rewvid.easypanel.host/api';

// 3. Submit handler
const handleSubmit = async (e: FormEvent) => {
  e.preventDefault();
  setError(null);
  setSubmitting(true);

  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email, password }),
      cache: 'no-store',
    });

    if (!res.ok) {
      const text = await res.text().catch(() => 'Credenciales inválidas.');
      throw new Error(text);
    }

    const data = (await res.json()) as LoginResponse;
    const user = data.user ?? { id: '', email, role: 'GUEST', entityId: null };

    const tokenPayload = { id: user.id, email: user.email, role: user.role, entityId: user.entityId };

    localStorage.setItem('tad_admin_token', data.access_token);
    localStorage.setItem('tad_admin_refresh_token', data.refresh_token);
    localStorage.setItem('tad_admin_user', JSON.stringify(tokenPayload));

    (window as any).__tad_user = tokenPayload;

    router.replace('/admin/dashboard'); // varies by portal
  } catch (err) {
    setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión.');
  } finally {
    setSubmitting(false);
  }
};
```

### Portal-specific localStorage keys and redirect

| Portal | Token key | Redirect |
|---|---|---|
| admin | `tad_admin_token` | `/admin/dashboard` |
| advertiser | `tad_advertiser_token` | `/advertiser/dashboard` |
| driver | `tad_driver_token` | `/driver/dashboard` |

### API contract

- **Endpoint:** `POST {API_BASE_URL}/auth/login`
- **Request body:** `{ "email": string, "password": string }`
- **Success response (200):**
  ```json
  {
    "access_token": "string",
    "refresh_token": "string",
    "user": { "id": "string", "email": "string", "role": "ADMIN|ADVERTISER|DRIVER", "entityId": "string|null" }
  }
  ```
- **Error (401/403):** plain text or `{ "message": "..." }`

---

## Portal Login Visual Spec (TAD NODE Master Console)

Follow v12.1.1 for all portal login pages:

1. **Background:** `#000000` with SVG grid (streets) + radial-gradient pulsing yellow nodes representing active fleet. No images.
2. **Card:** `rounded-[24px]`, `bg-black/40`, `backdrop-blur-xl`, `border-white/10`, `shadow-[0_0_40px_rgba(255,255,255,0.03)]` for soft elevation.
3. **Logo medallion:** circular, `bg-black`, silver border, portal-specific icon in `#fad400`.
4. **Inputs:** `border-white/10` → `border-[#eab308]` on focus with `shadow-[0_0_0_1px_rgba(234,179,8,0.35)]`.
5. **Password toggle:** Eye icon in `#eab308`, aria-label for accessibility.
6. **Submit button:** `bg-gradient-to-r from-[#eab308] to-[#fad400]`, bold black text, `shadow-[0_0_30px_rgba(234,179,8,0.25)]`, hover `scale-[1.02]`, submit icon (`Lock` for advertiser, `Shield` for admin).
7. **Verified Access badge:** icon + text in `text-gray-400`; use portal-appropriate icon (`Lock` for advertiser, `Shield` for admin).
8. **Footer:** `TAD Taxi Advertising S.R.L.` in `text-gray-600`, centered absolute bottom.
9. **Forbidden colors:** no standard Bootstrap blues, greens, or reds for primary elements. Only TAD Yellow + Black + White.

### Unification rule

`apps/admin/pages/admin/login.tsx` and `apps/advertiser/pages/login.tsx` should share the same Tailwind utility vocabulary, focus ring tokens, button treatment, and SVG background. When updating one login page, apply the same visual changes to the other to keep portals consistent.

### Portal-specific titles and copy

| Portal | Main title | Subtitle |
|---|---|---|
| admin | `TAD NODE` | `Centro de Control Administrativo` |
| advertiser | `TAD ADVERTISER` | `Panel de Control de Campañas` |
| driver | `TAD DRIVER` | `Portal del Conductor` |

---

## Tailwind v4 Conventions

- Use `@import "tailwindcss"` + `@theme {}` block in `globals.css`. NO `tailwind.config.js`.
- CSS-first: utility classes, `@apply` in custom classes inside `globals.css`.
- No inline styles.
- Portal-specific CSS lives in each app's `styles/globals.css`.

---

## Verification

After any change in the driver app, run **both** checks in `apps/driver` before claiming success:
1. `npx tsc --noEmit` — confirm there are no new TS errors.
2. `npm run build` — preferred final gate. If it times out on OneDrive-synced paths, use a non-synced copy or a working tree copied outside OneDrive; do not treat a build timeout as a code bug.

Confirm that `NotificationProvider`/`NotificationToast` stay wired through `_app.tsx` and toggle nothing public-page behavior.

---

## Pitfalls

- **Visual-only login:** submitting only `console.log`s — always integrate auth.
- **Wrong localStorage key:** must match portal type (`tad_admin_` vs `tad_advertiser_` vs `tad_driver_`).
- **Missing `cache: 'no-store'`** on the fetch — avoids stale credential caching.
- **OneDrive sync hangs on build:** run `npm run build` from a path not synced by OneDrive, or pause sync temporarily.
- **Wrong redirect URL:** advertiser portal redirects to `/advertiser/dashboard`, NOT `/admin/dashboard`.

---

## Realtime & Notificaciones (Driver Portal)

### Patrón canónico de notificaciones en el driver

1. **Backend (`finance.service.ts`, `campaign.service.ts`, etc.):**
   - Inyectar `NotificationsService` en los módulos que lo necesiten.
   - Llamar a `await this.notificationsService.sendDriverNotification(driverId, type, payload)`.
   - Soporta tipos: `'PAYMENT_LIQUIDATED' | 'CAMPAIGN_ASSIGNED' | 'SUBS_WARNING' | 'SUBS_CRITICAL' | 'DRIVER_STATUS'`.

2. **Frontend (`apps/driver`):**
   - **Ubicación:** `contexts/NotificationContext.tsx` + `components/Notifications/NotificationToast.tsx`.
   - **Provider:** Suscripción al canal `driver_notifications_<driverId>` con:
     - Deduplicación por TTL (5 min) vía `stableKey(type, payload)`.
     - Persistencia en `localStorage` (`tad_driver_notifications_v1`).
   - **Toast:** Componente global montado en `_app.tsx` que muestra:
     - Eventos de red (`online`/`offline`) con mensajes descriptivos.
     - Eventos de negocio (`PAYMENT_LIQUIDATED` → toast de celebración, `SUBS_CRITICAL` → error, etc.).
   - **Hook:** `useNotifications()` expone `lastEvent`, `push`, `subscribe`.

3. **Importacación:**
   - `supabase` ya está disponible vía `import('@tad/services').then(({ supabase }) => ...)`.
   - No crear canales adicionales; reutilizar la instancia del provider.

### Pitfalls adicionales
- **Dedup de notificaciones:** El TTL es 5min; evitar enviar el mismo evento repetido en esa ventana.
- **Tipo de payload:** Mantener la forma estable `Record<string, unknown>`; el hash de dedup depende de la serialización JSON.