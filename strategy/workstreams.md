# WORKSTREAMS

## Active Workstreams

### WS-1: Memory & State Architecture
**Lead**: Hermes Core
**Status**: In Progress (30%)
**Objective**: Memoria persistente de dos niveles con journal, checkpoints, recuperación
**Deliverables**:
- [x] Directory structure
- [x] MASTER.md + memory base files
- [ ] Journal append-only
- [ ] Consolidation hook
- [ ] Checkpoint schema + protocol
- [ ] Hierarchical recovery
- [ ] Memory consolidation automation
**Dependencies**: None
**Blockers**: None

### WS-2: Model Routing & Provider Failover
**Lead**: Hermes Core
**Status**: Not Started
**Objective**: Router dinámico dos niveles + 3 proveedores + fallback
**Deliverables**:
- [ ] models/registry.json + discovery
- [ ] Scoring engine
- [ ] Task classification
- [ ] Two-level routing
- [ ] Fallback chains
- [ ] FREE_MODE enforcement
- [ ] Context preservation on switch
- [ ] OpenRouter integration
- [ ] Qwen Cloud integration
- [ ] NVIDIA integration
- [ ] Provider health monitoring
**Dependencies**: WS-1 (checkpoint for context preservation)
**Blockers**: None

### WS-3: Evaluation & Benchmarking
**Lead**: Hermes Core
**Status**: Not Started
**Description**: Benchmarks internos + 9 eval families
**Deliverables**:
- [ ] Benchmark harness
- [ ] 8 benchmark types
- [ ] Performance tracking
- [ ] Weight adaptation
- [ ] Regression detection
- [ ] 9 eval families implementation
- [ ] CI integration
**Dependencies**: WS-2 (router to benchmark)
**Blockers**: None

### WS-4: Security & Credential Management
**Lead**: Hermes Core
**Status**: Not Started
**Objective**: Zero credential exposure guarantee
**Deliverables**:
- [ ] Env var enforcement
- [ ] Log redaction
- [ ] Code scanning for secrets
- [ ] Auto-rotation workflow
- [ ] Git history scan
**Dependencies**: None
**Blockers**: None

## Proposed Workstreams (Future)

### WS-5: Intelligence & Learning Loop
**Status**: Proposed
**Objective**: Auto-mejora continua basada en evidencia
**Deliverables**:
- [ ] Task outcome tracking
- [ ] Routing optimization from outcomes
- [ ] Capability drift detection
- [ ] Predictive quota management
- [ ] Custom benchmark generation

### WS-6: Advanced Orchestration
**Status**: Proposed
**Objective**: Multi-agent, DAG execution, parallelization
**Deliverables**:
- [ ] Task graph engine
- [ ] Sub-agent coordination
- [ ] Parallel execution
- [ ] Result synthesis

### WS-7: Developer Experience
**Status**: Proposed
**Objective**: Observabilidad, debugging, dashboards
**Deliverables**:
- [ ] Structured logging
- [ ] Router dashboard (TUI)
- [ ] Memory visualization
- [ ] Benchmark reports
- [ ] Debugging tools

## Workstream Coordination

### Sync Cadence
- Daily: Standup (async via MASTER.md updates)
- Weekly: Workstream review + priority adjustment
- Bi-weekly: Architecture audit (MASTER.md vs reality)

### Handoff Protocol
When workstream completes deliverable:
1. Update MASTER.md
2. Create checkpoint
3. Document in memory/decisions.md if architectural
4. Update relevant strategy files
5. Log to logs/executions/
6. Notify dependent workstreams

### Conflict Resolution
- MASTER.md is source of truth
- Decisions.md records architectural choices
- Conflicts → escalate to MASTER.md update with rationale
- Never duplicate functionality across workstreams