# GOALS

## Strategic Goals (Active)
- G1: Establecer arquitectura de memoria persistente de dos niveles (operativa + permanente)
- G2: Implementar router dinámico con scoring multi-dimensional
- G3: Integrar 3 proveedores: OpenRouter, Qwen Cloud, NVIDIA
- G4: Crear sistema de checkpoints y recuperación jerárquica
- G5: Implementar benchmarks internos y learning loop
- G6: Ejecutar evals obligatorios (9 familias)

## Tactical Goals (Current Sprint)
- G1.1: Crear estructura de directorios y MASTER.md ✓
- G1.2: Implementar memory/INDEX.md y archivos base ✓
- G1.3: Journal append-only por sesión
- G1.4: Consolidación automática al cierre de sesión
- G2.1: models/registry.json con schema completo
- G2.2: Provider configs (openrouter.md, qwencloud.md, nvidia.md)
- G2.3: Router con scoring y health scores
- G2.4: Fallback chains por task type
- G3.1: OpenRouter integration (catálogo dinámico)
- G3.2: Qwen Cloud integration (región, cuota, endpoint)
- G3.3: NVIDIA integration (OpenAI-compatible)
- G4.1: Checkpoint JSON schema
- G4.2: Recovery protocol (LOAD MASTER → STATE → PROJECT → TASK → MEMORY)
- G5.1: Benchmark harness (coding, reasoning, planning, tool_use, speed, reliability)
- G5.2: models/performance.json tracking
- G6.1-G6.9: 9 familias de evals

## Completed Goals
- Ninguno (inicialización)