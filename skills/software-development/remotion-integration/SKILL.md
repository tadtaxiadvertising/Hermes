---
name: remotion-integration
description: Install, configure, and integrate Remotion into an existing npm/pnpm monorepo. Covers dependency setup, version alignment, tsconfig, CLI, React compatibility, and preview/render validation.
triggers:
  - Install Remotion in a monorepo
  - Set up Remotion Studio / CLI in an existing project
  - Integrate video rendering into a web monorepo
  - Configure Remotion with React 19
---

# Remotion Integration (Monorepo)

## Detección inicial

Antes de instalar, determina automáticamente:

| Propiedad | Cómo detectarlo |
|-----------|----------------|
| Gestor de paquetes | `package.json` → `workspaces[]` (npm) o `pnpm-workspace.yaml` (pnpm) |
| React version | `node -e "console.log(require('react/package.json').version)"` |
| TypeScript version | `node -e "console.log(require('typescript/package.json').version)"` |
| Remotion existente | Buscar `remotion` y `@remotion/*` en `dependencies` de cualquier workspace |
| Entry point existente | Buscar archivos que llamen `registerRoot` |

## Pasos de instalación

### 1. Verificar compatibilidad React

Remotion 4.x soporta React >=16.8.0 (incluye React 19). Verificar que `react` y `react-dom` tengan la misma versión exacta.

### 2. Crear/identificar el workspace target

Si no existe un workspace para Remotion, crearlo en `apps/<name>/` con `package.json`, `tsconfig.json`, `src/`.

### 3. Instalar dependencias (orden recomendado)

```bash
# Core
npm install remotion@<version>               # o pnpm add
npm install @remotion/bundler@<version>
npm install @remotion/renderer@<version>

# CLI (siempre separado del core)
npm install --save-dev @remotion/cli@<version>

# TypeScript types
npm install --save-dev @types/react @types/react-dom
```

**⚠️ Regla crítica**: TODOS los paquetes `@remotion/*`, `remotion`, y `@remotion/cli` DEBEN tener la **misma versión exacta**. Usar versiones fijas sin caret (`4.0.451`) o caret (`^4.0.451` → npm resuelve al mismo). Si hay mismatch, `npx remotion versions` lo reporta y causa errores de React context/hooks en runtime.

### 4. Configurar tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "jsx": "react-jsx",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "moduleResolution": "node",
    "strict": true
  },
  "include": ["src/**/*"]
}
```

`jsx: "react"` (React clásico) **NO** funciona con Remotion 4.x + React 19. Usar `"react-jsx"`.

### 5. Crear estructura de archivos fuente

```
src/
  templates/
    dynamic-ad.tsx      ← Componente de video (usa hooks de Remotion)
    index.tsx           ← Entry point con registerRoot
  index.ts              ← (opcional) Servidor Express para render programático
```

### 6. Entry point (src/templates/index.tsx)

```tsx
import { Composition, registerRoot } from 'remotion';
import { MyComponent } from './my-component';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="MyComp"
    component={MyComponent}
    durationInFrames={300}
    fps={30}
    width={1080}
    height={1920}
  />
);

registerRoot(RemotionRoot);
```

### 7. Scripts en package.json

```json
{
  "scripts": {
    "studio": "remotion studio src/templates/index.tsx",
    "preview": "remotion studio src/templates/index.tsx",
    "render": "remotion render src/templates/index.tsx <compId> out/video.mp4",
    "compositions": "remotion compositions src/templates/index.tsx",
    "versions": "remotion versions",
    "ensure-browser": "remotion browser ensure"
  }
}
```

### 8. Verificar browser (Chromium Headless)

```bash
npx remotion browser ensure
# Descarga Chrome Headless Shell automáticamente a node_modules/.remotion/
```

## Validaciones

```bash
# 1. Compilación TypeScript
npm run build   # tsc

# 2. Versiones alineadas
npx remotion versions
# Output esperado: todos los paquetes en la MISMA versión

# 3. Composiciones reconocidas
npx remotion compositions src/templates/index.tsx
# Debe listar los Composition IDs registrados

# 4. Studio (local)
npx remotion studio src/templates/index.tsx --port=6123
# Abrir http://localhost:6123 en el navegador
```

## Problemas comunes

### `@remotion/cli` no encuentra binario
- **Causa**: El paquete `remotion` no incluye CLI; es un paquete separado `@remotion/cli`
- **Solución**: Instalar `npm install --save-dev @remotion/cli`

### Version mismatch entre paquetes
- **Causa**: Un paquete está en 4.0.446 y otro en 4.0.451
- **Solución**: Pinear todas las versiones al mismo número exacto

### React context/hooks no funcionan en runtime
- **Causa**: Version mismatch entre paquetes Remotion, O `jsx` incorrecto en tsconfig
- **Solución**: Verificar `npx remotion versions`, corregir tsconfig a `"jsx": "react-jsx"`

### `ERESOLVE` error al instalar en npm workspace
- **Causa**: Otro workspace en el monorepo tiene conflictos de peer deps (ej: expo)
- **Solución**: Usar `--legacy-peer-deps` o modificar el package.json conflictivo

### `remotion browser ensure` falla
- **Causa**: Falta conectividad o permisos de escritura
- **Solución**: Verificar que `node_modules/` tenga permisos de escritura, o descargar Chrome manualmente

### `remotion studio` inicia pero no carga composiciones
- **Causa**: El entry point no llama `registerRoot` o la ruta es incorrecta
- **Solución**: Verificar que el archivo pasado al CLI contenga `registerRoot(Component)`

## Plantilla de componente (templates/dynamic-ad.tsx)

```tsx
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

interface AdProps {
  primaryText?: string;
  brandColor?: string;
}

export const MyAd: React.FC<AdProps> = ({ primaryText = 'Oferta', brandColor = '#e51636' }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // ... animaciones
  return <AbsoluteFill>{/* JSX */}</AbsoluteFill>;
};
```