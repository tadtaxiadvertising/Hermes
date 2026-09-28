# PENDING DECISIONS

## Decisions Needed

### PD1: Journal Format & Consolidation Trigger
- **id**: pending-journal-001
- **created_at**: 2026-09-28T14:30:00Z
- **question**: ¿Formato exacto del journal (markdown vs JSONL) y trigger de consolidación (manual, auto on session end, periodic)?
- **options**:
  - A: Markdown + auto on session end
  - B: JSONL + auto on session end + periodic
  - C: JSONL + manual trigger only
- **impact**: Afecta implementation T1, T3
- **decide_by**: 2026-10-05
- **owner**: WS-1 lead
- **status**: open

### PD2: Checkpoint Storage Backend
- **id**: pending-checkpoint-001
- **created_at**: 2026-09-28T14:30:00Z
- **question**: ¿Dónde guardar checkpoints? (local file, SQLite, git, cloud sync)
- **options**:
  - A: Local JSON files (simple, portable)
  - B: SQLite (queryable, atomic)
  - C: Git (versioned, distributed)
  - D: Cloud sync (cross-device)
- **impact**: Afecta T2, T4, future distributed checkpoints
- **decide_by**: 2026-10-10
- **owner**: WS-1 lead
- **status**: open

### PD3: Benchmark Quality Metric
- **id**: pending-benchmark-001
- **created_at**: 2026-09-28T14:30:00Z
- **question**: ¿Cómo medir "quality" en benchmarks de coding/reasoning? (exact match, LLM-as-judge, test pass rate, human eval)
- **options**:
  - A: Test pass rate (coding) + exact match (reasoning)
  - B: LLM-as-judge para todos
  - C: Hybrid: automated + periodic human
- **impact**: Afecta T12, weight adaptation
- **decide_by**: 2026-11-01
- **owner**: WS-3 lead
- **status**: open

### PD4: Task Classification Method
- **id**: pending-classification-001
- **created_at**: 2026-09-28T14:30:00Z
- **question**: ¿Cómo clasificar tareas automáticamente? (keywords, LLM classifier, explicit user tag, hybrid)
- **options**:
  - A: Explicit user tag (task_type: CODING)
  - B: LLM classifier on task description
  - C: Keyword heuristics + override
  - D: Hybrid: auto + user correction
- **impact**: Afecta T9 (router input)
- **decide_by**: 2026-10-20
- **owner**: WS-2 lead
- **status**: open

### PD5: Health Score Formula
- **id**: pending-health-001
- **created_at**: 2026-09-28T14:30:00Z
- **question**: Fórmula exacta de health_score combinando availability, latency, error_rate, timeout_rate, quota_state
- **options**:
  - A: Weighted average (configurable)
  - B: Minimum of critical factors
  - C: Multiplicative (any zero = zero)
  - D: Custom per provider
- **impact**: Afecta T9, T10 (fallback triggers)
- **decide_by**: 2026-10-25
- **owner**: WS-2 lead
- **status**: open

## Decided (Moved to memory/decisions.md)
*All architectural decisions from initialization recorded in memory/decisions.md*