#!/usr/bin/env python3
"""
Hermes Router - Two-level dynamic model routing with scoring.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import math


@dataclass
class TaskRequirements:
    reasoning: float = 0.0
    coding: float = 0.0
    tool_use: float = 0.0
    vision: float = 0.0
    long_context: float = 0.0
    speed: float = 0.0
    planning: float = 0.0

    def to_vector(self) -> List[float]:
        return [self.reasoning, self.coding, self.tool_use, self.vision, 
                self.long_context, self.speed, self.planning]


TASK_DEFAULTS = {
    "CHAT": TaskRequirements(0.3, 0.1, 0.2, 0.0, 0.2, 0.7, 0.2),
    "FAST_QA": TaskRequirements(0.2, 0.1, 0.1, 0.0, 0.1, 0.9, 0.1),
    "REASONING": TaskRequirements(0.9, 0.2, 0.3, 0.0, 0.6, 0.4, 0.7),
    "PLANNING": TaskRequirements(0.8, 0.2, 0.4, 0.0, 0.5, 0.4, 0.9),
    "CODING": TaskRequirements(0.6, 0.9, 0.9, 0.0, 0.5, 0.6, 0.5),
    "DEBUGGING": TaskRequirements(0.7, 0.8, 0.8, 0.0, 0.6, 0.5, 0.6),
    "ARCHITECTURE": TaskRequirements(0.9, 0.5, 0.5, 0.0, 0.8, 0.4, 0.8),
    "RESEARCH": TaskRequirements(0.7, 0.2, 0.5, 0.0, 0.8, 0.4, 0.6),
    "SUMMARIZATION": TaskRequirements(0.5, 0.1, 0.2, 0.0, 0.7, 0.6, 0.3),
    "EXTRACTION": TaskRequirements(0.4, 0.1, 0.3, 0.0, 0.5, 0.7, 0.2),
    "VISION": TaskRequirements(0.5, 0.2, 0.3, 1.0, 0.4, 0.5, 0.3),
    "TOOL_USE": TaskRequirements(0.5, 0.4, 1.0, 0.0, 0.4, 0.6, 0.5),
    "LONG_CONTEXT": TaskRequirements(0.6, 0.3, 0.4, 0.0, 1.0, 0.4, 0.5),
    "MULTI_STEP_AGENT": TaskRequirements(0.8, 0.6, 0.9, 0.0, 0.7, 0.5, 0.9),
    "CRITICAL_DECISION": TaskRequirements(1.0, 0.5, 0.5, 0.0, 0.6, 0.4, 0.8),
}


@dataclass
class ModelScore:
    model_id: str
    provider: str
    capability_fit: float
    task_fit: float
    speed: float
    reliability: float
    quota_value: float
    context_fit: float
    total_score: float
    health_score: int
    latency_ms: Optional[float]
    free: bool
    context_window: Optional[int]


class HermesRouter:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.registry_file = self.base_path / "models" / "registry.json"
        self.health_file = self.base_path / "models" / "health.json"
        self.policy_file = self.base_path / "models" / "routing-policy.json"
        self.models: Dict = {}
        self.health: Dict = {}
        self.policy: Dict = {}
        self._load_all()

    def _load_all(self):
        if self.registry_file.exists():
            data = json.loads(self.registry_file.read_text(encoding="utf-8"))
            self.models = data.get("models", {})
        if self.health_file.exists():
            data = json.loads(self.health_file.read_text(encoding="utf-8"))
            self.health = data.get("models", {})
        if self.policy_file.exists():
            self.policy = json.loads(self.policy_file.read_text(encoding="utf-8"))

    def get_task_requirements(self, task_type: str) -> TaskRequirements:
        return TASK_DEFAULTS.get(task_type, TaskRequirements(0.5, 0.5, 0.5, 0.0, 0.5, 0.5, 0.5))

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def calculate_capability_fit(self, task_req: TaskRequirements, model_caps: Dict) -> float:
        task_vec = task_req.to_vector()
        model_vec = [
            model_caps.get("reasoning", 0),
            model_caps.get("coding", 0),
            model_caps.get("tool_use", 0),
            model_caps.get("vision", 0),
            model_caps.get("long_context", 0),
            model_caps.get("speed", 0),
            model_caps.get("planning", 0)
        ]
        return self.cosine_similarity(task_vec, model_vec)

    def calculate_task_fit(self, task_type: str, model_caps: Dict) -> float:
        bonus = 0.0
        if task_type == "CODING" and model_caps.get("coding", 0) > 0.8 and model_caps.get("tool_use", 0) > 0.8:
            bonus = 0.3
        elif task_type == "REASONING" and model_caps.get("reasoning", 0) > 0.85:
            bonus = 0.3
        elif task_type == "FAST_QA" and model_caps.get("speed", 0) > 0.7:
            bonus = 0.3
        elif task_type == "ARCHITECTURE" and model_caps.get("reasoning", 0) > 0.8 and model_caps.get("long_context", 0) > 0.7:
            bonus = 0.3
        elif task_type == "VISION" and model_caps.get("vision", 0) == 0:
            return 0.0  # Hard requirement
        elif task_type == "TOOL_USE" and model_caps.get("tool_use", 0) == 0:
            return 0.0  # Hard requirement
        elif all(v > 0.5 for v in model_caps.values()):
            bonus = 0.1
        return bonus

    def calculate_speed_score(self, model_id: str) -> float:
        health = self.health.get(model_id, {})
        tps = health.get("latency", {}).get("tokens_per_second")
        if tps:
            # Normalize against cohort max (simplified)
            return min(tps / 100.0, 1.0)
        return 0.5  # Default

    def calculate_reliability(self, model_id: str) -> float:
        health = self.health.get(model_id, {})
        health_score = health.get("health_score", 100)
        return health_score / 100.0

    def calculate_quota_value(self, model_id: str, free_mode: bool = True) -> float:
        model = self.models.get(model_id, {})
        free = model.get("free", False)
        if free_mode:
            if free:
                quota = model.get("quota", {})
                remaining = quota.get("remaining")
                if remaining is None or remaining > 0:
                    return 1.0
                return 0.0  # Exhausted
            return 0.0  # Paid model in free mode
        return 0.7 if free else 0.3

    def calculate_context_fit(self, task_req: TaskRequirements, model: Dict) -> float:
        ctx_window = model.get("context_window")
        if not ctx_window:
            return 0.5
        if task_req.long_context > 0.7:
            return min(ctx_window / 200000.0, 1.0)
        return 0.8  # Neutral for normal tasks

    def filter_candidates(self, models: Dict, task_type: str, free_mode: bool = True) -> Dict:
        task_req = self.get_task_requirements(task_type)
        filtered = {}
        
        for mid, model in models.items():
            # Health gate
            health = self.health.get(mid, {})
            health_score = health.get("health_score", 100)
            min_health = self.policy.get("thresholds", {}).get("health_minimum", 20)
            if task_type == "CRITICAL_DECISION":
                min_health = self.policy.get("thresholds", {}).get("critical_task_health_min", 80)
            if health_score < min_health:
                continue
            
            # Capability gates
            caps = model.get("capabilities", {})
            if task_type == "VISION" and caps.get("vision", 0) == 0:
                continue
            if task_type == "TOOL_USE" and caps.get("tool_use", 0) == 0:
                continue
            if task_type == "CRITICAL_DECISION":
                min_fit = self.policy.get("thresholds", {}).get("critical_task_capability_fit_min", 0.8)
                # Quick fit check
                fit = self.calculate_capability_fit(task_req, caps)
                if fit < min_fit:
                    continue
            
            # Free mode filter
            if free_mode and not model.get("free", False):
                continue
            if free_mode and model.get("free", False):
                quota = model.get("quota", {})
                remaining = quota.get("remaining")
                if remaining is not None and remaining <= 0:
                    continue
            
            filtered[mid] = model
        
        return filtered

    def score_model(self, model_id: str, model: Dict, task_type: str, free_mode: bool = True) -> ModelScore:
        task_req = self.get_task_requirements(task_type)
        caps = model.get("capabilities", {})
        health = self.health.get(model_id, {})
        
        capability_fit = self.calculate_capability_fit(task_req, caps)
        task_fit = self.calculate_task_fit(task_type, caps)
        speed = self.calculate_speed_score(model_id)
        reliability = self.calculate_reliability(model_id)
        quota_value = self.calculate_quota_value(model_id, free_mode)
        context_fit = self.calculate_context_fit(task_req, model)
        
        weights = self.policy.get("weights", {
            "capability_fit": 0.35, "task_fit": 0.20, "speed": 0.15,
            "reliability": 0.15, "quota_value": 0.10, "context_fit": 0.05
        })
        
        # Apply free mode weight adjustments
        if free_mode:
            weights = weights.copy()
            weights["quota_value"] = self.policy.get("modifiers", {}).get("free_mode", {}).get("quota_value_weight", 0.20)
            weights["speed"] = self.policy.get("modifiers", {}).get("free_mode", {}).get("speed_weight", 0.10)
            # Renormalize
            total = sum(weights.values())
            weights = {k: v/total for k, v in weights.items()}
        
        total_score = (
            capability_fit * weights["capability_fit"] +
            task_fit * weights["task_fit"] +
            speed * weights["speed"] +
            reliability * weights["reliability"] +
            quota_value * weights["quota_value"] +
            context_fit * weights["context_fit"]
        )
        
        # Apply penalties
        latency_penalty_threshold = self.policy.get("thresholds", {}).get("latency_penalty_threshold", 3.0)
        health_score = health.get("health_score", 100)
        if health_score < 40:
            total_score *= 0.5
        
        return ModelScore(
            model_id=model_id,
            provider=model.get("provider", "unknown"),
            capability_fit=capability_fit,
            task_fit=task_fit,
            speed=speed,
            reliability=reliability,
            quota_value=quota_value,
            context_fit=context_fit,
            total_score=total_score,
            health_score=health_score,
            latency_ms=health.get("latency", {}).get("total_p50_ms"),
            free=model.get("free", False),
            context_window=model.get("context_window")
        )

    def select_model(self, task_type: str, free_mode: bool = True) -> Optional[ModelScore]:
        candidates = self.filter_candidates(self.models, task_type, free_mode)
        if not candidates:
            return None
        
        scored = []
        for mid, model in candidates.items():
            score = self.score_model(mid, model, task_type, free_mode)
            scored.append(score)
        
        scored.sort(key=lambda s: s.total_score, reverse=True)
        
        if not scored:
            return None
        
        best = scored[0]
        
        # Log routing decision
        self._log_routing(task_type, scored[:5], best)
        
        return best

    def _log_routing(self, task_type: str, candidates: List[ModelScore], selected: ModelScore):
        log_dir = self.base_path / "logs" / "routing"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"routing_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "selected_model": selected.model_id,
            "selected_provider": selected.provider,
            "total_score": selected.total_score,
            "capability_fit": selected.capability_fit,
            "task_fit": selected.task_fit,
            "speed": selected.speed,
            "reliability": selected.reliability,
            "quota_value": selected.quota_value,
            "context_fit": selected.context_fit,
            "candidates": [
                {"model": c.model_id, "score": c.total_score, "provider": c.provider}
                for c in candidates
            ]
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_fallback_chain(self, task_type: str) -> List[str]:
        chains = self.policy.get("task_fallback_chains", {})
        return chains.get(task_type, chains.get("general_model", []))

    def get_models(self, provider: str = None, free_only: bool = False, 
                   capability_min: Dict = None) -> List[Dict]:
        """Get models matching criteria"""
        result = list(self.models.values())
        if provider:
            result = [m for m in result if m.get("provider") == provider]
        if free_only:
            result = [m for m in result if m.get("free", False)]
        if capability_min:
            result = [m for m in result if all(
                m.get("capabilities", {}).get(k, 0) >= v for k, v in capability_min.items()
            )]
        return result


def main():
    router = HermesRouter()
    
    print("Testing router with different task types:")
    for task_type in ["CODING", "REASONING", "FAST_QA", "ARCHITECTURE", "VISION"]:
        result = router.select_model(task_type, free_mode=True)
        if result:
            print(f"\n{task_type}:")
            print(f"  Selected: {result.model_id} (score: {result.total_score:.3f})")
            print(f"  Provider: {result.provider}, Free: {result.free}")
            print(f"  Capability: {result.capability_fit:.2f}, Task: {result.task_fit:.2f}, Speed: {result.speed:.2f}")
            print(f"  Reliability: {result.reliability:.2f}, Quota: {result.quota_value:.2f}, Context: {result.context_fit:.2f}")
        else:
            print(f"\n{task_type}: NO MODEL AVAILABLE")


if __name__ == "__main__":
    main()