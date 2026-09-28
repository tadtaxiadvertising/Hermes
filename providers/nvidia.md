# NVIDIA PROVIDER CONFIGURATION

## Provider Identity
- **name**: NVIDIA
- **type**: single-provider (NVIDIA)
- **base_url**: https://integrate.api.nvidia.com/v1
- **auth_env**: NVIDIA_API_KEY

## API Compatibility
- **format**: OpenAI-compatible (chat completions, models list)
- **extensions**: NVIDIA-specific parameters (if any)
- **versioning**: Track API version changes

## Model Discovery
- **method**: `/models` endpoint (OpenAI-compatible)
- **refresh_interval**: 24h
- **categories**:
  - reasoning: Nemotron, etc.
  - coding: CodeLlama variants, etc.
  - agentic: Function calling optimized
  - multimodal: Vision + language
  - long_context: Extended context windows
  - speed: Optimized for latency

## Capabilities Classification
Each discovered model must be classified:
- **reasoning**: 0.0-1.0
- **coding**: 0.0-1.0
- **tool_use**: 0.0-1.0 (function calling support)
- **vision**: 0.0-1.0 (multimodal)
- **long_context**: 0.0-1.0 (context window / benchmark)
- **speed**: 0.0-1.0 (tokens/sec relative)
- **planning**: 0.0-1.0 (multi-step reasoning)
- **agentic**: 0.0-1.0 (autonomous task execution)

## Health Tracking
- **latency_ms**: Rolling averages (last_10, last_50, last_100)
- **error_rate**: Failed / total
- **timeout_rate**: Timeouts / total
- **tool_success_rate**: Tool calls succeeded / attempted
- **health_score**: 0-100 with temporal decay
- **model_level**: Track per model (not just provider)

## Quota Tracking
- **tier_based**: Likely tier-based limits
- **rate_limits**: RPM, TPM per tier
- **tracking**: Per-model if headers expose
- **projection**: Estimate from usage patterns

## Routing Role
- Primary for NVIDIA-specialized models (Nemotron, etc.)
- High-performance reasoning/coding
- OpenAI-compatible fallback

## Configuration Notes
- Verify OpenAI compatibility per model
- Some models may not support all endpoints
- Track model deprecations
- Handle rate limit headers (retry-after)