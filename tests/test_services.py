import tempfile
import unittest

from src.agent_service import AgentService
from src.session_store import SessionStore


class FakeWorkflow:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def invoke(self, state):
        self.calls.append(state)
        return dict(self.result)


class TestSessionStore(unittest.TestCase):
    def test_save_trims_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(session_dir=tmpdir, max_history=2)
            store.save(
                "demo",
                {
                    "conversation_history": [
                        {"role": "user", "content": "1"},
                        {"role": "assistant", "content": "2"},
                        {"role": "user", "content": "3"},
                    ]
                },
            )
            loaded = store.load("demo")
            self.assertEqual(
                loaded["conversation_history"],
                [
                    {"role": "assistant", "content": "2"},
                    {"role": "user", "content": "3"},
                ],
            )


class TestAgentService(unittest.TestCase):
    def test_run_query_uses_saved_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(session_dir=tmpdir)
            store.save(
                "session-1",
                {
                    "conversation_history": [{"role": "user", "content": "old"}],
                    "environment": {"os_type": "linux"},
                },
            )
            workflow = FakeWorkflow({"response": "ok"})
            service = AgentService(workflow=workflow, session_store=store)

            execution = service.run_query("new", "session-1")

            self.assertEqual(execution["session_id"], "session-1")
            self.assertEqual(workflow.calls[0]["conversation_history"], [{"role": "user", "content": "old"}])
            self.assertEqual(workflow.calls[0]["environment"], {"os_type": "linux"})
            self.assertEqual(store.load("session-1")["user_input"], "new")

    def test_run_confirmation_uses_server_side_saved_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(session_dir=tmpdir)
            store.save(
                "session-2",
                {
                    "user_input": "delete user demo",
                    "conversation_history": [{"role": "user", "content": "delete user demo"}],
                    "command": "userdel demo",
                    "task_sequence": [{"intent": "delete_user", "parameters": {"username": "demo"}}],
                    "current_task_index": 0,
                    "task_status": "in_progress",
                    "environment": {"os_type": "linux"},
                    "risk_assessment": {"requires_confirmation": True},
                    "risk_level": "medium",
                    "risk_explanation": "needs confirmation",
                },
            )
            workflow = FakeWorkflow({"response": "confirmed"})
            service = AgentService(workflow=workflow, session_store=store)

            execution = service.run_confirmation("session-2", confirmed=True)

            state = workflow.calls[0]
            self.assertTrue(state["user_confirmation"])
            self.assertEqual(state["command"], "userdel demo")
            self.assertFalse(state["risk_assessment"]["requires_confirmation"])
            self.assertEqual(execution["result"]["response"], "confirmed")


if __name__ == "__main__":
    unittest.main()
