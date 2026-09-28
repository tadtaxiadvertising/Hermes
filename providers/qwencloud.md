# QWEN CLOUD PROVIDER CONFIGURATION

## Provider Identity
- **name**: Qwen Cloud / Alibaba Model Studio
- **type**: single-provider (Alibaba)
- **base_url_env**: QWEN_BASE_URL (required)
- **auth_env**: QWENCLOUD_API_KEY (or DASHSCOPE_API_KEY)

## Region & Endpoint
- **region**: Configurable via QWEN_BASE_URL
- **endpoint**: Must match API key region
- **detection**: Auto-detect from base_url at startup
- **validation**: Test authentication on init

## Model Discovery
- **method**: Provider-specific (DashScope/Model Studio API)
- **refresh_interval**: 24h
- **models**: Qwen series (Qwen2.5, Qwen2, etc.)
- **capabilities**: Vary by model version

## Free Quota (Critical)
- **free_quota**: Finite, trackable resource
- **quota_remaining**: Must track per model
- **quota_expiry**: Timestamp when quota resets/expires
- **alert_threshold**: Warn at 20% remaining
- **exhaustion_action**: Exclude from FREE_MODE routing

## Health Tracking
- **latency_ms**: Rolling averages (last_10, last_50, last_100)
- **error_rate**: Failed requests / total
- **timeout_rate**: Timeouts / total
- **tool_success_rate**: Tool calls succeeded / attempted
- **health_score**: 0-100 with temporal decay
- **region_latency**: Track per region if multi-region

## Quota Tracking
- **model_level**: Track per model if API supports
- **provider_level**: Aggregate fallback
- **reset_detection**: Auto-detect quota reset
- **projection**: Estimate exhaustion date

## Routing Role
- Primary for Qwen-specialized tasks
- Free tier contributor
- Regional optimization

## Configuration Notes
- API key MUST match base_url region
- DashScope vs Model Studio endpoints differ
- Monitor quota aggressively - finite resource
- Handle regional outages