#!/usr/bin/env python3
"""
Hermes Recovery System - Hierarchical session recovery.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class RecoveryState:
    master_loaded: bool = False
    state_loaded: bool = False
    project_loaded: bool = False
    tasks_loaded: bool = False
    checkpoint_loaded: bool = False
    memory_loaded: bool = False
    registry_loaded: bool = False
    health_loaded: bool = False
    context_reconstructed: bool = False
    unknown_items: List[str] = None


class HermesRecovery:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.unknown_items = []

    def load_master(self) -> Optional[Dict]:
        """LOAD MASTER - Load MASTER.md as strategic index"""
        master_file = self.base_path / "MASTER.md"
        if master_file.exists():
            content = master_file.read_text(encoding="utf-8")
            return {"loaded": True, "content": content, "path": str(master_file)}
        self.unknown_items.append("MASTER.md not found")
        return {"loaded": False, "error": "MASTER.md not found"}

    def load_state(self) -> Optional[Dict]:
        """LOAD CURRENT STATE - Load state/current.md"""
        state_file = self.base_path / "state" / "current.md"
        if state_file.exists():
            content = state_file.read_text(encoding="utf-8")
            return {"loaded": True, "content": content, "path": str(state_file)}
        self.unknown_items.append("state/current.md not found")
        return {"loaded": False, "error": "state/current.md not found"}

    def load_project(self) -> Optional[Dict]:
        """LOAD ACTIVE PROJECT - Load memory/projects/active.md or similar"""
        projects_dir = self.base_path / "memory" / "projects"
        if projects_dir.exists():
            projects = list(projects_dir.glob("*.md"))
            if projects:
                latest = max(projects, key=lambda p: p.stat().st_mtime)
                content = latest.read_text(encoding="utf-8")
                return {"loaded": True, "content": content, "path": str(latest)}
        self.unknown_items.append("No active project found")
        return {"loaded": False, "error": "No active project found"}

    def load_tasks(self) -> Optional[Dict]:
        """LOAD PENDING TASKS - Load state/active-tasks.md"""
        tasks_file = self.base_path / "state" / "active-tasks.md"
        if tasks_file.exists():
            content = tasks_file.read_text(encoding="utf-8")
            return {"loaded": True, "content": content, "path": str(tasks_file)}
        self.unknown_items.append("state/active-tasks.md not found")
        return {"loaded": False, "error": "state/active-tasks.md not found"}

    def load_checkpoint(self) -> Optional[Dict]:
        """LOAD RECENT CHECKPOINT - Load state/checkpoint.json"""
        from hermes_checkpoint import HermesCheckpoint
        cp = HermesCheckpoint(self.base_path)
        checkpoint = cp.load_latest()
        if checkpoint:
            return {"loaded": True, "checkpoint": asdict(checkpoint), "path": str(cp.current_file)}
        self.unknown_items.append("No checkpoint found")
        return {"loaded": False, "error": "No checkpoint found"}

    def load_memory(self) -> Optional[Dict]:
        """LOAD RELEVANT MEMORY - Load memory/INDEX.md and key files"""
        index_file = self.base_path / "memory" / "INDEX.md"
        memory = {"index": None, "files": {}}
        
        if index_file.exists():
            memory["index"] = index_file.read_text(encoding="utf-8")
        
        key_files = ["identity.md", "mission.md", "goals.md", "principles.md", 
                     "facts.md", "preferences.md", "decisions.md", "lessons.md",
                     "failures.md", "entities.md"]
        
        for fname in key_files:
            fpath = self.base_path / "memory" / fname
            if fpath.exists():
                memory["files"][fname] = fpath.read_text(encoding="utf-8")
            else:
                self.unknown_items.append(f"memory/{fname} not found")
        
        return {"loaded": True, "memory": memory}

    def load_registry(self) -> Optional[Dict]:
        """LOAD MODEL REGISTRY - Load models/registry.json"""
        registry_file = self.base_path / "models" / "registry.json"
        if registry_file.exists():
            data = json.loads(registry_file.read_text(encoding="utf-8"))
            return {"loaded": True, "models_count": len(data.get("models", {})), "path": str(registry_file)}
        self.unknown_items.append("models/registry.json not found")
        return {"loaded": False, "error": "models/registry.json not found"}

    def load_health(self) -> Optional[Dict]:
        """LOAD PROVIDER HEALTH - Load providers/provider-state.json"""
        health_file = self.base_path / "providers" / "provider-state.json"
        if health_file.exists():
            data = json.loads(health_file.read_text(encoding="utf-8"))
            return {"loaded": True, "providers": list(data.keys()), "path": str(health_file)}
        self.unknown_items.append("providers/provider-state.json not found")
        return {"loaded": False, "error": "providers/provider-state.json not found"}

    def reconstruct_context(self, recovery_data: Dict) -> Dict:
        """RECONSTRUCT EXECUTION CONTEXT - Build context from all loaded data"""
        context = {
            "recovery_timestamp": datetime.now().isoformat(),
            "session_id": recovery_data.get("checkpoint", {}).get("session_id", "unknown"),
            "objective": recovery_data.get("checkpoint", {}).get("objective", "unknown"),
            "current_task": recovery_data.get("checkpoint", {}).get("current_task", "unknown"),
            "next_action": recovery_data.get("checkpoint", {}).get("next_action", "unknown"),
            "completed": recovery_data.get("checkpoint", {}).get("completed", []),
            "in_progress": recovery_data.get("checkpoint", {}).get("in_progress", []),
            "blocked": recovery_data.get("checkpoint", {}).get("blocked", []),
            "model_used": recovery_data.get("checkpoint", {}).get("model_used", "unknown"),
            "provider_used": recovery_data.get("checkpoint", {}).get("provider_used", "unknown"),
            "risks": recovery_data.get("checkpoint", {}).get("risks", []),
            "unknown_items": self.unknown_items
        }
        
        # Extract key info from master
        if recovery_data.get("master", {}).get("loaded"):
            context["master_available"] = True
        
        # Extract key info from state
        if recovery_data.get("state", {}).get("loaded"):
            context["state_available"] = True
        
        # Extract project info
        if recovery_data.get("project", {}).get("loaded"):
            context["project_available"] = True
        
        # Extract tasks info
        if recovery_data.get("tasks", {}).get("loaded"):
            context["tasks_available"] = True
        
        # Extract memory info
        if recovery_data.get("memory", {}).get("loaded"):
            context["memory_available"] = True
        
        # Extract registry info
        if recovery_data.get("registry", {}).get("loaded"):
            context["models_available"] = recovery_data["registry"].get("models_count", 0)
        
        # Extract health info
        if recovery_data.get("health", {}).get("loaded"):
            context["providers_available"] = recovery_data["health"].get("providers", [])
        
        return context

    def recover_session(self) -> Dict:
        """Main recovery entry point - executes full hierarchical recovery"""
        print("=== Starting Hierarchical Recovery ===")
        
        recovery_data = {}
        
        # Level 1: MASTER
        print("1. Loading MASTER...")
        recovery_data["master"] = self.load_master()
        
        # Level 2: CURRENT STATE
        print("2. Loading CURRENT STATE...")
        recovery_data["state"] = self.load_state()
        
        # Level 3: ACTIVE PROJECT
        print("3. Loading ACTIVE PROJECT...")
        recovery_data["project"] = self.load_project()
        
        # Level 4: PENDING TASKS
        print("4. Loading PENDING TASKS...")
        recovery_data["tasks"] = self.load_tasks()
        
        # Level 5: RECENT CHECKPOINT
        print("5. Loading RECENT CHECKPOINT...")
        recovery_data["checkpoint"] = self.load_checkpoint()
        
        # Level 6: RELEVANT MEMORY
        print("6. Loading RELEVANT MEMORY...")
        recovery_data["memory"] = self.load_memory()
        
        # Level 7: MODEL REGISTRY
        print("7. Loading MODEL REGISTRY...")
        recovery_data["registry"] = self.load_registry()
        
        # Level 8: PROVIDER HEALTH
        print("8. Loading PROVIDER HEALTH...")
        recovery_data["health"] = self.load_health()
        
        # Level 9: RECONSTRUCT CONTEXT
        print("9. Reconstructing EXECUTION CONTEXT...")
        context = self.reconstruct_context(recovery_data)
        recovery_data["context"] = context
        
        # Summary
        loaded_levels = sum(1 for k, v in recovery_data.items() 
                           if k != "context" and isinstance(v, dict) and v.get("loaded"))
        total_levels = 8
        
        print(f"\n=== Recovery Complete ===")
        print(f"Levels loaded: {loaded_levels}/{total_levels}")
        print(f"Unknown items: {len(self.unknown_items)}")
        for item in self.unknown_items:
            print(f"  - {item}")
        
        return recovery_data


def main():
    recovery = HermesRecovery()
    result = recovery.recover_session()
    
    # Save recovery result
    output_file = recovery.base_path / "state" / f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRecovery result saved to: {output_file}")


if __name__ == "__main__":
    main()