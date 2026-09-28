# HERMES MASTER STATE

## Identity
Hermes es un agente de IA estratégico con memoria persistente, routing dinámico de modelos y arquitectura multi-proveedor. Diseñado para evolucionar continuamente basándose en evidencia y métricas.

## Mission
Convertir a Hermes en un sistema autónomo que recuerde, planifique, ejecute, verifique y aprenda sin depender de un único modelo o proveedor.

## North Star
Un agente que puede perder cualquier modelo, proveedor, sesión o ejecución sin perder su identidad, estrategia ni conocimiento.

## Current Strategic Objectives
1. Establecer memoria persistente y estructura maestra ✓
2. Implementar router dinámico multi-proveedor (OpenRouter, Qwen Cloud, NVIDIA) ✓ (parcial)
3. Crear sistema de checkpoints y recuperación ✓
4. Implementar benchmarks internos y learning loop ✓ (core + weight adaptation activo)
5. Verificar continuidad entre sesiones ✓ (recovery implementado)
6. Ejecutar evals obligatorios (9 familias) ✓ (21/22 passing - 95.4%)

## Current Projects
- **hermes-core**: Infraestructura base del agente ✓ COMPLETADO
- **model-router**: Router dinámico con scoring y fallback ✓ COMPLETADO (weights v2 adaptados)
- **memory-system**: Memoria permanente con journal y consolidación ✓ COMPLETADO
- **provider-integration**: Integración OpenRouter ✓, NVIDIA ✓, Qwen Cloud ✗ (API key inválida)
- **benchmark-harness**: Benchmarks internos para 8 task types ✓ CORE COMPLETADO
- **fallback-system**: Fallback automático con preservación de contexto ✓ COMPLETADO
- **eval-suite**: 9 familias de evals obligatorias ✓ 95.4% pass rate
- **weight-adaptation**: Auto-ajuste de pesos basado en evidencia ✓ ACTIVO (v2)

## Active Workstreams
- Memory & State Architecture ✓
- Model Routing & Provider Failover ✓
- Evaluation & Benchmarking ✓ (weight adaptation operational)
- Security & Credential Management ✓

## Current Task
**VERIFICACIÓN COMPLETA EXITOSA** - Todos los 10 sistemas core verificados y operativos. Arquitectura base COMPLETADA. Weight adaptation engine operativo (v2 - speed weight aumentado a 0.1916). Evals obligatorios pasando (95.4%). Próximos pasos: task classification automatizada, production hardening.

## Priorities
1. Estructura de memoria y MASTER.md ✓
2. Registry de modelos y proveedores ✓ (541 modelos descubiertos)
3. Router dinámico con scoring ✓ (funcional, weights v2 adaptados por evidencia)
4. Checkpoint system ✓ (implementado y probado - 15 checkpoints archivados)
5. Journal + consolidación ✓ (implementado y probado)
6. Hierarchical recovery ✓ (implementado y probado - 7/8 niveles)
7. Fallback chains + context preservation ✓ (implementado y probado)
8. Benchmarks internos ✓ (core - 5 modelos, 3 task types, métricas en performance.json)
9. Evals obligatorios 9 familias ✓ (21/22 passing - 95.4%)
10. Weight adaptation engine ✓ (v2 activo - speed weight optimizado r=0.254)
11. Task classification automatizada (pendiente decisión PD4)
12. Production hardening (siguiente - P3)

## Constraints
- No hardcodear claves API
- No fallback pago silencioso
- No dependencia de un solo proveedor
- Memoria debe sobrevivir a interrupciones
- Modelos son recursos intercambiables

## Important Decisions
- Usar dos niveles de memoria: operativa y permanente
- Journal append-only para cada sesión
- Checkpoint obligatorio antes de cambios destructivos
- Router con scoring multi-dimensional
- Free mode por defecto

## Risks
- Pérdida de contexto al cambiar modelos → MITIGADO (context preservation implementado)
- Agotamiento de cuotas gratuitas sin detección → MONITOREADO (quota tracking en registry)
- Degradación silenciosa de performance de proveedores → MONITOREADO (health scores con decay)
- Credenciales expuestas en logs o memoria → MITIGADO (env vars only, redacted logs)
- Qwen Cloud API key inválida - proveedor no disponible
- No hay modelos VISION gratuitos disponibles
- Latencia alta en modelos gratuitos (~10-30s)

## Model Environment
- OpenRouter: Multi-modelo, catálogo dinámico (460 modelos, 20 gratuitos), free tier disponible
- Qwen Cloud: Alibaba Model Studio - API key inválida, no disponible
- NVIDIA: API compatible OpenAI (81 modelos), modelos especializados (accesibles via OpenRouter)

## Routing Policy (v2 - Adapted)
- Nivel 1: Provider routing (OpenRouter → NVIDIA → QwenCloud)
- Nivel 2: Model routing (modelo concreto)
- Scoring v2: capability_fit(33.3%) + task_fit(19.0%) + speed(19.2%) + reliability(14.3%) + quota_value(9.5%) + context_fit(4.8%)
- Health score decay temporal
- Fallback chains por tipo de tarea (role-based)
- Free mode: excluye modelos de pago y cuotas agotadas
- Context preservation en model switch (checkpoint + summary + injection)

## Known Failures
- Qwen Cloud: Invalid API key (401 Unauthorized) - proveedor excluido temporalmente
- VISION task: No hay modelos gratuitos con capacidad vision
- nemotron-3.5-content-safety:free - calidad 0 en benchmarks (modelo de safety, no general)

## Lessons
- La memoria conversacional no es suficiente para continuidad
- Benchmarks externos no reflejan latencia real
- Las claves API deben estar solo en variables de entorno
- OpenRouter free tier tiene 20 modelos utilizables
- Router scoring funcional con 541 modelos registrados
- Journal consolidation detecta FACT/DECISION/LESSON/TASK prefixes
- Recovery jerárquico funciona - 7/8 niveles recuperables
- Fallback role-based resuelve a modelos concretos dinámicamente
- Context preservation via checkpoint + injection prompt funciona
- Modelos nemotron son lentos pero calidad alta; space-bunny y lfm son rápidos
- Evals obligatorios validan arquitectura: 21/22 passing (95.4%)
- **Weight adaptation engine operativo**: speed weight aumentó de 0.15 → 0.192 basado en correlación r=0.254 con quality

## Last Checkpoint
2026-09-28T17:55:00Z - VERIFICACIÓN COMPLETA EXITOSA. Todos los 10 sistemas core verificados y operativos:
- Memoria persistente (journal + checkpoints + consolidación + recovery 7/8 niveles)
- Model registry dinámico (541 modelos, discovery automático, 20 gratuitos)
- Router dinámico con scoring multi-dimensional + logging (weights v2 auto-adaptados)
- Recovery jerárquico (7/8 niveles, reconstrucción de contexto funcional)
- Fallback automático (role-based chains + provider-level fallback)
- Context preservation (checkpoint + summary + injection)
- Benchmarks internos (5 modelos, 3 task types, métricas en performance.json)
- Weight adaptation engine operativo (v2 - speed weight 0.15→0.192, r=0.254)
- Evals: 9 familias, 21/22 passing (95.4%)
- Security: API keys en env vars únicamente, sin secrets en logs/checkpoints/journal