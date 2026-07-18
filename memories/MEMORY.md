TAD DOOH Platform monorepo (tadtaxiadvertising org). Clone at C:\Users\Arismendy\OneDrive\Documentos\GitHub\tad-dooh-platform, branch main. EasyPanel-hosted; NestJS 10 at tad-api.rewvid.easypanel.host, portals tad-dashboard/tad-advertiser/tad-driver/tad-remotion. Supabase ltdcdhqixvbpdcitthqf. Admin admin@tad.do/TadAdmin2026!. HTTPS cred helper configured; don't re-clone, don't ask for creds unless git auth fails.
§
TAD tool quirks: tsc --noEmit (no lint/build/test, ignoreBuildErrors), search_files over grep (node_modules timeout). Tailwind v4: CSS-first (postcss.config.mjs+@import+@theme, no tailwind.config.js). EasyPanel router port 80 default; 502 → check primaryDomain port (getPrimaryDomain API) y fix con updateDomain. Next redirects nativa para root→login.
§
OneDrive-sync causa hangs en next build (apps/admin). Para verificar: usar solo tsc --noEmit, o mover a temp fuera de OneDrive, o pausar sync.
§
Builds must run outside OneDrive.
Remotion typesheet pitfalls session: duplicate type-name exports (TS2300), union-branch intersection causing unreachable type branches, and motion-config interpolation referenced from template-string scope (TS2304). Last typecheck state was incomplete; stale tool results should not be treated as current file state. Next typecheck should be treated as the source of truth.
§
Android DOOH driver app (apps/driver-android): gradle needs JAVA_HOME/ANDROID_HOME. Supabase 3.1.0 realtime-kt ships Kotlin metadata 2.3.x despite 3.1 branch — breaks Hilt 2.56 and Kotlin 2.1.x; workaround is hard-remove realtime usage. Hilt: @HiltAndroidApp types are members-injected only; cast context.applicationContext in @Provides providers instead of requesting Application as a parameter.
§
Hilt DI pattern: @HiltAndroidApp Application classes expose only members injection, not direct provision. When a @Provides method needs the Application, cast context.applicationContext inside the provider — do NOT add @Inject constructor to the Application or request it as a @Provides parameter.