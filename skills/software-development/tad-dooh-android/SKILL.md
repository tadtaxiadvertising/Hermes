---
name: tad-dooh-android
title: TAD DOOH Android Driver App
description: >
  Android driver app (Kotlin, Jetpack Compose, Hilt, Room, Retrofit) for the
  TAD DOOH Platform. Use when the user wants to refactor DI, fix Gradle build,
  migrate to Hilt, or audit the driver-android module (apps/driver-android).
---

# TAD DOOH Android Driver App

Canonical tree: `di/` (Hilt modules), `data/local/` (Room), `data/remote/` (Retrofit + interceptors), `service/` (foreground), `worker/` (WorkManager), `ui/` (Compose + `TadNavHost`), `ui/viewmodel/`.

## Hilt structure

- `TadApplication` is `@HiltAndroidApp` + `Configuration.Provider` (injects `HiltWorkerFactory`).
- ViewModels are `@HiltViewModel` + `@Inject constructor`; obtained in Compose via `hiltViewModel()`.
- `TadApiClient` stays as Kotlin `object`; `NetworkModule` exposes it via `@Provides` to keep call sites intact.

### Interceptor recursion

KillSwitchInterceptor must not call `apiService` through the same Retrofit client chain. `TadApiClient` exposes `apiService` (full chain) and `bareApiService` (no KillSwitch, no auth). The interceptor gets `bareApiService` for its silent re-login call.

### Workers

Workers are `@HiltWorker` + `@AssistedInject constructor(@Assisted ctx, @Assisted params, ...)`. No extra `@Module` binding needed; KSP emits it. Do not use `TadApplication.getInstance()` inside a worker.

## Interceptor → service-locator boundary

Not every type can have a clean constructor: `TelemetryRepository` requires `TadApplication` and several DAOs. The supported migration pattern:

- Keep `KillSwitchInterceptor` cleanly injected (DI) via `@Provides` + `@ApplicationContext`.
- The legacy non-Hilt singleton stays as `TelemetryRepository(app)` exposed via `TadApplication.getInstance(); `
- Expose a `companion object create(Context)` factory in `TelemetryRepository` for Tests/new ViewModels; don't delete the non-Hilt side until the service itself is explicitly migrated in a ticket.
- An empty Hilt module with no bindings is **invalid** and will fail at processing.

## Gradle gotchas

- `settings.gradle.kts` uses `dependencyResolutionManagement { ... }`; `dependencyResolution { ... }` is invalid.
- Root + app build files both need `com.google.dagger.hilt.android` plugin alias declared.
- `local.properties` must exist with `sdk.dir=<absolute-path>` before any Gradle invocation; without it Gradle won't find the Android SDK even if it's installed.

### Transitive dep conflicts under AGP 8.7 / compileSdk 35

- Supabase `3.6.0` transitively pulls Ktor 3.x / Kotlin metadata 2.3.x, incompatible with Kotlin 2.1.x compilers. Downgrade to Supabase `3.1.0` + Ktor `2.3.11` rather than upgrading the Kotlin compiler:

  - `postgrest-kt:3.1.0` → ✅ metadata 2.1.x compatible
  - `auth-kt:3.1.0` → ✅ metadata 2.1.x compatible
  - `realtime-kt:3.1.0` → ❌ metadata 2.3.x **despite its version**; APIs like `supabaseClient.realtime.channel(...)`, `channel { broadcast { ... } }`, and standalone `channel()` / `broadcast()` all fail with `Unresolved reference` on a Kotlin 2.1.x compiler.
  ```kotlin
  // Build-level forcing — MUST cover all Ktor modules the transitive tree pulls
  configurations.all {
      resolutionStrategy {
          force("org.jetbrains.kotlin:kotlin-stdlib:2.1.20")
          force("org.jetbrains.kotlin:kotlin-reflect:2.1.20")
          force("org.jetbrains.kotlinx:kotlinx-serialization-core:1.7.3")
          force("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
          force("org.jetbrains.ktor:ktor-client-core:2.3.11")
          force("org.jetbrains.ktor:ktor-client-okhttp:2.3.11")
          force("org.jetbrains.ktor:ktor-client-content-negotiation:2.3.11")
          force("org.jetbrains.ktor:ktor-serialization-kotlinx-json:2.3.11")
          force("org.jetbrains.kotlinx:kotlinx-io-core:0.5.3")
          force("org.jetbrains.kotlinx:kotlinx-io-bytestring:0.5.3")
      }
  }
  ```
