import json
import os
from typing import Any, Dict


SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions")
MAX_SESSION_HISTORY = 50


class SessionStore:
    def __init__(self, session_dir: str = SESSION_DIR, max_history: int = MAX_SESSION_HISTORY):
        self.session_dir = session_dir
        self.max_history = max_history
        os.makedirs(self.session_dir, exist_ok=True)

    def _build_path(self, session_id: str) -> str:
        return os.path.join(self.session_dir, f"{session_id}.json")

    def load(self, session_id: str) -> Dict[str, Any]:
        path = self._build_path(session_id)
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
        except Exception:
            pass
        return {}

    def save(self, session_id: str, state: Dict[str, Any]) -> None:
        path = self._build_path(session_id)
        tmp_path = path + ".tmp"
        try:
            serializable = {}
            for key, value in state.items():
                if key == "conversation_history" and isinstance(value, list):
                    serializable[key] = value[-self.max_history :]
                else:
                    serializable[key] = value

            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(serializable, handle, ensure_ascii=False, indent=2, default=str)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def delete(self, session_id: str) -> bool:
        path = self._build_path(session_id)
        if not os.path.exists(path):
            return False
        os.remove(path)
        return True


default_session_store = SessionStore()


def load_session(session_id: str) -> Dict[str, Any]:
    return default_session_store.load(session_id)


def save_session(session_id: str, state: Dict[str, Any]) -> None:
    default_session_store.save(session_id, state)


def delete_session(session_id: str) -> bool:
    return default_session_store.delete(session_id)
