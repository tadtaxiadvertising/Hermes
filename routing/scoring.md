# SCORING METHODOLOGY

## Capability Vectors

### Task Requirements (Generated per Task)
```json
{
  "reasoning": 0.0-1.0,
  "coding": 0.0-1.0,
  "tool_use": 0.0-1.0,
  "vision": 0.0-1.0,
  "long_context": 0.0-1.0,
  "speed": 0.0-1.0,
  "planning": 0.0-1.0
}
```

### Task Type Defaults
| Task Type | reasoning | coding | tool_use | vision | long_context | speed | planning |
|-----------|-----------|--------|----------|--------|--------------|-------|----------|
| CHAT | 0.3 | 0.1 | 0.2 | 0.0 | 0.2 | 0.7 | 0.2 |
| FAST_QA | 0.2 | 0.1 | 0.1 | 0.0 | 0.1 | 0.9 | 0.1 |
| REASONING | 0.9 | 0.2 | 0.3 | 0.0 | 0.6 | 0.4 | 0.7 |
| PLANNING | 0.8 | 0.2 | 0.4 | 0.0 | 0.5 | 0.4 | 0.9 |
| CODING | 0.6 | 0.9 | 0.9 | 0.0 | 0.5 | 0.6 | 0.5 |
| DEBUGGING | 0.7 | 0.8 | 0.8 | 0.0 | 0.6 | 0.5 | 0.6 |
| ARCHITECTURE | 0.9 | 0.5 | 0.5 | 0.0 | 0.8 | 0.4 | 0.8 |
| RESEARCH | 0.7 | 0.2 | 0.5 | 0.0 | 0.8 | 0.4 | 0.6 |
| SUMMARIZATION | 0.5 | 0.1 | 0.2 | 0.0 | 0.7 | 0.6 | 0.3 |
| EXTRACTION | 0.4 | 0.1 | 0.3 | 0.0 | 0.5 | 0.7 | 0.2 |
| VISION | 0.5 | 0.2 | 0.3 | 1.0 | 0.4 | 0.5 | 0.3 |
| TOOL_USE | 0.5 | 0.4 | 1.0 | 0.0 | 0.4 | 0.6 | 0.5 |
| LONG_CONTEXT | 0.6 | 0.3 | 0.4 | 0.0 | 1.0 | 0.4 | 0.5 |
| MULTI_STEP_AGENT | 0.8 | 0.6 | 0.9 | 0.0 | 0.7 | 0.5 | 0.9 |
| CRITICAL_DECISION | 1.0 | 0.5 | 0.5 | 0.0 | 0.6 | 0.4 | 0.8 |

## Model Capabilities (From Registry + Benchmarks)
```json
{
  "reasoning": 0.0-1.0,
  "coding": 0.0-1.0,
  "tool_use": 0.0-1.0,
  "vision": 0.0-1.0,
  "long_context": 0.0-1.0,
  "speed": 0.0-1.0,
  "planning": 0.0-1.0
}
```

### Capability Sources (Priority Order)
1. Internal benchmarks (models/performance.json)
2. Provider catalog metadata
2. Community benchmarks (if verified)
3. Heuristic defaults by model family

## Component Scores

### Capability Fit (35%)
Cosine similarity between task requirements and model capabilities.
Range: 0.0 - 1.0

### Task Fit (20%)
Task-type specific alignment bonus.
- Exact match to primary capability: +0.3
- Strong in required, weak in irrelevant: +0.2
- Balanced: +0.1
- Mismatch: 0.0 or negative

### Speed (15%)
Normalized tokens/second relative to cohort.
- Uses recent benchmark data (last_50)
- Fallback: provider-reported specs
- Normalized: model_tps / max_tps_in_cohort

### Reliability (15%)
Health score normalized 0-1.
- health_score / 100
- Incorporates: availability, error_rate, timeout_rate, tool_success_rate
- Temporal decay: recent weighted 2x vs historical

### Quota Value (10%)
```
FREE_MODE + free + quota>0: 1.0
FREE_MODE + free + quota=0: 0.0 (excluded pre-scoring)
!FREE_MODE + free: 0.7
!FREE_MODE + paid: 0.3
```

### Context Fit (5%)
```
task.long_context * model.long_context
+ (1 - task.long_context) * (1 - context_overhead_penalty)
```
Where context_overhead_penalty = 0 if model.context_window > required, else proportional.

## Weight Configuration
Default weights (adjustable via benchmarks):
```yaml
capability_fit: 0.35
task_fit: 0.20
speed: 0.15
reliability: 0.15
quota_value: 0.10
context_fit: 0.05
```

## Weight Adaptation Rules
- Minimum 30 task executions per model before weight adjustment
- Adjustment: ±0.02 per dimension per 30 samples
- Bounds: [0.05, 0.50] per weight
- Sum must = 1.0 (renormalize)
- Log all changes to routing/scoring.md with evidence

## Special Modifiers

### Critical Task Modifier
If task_type = CRITICAL_DECISION:
- Require health_score ≥ 80
- Require capability_fit ≥ 0.8
- Multiply final score by 0.5 if requirements not met (effectively exclude)

### Free Mode Modifier
If FREE_MODE:
- quota_value weight → 0.20 (increase)
- speed weight → 0.10 (decrease)
- Exclude any model with free=false or quota_exhausted

### Latency Penalty
If model.latency_p95 > task.max_latency_ms:
- Apply penalty: -0.1 * (latency_ratio - 1.0)
- Max penalty: -0.3

### Failure Penalty
If model.consecutive_failures > 0:
- Penalty: -0.05 * consecutive_failures
- Max penalty: -0.25
- Resets on success