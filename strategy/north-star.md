# NORTH STAR

## Vision
Un agente que puede perder cualquier modelo, proveedor, sesión o ejecución sin perder su identidad, su estrategia ni su conocimiento.

## Guiding Metric
**Continuity Score**: % de tareas que completan exitosamente tras interrupción, cambio de modelo, o agotamiento de cuota.

Target: > 95% continuity across all disruption types.

## Strategic Pillars
1. **Memory as Infrastructure** - Persistente, clasificada, recuperable, auditable
2. **Models as Resources** - Intercambiables, benchmarkeados, con health tracking
3. **Routing as Nervous System** - Dinámico, multi-dimensional, con fallback garantizado
4. **State as Continuity** - Checkpoints, recuperación jerárquica, handoff explícito
5. **Verification as Defense** - Evals obligatorios, benchmarks internos, learning loop

## Success Definition
Hermes demuestra:
- [ ] Sesión N+1 recupera estado de sesión N sin pérdida
- [ ] Cambio de modelo mid-task preserva contexto
- [ ] Agotamiento de cuota → fallback gratuito automático
- [ ] Proveedor lento/degradado → otro proveedor asume
- [ ] Tarea requiere capacidad X → modelo con X seleccionado
- [ ] Latencia optimizada sin sacrificar capacidad requerida
- [ ] $0 gastado sin consentimiento explícito
- [ ] Métricas de ejecución → mejoras en routing
- [ ] Interrupción (crash, kill, timeout) → recovery desde checkpoint
- [ ] Decisiones trazables a evidencia
- [ ] Cero credenciales en memoria/logs/git
- [ ] Benchmarks reproducibles y comparables

## Anti-Goals
- ❌ Un modelo para gobernarlos a todos
- ❌ Un proveedor para atarlos
- ❌ Memoria que se pierde al cerrar sesión
- ❌ Fallback pago silencioso
- ❌ Decisiones sin persistencia
- ❌ Benchmarks externos como única verdad
- ❌ Hardcodeo de cualquier modelo/proveedor
- ❌ Recuperación que alucina estado previo