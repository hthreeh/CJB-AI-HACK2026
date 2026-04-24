import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple


TERMINAL_FAILURE_STATUSES = {"failed", "cancelled", "rolled_back", "blocked"}
SUCCESSFUL_DEPENDENCY_STATUSES = {"completed", "skipped"}
ELEVATED_INTENTS = {
    "create_user",
    "delete_user",
    "set_login_shell",
    "delete_path",
    "install_software",
    "uninstall_software",
    "manage_service",
    "cleanup_logs",
    "configure_sudo",
    "deploy_workspace",
    "modify_service_config",
    "ensure_home_directory",
    "write_file",
    "set_permissions",
}


def _default_home_for_user(username: str, os_type: str) -> str:
    if os_type == "windows":
        return f"C:\\Users\\{username}"
    return f"/home/{username}"


def _contains_any(text: str, patterns: List[str]) -> bool:
    lowered = (text or "").lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _strip_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"', "\u201c", "\u201d", "\u2018", "\u2019"}:
        return text[1:-1]
    return text


def build_specialized_task_sequence(user_input: str, os_type: str = "linux") -> List[Dict[str, Any]]:
    text = user_input.strip()

    create_user_match = re.search(
        r"(?:\u521b\u5efa|\u65b0\u5efa|create|add)\s*(?:\u666e\u901a)?\s*(?:\u7528\u6237|user)\s*([A-Za-z_][A-Za-z0-9_-]{0,31})(?![A-Za-z0-9_-])",
        text,
        re.IGNORECASE,
    )
    delete_user_match = re.search(
        r"(?:\u5220\u9664|\u79fb\u9664|delete|remove).*?(?:\u7528\u6237|user)\s*([A-Za-z_][A-Za-z0-9_-]{0,31})(?![A-Za-z0-9_-])",
        text,
        re.IGNORECASE,
    )
    home_match = re.search(r"((?:/|~|[A-Za-z]:\\)[^,\s\uff0c\u3002;]+)", text)

    if delete_user_match:
        username = delete_user_match.group(1)
        remove_home = (
            _contains_any(
                text,
                [
                    "\u5bb6\u76ee\u5f55",
                    "\u4e3b\u76ee\u5f55",
                    "remove home",
                    "home directory",
                    "--remove-home",
                ],
            )
            and _contains_any(
                text,
                [
                    "\u5220\u9664",
                    "\u79fb\u9664",
                    "\u6e05\u7406",
                    "\u6e05\u9664",
                    "delete",
                    "remove",
                    "cleanup",
                ],
            )
        )
        return [
            {
                "task_id": "task_delete_user",
                "intent": "delete_user",
                "description": f"Delete user {username}",
                "parameters": {
                    "username": username,
                    "remove_home": remove_home,
                },
                "depends_on": [],
                "branch_type": "sequential",
                "error_strategy": "abort",
                "is_critical": True,
                "can_rollback": False,
                "post_validation": {
                    "validation_command": f"if id {username} >/dev/null 2>&1; then exit 1; fi" + (f"; if [ -d /home/{username} ]; then exit 1; fi" if remove_home else ""),
                    "expected_result": "",
                    "failure_action": "abort",
                },
            }
        ]

    if not create_user_match:
        return []

    username = create_user_match.group(1)
    home_directory = home_match.group(1) if home_match else _default_home_for_user(username, os_type)
    disable_login = _contains_any(
        text,
        [
            "\u7981\u6b62\u8fdc\u7a0b\u767b\u5f55",
            "\u7981\u6b62\u767b\u5f55",
            "\u7981\u7528\u767b\u5f55",
            "nologin",
            "/sbin/nologin",
        ],
    )

    tasks: List[Dict[str, Any]] = [
        {
            "task_id": "task_create_user",
            "intent": "create_user",
            "description": f"Create user {username}",
            "parameters": {
                "username": username,
                "home_directory": home_directory,
            },
            "depends_on": [],
            "branch_type": "sequential",
            "error_strategy": "abort",
            "is_critical": True,
            "can_rollback": True,
            "rollback_action": {
                "command": f"userdel {username}",
                "description": f"Delete user {username} if subsequent tasks fail",
            },
            "post_validation": {
                "validation_command": f"id {username}",
                "expected_result": username,
                "failure_action": "abort",
            },
        }
    ]

    if disable_login:
        tasks.append(
            {
                "task_id": "task_set_login_shell",
                "intent": "set_login_shell",
                "description": f"Set login shell for {username}",
                "parameters": {
                    "username": username,
                    "shell": "/sbin/nologin",
                },
                "depends_on": ["task_create_user"],
                "branch_type": "sequential",
                "error_strategy": "abort",
                "is_critical": True,
                "can_rollback": False,
                "post_validation": {
                    "validation_command": f"getent passwd {username} | grep /sbin/nologin",
                    "expected_result": "/sbin/nologin",
                    "failure_action": "abort",
                },
            }
        )

    file_match = re.search(r"(?:\u521b\u5efa\u6587\u4ef6|create file)\s+([A-Za-z0-9_.-]+)", text, re.IGNORECASE)
    content_match = re.search(r"(?:\u5199\u5165|write)\s*[\"'\u201c\u201d](.+?)[\"'\u201c\u201d]", text, re.IGNORECASE)
    mode_match = re.search(r"(?:\u6743\u9650\u8bbe\u4e3a|chmod|mode)\s*([0-7]{3,4})", text, re.IGNORECASE)

    if not (file_match and content_match and mode_match):
        return tasks

    file_name = file_match.group(1)
    file_content = _strip_quotes(content_match.group(1))
    file_mode = mode_match.group(1)

    tasks.extend(
        [
            {
                "task_id": "task_ensure_home",
                "intent": "ensure_home_directory",
                "description": f"Ensure home directory for {username}",
                "parameters": {
                    "path": "{{task_create_user.home_directory}}",
                    "owner": username,
                    "mode": "755",
                },
                "depends_on": ["task_create_user"],
                "branch_type": "sequential",
                "error_strategy": "abort",
                "is_critical": True,
                "can_rollback": False,
                "post_validation": {
                    "validation_command": "test -d {{task_create_user.home_directory}}",
                    "expected_result": "",
                    "failure_action": "abort",
                },
            },
            {
                "task_id": "task_write_file",
                "intent": "write_file",
                "description": f"Write file {file_name} in {username} home",
                "parameters": {
                    "path": f"{{{{task_create_user.home_directory}}}}/{file_name}",
                    "content": file_content,
                    "owner": username,
                    "mode": "644",
                },
                "depends_on": ["task_ensure_home"],
                "branch_type": "sequential",
                "error_strategy": "abort",
                "is_critical": True,
                "can_rollback": False,
                "post_validation": {
                    "validation_command": f"test -f {{{{task_create_user.home_directory}}}}/{file_name}",
                    "expected_result": "",
                    "failure_action": "abort",
                },
            },
            {
                "task_id": "task_set_permissions",
                "intent": "set_permissions",
                "description": f"Set permissions on {file_name}",
                "parameters": {
                    "path": "{{task_write_file.file_path}}",
                    "mode": file_mode,
                },
                "depends_on": ["task_write_file"],
                "branch_type": "sequential",
                "error_strategy": "abort",
                "is_critical": True,
                "can_rollback": False,
                "post_validation": {
                    "validation_command": "test \"$(stat -c '%a' {{task_write_file.file_path}} 2>/dev/null || stat -f '%Lp' {{task_write_file.file_path}} 2>/dev/null)\" = \"" + file_mode + "\"",
                    "expected_result": "",
                    "failure_action": "abort",
                },
            },
        ]
    )
    return tasks


