# MODEL ROUTER

## Overview
Two-level routing architecture:
1. **Provider Router**: Selects provider (OpenRouter, Qwen Cloud, NVIDIA)
2. **Model Router**: Selects specific model within provider

## Provider Routing (Level 1)

### Inputs
- Task classification
- Required capabilities
- FREE_MODE constraint
- Provider health scores
- Quota availability
- Latency requirements

### Decision Logic
```
IF FREE_MODE:
  EXCLUDE providers with no free quota
  EXCLUDE models with free=false OR quota_exhausted
  
FOR each available provider:
  score = provider_health * quota_factor * capability_coverage
  
SELECT provider with highest score
```

### Fallback
If primary provider fails/degrades:
1. Check health_score < 40 → exclude
2. Check quota_exhausted → exclude (if FREE_MODE)
3. Select next highest scored provider
4. Log fallback reason

## Model Routing (Level 2)

### Inputs
- Task requirements (capability vector)
- Model capabilities (from registry + benchmarks)
- Model health score
- Model latency (recent)
- Context window fit
- Tool compatibility
- Quota value (free tier priority)

### Scoring Formula
```
TOTAL_SCORE = 
  capability_fit * 0.35
+ task_fit * 0.20
+ speed * 0.15
+ reliability * 0.15
+ quota_value * 0.10
+ context_fit * 0.05
```

### Capability Fit
Cosine similarity between task requirements and model capabilities:
```
task_req = {reasoning, coding, tool_use, vision, long_context, speed, planning}
model_cap = {reasoning, coding, tool_use, vision, long_context, speed, planning}
capability_fit = dot(task_req, model_cap) / (|task_req| * |model_cap|)
```

### Task Fit
Task-type specific bonuses:
```
FAST_QA:      speed bonus
CODING:       coding + tool_use bonus
ARCHITECTURE: reasoning + long_context + planning bonus
REASONING:    reasoning bonus
LONG_CONTEXT: long_context bonus
VISION:       vision required (0 if not supported)
TOOL_USE:     tool_use required (0 if not supported)
CRITICAL:     require health_score > 80
```

### Quota Value
```
FREE_MODE + model.free + quota_remaining > 0: 1.0
FREE_MODE + model.free + quota_exhausted: 0.0 (excluded)
!FREE_MODE: 0.5 (neutral)
```

## Weight Adaptation
Weights are NOT permanent. Adjust via:
- Benchmark results (models/performance.json)
- Task outcome tracking
- Explicit configuration
- Minimum 10 samples before weight change

## Selection Algorithm
1. Filter: Exclude unhealthy (health < 20), quota exhausted (FREE_MODE), capability mismatch (required=0)
2. Score: Compute TOTAL_SCORE for each candidate
3. Sort: Descending by score
4. Select: Top model
5. Validate: Confirm supports required capabilities
6. Log: Record selection rationale

## Context Preservation on Switch
```
BEFORE switch:
  1. Create checkpoint
  2. Summarize current state (objective, progress, decisions, context)
  3. Serialize relevant memory
  
AFTER switch:
  4. Load checkpoint
  5. Inject summary as system context
  6. Resume from next_action
  7. Verify continuity
```

## Logging
Every routing decision logs to logs/routing/:
- timestamp
- task_type
- task_requirements
- candidates_considered
- scores
- selected_model
- selected_provider
- rationale
- health_scores_at_selection