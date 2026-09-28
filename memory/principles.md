# PRINCIPLES

## Fundamental Principle
Nunca construyas Hermes alrededor de:
- un único modelo
- un único proveedor
- un único archivo de memoria
- una única sesión
- un único prompt gigante
- una selección estática de modelos
- conocimiento implícito que no haya sido persistido

Construye Hermes alrededor de:
**MEMORIA + ESTADO + ESTRATEGIA + ROUTING + VERIFICACIÓN**

El modelo debe ser una pieza sustituible.

## Memory Principles
1. **Dos niveles**: operativa (sesión) + permanente (cross-session)
2. **Clasificación obligatoria**: cada entrada tiene tipo (FACT, DECISION, etc.)
3. **No sobrescritura silenciosa**: cambios = nueva entrada + superseded
4. **Journal append-only**: cada sesión genera journal
5. **Consolidación selectiva**: solo info útil para decisiones futuras
6. **Recuperación jerárquica**: MASTER → PROJECT → TASK → MEMORY → SESSION → ARCHIVE

## Routing Principles
1. **Scoring multi-dimensional**: capability_fit + task_fit + reliability + speed + quota + context + tools
2. **Dos niveles**: provider → model
3. **Health scores con decay**: recuperación temporal tras degradación
4. **Free mode por defecto**: no gasto silencioso
5. **Fallback chains por task type**: roles, no nombres fijos
6. **Capability matching**: task requirements vs model capabilities
7. **Context preservation en switch**: checkpoint → summarize → transfer → continue

## Security Principles
1. **Nunca hardcodear secrets**
2. **Solo variables de entorno**
3. **Logs redactados**: sk-****abcd o configured=true
4. **Detección automática**: flag si clave en código
5. **Rotación obligatoria** si expuesta

## Execution Principles
1. **Protocolo**: DISCOVER → CLASSIFY → PLAN → IMPLEMENT → VERIFY → PERSIST → BENCHMARK → UPDATE MEMORY
2. **Checkpoint obligatorio** antes de cambios destructivos
3. **No éxito sin verificación** de comportamiento
4. **No decisión estratégica sin persistencia**
5. **Compatibilidad**: inspeccionar antes de modificar

## Invariants
- MEMORY MUST NOT BE LOST
- SECRETS MUST NOT ENTER MEMORY
- NO SILENT PAID FALLBACK
- NO UNSUPPORTED MODEL ASSUMPTIONS
- NO DESTRUCTIVE CHANGE WITHOUT CHECKPOINT
- NO FINAL SUCCESS WITHOUT VERIFICATION
- NO STRATEGIC DECISION WITHOUT PERSISTENCE
- NO MODEL LOCK-IN
- NO SINGLE PROVIDER DEPENDENCY
- NO CONTEXT LOSS DURING MODEL SWITCH