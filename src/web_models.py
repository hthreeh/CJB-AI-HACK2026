from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UserRequest(BaseModel):
    input: str
    session_id: Optional[str] = None


class ConfirmRequest(BaseModel):
    session_id: str
    confirmed: bool
    user_input: Optional[str] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    command: Optional[str] = None
    task_sequence: Optional[List[Dict[str, Any]]] = None
    current_task_index: Optional[int] = None
    task_status: Optional[str] = None
    environment: Optional[Dict[str, Any]] = None
    risk_level: Optional[str] = None
    risk_explanation: Optional[str] = None


class AgentResponse(BaseModel):
    response: str
    execution_result: str
    risk_level: Optional[str] = None
    requires_confirmation: Optional[bool] = False
    risk_assessment: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    command: Optional[str] = None
    task_sequence: Optional[List[Dict[str, Any]]] = None
    current_task_index: Optional[int] = None
    task_status: Optional[str] = None
    environment: Optional[Dict[str, Any]] = None
    branch_results: Optional[Dict[str, Any]] = None
    execution_log: Optional[List[Dict[str, Any]]] = None
    explanation: Optional[str] = None
