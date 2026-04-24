import unittest

from src.task_orchestration import (
    build_specialized_task_sequence,
    build_task_outputs,
    evaluate_dependency_state,
    resolve_template_value,
)


class TestTaskOrchestration(unittest.TestCase):
    def test_build_specialized_task_sequence_for_user_home_file_flow(self):
        tasks = build_specialized_task_sequence(
            "创建用户 dev01，并设置它的家目录，然后在它的家目录下创建文件 test，并写入“agent-test”，然后再把这个文件的权限设为755",
            "linux",
        )

        self.assertEqual(len(tasks), 4)
        self.assertEqual(tasks[0]["intent"], "create_user")
        self.assertEqual(tasks[1]["depends_on"], ["task_create_user"])
        self.assertEqual(tasks[2]["parameters"]["path"], "{{task_create_user.home_directory}}/test")
        self.assertEqual(tasks[3]["parameters"]["path"], "{{task_write_file.file_path}}")

    def test_resolve_template_value_uses_task_outputs(self):
        resolved = resolve_template_value(
            {
                "path": "{{task_create_user.home_directory}}/test",
                "mode": "{{task_set_permissions.mode}}",
            },
            {
                "task_create_user": {"home_directory": "/home/dev01"},
                "task_set_permissions": {"mode": "755"},
            },
        )

        self.assertEqual(resolved["path"], "/home/dev01/test")
        self.assertEqual(resolved["mode"], "755")

    def test_dependency_failure_blocks_task(self):
        ready, blockers = evaluate_dependency_state(
            [
                {"task_id": "task_a", "status": "failed"},
                {"task_id": "task_b", "status": "pending", "depends_on": ["task_a"]},
            ],
            {"task_id": "task_b", "status": "pending", "depends_on": ["task_a"]},
        )

        self.assertFalse(ready)
        self.assertEqual(blockers, ["task_a"])

    def test_build_task_outputs_tracks_file_path(self):
        outputs = build_task_outputs(
            {"intent": "write_file"},
            {"path": "/home/dev01/test", "content": "agent-test"},
            "linux",
        )

        self.assertEqual(outputs["file_path"], "/home/dev01/test")
        self.assertEqual(outputs["content"], "agent-test")

    def test_build_specialized_task_sequence_for_create_user_with_disabled_login(self):
        tasks = build_specialized_task_sequence(
            "创建普通用户dev_test并设置禁止远程登录",
            "linux",
        )

        self.assertEqual([task["intent"] for task in tasks], ["create_user", "set_login_shell"])
        self.assertEqual(tasks[0]["parameters"]["username"], "dev_test")
        self.assertEqual(tasks[1]["parameters"]["shell"], "/sbin/nologin")
        self.assertEqual(tasks[1]["depends_on"], ["task_create_user"])

    def test_build_specialized_task_sequence_for_delete_user_with_home_cleanup(self):
        tasks = build_specialized_task_sequence(
            "删除刚才创建的用户dev_test并清理它的家目录",
            "linux",
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["intent"], "delete_user")
        self.assertEqual(tasks[0]["parameters"]["username"], "dev_test")
        self.assertTrue(tasks[0]["parameters"]["remove_home"])


if __name__ == "__main__":
    unittest.main()
