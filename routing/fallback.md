# FALLBACK CHAINS

## Concept
Fallback chains define role-based fallbacks per task type.
Roles are filled dynamically from registry at routing time.
Never hardcode specific model names.

## Chain Structure
```yaml
task_type:
  primary_role: "role_name"
  fallback_roles:
    - "role_name_1"
    - "role_name_2"
    - "role_name_3"
```

## Role Definitions
| Role | Description | Selection Criteria |
|------|-------------|-------------------|
| best_available_coder | Highest coding+tool_use score | capability_fit(coding) > 0.8, tool_use > 0.8 |
| fast_coder | Good coding, high speed | coding > 0.6, speed > 0.7 |
| reasoning_model | Highest reasoning score | reasoning > 0.85 |
| balanced_reasoner | Good reasoning, decent speed | reasoning > 0.7, speed > 0.5 |
| fast_reasoner | Reasoning optimized for speed | reasoning > 0.6, speed > 0.7 |
| general_model | Balanced across capabilities | All capabilities > 0.5 |
| lowest_latency_free_model | Free, fastest | free=true, quota>0, max speed |
| vision_model | Vision capability required | vision > 0.5 |
| long_context_model | Large context window | long_context > 0.8, context_window > 100k |
| tool_specialist | Best tool use | tool_use > 0.85 |

## Fallback Chains by Task Type

### CODING
```yaml
coding:
  primary_role: best_available_coder
  fallback_roles:
    - fast_coder
    - reasoning_model
    - general_model
    - tool_specialist
```

### DEBUGGING
```yaml
debugging:
  primary_role: best_available_coder
  fallback_roles:
    - reasoning_model
    - fast_coder
    - tool_specialist
    - general_model
```

### ARCHITECTURE
```yaml
architecture:
  primary_role: reasoning_model
  fallback_roles:
    - balanced_reasoner
    - fast_reasoner
    - general_model
```

### REASONING
```yaml
reasoning:
  primary_role: reasoning_model
  fallback_roles:
    - balanced_reasoner
    - fast_reasoner
    - general_model
```

### PLANNING
```yaml
planning:
  primary_role: reasoning_model
  fallback_roles:
    - balanced_reasoner
    - fast_reasoner
    - general_model
```

### MULTI_STEP_AGENT
```yaml
multi_step_agent:
  primary_role: best_available_coder
  fallback_roles:
    - reasoning_model
    - tool_specialist
    - balanced_reasoner
    - general_model
```

### FAST_QA
```yaml
fast_qa:
  primary_role: lowest_latency_free_model
  fallback_roles:
    - fast_coder
    - fast_reasoner
    - general_model
```

### CHAT
```yaml
chat:
  primary_role: general_model
  fallback_roles:
    - fast_reasoner
    - balanced_reasoner
    - lowest_latency_free_model
```

### RESEARCH
```yaml
research:
  primary_role: reasoning_model
  fallback_roles:
    - long_context_model
    - balanced_reasoner
    - general_model
```

### SUMMARIZATION
```yaml
summarization:
  primary_role: long_context_model
  fallback_roles:
    - reasoning_model
    - general_model
    - fast_reasoner
```

### EXTRACTION
```yaml
extraction:
  primary_role: fast_coder
  fallback_roles:
    - lowest_latency_free_model
    - general_model
```

### VISION
```yaml
vision:
  primary_role: vision_model
  fallback_roles:
    - reasoning_model
    - general_model
```

### TOOL_USE
```yaml
tool_use:
  primary_role: tool_specialist
  fallback_roles:
    - best_available_coder
    - reasoning_model
    - general_model
```

### LONG_CONTEXT
```yaml
long_context:
  primary_role: long_context_model
  fallback_roles:
    - reasoning_model
    - general_model
```

### CRITICAL_DECISION
```yaml
critical_decision:
  primary_role: reasoning_model
  fallback_roles:
    - best_available_coder
    - balanced_reasoner
  requirements:
    health_score_min: 80
    capability_fit_min: 0.8
    verification_required: true
```

## Provider-Level Fallback
If ALL models from primary provider fail/exhausted:
1. Log provider failure
2. Move to next provider in global fallback_chain
3. Re-run model selection within new provider
4. Preserve context via checkpoint

Global provider fallback chain (configurable):
```yaml
provider_fallback_chain:
  - openrouter
  - qwencloud
  - nvidia
```

## Free Mode Fallback
In FREE_MODE:
1. Exclude paid models at provider level
2. Exclude quota-exhausted models
3. If provider has NO free models with quota → skip provider
4. If ALL providers exhausted → STOP with constraint report

## Fallback Triggers
Automatic fallback when:
- Model returns error (rate limit, timeout, 5xx)
- Model health_score < 40
- Model quota exhausted (FREE_MODE)
- Model missing required capability (vision, tool_use)
- Latency > 3x task threshold
- Consecutive failures ≥ 3

## Fallback Logging
Every fallback logs to logs/routing/fallback.log:
- timestamp
- original_model
- original_provider
- fallback_model
- fallback_provider
- trigger
- task_type
- context_preserved (boolean)
- checkpoint_id