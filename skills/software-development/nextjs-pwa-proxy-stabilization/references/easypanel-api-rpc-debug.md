# EasyPanel API RPC Debug Reference

Session-specific evidence and patterns discovered during the 2026-07-12 TAD advertiser CSS recovery operation.

## Login & Auth

EasyPanel v2.32.0+ exposes an **RPC endpoint** (not a REST/GraphQL one):

```
POST https://{panel-host}/api/rpc/auth/login
Content-Type: application/json
Body: {"json": {"email": "...", "password": "...", "rememberMe": true/false}}

Response: {"json": {"token": "..."}} — bearer token for subsequent calls
```

**Pitfall: passwords with special characters** — `$` and `@` in the password must be single-quoted in bash (`'pass@word$$'`) and embedded via `-d` with variable expansion (`"${PASS}"`). Use `--data-raw` to avoid curl interfering with escaped chars.

Token expiry is returned in `getSession`:
```
GET (or POST with {"json": {}})
https://{panel-host}/api/rpc/auth/getSession
Authorization: Bearer {token}
Response: {"json": {"createdAt": ..., "expiresAt": ..., "userId": ..., "demoMode": false}}
```

## RPC Endpoint Shape Discovery

The OpenAPI spec lives at:
```
GET https://{panel-host}/api/openapi.json
```

Returned paths use **POST with `{"json": {params}}`** body for most parameterized endpoints, even when OpenAPI declares a GET + query params. Example:

```
# OpenAPI declares GET /api/rpc/services/app/inspectService?projectName=...&serviceName=...
# But GET with query params → 400 BAD_REQUEST every time
# POST with JSON body → WORKS:
POST https://ibusiness.com.do/api/rpc/services/app/inspectService
Content-Type: application/json
Body: {"json": {"projectName": "proyecto_ia", "serviceName": "tad-advertiser"}}
Response: 200 with full service config
```

**Rule of thumb**: if a GET with query params returns 400 `"Input validation failed" / "zodErrors": {}`, try the POST shape with `{"json": {params}}` before assuming the endpoint is broken. Also try the tRPC batch-style GET `?input={"0":{"param":"val"}}` but POST is more reliable.

## Critical Endpoints for Deployment Debugging

| Endpoint | Shape | Use |
|---|---|---|
| `projects.listProjectsAndServices` | GET (no params) | List ALL projects + ALL services in one call. Click here first. |
| `services.app.inspectService` | POST `{"json":{"projectName","serviceName"}}` | Full service config: commit hash, env vars, Dockerfile, build type, deployment URL |
| `actions.listActions` | POST `{"json":{"projectName","serviceName","limit"}}` | Deployment history: pending/done/error per action |
| `services.app.deployService` | POST `{"json":{"projectName","serviceName"}}` | Force redeploy → async, returns empty `{}` for success |
| `services.app.restartService` | POST `{"json":{"projectName","serviceName"}}` | Restart container → async |
| `services.app.startService` | POST `{"json":{"projectName","serviceName"}}` | Start container → async |
| `metrics.getServiceStats` | POST `{"json":{"projectName","serviceName"}}` | Container runtime stats (RAM, CPU, uptime). `null` = container not running |
| `logs.queryServiceLogs` | POST `{"json":{"projectName","serviceName","limit","levels"}}` | Runtime logs. Returns 500 if container is down (no Docker log driver). |
| `domains.listDomains` | POST `{"json":{}}` | All configured Traefik host rules (`proyecto-ia-tad-*.rewvid.easypanel.host` pattern) |
| `services.common.getServiceError` | POST `{"json":{"projectName","serviceName"}}` | Active error message (null = no error) |

## Subdomain Pattern

EasyPanel generates hostnames following the pattern:
```
{projectName}-{serviceName}.{baseDomain}
```
With hyphens replacing underscores in project names (e.g., `proyecto_ia` → `proyecto-ia`).

**Example from TAD DOOH:**
| Project | Service | Generated Hostname |
|---|---|---|
| `proyecto_ia` | `tad-advertiser` | `proyecto-ia-tad-advertiser.rewvid.easypanel.host` |
| `proyecto_ia` | `tad-admin` | `proyecto-ia-tad-dashboard.rewvid.easypanel.host` |
| `proyecto_ia` | `tad-api` | `proyecto-ia-tad-api.rewvid.easypanel.host` |
| `proyecto_ia` | `tad-driver` | `proyecto-ia-tad-driver.rewvid.easypanel.host` |

**Pitfall discovered**: We probed `tad-advertiser.rewvid.easypanel.host` for 5 rounds and got 404 from Traefik's default 404 page. DNS resolved to the correct VPS IP, but Traefik had no router for that hostname — the router was registered under `proyecto-ia-tad-advertiser`. Always check `domains.listDomains` first.

## Deploy Monitor Pattern (Background Python)

When forcing redeploy via `deployService`:
1. Get the action ID from `listActions` (top entry, usually `pending`).
2. Poll `listActions` every 20-30 seconds.
3. When status transitions to `done` or `error`, probe the service URL.
4. If `done` but URL gives 404: check `getServiceStats` — null means container didn't start; check `getServiceError` for crash message; try `startService`.
5. If `done` but stats null and all sibling services also null: the containers are built but Docker daemon or Traefik routing is broken — check `domains.listDomains` to confirm hostname mapping exists; if missing, the automated router creation may have silently failed.

**Python monitor script template (re-runnable):**
```python
import urllib.request, json, time, subprocess
TOKEN = '<bearer-token>'
PROJECT = '<project>'      # e.g. 'proyecto_ia'
SERVICE = '<service>'      # e.g. 'tad-advertiser'

def post_rpc(endpoint, params):
    url = f'https://ibusiness.com.do/api/rpc/{endpoint}'
    body = json.dumps({'json': params}).encode()
    req = urllib.request.Request(url, data=body,
        headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())['json']

def curl(url):
    r = subprocess.run(['curl', '-sSI', '-m', '8', url], capture_output=True, text=True, timeout=12)
    return r.stdout.split('\r\n')[0]

last_status = None
while True:
    actions = post_rpc('actions/listActions', {'projectName': PROJECT, 'serviceName': SERVICE, 'limit': 3})
    latest = actions[0]
    status = latest['status']
    if status != last_status:
        print(f'{latest["id"][:20]} -> {status} (deploy at {latest["createdAt"][:19]})')
        last_status = status
        if status in ('done', 'error'):
            print(f'Probing URL: {curl("https://FULL-HOSTNAME/login")}')
            if status == 'done':
                time.sleep(10)
                print(f'Post-wait probe: {curl("https://FULL-HOSTNAME/login")}')
            break
    time.sleep(20)
```

## Known Quirks

- `getServiceStats` returns `null` for ALL services when the EasyPanel monitoring agent is down — don't conclude "all containers crashed" from this alone; check the runtime via URL probes.
- `queryServiceLogs` returns HTTP 500 when the container has NEVER produced stdout — this happens if the process crashes at startup before any `console.log`. Check `getServiceError` instead for the error code.
- Token expires in ~24h. For multi-session work, generate a long-lived API token from the EasyPanel UI (User → Settings → API Tokens) and store it in `.env.local` or memory.
- The `deployService` endpoint times out client-side after ~30s but the deploy is actually triggered — always poll `listActions` to confirm status.