def resolve_template_value(value: Any, task_outputs: Dict[str, Dict[str, Any]]) -> Any:
    if isinstance(value, str):
        pattern = re.compile(r"\{\{([^{}]+)\}\}")

        def replacer(match: re.Match[str]) -> str:
            expr = match.group(1).strip()
            if "." not in expr:
                return match.group(0)
            task_id, field = expr.split(".", 1)
            task_data = task_outputs.get(task_id, {})
            replacement = task_data.get(field)
            return str(replacement) if replacement is not None else match.group(0)

        return pattern.sub(replacer, value)

    if isinstance(value, dict):
        return {key: resolve_template_value(item, task_outputs) for key, item in value.items()}

    if isinstance(value, list):
        return [resolve_template_value(item, task_outputs) for item in value]

    return value


def evaluate_dependency_state(task_sequence: List[Dict[str, Any]], task: Dict[str, Any]) -> Tuple[bool, List[str]]:
    if not task.get("depends_on"):
        return True, []

    task_map = {item.get("task_id", ""): item for item in task_sequence}
    blockers = []
    for dep_id in task.get("depends_on", []):
        dep_task = task_map.get(dep_id)
        if not dep_task:
            blockers.append(f"missing:{dep_id}")
            continue
        dep_status = dep_task.get("status", "pending")
        if dep_status in TERMINAL_FAILURE_STATUSES:
            blockers.append(dep_id)
        elif dep_status not in SUCCESSFUL_DEPENDENCY_STATUSES:
            blockers.append(dep_id)
    return not blockers, blockers


