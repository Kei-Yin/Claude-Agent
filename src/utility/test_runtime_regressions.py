"""不调用模型的启动路径与工具回执回归测试。"""

import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

from src.llm_tool.tool_executor import execute_code_tool
from src.utility.config_loader import _resolve_config_paths, find_project_root


class TestConfigPaths(unittest.TestCase):
    def test_find_repository_with_arbitrary_directory_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "config.yaml").write_text("{}", encoding="utf-8")
            nested = root / "src" / "utility"
            nested.mkdir(parents=True)
            self.assertEqual(find_project_root(nested, "config.yaml"), root.resolve())

    def test_relative_paths_follow_repository_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = {
                "base_path": {"project_root": ".", "logs_root": "log"},
                "memory_ex": {"storage": {"base_dir": "memory_storage/memory_ex"}},
            }
            resolved = _resolve_config_paths(config, root)
            self.assertEqual(Path(resolved["base_path"]["project_root"]), root)
            self.assertEqual(Path(resolved["base_path"]["logs_root"]), root / "log")
            self.assertEqual(
                Path(resolved["memory_ex"]["storage"]["base_dir"]),
                root / "memory_storage" / "memory_ex",
            )

    def test_explicit_absolute_output_path_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            output = root / "custom-logs"
            resolved = _resolve_config_paths(
                {"base_path": {"project_root": ".", "logs_root": str(output)}}, root,
            )
            self.assertEqual(Path(resolved["base_path"]["logs_root"]), output)


class TestToolReceipts(unittest.TestCase):
    def test_existing_file_create_reports_blocked_even_with_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing.txt"
            target.write_text("original", encoding="utf-8")
            result = execute_code_tool({
                "llm_tool": "create",
                "params": {"path": str(target), "content": "replacement", "summary": "创建文件"},
            })
            self.assertIn("[BLOCKED]", result["content"])
            self.assertNotIn("文件已创建", result["content"])
            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_failed_replace_reports_blocked_even_with_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing.txt"
            target.write_text("original", encoding="utf-8")
            result = execute_code_tool({
                "llm_tool": "str_replace",
                "params": {"path": str(target), "old": "absent", "new": "new", "summary": "修改文件"},
            })
            self.assertIn("[BLOCKED]", result["content"])
            self.assertNotIn("文件已修改", result["content"])
            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_successful_create_and_replace_change_real_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "new.txt"
            created = execute_code_tool({
                "llm_tool": "create",
                "params": {"path": str(target), "content": "original", "summary": "创建文件"},
            })
            self.assertIn("文件已创建", created["content"])
            self.assertEqual(created["role"], "user")
            replaced = execute_code_tool({
                "llm_tool": "str_replace",
                "params": {"path": str(target), "old": "original", "new": "updated", "summary": "修改文件"},
            })
            self.assertIn("文件已修改", replaced["content"])
            self.assertEqual(target.read_text(encoding="utf-8"), "updated\n")


class TestApiFailure(unittest.TestCase):
    def test_api_error_stops_query_without_tool_follow_up(self):
        from src.memory_ex.memory_interface import NoopMemory
        from src.query.query_loop import QueryLoop

        with (
            patch("src.query.query_loop.llm_api_msg.LLMAPIMessage"),
            patch("src.query.query_loop.SessionLog"),
            patch.object(QueryLoop, "_init_memory"),
        ):
            loop = QueryLoop()
        loop._memory = NoopMemory()
        error = "[API_ERROR: 401 invalid credentials]"
        with (
            patch("src.query.query_loop.chat_llm.chat_with_retry", return_value=(error, False, "", None)) as chat,
            patch.object(loop, "_on_llm_req", return_value="start"),
            patch.object(loop, "_on_llm_rsp") as parse_response,
        ):
            loop.run("hello", lambda _: nullcontext(), Mock(), Mock(), Mock(), Mock())
        self.assertEqual(loop.last_error, error)
        chat.assert_called_once()
        parse_response.assert_not_called()
        loop.session.end_query.assert_called_once()


    def test_repeated_tool_circuit_breaker_reports_failure(self):
        from src.memory_ex.memory_interface import NoopMemory
        from src.query.query_loop import QueryLoop

        with (
            patch("src.query.query_loop.llm_api_msg.LLMAPIMessage"),
            patch("src.query.query_loop.SessionLog"),
            patch.object(QueryLoop, "_init_memory"),
        ):
            loop = QueryLoop()
        loop._memory = NoopMemory()
        tool = {"llm_tool": "file_view", "params": {"path": "D:/test.txt", "limit": 1}}
        with (
            patch("src.query.query_loop.chat_llm.chat_with_retry", return_value=("tool", False, "", None)),
            patch.object(loop, "_on_llm_req", return_value="start"),
            patch.object(loop, "_on_llm_rsp", return_value=([tool], "")),
            patch("src.query.query_loop.tool_executor.execute_code_tool", return_value={"role": "user", "content": "first line"}) as execute,
        ):
            loop.run("read and create", lambda _: nullcontext(), Mock(), Mock(), Mock(), Mock())
        self.assertIn("熔断", loop.last_error)
        execute.assert_called_once()


class TestMessageRoles(unittest.TestCase):
    def test_runtime_feedback_is_user_input_after_assistant_turn(self):
        from src.utility.llm_api_msg import LLMAPIMessage

        messages = LLMAPIMessage.__new__(LLMAPIMessage)
        messages.api_messages = [
            {"role": "system", "content": "instructions"},
            {"role": "user", "content": "request"},
            {"role": "assistant", "content": "tool call"},
        ]
        messages.append_tool_exec_result({"role": "system", "content": "tool result"})
        messages.append_micro_info("system", "memory result")
        self.assertEqual([m["role"] for m in messages.get_msg()[-2:]], ["user", "user"])
        self.assertIn("tool result", messages.get_msg()[-2]["content"])

    def test_initial_system_context_keeps_its_role(self):
        from src.utility.llm_api_msg import LLMAPIMessage

        messages = LLMAPIMessage.__new__(LLMAPIMessage)
        messages.api_messages = [{"role": "system", "content": "instructions"}]
        messages.append_micro_info("system", "project context")
        self.assertEqual(messages.get_msg()[-1]["role"], "system")


if __name__ == "__main__":
    unittest.main()
