from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

DEFAULT_STATE = {"sessions": []}

class StorageJSON:
    def __init__(self, path: str | Path = "data/data.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return DEFAULT_STATE.copy()
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, state: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
