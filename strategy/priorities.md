# PRIORITIES

## Current Priorities (Ranked)

### P0 - Critical (Blocking)
1. **Memory persistence** - Sin esto, no hay continuidad
2. **Security: credential handling** - Riesgo crítico si falla
3. **Checkpoint system** - Requerido para recovery y model switch

### P1 - High (This Sprint)
4. **Journal append-only** - Base para consolidación
5. **Model registry + discovery** - Requerido para router
6. **Provider health tracking** - Requerido para scoring
7. **Router scoring engine** - Core del routing dinámico

### P2 - Medium (Next Sprint)
8. **Fallback chains execution** - Completa el router
9. **FREE_MODE enforcement** - User requirement
10. **Context preservation on switch** - Quality requirement
11. **OpenRouter integration** - Provider 1
12. **Qwen Cloud integration** - Provider 2
13. **NVIDIA integration** - Provider 3

### P3 - Important (Phase 3)
14. **Benchmark harness** - Learning loop
15. **Performance tracking** - Evidence for routing
16. **Weight adaptation** - Self-improvement
16. **Eval suite (9 families)** - Verification

### P4 - Nice to Have
17. **Advanced task graphs (DAG)**
18. **Predictive quota management**
19. **Multi-agent coordination**
20. **Custom model fine-tuning**

## Priority Rules
- P0 blocks everything else
- Max 3 P0/P1 concurrent
- P2 can start when P1 > 50% complete
- Re-evaluate weekly
- Emergency items can preempt (with checkpoint)