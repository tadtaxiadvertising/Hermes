# killswitch-interceptor-recursion-fix.md

## Why `bareApiService` exists

The KillSwitchInterceptor on HTTP 401 silently re-logs in with cached driver credentials using `TadApiService.login(phone, password)`. Naively wiring it to `TadApiClient.apiService` creates infinite recursion because that service is built from the same OkHttpClient that owns the interceptor:

  apiService -> Retrofit -> OkHttpClient -> KillSwitchInterceptor -> apiService.login(...) -> Retrofit -> ...

## Fix

Expose two `TadApiService` instances from `TadApiClient`:
- `apiService` — full chain (NetworkMonitor -> KillSwitch -> Logging)
- `bareApiService` — stripped chain (NetworkMonitor + Logging only; no KillSwitch, no auth headers)

The interceptor receives only `bareApiService` for re-login. The Hilt wiring in `NetworkModule.provideKillSwitchInterceptor()` passes `TadApiClient.bareApiService` directly.

## AuthDao credential contract

401 re-login path reads two Room keys (written at login time):
- `AUTH_KEY_PHONE` (= "tad_driver_phone")
- `AUTH_KEY_PASSWORD` (= "tad_driver_password")

If either is missing, skip re-login and set `GlobalState.forceLogoutReason = "TOKEN_EXPIRED"` so the UI navigates to LoginScreen.
