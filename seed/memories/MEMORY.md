TAD DOOH Platform monorepo (tadtaxiadvertising org). GitHub repo: https://github.com/tadtaxiadvertising/tad-dooh-platform (private). Clone locally or on VPS at /opt/data/tad-dooh-platform, branch main. EasyPanel-hosted; NestJS 10 API at tad-api.rewvid.easypanel.host, portals: tad-dashboard, tad-advertiser, tad-driver, tad-remotion. Supabase project id ltdcdhqixvbpdcitthqf. HTTPS cred helper configured; don't re-clone, don't ask for creds unless git auth fails.
§
TAD tool quirks: tsc --noEmit (no lint/build/test, ignoreBuildErrors), search_files over grep (node_modules timeout). Tailwind v4: CSS-first (postcss.config.mjs+@import+@theme, no tailwind.config.js). EasyPanel router port 80 default; 502 → check primaryDomain port (getPrimaryDomain API) y fix con updateDomain. Next redirects nativa para root→login.
§
Android DOOH driver app (apps/driver-android): gradle needs JAVA_HOME/ANDROID_HOME. Supabase 3.1.0 realtime-kt ships Kotlin metadata 2.3.x despite 3.1 branch — breaks Hilt 2.56 and Kotlin 2.1.x; workaround is hard-remove realtime usage. Hilt: @HiltAndroidApp types are members-injected only; cast context.applicationContext in @Provides providers instead of requesting Application as a parameter.
§
Hilt DI pattern: @HiltAndroidApp Application classes expose only members injection, not direct provision. When a @Provides method needs the Application, cast context.applicationContext inside the provider — do NOT add @Inject constructor to the Application or request it as a @Provides parameter.
§
Hermes on Easypanel VPS: domain database-hermes.rewvid.easypanel.host, Telegram bot @taxiadvertising_bot, user Mendy (ID 8141870829). VPS IP 213.199.55.181. Port 8642. Running as gateway mode (Telegram only). Browser disabled (use browser-use cloud or firecrawl for web tasks). Terminal backend local, cwd /opt/data.
§
Key Easypanel services: tad-api (NestJS backend), tad-dashboard (Next.js admin portal), tad-advertiser (Next.js advertiser portal), tad-driver (Next.js driver portal), tad-remotion (Remotion video renderer). All on rewvid.easypanel.host subdomains.
