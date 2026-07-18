---
name: tad-dooh-backend-notifications
description: "TAD DOOH backend notification wiring: private Supabase Realtime channels for drivers, campaign-assignment events, payment-liquidated events, and DI of NotificationsService across NestJS modules."
version: 1.0.0
author: Hermes Agent
platforms: [windows, linux]
tags: [nestjs, supabase, realtime, notifications, tad, monorepo]
---

# TAD DOOH Backend Notifications

## Scope

All backend notification emission in the TAD DOOH monorepo: private driver channels, campaign assignment events, payment-liquidated events, and reuse of `NotificationsService` from domain services (`FinanceService`, `CampaignService`, `FleetService`).

## Canonical Realtime Contract

- Private driver channel: `driver_notifications_${driverId}`.
- Fleet/default broadcast channel: `fleet_sync`.
- Prefer private driver channels when the event is actionable per-driver. Use fleet channels for broadcast-only wake-up calls.
- Every backend emit is best-effort: swallow failures, log them, never throw from notification code.

## Required Backend Layering

1. `NotificationsService` owns the send path.
2. Domain services call `NotificationsService`, never open channels inline.
3. New events go in this order:
 - Add the event type constant in `NotificationContext` frontend.
 - Add the emit site in the relevant domain service.
 - Do NOT add publish logic inside `SupabaseService` callers outside `NotificationsService`.

## NestJS DI Gotcha

When adding `NotificationsService` to a domain service constructor:
- Import `NotificationsService` explicitly from `../notifications/notifications.service`.
- Add `NotificationsModule` to the owning module `imports` (FinanceModule already does this in the current codebase).
- Do NOT collapse notification emission into `SupabaseService.broadcastEvent`. Keep the domain service thin and delegate to `this.notificationsService.sendDriverNotification(...)`.

## Verification
Before calling done, verify the notification surface, not just build:
- Confirm the changed service is covered by an import that exercises `sendDriverNotification` directly or indirectly through its broadcast/channel code paths.
- Prefer running the relevant project's build/test command; do not infer success from prior session evidence.

## Emit Pattern

Use `sendDriverNotification(driverId, eventType, payload)` for driver-private pushes. Use `supabaseService.broadcastEvent('fleet_sync', ...)` only for fleet broadcast.

## Driver Identification

Resolve `driverId` from `device.driverId` or `Driver` relations in the same transaction that triggers the event. If the driver is unknown or absent, skip driver notification but keep the fleet broadcast.

## Failure Policy

Notifications are non-critical UX value:
- Log a warning on send failure.
- Do not rollback the surrounding transaction for a failed notification publish.
- Do not create retry loops in NestJS unless BullMQ/Redis is provisioned.

## Across-Session Detail

See `references/driver-notification-channels.md` for the exact channel names and event types currently emitted, plus current call sites for payment/campaign notifications.
