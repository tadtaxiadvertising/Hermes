# Eventos de Notificaciones en Tiempo Real

## Esquema del Payload

```ts
type NotificationEnvelope = {
  type: NotificationType;
  receivedAt: number;
  payload: Record<string, unknown>;
};

type NotificationType =
  | 'PAYMENT_LIQUIDATED'
  | 'CAMPAIGN_ASSIGNED'
  | 'SUBS_WARNING'
  | 'SUBS_CRITICAL'
  | 'DRIVER_STATUS';
```

## Tipos Soportados

### `PAYMENT_LIQUIDATED`

**Disparador:** Liquidación de nómina mensual completada.

**Payload esperado:**
```ts
{
  amount: number;        // Monto en RD$
  currency: string;      // 'RD$'
  month: string;         // 'Enero', 'Febrero', etc.
  year: number;          // 2026
  activeAds: number;     // Cantidad de anuncios activos
  paidAt: string;        // ISO timestamp
}
```

**UI:** Toast de celebración (success) con ayuda de `sonner`.

---

### `CAMPAIGN_ASSIGNED`

**Disparador:** Nueva campaña asignada al conductor.

**Payload esperado:**
```ts
{
  campaignId: string;
  campaignName: string;
  startDate: string;     // ISO timestamp
  endDate: string;       // ISO timestamp
  dailyRate: number;     // RD$ por día
}
```

**UI:** Toast info ("Nueva campaña asignada").

---

### `SUBS_WARNING`

**Disparador:** Suscripción próxima a vencer (7 días de禅).

**Payload esperado:**
```ts
{
  message: string;       // "Quedan 7 días para tu renovación."
  daysRemaining: number;
  renewalAmount: number; // RD$6,000
}
```

**UI:** Toast warning.

---

### `SUBS_CRITICAL`

**Disparador:** Suscripción vencida o pago pendiente.

**Payload esperado:**
```ts
{
  message: string;       // "Regulariza tu pago para evitar el bloqueo."
  daysOverdue: number;
  penaltyAmount?: number;
}
```

**UI:** Toast error (puede activar kill-switch).

---

### `DRIVER_STATUS`

**Disparador:** Cambio de estado del conductor (offline, locked, suspended).

**Payload esperado:**
```ts
{
  status: 'online' | 'offline' | 'locked' | 'suspended';
  message: string;       // Razón del cambio
  reason?: 'PAYMENT_UNPAID' | 'ADMIN.action' | 'SYSTEM';
}
```

**UI:** Toast error si `status === 'offline' | 'locked'`.

---

## Backend: Enviar Notificación

```ts
// En cualquier servicio inyectado con NotificationsService
await this.notificationsService.sendDriverNotification(
  driverId,
  'PAYMENT_LIQUIDATED',
  {
    amount: 25000,
    currency: 'RD$',
    month: 'Enero',
    year: 2026,
    activeAds: 12,
    paidAt: new Date().toISOString(),
  }
);
```

---

## Frontend: Suscribirse

```tsx
import { useNotifications } from '@/contexts/NotificationContext';

function Dashboard() {
  const { lastEvent } = useNotifications();

  // La UI se re-renderiza automáticamente cuando llega un evento
  useEffect(() => {
    if (!lastEvent) return;

    if (lastEvent.type === 'PAYMENT_LIQUIDATED') {
      toast.success('Pago recibido', {
        description: `RD$${lastEvent.payload.amount}`,
      });
    }
  }, [lastEvent]);

  return <div>...</div>;
}
```

---

## Deduplicación

- **TTL:** 5 minutos (`DEDUP_TTL_MS = 5 * 60 * 1000`).
- **Clave estable:** `stableKey(type, payload)` ~ `JSON.stringify({type, payloadOrdenado})`.
- **Persistencia:** `localStorage` bajo `tad_driver_notifications_v1`.

Evitar enviar el mismo evento (mismo `type` + `payload`) dentro del mismo TTL.