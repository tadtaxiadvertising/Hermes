# ENTITIES

## Known Entities

### Models (To be populated from registries)
*Populated dynamically from provider catalogs and benchmarks*

### Providers

#### E1: OpenRouter
- **id**: ent-prov-openrouter
- **type**: PROVIDER
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: configuration
- **status**: active
- **content**: 
  - name: OpenRouter
  - base_url: https://openrouter.ai/api/v1
  - auth_env: OPENROUTER_API_KEY
  - model_discovery: dynamic (catalog API)
  - free_tier: true (via provider mechanism)
  - capabilities: multi-model, routing, fallbacks

#### E2: Qwen Cloud
- **id**: ent-prov-qwencloud
- **type**: PROVIDER
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: configuration
- **status**: active
- **content**:
  - name: Qwen Cloud / Alibaba Model Studio
  - base_url_env: QWEN_BASE_URL
  - auth_env: QWENCLOUD_API_KEY (or DASHSCOPE_API_KEY)
  - region: configurable
  - free_quota: finite, trackable
  - quota_expiry: trackable

#### E3: NVIDIA
- **id**: ent-prov-nvidia
- **type**: PROVIDER
- **created_at**: 2026-09-28T14:30:00Z
- **confidence**: 1.0
- **source**: configuration
- **status**: active
- **content**:
  - name: NVIDIA
  - base_url: https://integrate.api.nvidia.com/v1
  - auth_env: NVIDIA_API_KEY
  - compatibility: OpenAI-compatible
  - model_discovery: dynamic
  - specializations: reasoning, coding, agentic, multimodal

### Tools
*To be populated from available toolsets*

### Projects
*Defined in memory/projects/*

### Sessions
*Logged in memory/sessions/ and memory/journal/*