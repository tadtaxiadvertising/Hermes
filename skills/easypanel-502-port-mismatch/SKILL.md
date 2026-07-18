---
name: easypanel-502-port-mismatch
description: Diagnosticar y resolver 502 Bad Gateway / 404 Traefik en EasyPanel por mismatch de puertos entre Dockerfile y router
---

# EasyPanel 502/404 — Port Mismatch Diagnosis

## Síntoma
- Contenedor Docker se construye y deploya exitosamente (`action: done`)
- URL pública responde 502 Bad Gateway o 404 Traefik
- `getServiceStats` devuelve null (o contenedor no aparece en monitor)
- Otros servicios en el mismo EasyPanel funcionan OK

## Causa raíz
EasyPanel crea routers Traefik con **port 80 por defecto**. Si el Dockerfile expone otro puerto (3000, 8080, etc.), el router apunta al puerto equivocado.

## Diagnóstico

### 1. Verificar puerto del router
```bash
# Autenticarse
curl -sS -X POST -H "Content-Type: application/json" \
  -d '{"json":{"email":"...","password":"..."}}' \
  "https://<panel>/api/rpc/auth/login"

# Guardar TOKEN

# Ver puerto del router
curl -sS -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"json":{"projectName":"<project>","serviceName":"<service>"}}' \
  "https://<panel>/api/rpc/domains/getPrimaryDomain"
```

### 2. Verificar puerto expuesto del contenedor
```bash
curl -sS -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"json":{"projectName":"<project>","serviceName":"<service>"}}' \
  "https://<panel>/api/rpc/services/app/getExposedPorts"
```

### 3. Verificar Dockerfile
- Buscar `EXPOSE`, `ENV PORT`, o `PORT=` en el Dockerfile

## Corrección

### Opción A (recomendada): Alinear Dockerfile con port 80
Cambiar Dockerfile:
```dockerfile
EXPOSE 80
ENV PORT=80
```

### Opción B: Actualizar router en EasyPanel vía API
```bash
curl -sS -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"json":{
    "id":"<domain_id>",
    "host":"<host>",
    "https":true,
    "path":"/",
    "wildcard":false,
    "certificateResolver":"",
    "middlewares":[],
    "destinationType":"service",
    "serviceDestination":{
      "projectName":"<project>",
      "serviceName":"<service>",
      "port":3000,
      "path":"/",
      "protocol":"http"
    }
  }}' \
  "https://<panel>/api/rpc/domains/updateDomain"
```

### Forzar redeploy tras la corrección
```bash
curl -sS -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"json":{"projectName":"<project>","serviceName":"<service>"}}' \
  "https://<panel>/api/rpc/services/app/restartService"

# O redeploy desde git
curl -sS -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"json":{"projectName":"<project>","serviceName":"<service>"}}' \
  "https://<panel>/api/rpc/services/app/deployService"
```

## App Router root page sin CSS
- Páginas en `app/` (App Router) NO importan `globals.css`
- Páginas en `pages/` (Pages Router) importan vía `_app.tsx`
- Si root `/` se ve en blanco con HTML plano, añadir redirect en `next.config.js`:
```js
async redirects() {
  return [
    { source: '/', destination: '/login', permanent: false },
  ];
}
```