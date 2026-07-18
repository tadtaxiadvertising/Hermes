# Metadata incompatibility & Kotlin compile fixes

## Kotlin 2.1.20 can't read metadata 2.3.0

**Symptom**: `KspDebugKotlin` fails with `<library> was compiled with an incompatible version of Kotlin. The binary version of its metadata is 2.3.0, expected version is 2.0.0`.

**Root cause**: Supabase 3.6.0 → Ktor 3.4.3 → both compiled with Kotlin 2.3.x metadata. Kotlin 2.1.20 reads metadata up to 2.1.x, not 2.3.x.

**Fix chain**:
1. Downgrade Supabase to **3.1.0** (last metadata-2.1.x-compatible release)
2. Downgrade Ktor to **2.3.11** and force every Ktor module in `configurations.all.resolutionStrategy`
3. Force `kotlin-stdlib`, `kotlin-reflect`, `kotlinx-serialization-core/json`, `kotlinx-io-core/bytestring` to versions compiled with Kotlin 2.1.x

## `realtime-kt:3.1.0` is NOT Kotlin 2.1-safe despite sharing the Supabase 3.1 branch

**Symptom chain** (appears even when `postgrest-kt:3.1.0` and `auth-kt:3.1.0` are fine):

| Site | Error |
|---|---|
| `suppress realtime.channel(...)` | `Unresolved reference 'realtime'` |
| standalone `channel(...).apply { broadcast { ... } }` | `Unresolved reference 'channel'` |
| `broadcast { ack = true }` inside channel DSL | `Unresolved reference 'ack'` / `No value passed for parameter 'event'` |
| `channel.broadcast(event, ...)` | `Suspend function ... can only be called from a coroutine` |
| `unsubscribe()` / `removeChannel(...)` | Also unresolved after the property itself fails |

**Fix**: Do not try to repair the calls. The artifact's metadata prevents the symbols from resolving. Confirm all Realtime usage is removed, delete the `realtime-kt` dependency, and document a post-migration path to restore the Admin Map live-ping via a non-Supabase channel if/when the Kotlin toolchain catches up.

### Hard-remove checklist (already applied in `apps/driver-android`)

- [ ] remove `realtime-kt` from `app/build.gradle.kts` dependencies
- [ ] comment out `import io.github.jan.supabase.realtime.Realtime` in `TadApplication.kt`
- [ ] comment out `install(Realtime)` in the Supabase client builder
- [ ] remove `RealtimeChannel`, `SupabaseClient`, `broadcast()`, `buildJsonObject/put` imports from `TelemetryForegroundService.kt`
- [ ] stub out `initRealtimeChannel()`, `broadcastLivePing()`, `epochToIso()`
- [ ] remove `realtimeChannel`, `lastLivePingTs`, `LIVE_PING_THROTTLE_MS` fields and their use sites
- [ ] replace `database.withTransaction { ... }` with sequential `insertAll(...)` + `deleteByStatus(...)` (Realtime paths were the only callers of `withTransaction` in that service)

After the hard-remove, the Android driver app's offline-first contract (`5 min flush → 50-chunk drip-sync → eviction at 500 → 402 kill-switch → Room WAL`) is untouched — only Admin Map ephemeral live-ping is temporarily deferred.

## `MutableStateFlow.update` unresolvable

**Symptom**: `Unresolved reference 'update'` followed by `Unresolved reference 'it'` on every `_uiState.update { it.copy(...) }` call.

**Root cause**: `update` is a `kotlinx.coroutines.flow` extension function, NOT a member of `MutableStateFlow`. Requires explicit `import kotlinx.coroutines.flow.update`.

## `.collect()` on combine fails

**Symptom**: `No value passed for parameter 'collector'`

**Fix**: Use `.launchIn(viewModelScope)` (requires `import kotlinx.coroutines.flow.launchIn`) or `.collect { }` with empty lambda.

## Compose API name changes

| Old | New | Error message |
|---|---|---|
| `StaticCompositionLocal<T> { ... }` | `staticCompositionLocalOf<T> { ... }` | `Unresolved reference 'StaticCompositionLocal'` |
| (implicit `BorderStroke`) | `import androidx.compose.foundation.BorderStroke` | `Unresolved reference 'BorderStroke'` |

## Bare `return` in Compose lambdas

**Symptom**: `'return' is prohibited here`

**Fix**: Replace bare `return` with `return@run` inside `run { ... }` blocks used inside `Button(onClick = ...)` or `scope.launch { ... }`. For `?: run { ...; return }`, use `return@run` to exit the run lambda rather than the enclosing function.

## Compile-error triage order

When iterating on Kotlin/Android builds, verify in this order — the first passing phase eliminates entire classes of error:

1. `processDebugResources` — resource linking (missing drawables, theme attrs)
2. `kspDebugKotlin` — Hilt/Room/KSP code generation (metadata version errors surface here)
3. `compileDebugKotlin` — actual source compilation (type errors, unresolved references)
4. `mergeExtDexDebug` — final packaging (duplicate classes, method limit)

Only when KSP passes is it worth looking at compile errors — everything before that is toolchain or metadata.