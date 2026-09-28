# RISKS

## Technical Risks

### R1: Context Loss on Model Switch
- **Probability**: High
- **Impact**: Critical
- **Mitigation**: Checkpoint protocol obligatorio, summarization, context transfer, verification
- **Status**: Mitigation designed, not implemented

### R2: Quota Exhaustion Without Detection
- **Probability**: High (free tiers are limited)
- **Impact**: High (silent failure, task abort)
- **Mitigation**: Per-model quota tracking, proactive exclusion, FREE_MODE STOP behavior
- **Status**: Designed in router/fallback, not implemented

### R3: Provider Degradation Without Failover
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Health scores with temporal decay, consecutive failure tracking, automatic fallback
- **Status**: Designed in routing/scoring, not implemented

### R4: Credential Exposure
- **Probability**: Low (if discipline maintained)
- **Impact**: Critical
- **Mitigation**: Env var only, log redaction, code scanning, git hooks
- **Status**: Policy defined, tooling not implemented

### R5: Benchmark Gaming / Overfitting
- **Probability**: Medium
- **Impact**: Medium (routing degrades on real tasks)
- **Mitigation**: Diverse benchmark tasks, minimum sample sizes, regression tests, human evaluation
- **Status**: Designed in benchmarks, not implemented

### R6: Memory Corruption / Checkpoint Loss
- **Probability**: Low
- **Impact**: Critical
- **Mitigation**: Atomic writes, checksums, multiple checkpoint copies, journal backup
- **Status**: Not implemented

### R7: Model Capability Drift
- **Probability**: Medium (providers update models)
- **Impact**: Medium
- **Mitigation**: Periodic re-benchmarking, catalog refresh, version tracking
- **Status**: Designed in registry refresh, not implemented

### R8: Recovery Hallucination
- **Probability**: Medium (if recovery incomplete)
- **Impact**: Critical (wrong state)
- **Mitigation**: Hierarchical recovery, mark unknown, never hallucinate, verification step
- **Status**: Protocol defined, not implemented

## Operational Risks

### R9: Single Point of Failure in Router
- **Probability**: Low
- **Impact**: High
- **Mitigation**: Router is stateless logic, can be re-instantiated, fallback to static config
- **Status**: Architecture supports

### R10: Scope Creep / Architecture Drift
- **Probability**: High
- **Impact**: Medium
- **Mitigation**: MASTER.md as constitution, protocol enforcement, regular audits
- **Status**: MASTER.md established

## External Risks

### R11: Provider API Changes
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Version detection, graceful degradation, adapter pattern
- **Status**: Not implemented

### R12: Free Tier Elimination
- **Probability**: Medium (business risk)
- **Impact**: High (FREE_MODE breaks)
- **Mitigation**: Multi-provider free tier, paid fallback with consent, local model option
- **Status**: Designed in provider diversity