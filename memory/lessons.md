# LESSONS

## Learnings from Executions

### L1: Conversation Memory Insufficient
- **id**: lesson-mem-001
- **type**: LESSON
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: observation
- **status**: active
- **content': La memoria conversacional no es suficiente para continuidad cross-session. Se requiere memoria persistente estructurada con índices y recuperación jerárquica.
- **related**: [principle-mem-005, dec-mem-001]

### L2: External Benchmarks Unreliable
- **id**: lesson-bench-001
- **type**: LESSON
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 0.9
- **source**: observation
- **status**: active
- **content': Benchmarks externos no reflejan latencia real, disponibilidad actual, ni cuotas. Se necesitan benchmarks internos continuos con métricas reales (TTFT, tokens/sec, error_rate, tool_success_rate).

### L3: API Keys in Code Risk
- **id**: lesson-sec-001
- **type**: LESSON
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: security
- **status**: active
- **content': Cualquier clave API en código, prompts, memoria o logs es una vulnerabilidad crítica. Solo variables de entorno con detección automática y logs redactados.

### L4: Model Lock-in Danger
- **id**: lesson-lockin-001
- **type**: LESSON
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: architecture
- **status**: active
- **content': Depender de un solo modelo o proveedor crea punto único de fallo. Router debe tratar modelos como recursos intercambiables con fallbacks automáticos.

### L5: Context Loss on Model Switch
- **id**: lesson-switch-001
- **type**: LESSON
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: observation
- **status**: active
- **content': Cambiar de modelo durante tarea destruye contexto si no hay checkpoint + resumen + transferencia explícita. Protocolo obligatorio: save checkpoint → summarize → transfer → switch → continue.

### L6: Quota Exhaustion Silent Failure
- **id**: lesson-quota-001
- **type**: LESSON
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: observation
- **status**: active
- **content': Cuotas gratuitas se agotan sin aviso. Router debe trackear quota_remaining, quota_expiry por modelo/proveedor y excluir modelos agotados en FREE_MODE.

### L7: Health Score Decay Needed
- **id**: lesson-health-001
- **type**: LESSON
- **created_at**: 2026-09-28T14:30:00Z
- **confidence': 0.9
- **source**: observation
- **status': active
- **content': Un fallo aislado no debe bloquear modelo permanentemente. Health scores necesitan decay temporal para recuperar modelos tras degradación temporal.

### L8: Task Classification Critical
- **id**: lesson-task-001
- **type**: LESSON
- **created_at': 2026-09-28T14:30:00Z
- **confidence': 1.0
- **source': architecture
- **status': active
- **content': Clasificar tarea ANTES de seleccionar modelo es crítico. FAST_QA ≠ CODING ≠ ARCHITECTURE. Cada tipo requiere capacidades y prioridades diferentes.