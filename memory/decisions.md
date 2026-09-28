# DECISIONS

## Architectural Decisions (Active)

### D1: Two-Level Memory
- **id**: dec-mem-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **updated_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': Implementar memoria operativa (sesión) + memoria permanente (cross-session) con journal append-only y consolidación selectiva
- **related**: [principle-mem-001, principle-mem-004, fact-arch-001]

### D2: Master.md as Strategic Index
- **id**: dec-master-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': MASTER.md es representación ejecutiva, no contiene todo el conocimiento. Índice estratégico con punteros a memoria detallada.

### D3: Dynamic Model Router
- **id**: dec-router-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': Router de dos niveles (provider → model) con scoring multi-dimensional. No selección estática. Health scores con decay temporal.

### D4: Three Providers
- **id**: dec-prov-001
- **type**: DECISION
- **created_at**: 206-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': Integrar OpenRouter, Qwen Cloud, NVIDIA como proveedores iniciales. Cada uno con config propia, health tracking, quota tracking.

### D5: Free Mode Default
- **id**: dec-free-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture + user preference
- **status**: active
- **supersedes**: null
- **content': FREE_MODE=true por defecto. Excluir pago, cuotas agotadas. STOP si no hay opción gratuita viable. No fallback pago silencioso.

### D6: Checkpoint Protocol
- **id**: dec-checkpoint-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': Checkpoint JSON obligatorio antes de: tarea importante, cambio modelo/proveedor, modificación destructiva, cierre sesión, interrupción detectada.

### D7: Credential Security
- **id**: dec-sec-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: security
- **status**: active
- **supersedes**: null
- **content': Solo env vars para secrets. Logs redactados. Detección automática de claves en código. Rotación obligatoria si expuesta.

### D8: Benchmark-Driven Routing
- **id**: dec-bench-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': Benchmarks internos (coding, reasoning, planning, tool_use, speed, reliability) alimentan router. No confiar solo en benchmarks externos.

### D9: Recovery Hierarchical
- **id**: dec-recovery-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': Recuperación: LOAD MASTER → CURRENT STATE → ACTIVE PROJECT → PENDING TASKS → RECENT CHECKPOINT → RELEVANT MEMORY → MODEL REGISTRY → PROVIDER HEALTH → RECONSTRUCT CONTEXT

### D10: 9 Eval Families Mandatory
- **id**: dec-evals-001
- **type**: DECISION
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **supersedes**: null
- **content': 9 familias de evals obligatorias: memoria recovery, model switch, quota exhaustion, latency, capability mismatch, security, contradictory memory, recovery, no-trigger.

## Superseded Decisions (Archived)

### D0: Single Provider Architecture (SUPERSEDED)
- **id**: dec-single-prov-000
- **type**: DECISION
- **created_at**: 2026-09-28T10:00:00Z
- **updated_at**: 2026-09-28T14:30:00Z
- **confidence**: 0.5
- **source**: initial_prototype
- **status**: superseded
- **supersedes**: null
- **superseded_by**: dec-prov-001
- **content': Usar solo OpenRouter como proveedor único.
- **superseded_reason**: Single provider creates single point of failure. Multi-provider architecture with failover is required for resilience.