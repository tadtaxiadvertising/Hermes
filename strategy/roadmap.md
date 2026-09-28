# ROADMAP

## Phase 1: Foundation (Sep 28 - Oct 15, 2026)
**Goal**: Memoria persistente + Seguridad básica

### Week 1 (Sep 28 - Oct 5)
- [x] Estructura maestra de directorios
- [x] MASTER.md + memory/ base files
- [x] Provider configs (OpenRouter, Qwen, NVIDIA)
- [x] Router design (scoring, fallback chains)
- [ ] Journal append-only implementation
- [ ] Checkpoint system (schema + protocol)
- [ ] Security: env var enforcement + log redaction
- [ ] Memory consolidation hook

### Week 2 (Oct 6 - Oct 15)
- [ ] Recovery hierarchical implementation
- [ ] models/registry.json with discovery
- [ ] OpenRouter catalog integration
- [ ] Qwen Cloud quota tracking
- [ ] NVIDIA model classification
- [ ] Provider health monitoring
- [ ] OBJ-1 complete: Memory & State Architecture
- [ ] OBJ-5 complete: Security & Credential Management

## Phase 2: Routing & Integration (Oct 16 - Oct 31, 2026)
**Goal**: Router dinámico funcional + 3 proveedores

### Week 3 (Oct 16 - Oct 22)
- [ ] Scoring engine implementation
- [ ] Task classification system
- [ ] Two-level routing (provider → model)
- [ ] Fallback chain execution
- [ ] FREE_MODE enforcement
- [ ] Context preservation on switch

### Week 4 (Oct 23 - Oct 31)
- [ ] OpenRouter full integration
- [ ] Qwen Cloud full integration
- [ ] NVIDIA full integration
- [ ] Cross-provider fallback testing
- [ ] Load testing & latency baseline
- [ ] OBJ-2 complete: Model Router & Provider Integration

## Phase 3: Intelligence & Learning (Nov 1 - Nov 15, 2026)
**Goal**: Benchmarks internos + Learning loop

### Week 5 (Nov 1 - Nov 8)
- [ ] Benchmark harness framework
- [ ] Coding benchmark
- [ ] Reasoning benchmark
- [ ] Planning benchmark
- [ ] Tool use benchmark

### Week 6 (Nov 9 - Nov 15)
- [ ] Speed benchmark
- [ ] Reliability benchmark
- [ ] Long context benchmark
- [ ] Structured output benchmark
- [ ] Performance tracking (models/performance.json)
- [ ] Weight adaptation engine
- [ ] Regression detection
- [ ] OBJ-3 complete: Benchmarks & Learning Loop

## Phase 4: Verification & Hardening (Nov 16 - Nov 30, 2026)
**Goal**: 9 eval families passing + production ready

### Week 7 (Nov 16 - Nov 23)
- [ ] Familia 1: Memory recovery
- [ ] Familia 2: Model switch
- [ ] Familia 3: Quota exhaustion
- [ ] Familia 4: Latency degradation
- [ ] Familia 5: Capability mismatch

### Week 8 (Nov 24 - Nov 30)
- [ ] Familia 6: Security (credentials)
- [ ] Familia 7: Contradictory memory
- [ ] Familia 8: Recovery from checkpoint
- [ ] Familia 9: No-trigger verification
- [ ] CI/CD integration
- [ ] Documentation complete
- [ ] OBJ-4 complete: Evaluation Suite

## Phase 5: Continuous Improvement (Dec 2026+)
**Goal**: Production optimization + advanced features

- [ ] Advanced task graph execution (DAG)
- [ ] Multi-agent coordination
- [ ] Predictive quota management
- [ ] Custom model fine-tuning pipeline
- [ ] Distributed checkpoint sync
- [ ] Advanced security (secret rotation, audit)