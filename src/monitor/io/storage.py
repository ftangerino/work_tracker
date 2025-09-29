###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

###################################################################################################
# 💾 STORAGE (persistência simples em JSON)
###################################################################################################

_DEFAULT_STATE: Dict[str, Any] = {"sessions": []}

class StorageJSON:
    """
    Persistência leve em arquivo JSON.
    - Garante que a pasta exista.
    - Retorna um estado padrão quando o arquivo ainda não existe.
    """
    def __init__(self, path: str | Path = "data/data.json") -> None:
        self.path: Path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ----------------- I/O -----------------

    def load(self) -> Dict[str, Any]:
        """Carrega o dicionário de estado do arquivo JSON (ou estado padrão)."""
        if not self.path.exists():
            # cópia para evitar mutação externa do default
            return dict(_DEFAULT_STATE)
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, state: Dict[str, Any]) -> None:
        """Salva o dicionário de estado no arquivo JSON (indentado e UTF-8)."""
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
