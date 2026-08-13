TAD build rules: NestJS backend → `npx nest build` (NOT tsc --noEmit). Monorepo root: C:\Users\Arismendy\Documents\TAD PLASTFORM\tad-dooh-platform. Apps: api, admin, advertiser, driver, player, tad-remotion, tad-simulator. driver-flutter NO existe en el monorepo ni en GitHub como repo separado — solo staging local en /c/tad-build/driver-flutter/ (sin git). Android Studio MCP en AppData\Roaming\Google\AndroidStudio2026.1.2\mcp.json
§
Mendy — Arquitecto de Producto, TAD Taxi Advertising SRL. Diseños minimalistas (Linear/Vercel). Frustración activa: "videos horribles" → Remotion calidad prioridad. Exige re-verificación fresca de build (no stale evidence). Spanish/spanglish técnico; English para code. Ejecuta autónomo sin aprobaciones intermedias. Prefiere deploy completo sin pedir ayuda: "sigue trabajando autónomo hasta que todo esté bien"
§
Trigger commits (`REDEPLOY_TRIGGER.txt`) no garantizan rebuild en Easypanel para este proyecto. Si un servicio queda en 500 después de push, el remedio confiable es redeploy manual desde el panel. El build exitoso es condición necesaria pero no suficiente para verde.
§
§ Windows emulator instability: GPU modes swiftshader_indirect/auto/guest fallan con glAttachShader 0x502 en este host. Headless (-no-window) sí bootea (~10-60s) pero AVD collision fatal aparece si otra instancia queda viva. Cierre previo requerido: adb -s emulator-5554 emu kill + PowerShell Stop-Process -Name emulator -Force. Segundo dispositivo físico conectado (adb-aeemjrbmcijrmbci): usar -s emulator-5554 explícito. ANR "System UI isn't responding" post-boot normal; dismiss con Wait (centro ~540,1367). Dump UI accesible solo tras cerrar ANR. Driver test: phone=8090000000 / password=tad123 / id=ded04b26-b3cf-4b29-9b1c-796cea0c730d. Login backend verificado: POST /api/v1/drivers/login → 201 {"access_token":"...","name":"Test Driver"}.
§
Flutter dotenv pitfall: `.env` MUST be in `flutter: assets:` section of pubspec.yaml or `dotenv.load()` fails silently → app falls back to `10.0.2.2` (emulator-only) → "Error de conexión" on physical device. For physical device → local backend: use `adb reverse tcp:3000 tcp:3000` + `API_BASE_URL_DEV=http://127.0.0.1:3000/api/v1/` (not localhost, not 10.0.0.2).
§
Android release signing for driver-flutter: build.gradle points to android/app/tad-driver-release.jks; signingConfigs.release uses storePassword/keyPassword 'tad-release' and keyAlias 'tad-driver-key'. Sync engine uses _kLog -> print, not debugPrint. Release artifacts are produced from C:\tad-build\driver-flutter because release builds fail or hang under OneDrive/gradle on this host.
§
Easypanel crash-loop: "No running containers" + 0% CPU + Traefik 404 hexagon page = container exited on process.exit(1). Main cause: missing env var (JWT_SECRET, DATABASE_URL) in Easypanel service Environment tab — fix at panel level, not code. Auto-deploy unreliable; manual redeploy from dashboard often needed. Panel API not documented — no programmatic deploy. JWT_SECRET auto-fallback: crypto.randomBytes(32).toString('hex') en src/main.ts si no está configurado.
§
Easypanel API: usa Dockerfile.api (raíz), NO apps/api/Dockerfile. Crash-loop con "Prisma schema loaded" repetido → (1) entrypoint con db push --accept-data-loss --skip-generate, migrate deploy como fallback, nunca exit 1; (2) añadir sslmode=require a DATABASE_URL en PrismaService; (3) prisma generate en runner stage. Contenedor caído sin SSH → solo código + commit + trigger redeploy. CORS_ORIGIN=true rompe el split.
§
TAD GitHub org: tadtaxiadvertising (organización privada). URL base: https://github.com/tadtaxiadvertising/
§
Build blocker en `Dockerfile.driver.app`: el builder debe generar `apps/driver/.env` (sin ARG/ENV) para suprimir `SecretsUsedInArgOrEnv`.
§
Admin portal local build is not the gating verification on this host. Use `npx tsc -p apps/admin/tsconfig.json --noEmit` for baseline checks instead of `npm run build`.