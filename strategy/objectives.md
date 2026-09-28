# OBJECTIVES

## Current Strategic Objectives (Active)

### OBJ-1: Memory & State Architecture
**Status**: In Progress (30%)
**Target**: 2026-10-15
**Description**: Establecer memoria persistente de dos niveles con journal, consolidación, checkpoints y recuperación jerárquica.

**Key Results**:
- [x] Estructura de directorios creada
- [x] MASTER.md inicializado
- [x] Memory INDEX.md y archivos base (identity, mission, goals, principles, facts, preferences, decisions, lessons, failures, entities)
- [ ] Journal append-only por sesión
- [ ] Consolidación automática al cierre
- [ ] Checkpoint JSON schema + protocolo
- [ ] Recuperación jerárquica implementada
- [ ] Test: Interrumpir sesión y recuperar estado

### OBJ-2: Model Router & Provider Integration
**Status**: Not Started
**Target**: 2026-10-31
**Description**: Router dinámico de dos niveles con 3 proveedores integrados.

**Key Results**:
- [ ] models/registry.json con schema completo
- [ ] OpenRouter integration (catálogo dinámico)
- [ ] Qwen Cloud integration (región, cuota, endpoint)
- [ ] NVIDIA integration (OpenAI-compatible)
- [ ] Provider health tracking
- [ ] Scoring engine (capability_fit, task_fit, speed, reliability, quota, context)
- [ ] Fallback chains por task type
- [ ] FREE_MODE enforcement
- [ ] Context preservation en model switch

### OBJ-3: Benchmarks & Learning Loop
**Status**: Not Started
**Target**: 2026-11-15
**Description**: Benchmarks internos continuos que alimentan router y mejoran decisiones.

**Key Results**:
- [ ] Benchmark harness (coding, reasoning, planning, tool_use, speed, reliability, long_context, structured_output)
- [ ] models/performance.json tracking
- [ ] Automated benchmark scheduling
- [ ] Weight adaptation based on evidence
- [ ] Task outcome tracking → routing improvement
- [ ] Regression detection

### OBJ-4: Evaluation Suite
**Status**: Not Started
**Target**: 2026-11-30
**Description**: 9 familias de evals obligatorias pasando.

**Key Results**:
- [ ] Familia 1: Memoria recovery
- [ ] Familia 2: Cambio de modelo
- [ ] Familia 3: Cuota agotada
- [ ] Familia 4: Latencia
- [ ] Familia 5: Capability mismatch
- [ ] Familia 6: Seguridad (credenciales)
- [ ] Familia 7: Memoria contradictoria
- [ ] Familia 8: Recovery
- [ ] Familia 9: No-trigger
- [ ] CI integration

### OBJ-5: Security & Credential Management
**Status**: Not Started
**Target**: 2026-10-15
**Description**: Zero credential exposure guarantee.

**Key Results**:
- [ ] Env var only enforcement
- [ ] Log redaction (sk-****abcd)
- [ ] Code scanning for secrets
- [ ] Auto-rotation workflow
- [ ] Git history scan capability