def get_privilege_context(os_type: str) -> Dict[str, Any]:
    if os_type == "windows":
        return {
            "is_root": False,
            "sudo_available": False,
            "passwordless_sudo": False,
            "strategy": "windows-elevation-required",
        }

    is_root = hasattr(os, "geteuid") and os.geteuid() == 0
    sudo_path = shutil.which("sudo")
    passwordless = False

    if not is_root and sudo_path:
        try:
            result = subprocess.run(
                [sudo_path, "-n", "true"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            passwordless = result.returncode == 0
        except Exception:
            passwordless = False

    return {
        "is_root": is_root,
        "sudo_available": bool(sudo_path),
        "passwordless_sudo": passwordless,
        "strategy": "direct" if is_root else ("sudo-n" if passwordless else "unavailable"),
    }


def task_requires_elevation(task: Dict[str, Any], params: Optional[Dict[str, Any]] = None, os_type: str = "linux") -> bool:
    if os_type == "windows":
        return task.get("intent") in ELEVATED_INTENTS
    if params and params.get("requires_elevation") is False:
        return False
    if params and params.get("requires_elevation") is True:
        return True
    return task.get("intent") in ELEVATED_INTENTS


def apply_privilege_prefix(command: str, task: Dict[str, Any], params: Dict[str, Any], os_type: str) -> Tuple[str, Dict[str, Any]]:
    context = get_privilege_context(os_type)
    if not task_requires_elevation(task, params, os_type):
        return command, context
    if context["is_root"]:
        return command, context
    if os_type != "windows" and context["passwordless_sudo"]:
        return f"sudo -n {command}", context
    return command, context


def build_task_outputs(task: Dict[str, Any], params: Dict[str, Any], os_type: str) -> Dict[str, Any]:
    intent = task.get("intent", "other")
    outputs: Dict[str, Any] = {}

    if intent == "create_user":
        username = params.get("username", "")
        outputs["username"] = username
        outputs["home_directory"] = params.get("home_directory") or _default_home_for_user(username, os_type)
    elif intent == "set_login_shell":
        outputs["username"] = params.get("username", "")
        outputs["shell"] = params.get("shell", "")
    elif intent == "ensure_home_directory":
        outputs["home_directory"] = params.get("path", "")
    elif intent == "write_file":
        outputs["file_path"] = params.get("path", "")
        outputs["content"] = params.get("content", "")
    elif intent == "set_permissions":
        outputs["path"] = params.get("path", "")
        outputs["mode"] = params.get("mode", "")
    elif "path" in params:
        outputs["path"] = params.get("path", "")

    return outputs


def is_non_retryable_failure(command: str, stderr: str) -> bool:
    combined = f"{command}\n{stderr}".lower()
    return any(
        token in combined
        for token in (
            "sudo: a password is required",
            "sudo: no tty present",
            "permission denied",
            "command not found",
            "useradd: permission denied",
            "already exists",
            "does not exist",
            "doesn't exist",
        )
    )
