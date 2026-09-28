# FACTS

## Confirmed Facts

### F1: Architecture
- **id**: fact-arch-001
- **type**: FACT
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: initialization
- **status**: active
- **content**: Hermes usa arquitectura de dos niveles de memoria (operativa + permanente) con journal append-only y checkpoints obligatorios
- **related**: [principle-mem-001, principle-mem-004]

### F2: Providers
- **id**: fact-prov-001
- **type**: FACT
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: initialization
- **status**: active
- **content': Tres proveedores iniciales: OpenRouter (multi-modelo, catálogo dinámico), Qwen Cloud (Alibaba, cuota finita, región configurable), NVIDIA (OpenAI-compatible, modelos especializados)

### F3: Routing
- **id**: fact-routing-001
- **type**: FACT
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: initialization
- **status**: active
- **content**: Router de dos niveles (provider → model) con scoring: capability_fit(35%) + task_fit(20%) + speed(15%) + reliability(15%) + quota_value(10%) + context_fit(5%)

### F4: Security
- **id**: fact-sec-001
- **type**: FACT
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: initialization
- **status**: active
- **content**: API keys solo en variables de entorno (OPENROUTER_API_KEY, QWENCLOUD_API_KEY, NVIDIA_API_KEY, QWEN_BASE_URL). Nunca en código, memoria, logs, git.

### F5: Free Mode
- **id**: fact-free-001
- **type**: FACT
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: initialization
- **status**: active
- **content**: FREE_MODE=true por defecto. Excluye modelos de pago, cuotas agotadas. Fallback entre proveedores gratuitos. STOP si no hay modelo gratuito adecuado.