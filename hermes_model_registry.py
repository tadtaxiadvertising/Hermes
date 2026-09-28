#!/usr/bin/env python3
"""
Hermes Model Registry - Dynamic model discovery from providers.
"""
import json
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class ModelCapability:
    reasoning: float = 0.0
    coding: float = 0.0
    tool_use: float = 0.0
    vision: float = 0.0
    long_context: float = 0.0
    speed: float = 0.0
    planning: float = 0.0
    structured_output: float = 0.0


@dataclass
class ModelHealth:
    available: bool = True
    latency_ms: Optional[float] = None
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    tool_success_rate: float = 1.0
    health_score: int = 100
    last_checked: Optional[str] = None


@dataclass
class ModelQuota:
    free: bool = False
    remaining: Optional[int] = None
    reset_at: Optional[str] = None
    percentage: Optional[float] = None


@dataclass
class ModelEntry:
    id: str
    provider: str
    availability: str = "available"
    free: bool = False
    context_window: Optional[int] = None
    capabilities: ModelCapability = field(default_factory=ModelCapability)
    health: ModelHealth = field(default_factory=ModelHealth)
    quota: ModelQuota = field(default_factory=ModelQuota)
    last_tested_at: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class ModelRegistry:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.registry_file = self.base_path / "models" / "registry.json"
        self.capabilities_file = self.base_path / "models" / "capabilities.json"
        self.performance_file = self.base_path / "models" / "performance.json"
        self.health_file = self.base_path / "models" / "health.json"
        self.models: Dict[str, ModelEntry] = {}
        self._load_registry()
        self._load_capabilities()

    def _load_registry(self):
        if self.registry_file.exists():
            data = json.loads(self.registry_file.read_text(encoding="utf-8"))
            for mid, mdata in data.get("models", {}).items():
                self.models[mid] = ModelEntry(
                    id=mdata["id"],
                    provider=mdata["provider"],
                    availability=mdata.get("availability", "available"),
                    free=mdata.get("free", False),
                    context_window=mdata.get("context_window"),
                    capabilities=ModelCapability(**mdata.get("capabilities", {})),
                    health=ModelHealth(**mdata.get("health", {})),
                    quota=ModelQuota(**mdata.get("quota", {})),
                    last_tested_at=mdata.get("last_tested_at"),
                    metadata=mdata.get("metadata", {})
                )

    def _load_capabilities(self):
        if self.capabilities_file.exists():
            data = json.loads(self.capabilities_file.read_text(encoding="utf-8"))
            self.capability_defaults = data.get("defaults_by_family", {})

    def _save_registry(self):
        data = {
            "models": {mid: asdict(m) for mid, m in self.models.items()},
            "last_updated": datetime.now().isoformat(),
            "version": "1.0",
            "schema_version": "1.0"
        }
        self.registry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _estimate_capabilities(self, model_name: str) -> ModelCapability:
        name_lower = model_name.lower()
        for family, caps in self.capability_defaults.items():
            if family in name_lower:
                return ModelCapability(**caps)
        return ModelCapability()

    def discover_openrouter(self) -> List[ModelEntry]:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            print("OPENROUTER_API_KEY not set")
            return []

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    model_id = f"openrouter/{m['id']}"
                    is_free = m.get("pricing", {}).get("prompt", "0") == "0" and m.get("pricing", {}).get("completion", "0") == "0"
                    capabilities = self._estimate_capabilities(m["id"])
                    models.append(ModelEntry(
                        id=model_id,
                        provider="openrouter",
                        free=is_free,
                        context_window=m.get("context_length"),
                        capabilities=capabilities,
                        metadata={"openrouter_data": m}
                    ))
                return models
        except Exception as e:
            print(f"OpenRouter discovery error: {e}")
        return []

    def discover_qwencloud(self) -> List[ModelEntry]:
        api_key = os.environ.get("QWENCLOUD_API_KEY")
        base_url = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            print("QWENCLOUD_API_KEY not set")
            return []

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get(f"{base_url}/models", headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    model_id = f"qwencloud/{m['id']}"
                    capabilities = self._estimate_capabilities(m["id"])
                    models.append(ModelEntry(
                        id=model_id,
                        provider="qwencloud",
                        free=True,
                        capabilities=capabilities,
                        metadata={"qwen_data": m}
                    ))
                return models
        except Exception as e:
            print(f"QwenCloud discovery error: {e}")
        return []

    def discover_nvidia(self) -> List[ModelEntry]:
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            print("NVIDIA_API_KEY not set")
            return []

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get("https://integrate.api.nvidia.com/v1/models", headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    model_id = f"nvidia/{m['id']}"
                    capabilities = self._estimate_capabilities(m["id"])
                    models.append(ModelEntry(
                        id=model_id,
                        provider="nvidia",
                        free=False,
                        capabilities=capabilities,
                        metadata={"nvidia_data": m}
                    ))
                return models
        except Exception as e:
            print(f"NVIDIA discovery error: {e}")
        return []

    def discover_all(self) -> Dict[str, List[ModelEntry]]:
        results = {}
        results["openrouter"] = self.discover_openrouter()
        results["qwencloud"] = self.discover_qwencloud()
        results["nvidia"] = self.discover_nvidia()

        for provider, models in results.items():
            for m in models:
                self.models[m.id] = m

        self._save_registry()
        return results

    def get_models(self, provider: str = None, free_only: bool = False,
                   capability_min: Dict = None) -> List[ModelEntry]:
        result = list(self.models.values())
        if provider:
            result = [m for m in result if m.provider == provider]
        if free_only:
            result = [m for m in result if m.free]
        if capability_min:
            result = [m for m in result if all(
                getattr(m.capabilities, k) >= v for k, v in capability_min.items()
            )]
        return result


def main():
    registry = ModelRegistry()
    print("Discovering models from all providers...")
    results = registry.discover_all()

    for provider, models in results.items():
        print(f"\n{provider}: {len(models)} models")
        for m in models[:5]:
            print(f"  - {m.id} (free={m.free}, ctx={m.context_window})")

    print(f"\nTotal models in registry: {len(registry.models)}")


if __name__ == "__main__":
    main()