---
name: android-native-dev
title: Android Native Development
description: "Skills for Android Kotlin/Gradle work — build debugging, dependency resolution, room, supabase Realtime 3.x, compose nav. Use when fixing metadata mismatches, DAO suspend constraints, or OneDrive-sync build issues."
---

# Android Native Development

## Commitment Rules (non-negotiable for this project)

1. **Verification contract** — you must show named errors, file paths, and line numbers; "close enough" does not count.
2. **Work continues after verification** — verification is not the end state; fixes follow immediately.
3. **Stated scope is a floor, not a ceiling** — if a root cause is found outside the named scope, fix it too.
4. **State rebuild attempt** — if a problem persists or status is unclear, attempt a full rebuild rather than continuing from assumed state.
5. **Each dialogue is a cohesive unit** — plan, execute, and deliver in one coherent flow.
6. **Confirm before presuming** — when findings contradict your prep, stop and ask before re-planning.

## When to Use

- Fixing Gradle/Kotlin compile errors: `metadata` mismatch, `module-info.class`, Kotlin stdlib version conflicts
- Debugging dependency resolution: force downgrades, resolutionStrategy
- Room: transaction constraints, DAO suspend patterns
- Supabase Kotlin SDK 3.x: Realtime channel API, broadcast parameters, version pinning
- Compose navigation: screen parameter contracts, NavHost wiring
- OneDrive-synced path warnings for build/test commands

---

## 1. Kotlin Metadata Mismatch (most common)

### Sign
`KotlinMetadataVersion` exception; module-info.class version mismatch; stdlib 2.3.x vs Kotlin compiler 2.1.x.

### Root cause
A dependency was compiled against a newer Kotlin metadata version than the project's compiler can handle.

### Fix — resolutionStrategy
```kotlin
configurations.all {
    resolutionStrategy {
        force("org.jetbrains.kotlin:kotlin-stdlib:2.1.20")
        force("org.jetbrains.kotlin:kotlin-stdlib-jdk7:2.1.20")
        force("org.jetbrains.kotlin:kotlin-stdlib-jdk8:2.1.20")
        force("org.jetbrains.kotlin:kotlin-reflect:2.1.20")
        force("io.ktor:ktor-client-core:2.3.11")
        force("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    }
}
```

### Downgrade Supabase
Supabase 3.6.0+ JAR uses Kotlin 2.3.0 metadata. Pin 3.1.0. Group: `io.github.jan-tennert.supabase`, not `io.github.jan.supabase`.

### Verification command
```bash
JAVA_HOME=/c/tad-android-sdk/jdk-17.0.9 ANDROID_HOME=/c/tad-android-sdk ANDROID_SDK_ROOT=/c/tad-android-sdk ./gradlew :app:assembleDebug --no-daemon --no-configuration-cache --rerun-tasks 2>&1 | tail -n 60
```

---

## 2. Room Transaction Constraints (Room 2.6.x)

**RULE**: `database.withTransaction { }` does NOT support `suspend` lambdas in Room 2.6.x.
If the lambda contains DAO calls annotated `suspend`, the transaction block will fail to compile.

**Wrong**
```kotlin
database.withTransaction {
    telemetryDao.insertAll(offlineCoords)   // suspend DAO — compile error
}
```

**Right**: Move suspend calls outside withTransaction block, or use `database.runInTransaction { ... }` from a non-suspend context.

---

## 3. Supabase Realtime 3.x API (correct usage)

### Channel creation — use `.apply {}`, NOT DSL lambda
```kotlin
val channel = supabaseClient.realtime.channel("fleet_tracking_live").apply {
    broadcast { ack = true }
}
realtimeChannel = channel
```

### Broadcast — named params `event` and `message` (NOT `payload`)
```kotlin
serviceScope.launch {
    try {
        channel.broadcast(
            event = "telemetry_ping",
            message = buildJsonObject {
                put("driverId", driverId)
                put("lat", location.latitude)
            }
        )
    } catch (e: Exception) {
        Log.w(TAG, "broadcast failed: ${e.message}")
    }
}
```

### Subscribe / Unsubscribe — both `suspend`, must be in coroutine
```kotlin
serviceScope.launch {
    try { channel.subscribe() } catch (e: Exception) { Log.e(TAG, "subscribe failed", e) }
}
serviceScope.launch { channel.unsubscribe() }
```

---

## 4. OneDrive-Sync Build Constraint (project rule v12)

**RULE**: Do NOT run Gradle builds inside OneDrive-synced paths.

**Detection symptom**: `gradlew` hangs with no CPU/network activity after 2-3 minutes.

**Fix**: Move project checkout to a non-synced drive. Set `JAVA_HOME` and `ANDROID_HOME` vars before running — these persist across `terminal()` calls in the same Hermes session.

---

## 5. Compose Navigation: Screen Parameter Contracts

**Pattern**: Each `@Composable` screen defines named lambda params. The `NavHost` call site must pass the same names.

**Symptom**: Generic compile error `No parameter with name 'X' found` = name mismatch between NavHost call and screen definition.

---

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `withTransaction` + suspend DAO | `Suspension functions can only be called within coroutine` | Move suspend calls outside withTransaction |
| `realtime.channel { }` lambda form | `Cannot infer type for this parameter` | Use `.apply {}` |
| `broadcast(payload=...)` | `No parameter with name 'payload' found` | Use `message =` |
| `subscribe()` not in coroutine | `Suspend function ... can only be called from coroutine` | Wrap in `serviceScope.launch { channel.subscribe() }` |
| Wrong Supabase Maven group | Version pin silently fails | Use `io.github.jan-tennert.supabase` |
| Build in OneDrive sync path | Gradle hangs indefinitely | Move checkout to non-synced drive first |
