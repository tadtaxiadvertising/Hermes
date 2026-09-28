#!/usr/bin/env python3
"""
Hermes Checkpoint System - Atomic checkpoints for recovery.
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class Checkpoint:
    timestamp: str
    session_id: str
    objective: str
    current_task: str
    completed: List[str] = field(default_factory=list)
    in_progress: List[str] = field(default_factory=list)
    blocked: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    model_used: str = ""
    provider_used: str = ""
    next_action: str = ""
    risks: List[str] = field(default_factory=list)
    version: str = "1.0"
    schema_version: str = "1.0"


class HermesCheckpoint:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.checkpoint_dir = self.base_path / "state" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.base_path / "state" / "checkpoint.json"
        self.session_id = os.environ.get("HERMES_SESSION_ID", datetime.now().strftime("%Y-%m-%d-session-1"))

    def create(self, **kwargs) -> Checkpoint:
        checkpoint = Checkpoint(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            **kwargs
        )
        self._atomic_write(checkpoint)
        self._archive(checkpoint)
        return checkpoint

    def _atomic_write(self, checkpoint: Checkpoint):
        temp_file = self.current_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(asdict(checkpoint), indent=2, ensure_ascii=False), encoding="utf-8")
        temp_file.replace(self.current_file)

    def _archive(self, checkpoint: Checkpoint):
        archive_file = self.checkpoint_dir / f"{checkpoint.timestamp.replace(':', '-')}_{self.session_id}.json"
        archive_file.write_text(json.dumps(asdict(checkpoint), indent=2, ensure_ascii=False), encoding="utf-8")

    def load_current(self) -> Optional[Checkpoint]:
        if self.current_file.exists():
            data = json.loads(self.current_file.read_text(encoding="utf-8"))
            return Checkpoint(**data)
        return None

    def load_latest(self) -> Optional[Checkpoint]:
        checkpoints = sorted(self.checkpoint_dir.glob("*.json"), reverse=True)
        if checkpoints:
            data = json.loads(checkpoints[0].read_text(encoding="utf-8"))
            return Checkpoint(**data)
        return None

    def load_by_session(self, session_id: str) -> Optional[Checkpoint]:
        checkpoints = sorted(self.checkpoint_dir.glob(f"*_{session_id}.json"), reverse=True)
        if checkpoints:
            data = json.loads(checkpoints[0].read_text(encoding="utf-8"))
            return Checkpoint(**data)
        return None

    def list_checkpoints(self) -> List[Dict]:
        result = []
        for f in sorted(self.checkpoint_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                result.append({
                    "file": f.name,
                    "timestamp": data.get("timestamp"),
                    "objective": data.get("objective"),
                    "current_task": data.get("current_task")
                })
            except:
                pass
        return result


def checkpoint_before_destructive(func):
    """Decorator to auto-checkpoint before destructive operations."""
    def wrapper(*args, **kwargs):
        cp = HermesCheckpoint()
        cp.create(
            objective=f"Pre-destructive: {func.__name__}",
            current_task=func.__name__,
            next_action=f"Execute {func.__name__}"
        )
        return func(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    cp = HermesCheckpoint()
    checkpoint = cp.create(
        objective="Test checkpoint system",
        current_task="Initialize checkpoint",
        next_action="Verify checkpoint loading"
    )
    print(f"Created checkpoint: {checkpoint.timestamp}")
    
    loaded = cp.load_current()
    print(f"Loaded: {loaded.objective}")