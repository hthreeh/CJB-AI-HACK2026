import time
from typing import Any, Dict, Optional

from src.runtime import get_workflow
from src.session_store import SessionStore, default_session_store


class AgentService:
    def __init__(self, workflow=None, session_store: Optional[SessionStore] = None):
        self.workflow = workflow or get_workflow()
        self.session_store = session_store or default_session_store

    @staticmethod
    def new_session_id() -> str:
        return f"session_{int(time.time())}"

    def load_session(self, session_id: str) -> Dict[str, Any]:
        return self.session_store.load(session_id)

    def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        self.session_store.save(session_id, state)

    def delete_session(self, session_id: str) -> bool:
        return self.session_store.delete(session_id)

    def build_initial_state(self, user_input: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        resolved_session_id = session_id or self.new_session_id()
        saved = self.session_store.load(resolved_session_id)
        return {
            "session_id": resolved_session_id,
            "user_input": user_input,
            "conversation_history": saved.get("conversation_history", []),
            "environment": saved.get("environment", {}),
        }

    def run_query(self, user_input: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        initial_state = self.build_initial_state(user_input=user_input, session_id=session_id)
        result = self.workflow.invoke(initial_state)
        result["user_input"] = user_input
        self.session_store.save(initial_state["session_id"], result)
        return {
            "session_id": initial_state["session_id"],
            "result": result,
        }

    def build_confirmation_state(
        self,
        session_id: str,
        confirmed: bool,
        user_input: Optional[str] = None,
    ) -> Dict[str, Any]:
        saved = self.session_store.load(session_id)
        if not saved:
            raise KeyError(session_id)

        task_sequence = saved.get("task_sequence", [])
        return {
            "session_id": session_id,
            "user_input": saved.get("user_input", user_input or ""),
            "user_confirmation": confirmed,
            "conversation_history": saved.get("conversation_history", []),
            "command": saved.get("command", ""),
            "task_sequence": task_sequence,
            "current_task_index": saved.get("current_task_index", 0),
            "task_status": saved.get("task_status", "in_progress"),
            "environment": saved.get("environment", {}),
            "risk_assessment": {
                **saved.get("risk_assessment", {}),
                "requires_confirmation": False,
            },
            "risk_level": saved.get("risk_level", "medium"),
            "risk_explanation": saved.get("risk_explanation", ""),
            "task_execution_order": saved.get("task_execution_order", []),
            "execution_log": saved.get("execution_log", []),
            "rollback_stack": saved.get("rollback_stack", []),
            "branch_results": saved.get("branch_results", {}),
            "intent": saved.get(
                "intent",
                task_sequence[0].get("intent", "other") if task_sequence else "other",
            ),
            "parameters": saved.get(
                "parameters",
                task_sequence[0].get("parameters", {}) if task_sequence else {},
            ),
            "last_intent": saved.get("last_intent", ""),
            "consistency_issues": saved.get("consistency_issues", []),
            "confirmation_processed": False,
        }

    def run_confirmation(
        self,
        session_id: str,
        confirmed: bool,
        user_input: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = self.build_confirmation_state(
            session_id=session_id,
            confirmed=confirmed,
            user_input=user_input,
        )
        result = self.workflow.invoke(state)
        self.session_store.save(session_id, result)
        return {
            "session_id": session_id,
            "result": result,
        }
