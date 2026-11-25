import os
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import main, tools
from app.lsp_client import LSPClient


class LSPDiagnosticsTests(unittest.TestCase):
    def test_agent_and_tools_share_lsp_initializer(self):
        self.assertIs(main.initialize_lsp, tools.initialize_lsp)

    def test_empty_references_suggest_checking_updated_symbol_position(self):
        client = LSPClient.__new__(LSPClient)
        client.open_documents = {}
        client.notify = Mock()
        client.request = Mock(return_value=[])
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.py"
            path.write_text("def example(): pass\n", encoding="utf-8")
            result = client.findReferences(str(path), 1, 5)

        self.assertIn("No references found.", result)
        self.assertIn("edits can change its position", result)

    def test_collects_only_current_new_diagnostics(self):
        original_cwd = Path.cwd()
        with TemporaryDirectory(dir=original_cwd) as temp_dir:
            root = Path(temp_dir)
            pricing_path = root / "pricing.py"
            preview_path = root / "preview.py"
            pricing_path.touch()
            preview_path.touch()
            os.chdir(root)
            try:
                client = LSPClient.__new__(LSPClient)
                pricing_key = client._document_key(str(pricing_path))
                client.open_documents = {pricing_key: 2}
                client.notification_cursor = 0
                client.current_diagnostics = {}
                client.shown_diagnostics = {}

                current_issue = {
                    "range": {"start": {"line": 4, "character": 11}},
                    "message": "Type Price is not assignable to return type int",
                }
                stale_issue = {
                    "range": {"start": {"line": 1, "character": 2}},
                    "message": "stale report",
                }
                preview_issue = {
                    "range": {"start": {"line": 0, "character": 0}},
                    "message": "preview warning",
                }
                new_issue = {
                    "range": {"start": {"line": 0, "character": 0}},
                    "message": "new issue",
                }
                client.notifications = Mock(
                    side_effect=[
                        {
                            "cursor": 5,
                            "notifications": [
                                {
                                    "method": "textDocument/publishDiagnostics",
                                    "params": {
                                        "uri": pricing_path.as_uri(),
                                        "version": 2,
                                        "diagnostics": [current_issue],
                                    },
                                },
                                {
                                    "method": "textDocument/publishDiagnostics",
                                    "params": {
                                        "uri": pricing_path.as_uri(),
                                        "version": 1,
                                        "diagnostics": [stale_issue],
                                    },
                                },
                                {
                                    "method": "textDocument/publishDiagnostics",
                                    "params": {
                                        "uri": preview_path.as_uri(),
                                        "diagnostics": [preview_issue],
                                    },
                                },
                                {
                                    "method": "textDocument/didChange",
                                    "params": {},
                                },
                            ],
                        },
                        {"cursor": 8, "notifications": []},
                        {
                            "cursor": 9,
                            "notifications": [
                                {
                                    "method": "textDocument/publishDiagnostics",
                                    "params": {
                                        "uri": pricing_path.as_uri(),
                                        "version": 2,
                                        "diagnostics": [current_issue, new_issue],
                                    },
                                }
                            ],
                        },
                        {
                            "cursor": 10,
                            "notifications": [
                                {
                                    "method": "textDocument/publishDiagnostics",
                                    "params": {
                                        "uri": pricing_path.as_uri(),
                                        "version": 2,
                                        "diagnostics": [],
                                    },
                                }
                            ],
                        },
                        {
                            "cursor": 11,
                            "notifications": [
                                {
                                    "method": "textDocument/publishDiagnostics",
                                    "params": {
                                        "uri": pricing_path.as_uri(),
                                        "version": 2,
                                        "diagnostics": [current_issue],
                                    },
                                }
                            ],
                        },
                    ]
                )

                first_feedback = client.collect_diagnostic_feedback()
                self.assertIn("pricing.py:", first_feedback)
                self.assertIn(
                    "[Line 5:12] Type Price is not assignable to return type int",
                    first_feedback,
                )
                self.assertIn("preview.py:", first_feedback)
                self.assertNotIn("stale report", first_feedback)
                self.assertEqual(client.collect_diagnostic_feedback(), "")

                new_feedback = client.collect_diagnostic_feedback()
                self.assertIn("[Line 1:1] new issue", new_feedback)
                self.assertNotIn("Line 5:12", new_feedback)
                self.assertEqual(client.collect_diagnostic_feedback(), "")
                self.assertIn(
                    "Type Price is not assignable to return type int",
                    client.collect_diagnostic_feedback(),
                )
                self.assertEqual(
                    [
                        call.kwargs["after"]
                        for call in client.notifications.call_args_list
                    ],
                    [0, 5, 8, 9, 10],
                )
            finally:
                os.chdir(original_cwd)

    def test_attaches_diagnostics_to_latest_tool_result_before_request(self):
        class FakeLSP:
            def __init__(self):
                self.feedback = iter(
                    ["", "", "<new-diagnostics>new issue</new-diagnostics>"]
                )

            def collect_diagnostic_feedback(self):
                return next(self.feedback)

        tool_call = SimpleNamespace(
            id="call-1",
            type="function",
            function=SimpleNamespace(name="write_file", arguments="{}"),
        )
        tool_response = SimpleNamespace(
            role="assistant", content="", tool_calls=[tool_call]
        )
        final_response = SimpleNamespace(role="assistant", content="Done")
        requests = []

        def create(**kwargs):
            requests.append(deepcopy(kwargs["messages"]))
            response = [tool_response, final_response][len(requests) - 1]
            return SimpleNamespace(choices=[SimpleNamespace(message=response)])

        model = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            )
        )
        conversation = [{"role": "user", "content": "Make the migration"}]

        with (
            patch.object(main, "initialize_lsp", return_value=FakeLSP()),
            patch.object(
                main, "process_tool_call", return_value="Successfully wrote file"
            ),
        ):
            self.assertEqual(main.run_agent_loop(model, conversation), "Done")

        tool_result = next(
            message for message in requests[1] if message["role"] == "tool"
        )
        self.assertEqual(
            tool_result["content"],
            "Successfully wrote file\n\n<new-diagnostics>new issue</new-diagnostics>",
        )

    def test_defers_batched_tools_when_diagnostics_arrive_between_calls(self):
        feedback = (
            "<new-diagnostics>checkout.py [Line 5:12] type mismatch</new-diagnostics>"
        )
        lsp = Mock()
        lsp.collect_diagnostic_feedback.side_effect = ["", "", feedback, ""]
        calls = [
            SimpleNamespace(
                id=f"call-{index}",
                type="function",
                function=SimpleNamespace(name="write_file", arguments="{}"),
            )
            for index in range(3)
        ]
        responses = [
            SimpleNamespace(role="assistant", content="", tool_calls=calls),
            SimpleNamespace(role="assistant", content="Done"),
        ]
        requests = []

        def create(**kwargs):
            requests.append(deepcopy(kwargs["messages"]))
            return SimpleNamespace(
                choices=[SimpleNamespace(message=responses[len(requests) - 1])]
            )

        model = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        conversation = [{"role": "user", "content": "Make the migration"}]
        with (
            patch.object(main, "initialize_lsp", return_value=lsp),
            patch.object(
                main, "process_tool_call", return_value="Write succeeded"
            ) as run,
        ):
            self.assertEqual(main.run_agent_loop(model, conversation), "Done")

        self.assertEqual(run.call_count, 1)
        results = [message for message in requests[1] if message["role"] == "tool"]
        self.assertEqual(results[0]["content"], "Write succeeded")
        self.assertIn("not executed", results[1]["content"])
        self.assertIn(feedback, results[2]["content"])

    def test_defers_second_write_even_when_diagnostics_are_not_yet_available(self):
        lsp = Mock()
        lsp.collect_diagnostic_feedback.return_value = ""
        calls = [
            SimpleNamespace(
                id=f"call-{index}",
                type="function",
                function=SimpleNamespace(name="write_file", arguments="{}"),
            )
            for index in range(2)
        ]
        responses = [
            SimpleNamespace(role="assistant", content="", tool_calls=calls),
            SimpleNamespace(role="assistant", content="Done"),
        ]
        requests = []

        def create(**kwargs):
            requests.append(deepcopy(kwargs["messages"]))
            return SimpleNamespace(
                choices=[SimpleNamespace(message=responses[len(requests) - 1])]
            )

        model = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        conversation = [{"role": "user", "content": "Make the migration"}]
        with (
            patch.object(main, "initialize_lsp", return_value=lsp),
            patch.object(
                main, "process_tool_call", return_value="Write succeeded"
            ) as run,
        ):
            self.assertEqual(main.run_agent_loop(model, conversation), "Done")

        self.assertEqual(run.call_count, 1)
        results = [message for message in requests[1] if message["role"] == "tool"]
        self.assertEqual(results[0]["content"], "Write succeeded")
        self.assertIn("Write not executed", results[1]["content"])


if __name__ == "__main__":
    unittest.main()
