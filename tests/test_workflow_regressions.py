import importlib
import os
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestWorkflowRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._stub_dir = tempfile.TemporaryDirectory()
        stub_root = cls._stub_dir.name
        os.makedirs(os.path.join(stub_root, "langgraph"), exist_ok=True)

        with open(os.path.join(stub_root, "dotenv.py"), "w", encoding="utf-8") as f:
            f.write("def load_dotenv(*args, **kwargs):\n    return False\n")

        with open(os.path.join(stub_root, "openai.py"), "w", encoding="utf-8") as f:
            f.write("class OpenAI:\n    def __init__(self, *args, **kwargs):\n        pass\n")

        with open(os.path.join(stub_root, "langgraph", "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")

        with open(os.path.join(stub_root, "langgraph", "graph.py"), "w", encoding="utf-8") as f:
            f.write(
                textwrap.dedent(
                    """
                    END = object()

                    class StateGraph:
                        def __init__(self, *args, **kwargs):
                            pass

                        def add_node(self, *args, **kwargs):
                            pass

                        def add_edge(self, *args, **kwargs):
                            pass

                        def add_conditional_edges(self, *args, **kwargs):
                            pass

                        def set_entry_point(self, *args, **kwargs):
                            pass

                        def compile(self):
                            class _Workflow:
                                def invoke(self, state):
                                    return state

                            return _Workflow()
                    """
                )
            )

        cls._old_openai_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = ""
        sys.path.insert(0, stub_root)
        sys.path.insert(0, ROOT_DIR)

        for mod in [
            "config.config",
            "tools.task_decomposer",
            "src.agent_workflow",
            "src.task_orchestration",
        ]:
            sys.modules.pop(mod, None)

        cls.task_orchestration = importlib.import_module("src.task_orchestration")
        cls.agent_workflow = importlib.import_module("src.agent_workflow")

    @classmethod
    def tearDownClass(cls):
        if cls._old_openai_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = cls._old_openai_key

        stub_root = cls._stub_dir.name
        if stub_root in sys.path:
            sys.path.remove(stub_root)
        if ROOT_DIR in sys.path:
            try:
                sys.path.remove(ROOT_DIR)
            except ValueError:
                pass
        cls._stub_dir.cleanup()

    def test_delete_etc_is_blocked_as_high_risk_path_delete(self):
        intent = self.agent_workflow._extract_single_intent("强制删除/etc目录")
        self.assertEqual(intent["intent"], "delete_path")
        self.assertEqual(intent["parameters"]["path"], "/etc")

        identified = self.agent_workflow.identify_intent(
            {
                "user_input": "强制删除/etc目录",
                "conversation_history": [],
                "environment": {"os_type": "linux"},
            }
        )
        task = identified["task_sequence"][0]
        generated = self.agent_workflow.generate_command(
            {
                **identified,
                "environment": {"os_type": "linux"},
                "branch_results": {},
                "task_outputs": {},
                "resolved_parameters": task["parameters"],
            }
        )

        self.assertEqual(generated["command"], "rm -rf /etc")
        self.assertEqual(generated["risk_level"], "high")

        blocked = self.agent_workflow.execute_command(
            {
                "command": generated["command"],
                "environment": {"os_type": "linux"},
                "task_sequence": [{**task, "status": "pending"}],
                "current_task_index": 0,
                "rollback_stack": [],
                "execution_log": [],
                "task_outputs": {},
                "resolved_parameters": task["parameters"],
                "session_id": "test_delete_etc",
                "risk_explanation": generated.get("risk_explanation", ""),
                "risk_assessment": generated.get("risk_assessment", {}),
            }
        )

        self.assertEqual(blocked["task_sequence"][0]["status"], "failed")
        self.assertIn("rm -rf /etc", blocked["execution_result"])

    def test_create_user_with_disabled_login_stays_in_user_flow(self):
        tasks = self.task_orchestration.build_specialized_task_sequence(
            "创建普通用户dev_test并设置禁止远程登录",
            "linux",
        )

        self.assertEqual([task["intent"] for task in tasks], ["create_user", "set_login_shell"])
        self.assertEqual(tasks[0]["parameters"]["username"], "dev_test")
        self.assertEqual(tasks[1]["parameters"]["shell"], "/sbin/nologin")

    def test_partial_create_user_is_marked_completed_after_verification(self):
        state = {
            "command": "useradd -m dev_test",
            "environment": {"os_type": "linux"},
            "task_sequence": [
                {
                    "intent": "create_user",
                    "task_id": "task_create_user",
                    "parameters": {"username": "dev_test"},
                }
            ],
            "current_task_index": 0,
            "rollback_stack": [],
            "execution_log": [],
            "task_outputs": {},
            "resolved_parameters": {"username": "dev_test"},
            "session_id": "test_partial_create",
            "risk_assessment": {},
        }
        verify_result = type("VerifyRes", (), {"passed": True, "message": "verified"})()

        with mock.patch.object(
            self.agent_workflow.SystemTools,
            "_run_command",
            return_value={"exit_code": 1, "stdout": "", "stderr": "useradd already exists"},
        ), mock.patch.object(
            self.agent_workflow.ExecutionVerifier,
            "verify",
            return_value=verify_result,
        ):
            result = self.agent_workflow.execute_command(state)

        self.assertEqual(result["task_sequence"][0]["status"], "completed")

    def test_delete_user_with_home_cleanup_uses_userdel_r(self):
        tasks = self.task_orchestration.build_specialized_task_sequence(
            "删除刚才创建的用户dev_test并清理它的家目录",
            "linux",
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["intent"], "delete_user")
        self.assertTrue(tasks[0]["parameters"]["remove_home"])

        generated = self.agent_workflow.generate_command(
            {
                "task_sequence": tasks,
                "current_task_index": 0,
                "environment": {"os_type": "linux"},
                "branch_results": {},
                "task_outputs": {},
                "resolved_parameters": tasks[0]["parameters"],
            }
        )

        self.assertEqual(generated["command"], "userdel -r dev_test")


if __name__ == "__main__":
    unittest.main()