- Keep the root Kotlin plugin at `2.1.20` — do NOT upgrade it to match library metadata. The mismatch is in the library artifacts, not the compiler version.
- Verify KSP actually ran by checking the exit status of `kspDebugKotlin` separately from `compileDebugKotlin` in log output.
- The coordinates `io.github.jan-tennert.supabase:auth-kt:2.6.1` (and other `*:2.6.1` artifacts) do **not** exist in Maven Central; the 2.x line was never published. Use `3.1.0` (not `3.6.0`) consistently across `postgrest-kt`, `auth-kt` for Kotlin 2.1.x compatibility.

### Hilt 2.52 → 2.56.2 for Kotlin metadata 2.3.x

**Symptom**: `:app:hiltJavaCompileDebug` fails with ``` java.lang.IllegalStateException: Unable to read Kotlin metadata due to unsupported metadata version. ``` at `dagger.internal.codegen.kotlin.KotlinMetadata.metadataOf`.

**Root cause**: Hilt 2.52's annotation processor can't read Kotlin metadata 2.3.x (pulled in transitively by `supabase-kt:3.1.0`). The Kotlin compiler itself compiles fine — only Hilt's Java processor chokes.

**Fix**: Upgrade Hilt to **2.56.2** in BOTH:
```kotlin
// root build.gradle.kts
id("com.google.dagger.hilt.android") version "2.56.2" apply false

// app/build.gradle.kts
implementation("com.google.dagger:hilt-android:2.56.2")
ksp("com.google.dagger:hilt-compiler:2.56.2")
```
2.56.x supports Kotlin 2.x metadata. No other dependency changes required.

### `@HiltAndroidApp` classes are not directly injectable

**Symptom**: `:app:hiltJavaCompileDebug` fails with ``` dagger.MissingBinding: com.tad.dooh.driver.TadApplication cannot be provided without an @Inject constructor or an @Provides-annotated method. This type supports members injection but cannot be implicitly provided. ```

**Root cause**: `TadApplication` (annotated `@HiltAndroidApp`) only supports **members injection** (Hilt generates `TadApplication_GeneratedInjector` for it), not direct provision. Requesting it as a `@Provides` method parameter fails because Hilt can't implicitly construct or provide it.

**Fix pattern**: Retrieve the instance via `context.applicationContext` inside the `@Provides` method, keeping the legacy constructor shape intact without migrating the target class to Hilt:
```kotlin
@Module @InstallIn(SingletonComponent::class)
object RepositoryModule {
  @Provides @Singleton
  fun provideTelemetryRepository(
    @ApplicationContext context: Context,
    telemetryDao: TelemetryDao,
    authDao: AuthDao,
    apiService: TadApiService
  ): TelemetryRepository {
    val app = context.applicationContext as? com.tad.dooh.driver.TadApplication
      ?: throw IllegalStateException("Context is not TadApplication")
    return TelemetryRepository(context, telemetryDao, authDao, apiService, app)
  }
}
```
This avoids introducing an `@Inject` constructor on `TelemetryRepository` solely for Hilt and preserves call sites like `TelemetryRepository.create(context)` for tests and UI.

### OneDrive verification bypass (regla v12)

**Symptom**: Gradle hangs, `processDebugResources` fails with `The process cannot access the file because it is being used by another process`, or terminal commands stall indefinitely inside `C:\Users\<user>\OneDrive\...`.

