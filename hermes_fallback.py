#!/usr/bin/env python3
"""
Hermes Fallback System - Automatic fallback chain execution.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from hermes_router import HermesRouter
from hermes_checkpoint import HermesCheckpoint, Checkpoint
from hermes_journal import HermesJournal


@dataclass
class FallbackEvent:
    timestamp: str
    task_type: str
    original_model: str
    original_provider: str
    fallback_model: str
    fallback_provider: str
    trigger: str
    context_preserved: bool
    checkpoint_id: str
    success: bool


class HermesFallback:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.router = HermesRouter(self.base_path)
        self.checkpoint = HermesCheckpoint(self.base_path)
        self.journal = HermesJournal(self.base_path)
        self.log_dir = self.base_path / "logs" / "routing"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.fallback_log = self.log_dir / "fallback.jsonl"

    def execute_with_fallback(self, task_type: str, free_mode: bool = True,
                              execute_fn=None, context: Dict = None) -> Dict:
        """
        Execute a task with automatic fallback chain.
        """
        fallback_chain = self.router.get_fallback_chain(task_type)
        
        candidates = self._resolve_fallback_chain(fallback_chain, free_mode)
        
        if not candidates:
            return {"success": False, "error": "No candidates available in fallback chain"}
        
        for i, candidate in enumerate(candidates):
            model_id = candidate["model_id"]
            provider = candidate["provider"]
            role = candidate["role"]
            
            print(f"  Attempt {i+1}/{len(candidates)}: {model_id} ({role})")
            
            cp = self.checkpoint.create(
                objective=f"Task execution with fallback",
                current_task=f"{task_type} attempt {i+1}: {model_id}",
                next_action=f"Execute {task_type} with {model_id}",
                model_used=model_id,
                provider_used=provider
            )
            
            if execute_fn:
                try:
                    result = execute_fn(model_id, context)
                    
                    if result.get("success"):
                        self._log_fallback(FallbackEvent(
                            timestamp=datetime.now().isoformat(),
                            task_type=task_type,
                            original_model=candidates[0]["model_id"] if i > 0 else model_id,
                            original_provider=candidates[0]["provider"] if i > 0 else provider,
                            fallback_model=model_id,
                            fallback_provider=provider,
                            trigger="success" if i == 0 else f"fallback_{i}",
                            context_preserved=context is not None,
                            checkpoint_id=cp.timestamp,
                            success=True
                        ))
                        
                        return {
                            "success": True,
                            "result": result,
                            "model_used": model_id,
                            "provider_used": provider,
                            "fallback_chain": [c["model_id"] for c in candidates[:i+1]],
                            "attempt": i + 1
                        }
                    else:
                        print(f"    Failed: {result.get('error')}")
                        
                except Exception as e:
                    print(f"    Exception: {e}")
            
            if i < len(candidates) - 1:
                self._log_fallback(FallbackEvent(
                    timestamp=datetime.now().isoformat(),
                    task_type=task_type,
                    original_model=candidates[0]["model_id"],
                    original_provider=candidates[0]["provider"],
                    fallback_model=candidates[i+1]["model_id"],
                    fallback_provider=candidates[i+1]["provider"],
                    trigger=f"fallback_{i+1}",
                    context_preserved=context is not None,
                    checkpoint_id=cp.timestamp,
                    success=False
                ))
        
        return {"success": False, "error": "All fallback candidates exhausted", "attempted": len(candidates)}

    def _resolve_fallback_chain(self, role_chain: List[str], free_mode: bool) -> List[Dict]:
        """Resolve role names to actual model IDs based on current registry and health"""
        resolved = []
        
        key_mapping = {
            "coding_min": "coding",
            "tool_use_min": "tool_use",
            "reasoning_min": "reasoning",
            "speed_min": "speed",
            "long_context_min": "long_context",
            "vision_min": "vision",
            "all_min": None
        }
        
        for role in role_chain:
            criteria = self.router.policy.get("role_criteria", {}).get(role, {})
            
            capability_min = {}
            for k, v in criteria.items():
                if k in key_mapping and key_mapping[k]:
                    capability_min[key_mapping[k]] = v
            
            models = self.router.get_models(free_only=free_mode, capability_min=capability_min if capability_min else None)
            
            if models:
                scored = []
                for m in models:
                    score = self.router.score_model(m["id"], m, "CODING", free_mode)
                    scored.append((score.total_score, m))
                
                scored.sort(key=lambda x: x[0], reverse=True)
                if scored:
                    best = scored[0][1]
                    resolved.append({
                        "model_id": best["id"],
                        "provider": best["provider"],
                        "role": role
                    })
        
        return resolved

    def provider_fallback(self, task_type: str, free_mode: bool = True,
                          execute_fn=None, context: Dict = None) -> Dict:
        """Try provider-level fallback if all models from primary provider fail"""
        provider_chain = self.router.policy.get("provider_fallback_chain", ["openrouter", "nvidia", "qwencloud"])
        
        for provider in provider_chain:
            models = self.router.get_models(provider=provider, free_only=free_mode)
            if not models:
                continue
            
            print(f"  Trying provider: {provider} ({len(models)} models)")
            
            for model in models:
                if free_mode and not model.get("free"):
                    continue
                
                cp = self.checkpoint.create(
                    objective=f"Provider fallback: {provider}",
                    current_task=f"{task_type} with {model['id']}",
                    next_action=f"Execute {task_type}",
                    model_used=model["id"],
                    provider_used=provider
                )
                
                if execute_fn:
                    try:
                        result = execute_fn(model["id"], context)
                        if result.get("success"):
                            self._log_fallback(FallbackEvent(
                                timestamp=datetime.now().isoformat(),
                                task_type=task_type,
                                original_model="",
                                original_provider="",
                                fallback_model=model["id"],
                                fallback_provider=provider,
                                trigger="provider_fallback",
                                context_preserved=context is not None,
                                checkpoint_id=cp.timestamp,
                                success=True
                            ))
                            return {
                                "success": True,
                                "result": result,
                                "model_used": model["id"],
                                "provider_used": provider,
                                "fallback_type": "provider"
                            }
                    except Exception as e:
                        print(f"    {model['id']} failed: {e}")
        
        return {"success": False, "error": "All providers exhausted"}

    def _log_fallback(self, event: FallbackEvent):
        with open(self.fallback_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def preserve_context_on_switch(self, from_model: str, to_model: str,
                                   context: Dict) -> Dict:
        """Preserve context when switching models"""
        cp = self.checkpoint.create(
            objective=f"Model switch: {from_model} -> {to_model}",
            current_task=context.get("current_task", "unknown"),
            next_action=context.get("next_action", "Continue with new model"),
            model_used=to_model,
            provider_used=to_model.split("/")[0],
            files_changed=context.get("files_changed", [])
        )
        
        summary = {
            "previous_model": from_model,
            "new_model": to_model,
            "checkpoint_id": cp.timestamp,
            "objective": context.get("objective", ""),
            "completed_steps": context.get("completed", []),
            "current_state": context.get("current_state", ""),
            "key_decisions": context.get("decisions", []),
            "files_modified": context.get("files_changed", []),
            "variables": context.get("variables", {}),
            "conversation_summary": context.get("conversation_summary", "")
        }
        
        self.journal.append("MODEL_SWITCH", f"Switched from {from_model} to {to_model}", {
            "from": from_model,
            "to": to_model,
            "checkpoint": cp.timestamp,
            "context_preserved": True
        })
        
        return {
            "checkpoint": cp.timestamp,
            "summary": summary,
            "injection_prompt": self._build_injection_prompt(summary)
        }

    def _build_injection_prompt(self, summary: Dict) -> str:
        """Build system prompt to inject context into new model"""
        return f"""CONTEXT TRANSFER - CONTINUING FROM PREVIOUS MODEL

Previous Model: {summary['previous_model']}
New Model: {summary['new_model']}
Checkpoint: {summary['checkpoint_id']}

Objective: {summary['objective']}

Completed Steps:
{chr(10).join(f'- {s}' for s in summary['completed_steps'])}

Current State: {summary['current_state']}

Key Decisions:
{chr(10).join(f'- {d}' for d in summary['key_decisions'])}

Files Modified:
{chr(10).join(f'- {f}' for f in summary['files_modified'])}

Variables: {json.dumps(summary['variables'])}

Conversation Summary: {summary['conversation_summary']}

CONTINUE FROM HERE. Do not repeat completed work.
"""


def main():
    fallback = HermesFallback()
    print("Fallback system initialized")
    print(f"Fallback log: {fallback.fallback_log}")


if __name__ == "__main__":
    main()