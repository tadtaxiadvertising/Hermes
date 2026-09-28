#!/usr/bin/env python3
"""
Hermes Weight Adaptation Engine - Automatic router weight optimization from benchmark evidence.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from collections import defaultdict
import math


@dataclass
class WeightConfig:
    capability_fit: float = 0.35
    task_fit: float = 0.20
    speed: float = 0.15
    reliability: float = 0.15
    quota_value: float = 0.10
    context_fit: float = 0.05
    version: int = 1
    updated_at: str = ""
    evidence_count: int = 0
    adaptation_reason: str = ""


class WeightAdaptationEngine:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.performance_file = self.base_path / "models" / "performance.json"
        self.policy_file = self.base_path / "models" / "routing-policy.json"
        self.weights_history_file = self.base_path / "models" / "weights_history.json"
        self.weights = WeightConfig()
        self.min_samples_per_task = 5
        self.min_total_samples = 20
        self.adaptation_threshold = 0.02  # Minimum correlation to trigger adaptation
        self.max_adaptation_per_cycle = 0.05  # Max change per weight per cycle
        self.bounds = {"min": 0.05, "max": 0.50}
        self._load_current_weights()

    def _load_current_weights(self):
        if self.policy_file.exists():
            policy = json.loads(self.policy_file.read_text(encoding="utf-8"))
            w = policy.get("weights", {})
            self.weights = WeightConfig(
                capability_fit=w.get("capability_fit", 0.35),
                task_fit=w.get("task_fit", 0.20),
                speed=w.get("speed", 0.15),
                reliability=w.get("reliability", 0.15),
                quota_value=w.get("quota_value", 0.10),
                context_fit=w.get("context_fit", 0.05),
                updated_at=datetime.now().isoformat()
            )

    def _save_weights(self):
        # Update policy file
        if self.policy_file.exists():
            policy = json.loads(self.policy_file.read_text(encoding="utf-8"))
            policy["weights"] = {
                "capability_fit": round(self.weights.capability_fit, 4),
                "task_fit": round(self.weights.task_fit, 4),
                "speed": round(self.weights.speed, 4),
                "reliability": round(self.weights.reliability, 4),
                "quota_value": round(self.weights.quota_value, 4),
                "context_fit": round(self.weights.context_fit, 4)
            }
            policy["last_weight_update"] = datetime.now().isoformat()
            self.policy_file.write_text(json.dumps(policy, indent=2, ensure_ascii=False), encoding="utf-8")

        # Append to history
        history = []
        if self.weights_history_file.exists():
            history = json.loads(self.weights_history_file.read_text(encoding="utf-8"))
        
        history.append(asdict(self.weights))
        self.weights_history_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    def collect_evidence(self) -> Dict[str, List[Dict]]:
        """Collect per-run benchmark evidence with scores"""
        if not self.performance_file.exists():
            return {}
        
        data = json.loads(self.performance_file.read_text(encoding="utf-8"))
        evidence = defaultdict(list)
        
        for model_id, mdata in data.get("models", {}).items():
            model_caps = mdata.get("capabilities", {})
            model_health = mdata.get("health", {})
            
            for bench in mdata.get("benchmarks", []):
                task_type = bench["task_type"]
                for run in bench.get("runs", []):
                    if not run.get("success"):
                        continue
                    
                    # Calculate component scores for this run
                    caps = model_caps
                    health = model_health
                    
                    evidence[task_type].append({
                        "model_id": model_id,
                        "quality": run.get("quality_score", 0),
                        "latency_ms": run.get("latency_ms", 0),
                        "ttft_ms": run.get("ttft_ms", 0),
                        "tps": run.get("tokens_per_second", 0),
                        "success": run.get("success", False),
                        "capabilities": caps,
                        "health_score": health.get("health_score", 100),
                        "free": mdata.get("free", False),
                        "context_window": mdata.get("context_window")
                    })
        
        return evidence

    def compute_task_type_correlations(self, evidence: Dict) -> Dict[str, Dict]:
        """Compute which weight dimensions correlate with quality per task type"""
        correlations = {}
        
        for task_type, runs in evidence.items():
            if len(runs) < self.min_samples_per_task:
                continue
            
            n = len(runs)
            qualities = [r["quality"] for r in runs]
            
            # Compute component scores for each run
            component_scores = {
                "capability_fit": [],
                "task_fit": [],
                "speed": [],
                "reliability": [],
                "quota_value": [],
                "context_fit": []
            }
            
            for run in runs:
                caps = run["capabilities"]
                health = run["health_score"]
                
                # capability_fit: cosine similarity with task requirements
                # Simplified: average of relevant capabilities
                cf = (caps.get("reasoning", 0) + caps.get("coding", 0) + 
                      caps.get("tool_use", 0) + caps.get("planning", 0)) / 4
                component_scores["capability_fit"].append(cf)
                
                # task_fit: capability match for specific task
                if task_type == "CODING":
                    tf = (caps.get("coding", 0) + caps.get("tool_use", 0)) / 2
                elif task_type == "REASONING":
                    tf = caps.get("reasoning", 0)
                elif task_type == "FAST_QA":
                    tf = caps.get("speed", 0)
                else:
                    tf = sum(caps.values()) / max(len(caps), 1)
                component_scores["task_fit"].append(tf)
                
                # speed: normalized tps
                tps = run.get("tps", 0)
                component_scores["speed"].append(min(tps / 100.0, 1.0))
                
                # reliability: health score
                component_scores["reliability"].append(health / 100.0)
                
                # quota_value: free with quota
                component_scores["quota_value"].append(1.0 if run.get("free") else 0.0)
                
                # context_fit: context window adequacy
                ctx = run.get("context_window") or 4096
                component_scores["context_fit"].append(min(ctx / 100000.0, 1.0))
            
            # Compute Pearson correlations
            task_correlations = {}
            for comp_name, comp_values in component_scores.items():
                if len(comp_values) != n:
                    continue
                corr = self._pearson_correlation(comp_values, qualities)
                task_correlations[comp_name] = {
                    "correlation": corr,
                    "p_value_approx": self._approx_p_value(corr, n),
                    "samples": n
                }
            
            correlations[task_type] = {
                "correlations": task_correlations,
                "samples": n,
                "avg_quality": sum(qualities) / n,
                "quality_std": math.sqrt(sum((q - sum(qualities)/n)**2 for q in qualities) / max(n-1, 1))
            }
        
        return correlations

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        sum_y2 = sum(yi * yi for yi in y)
        
        num = n * sum_xy - sum_x * sum_y
        den = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))
        
        if den == 0:
            return 0.0
        return num / den

    def _approx_p_value(self, r: float, n: int) -> float:
        if n <= 2 or abs(r) >= 1:
            return 1.0
        t = r * math.sqrt((n - 2) / (1 - r**2))
        # Very rough approximation
        return 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))

    def compute_global_correlations(self, correlations: Dict) -> Dict[str, float]:
        """Aggregate correlations across task types weighted by sample count"""
        global_corr = defaultdict(list)
        total_samples = 0
        
        for task_type, data in correlations.items():
            weight = data["samples"]
            total_samples += weight
            for comp, comp_data in data["correlations"].items():
                global_corr[comp].append((comp_data["correlation"], weight))
        
        result = {}
        for comp, values in global_corr.items():
            weighted_sum = sum(corr * w for corr, w in values)
            total_w = sum(w for _, w in values)
            result[comp] = weighted_sum / total_w if total_w > 0 else 0.0
        
        return result

    def suggest_adaptations(self, global_corr: Dict[str, float]) -> Dict[str, float]:
        """Suggest weight adjustments based on correlations"""
        adjustments = {k: 0.0 for k in ["capability_fit", "task_fit", "speed", 
                                         "reliability", "quota_value", "context_fit"]}
        
        # Positive correlation → increase weight (component predicts quality)
        # Negative correlation → decrease weight
        for comp, corr in global_corr.items():
            if abs(corr) < self.adaptation_threshold:
                continue
            
            # Scale adjustment by correlation strength
            delta = corr * 0.1  # Max 0.1 per cycle
            delta = max(-self.max_adaptation_per_cycle, min(self.max_adaptation_per_cycle, delta))
            adjustments[comp] = delta
        
        return adjustments

    def apply_adaptations(self, adjustments: Dict[str, float], reason: str = ""):
        """Apply weight adjustments with bounds checking and renormalization"""
        for key, delta in adjustments.items():
            if hasattr(self.weights, key) and delta != 0:
                current = getattr(self.weights, key)
                new_val = max(self.bounds["min"], min(self.bounds["max"], current + delta))
                setattr(self.weights, key, round(new_val, 4))
        
        # Renormalize to sum = 1.0
        total = (self.weights.capability_fit + self.weights.task_fit + 
                 self.weights.speed + self.weights.reliability + 
                 self.weights.quota_value + self.weights.context_fit)
        
        for key in ["capability_fit", "task_fit", "speed", "reliability", 
                    "quota_value", "context_fit"]:
            val = getattr(self.weights, key)
            setattr(self.weights, key, round(val / total, 4))
        
        self.weights.version += 1
        self.weights.updated_at = datetime.now().isoformat()
        self.weights.evidence_count += 1
        self.weights.adaptation_reason = reason
        
        self._save_weights()
        self.print_weights()

    def print_weights(self):
        print(f"\nWeights v{self.weights.version} (evidence: {self.weights.evidence_count}):")
        print(f"  capability_fit: {self.weights.capability_fit:.4f}")
        print(f"  task_fit:       {self.weights.task_fit:.4f}")
        print(f"  speed:          {self.weights.speed:.4f}")
        print(f"  reliability:    {self.weights.reliability:.4f}")
        print(f"  quota_value:    {self.weights.quota_value:.4f}")
        print(f"  context_fit:    {self.weights.context_fit:.4f}")
        total = sum([self.weights.capability_fit, self.weights.task_fit, 
                     self.weights.speed, self.weights.reliability, 
                     self.weights.quota_value, self.weights.context_fit])
        print(f"  Sum: {total:.4f}")

    def run_adaptation_cycle(self) -> bool:
        """Run one complete adaptation cycle"""
        print("=== Weight Adaptation Cycle ===")
        
        # Collect evidence
        evidence = self.collect_evidence()
        total_runs = sum(len(runs) for runs in evidence.values())
        print(f"Collected {total_runs} successful runs across {len(evidence)} task types")
        
        if total_runs < self.min_total_samples:
            print(f"Insufficient evidence: {total_runs} < {self.min_total_samples} minimum")
            return False
        
        # Compute correlations
        correlations = self.compute_task_type_correlations(evidence)
        
        print("\nTask-type correlations:")
        for task_type, data in correlations.items():
            print(f"  {task_type} ({data['samples']} samples):")
            for comp, comp_data in data["correlations"].items():
                print(f"    {comp}: r={comp_data['correlation']:.3f} (p~{comp_data['p_value_approx']:.3f})")
        
        # Global correlations
        global_corr = self.compute_global_correlations(correlations)
        print("\nGlobal correlations (weighted):")
        for comp, corr in global_corr.items():
            print(f"  {comp}: r={corr:.3f}")
        
        # Suggest adaptations
        adjustments = self.suggest_adaptations(global_corr)
        print("\nSuggested adjustments:")
        for comp, delta in adjustments.items():
            if delta != 0:
                print(f"  {comp}: {delta:+.4f}")
        
        # Apply if any significant adjustments
        if any(v != 0 for v in adjustments.values()):
            self.apply_adaptations(adjustments, f"Auto-adaptation from {total_runs} benchmark runs")
            return True
        else:
            print("\nNo significant adaptations needed (all |r| < threshold)")
            return False


def main():
    engine = WeightAdaptationEngine()
    engine.print_weights()
    
    print("\nRunning adaptation cycle...")
    adapted = engine.run_adaptation_cycle()
    
    if adapted:
        print("\n[OK] Weights adapted successfully!")
    else:
        print("\n[SKIP] No adaptation performed (insufficient evidence or no significant correlations)")


if __name__ == "__main__":
    main()