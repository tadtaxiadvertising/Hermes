# OPENROUTER PROVIDER CONFIGURATION

## Provider Identity
- **name**: OpenRouter
- **type**: multi-model gateway
- **base_url**: https://openrouter.ai/api/v1
- **auth_env**: OPENROUTER_API_KEY

## Model Discovery
- **method**: Dynamic catalog via `/models` endpoint
- **refresh_interval**: 24h (configurable)
- **filter**: Include free models when FREE_MODE=true

## Capabilities Mapping
OpenRouter models inherit capabilities from underlying providers. Hermes must:
1. Fetch model metadata from catalog
2. Map to internal capability schema
3. Supplement with internal benchmarks

## Free Tier
- Uses provider's free model mechanism
- Not all "free" models remain free permanently
- Track `free: true/false` per model in registry
- Monitor for pricing changes

## Health Tracking
- **latency_ms**: Rolling average (last_10, last_50, last_100)
- **error_rate**: Requests failed / total
- **timeout_rate**: Timeouts / total
- **tool_success_rate**: Tool calls succeeded / attempted
- **health_score**: Computed 0-100 with temporal decay

## Quota Tracking
- Per-model quota if exposed by provider
- Fallback to provider-level limits
- Track `quota_remaining`, `quota_reset_at`

## Routing Role
- Primary for model diversity
- Fallback for other providers
- Free tier gateway

## Configuration Notes
- Never hardcode model list
- Always discover at runtime
- Cache with TTL
- Handle rate limits gracefully