**Fix**: Copy just the `apps/driver-android` module to a non-synced path (e.g. `C:\tad-build\driver-android`) and run Gradle from there:
```bash
cp -r "C:/Users/.../OneDrive/.../apps/driver-android" C:/tad-build/driver-android
cd C:/tad-build/driver-android
export JAVA_HOME=/c/tad-android-sdk/jdk-17.0.9
export ANDROID_HOME=/c/tad-android-sdk
./gradlew :app:compileDebugKotlin --no-daemon --offline
```
Use `--offline` after first successful download to avoid network stalls. The original OneDrive location is still the source of truth; copy back only after green build.

### Kotlin / Compose type-level pitfalls

- **`MutableStateFlow.update` is an extension function**: Requires explicit `import kotlinx.coroutines.flow.update`. Without it, every call site produces `Unresolved reference 'update'` and cascading `Unresolved reference 'it'` even when the lambda syntax looks correct.
- **`.collect()` on combine results**: `combine(...) { ... }.collect()` can fail with `No value passed for parameter 'collector'` in some Kotlin coroutines library configurations. Replace with `.launchIn(viewModelScope)` (requires `import kotlinx.coroutines.flow.launchIn`) or `.collect { }` with an empty callback.
- **`BorderStroke` requires explicit import**: Not covered by `import androidx.compose.foundation.*` — write `import androidx.compose.foundation.BorderStroke` explicitly.
- **`StaticCompositionLocal` → `staticCompositionLocalOf`**: Renamed in Compose 1.5+. Both the import and the constructor call must change (the old name was the type, not a function).
- **Bare `return` in Compose lambdas**: Inside a `Button(onClick = { ... })` or `run { ... }` block, bare `return` is prohibited. Use `return@run` or restructure the closure — the error message is `'return' is prohibited here`.

### Resource linking hygiene

- Under a Material3 theme do **not** use the `android:` namespace for Material3 attrs (`colorPrimary`, `colorPrimaryVariant`, `colorSurface`, `colorOnPrimary`, `colorOnSurface`). Those belong in the app namespace when the parent is `Theme.Material3.Dark.NoActionBar`.
- `android:attr/colorPrimaryVariant` and `android:colorSurface` are private in SDK 35 and trigger `processDebugResources` failures; switch them to the non-android namespace equivalents.
- If the splash icon referenced at `@drawable/ic_splash_tad` is not present, Gradle stops on `mergeDebugResources`. Remove the reference until the drawable exists (the windowBackground color alone is a valid splash surrogate).

## Backend contract (auth)

- Driver JWT is HS256, 7-day expiry.
- No `/drivers/refresh` endpoint exists; renews only via `POST /api/v1/drivers/login`.
- 401 path must silently re-login via cached phone/password in `AuthDao`; never call Supabase GoTrue for drivers.
- 402 path: purge `tad_driver_token` and `TAD_DEVICE_ID`, set `GlobalState.isKillSwitchActive`, broadcast/logout.

## Offline-first

- Room uses WAL pragmas via `WalPragmaCallback.onOpen`.
- NetworkMonitorInterceptor throws `NetworkUnavailableException` on `NET_NONE` so callers can enqueue to `OfflineQueueDao`.

## Support files

- `references/killswitch-interceptor-recursion-fix.md` — why `bareApiService` exists, interceptor wiring, and `AuthDao` credential keys
- `references/gradle-aggregate-pitfalls.md` — common Gradle 8.11 / AGP 8.7 / KSP 2.0 pitfalls for this module

## Pitfalls

- Never invent a `/drivers/refresh` endpoint.
- Do not create `ui/screen/`. The real package is `ui/screens/` (plural) and is consumed by `TadNavHost`.
- Builds in OneDrive-synced paths hang; move outside OneDrive or pause sync before Gradle.
- `compileSdk = 35`, `minSdk = 24`, Java 17 target.
- Once KSP passes, the next failing Gradle task has real source errors — diff the compilation diagnostics before rerunning metadata-era resolutions.
- `TelemetrySyncWorker.Factory` should NOT be a duplicate; the module is deleted and the worker class remains as injectable assembly. No extra empty Hilt module binding is valid.
