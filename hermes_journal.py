#!/usr/bin/env python3
"""
Hermes Journal System - Append-only session journal with consolidation.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class JournalEntry:
    timestamp: str
    event_type: str
    content: str
    metadata: Dict[str, Any]


class HermesJournal:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.journal_dir = self.base_path / "memory" / "journal"
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = self._generate_session_id()
        self.journal_file = self.journal_dir / f"{self.session_id}.md"
        self.entries: List[JournalEntry] = []
        self._load_existing()

    def _generate_session_id(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        existing = list(self.journal_dir.glob(f"{today}-session-*.md"))
        session_num = len(existing) + 1
        return f"{today}-session-{session_num}"

    def _load_existing(self):
        if self.journal_file.exists():
            content = self.journal_file.read_text(encoding="utf-8")
            for line in content.strip().split("\n"):
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        self.entries.append(JournalEntry(**data))
                    except json.JSONDecodeError:
                        pass

    def append(self, event_type: str, content: str, metadata: Dict = None):
        entry = JournalEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            content=content,
            metadata=metadata or {}
        )
        self.entries.append(entry)
        self._write_entry(entry)

    def _write_entry(self, entry: JournalEntry):
        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def get_entries(self, event_type: str = None) -> List[JournalEntry]:
        if event_type:
            return [e for e in self.entries if e.event_type == event_type]
        return self.entries

    def consolidate(self) -> Dict[str, List[Dict]]:
        """Extract facts, decisions, lessons from journal for promotion to permanent memory."""
        promoted = {
            "facts": [],
            "decisions": [],
            "lessons": [],
            "tasks": [],
            "entities": []
        }
        
        for entry in self.entries:
            content = entry.content
            if content.startswith("FACT:"):
                promoted["facts"].append({"content": content[5:].strip(), "source": "journal", "timestamp": entry.timestamp})
            elif content.startswith("DECISION:"):
                promoted["decisions"].append({"content": content[9:].strip(), "source": "journal", "timestamp": entry.timestamp})
            elif content.startswith("LESSON:"):
                promoted["lessons"].append({"content": content[7:].strip(), "source": "journal", "timestamp": entry.timestamp})
            elif content.startswith("TASK:"):
                promoted["tasks"].append({"content": content[5:].strip(), "source": "journal", "timestamp": entry.timestamp})
            elif content.startswith("ENTITY:"):
                promoted["entities"].append({"content": content[7:].strip(), "source": "journal", "timestamp": entry.timestamp})
        
        return promoted

    def close_session(self):
        self.append("SESSION_END", f"Session {self.session_id} closed", {"entries_count": len(self.entries)})


if __name__ == "__main__":
    journal = HermesJournal()
    journal.append("SESSION_START", "Journal system initialized", {"session_id": journal.session_id})
    print(f"Journal started: {journal.session_id}")
    print(f"File: {journal.journal_file}")