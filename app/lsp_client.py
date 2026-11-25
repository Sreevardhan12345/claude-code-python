# Only needed for the LSP extension.
# You can ignore this file until you reach that extension.
"""Course-supplied LSP transport client. Document state belongs in your agent."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


class LSPClient:
    @classmethod
    def from_environment(cls):
        if "CODECRAFTERS_LSP_URL" not in os.environ:
            return None
        return cls()

    def __init__(self):
        self.url = os.environ["CODECRAFTERS_LSP_URL"]
        self.open_documents: dict[str, int] = {}
        self.notification_cursor = 0
        self.current_diagnostics: dict[str, tuple[str, list[dict[str, Any]]]] = {}
        self.shown_diagnostics: dict[str, set[tuple[int, int, str]]] = {}
        self.extension_to_language = self.call("configuration", {})[
            "extensionToLanguage"
        ]

    @staticmethod
    def _document_key(path: str) -> str:
        return os.path.normcase(os.path.abspath(path))

    @staticmethod
    def _path_to_uri(path: str) -> str:
        return Path(os.path.abspath(path)).as_uri()

    @staticmethod
    def _path_from_uri(uri: str) -> str:
        parsed_uri = urlsplit(uri)
        if parsed_uri.scheme != "file":
            raise ValueError(f"Expected a file URI, got {uri!r}")

        path = unquote(parsed_uri.path)
        if parsed_uri.netloc:
            path = f"//{parsed_uri.netloc}{path}"
        if os.name == "nt" and len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return os.path.abspath(path)

    def call(self, action, payload):
        request = urllib.request.Request(
            self.url + "/" + action,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(error.read().decode("utf-8")) from error

    def request(self, method, params):
        return self.call("request", {"method": method, "params": params})

    def notify(self, method, params):
        return self.call("notify", {"method": method, "params": params})

    def notifications(self, after=0, timeout_ms=0):
        return self.call("notifications", {"after": after, "timeoutMs": timeout_ms})

    def goToDefinition(self, file_path: str, line: int, character: int) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError

        file_path = os.path.abspath(file_path)
        self.notifyOpen(file_path)

        definition = self.request(
            method="textDocument/definition",
            params={
                "textDocument": {"uri": self._path_to_uri(file_path)},
                "position": {"line": line - 1, "character": character - 1},
            },
        )

        uri = definition.get("uri", None)
        location = definition.get("range", None)

        location = location.get("start")
        line, character = location.get("line") + 1, location.get("character") + 1

        definition_path = self._path_from_uri(uri)
        if not os.path.exists(definition_path):
            raise FileNotFoundError

        return f"{definition_path} at {line}:{character} (1-based line:character)"

    def findReferences(self, file_path: str, line: int, character: int) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError

        file_path = os.path.abspath(file_path)
        self.notifyOpen(file_path)

        references = self.request(
            method="textDocument/references",
            params={
                "textDocument": {"uri": self._path_to_uri(file_path)},
                "position": {"line": line - 1, "character": character - 1},
                "context": {"includeDeclaration": True},
            },
        )

        if len(references) == 0:
            return (
                "No references found. Verify that the line and character point to "
                "the symbol's current definition; edits can change its position. "
                "Read the file and retry if needed."
            )

        locations = []
        for reference in references:
            uri = reference.get("uri", None)
            location = reference.get("range", None)

            location = location.get("start")
            line, character = location.get("line") + 1, location.get("character") + 1

            reference_path = self._path_from_uri(uri)
            if not os.path.exists(reference_path):
                raise FileNotFoundError

            locations.append(
                f"{reference_path} at {line}:{character} (1-based line:character)"
            )

        return "\n".join(locations)

    def notifyOpen(self, path: str):
        file_path = os.path.abspath(path)
        document_key = self._document_key(file_path)
        if document_key in self.open_documents:
            return

        with open(file_path, "r") as file:
            self.notify(
                method="textDocument/didOpen",
                params={
                    "textDocument": {
                        "uri": self._path_to_uri(file_path),
                        "languageId": "python",
                        "version": 1,
                        "text": file.read(),
                    }
                },
            )
        self.open_documents[document_key] = 1

    def notifyChange(self, path: str):
        file_path = os.path.abspath(path)
        document_key = self._document_key(file_path)
        if document_key not in self.open_documents:
            self.notifyOpen(file_path)
            return

        version = self.open_documents[document_key] + 1
        with open(file_path, "r") as file:
            self.notify(
                method="textDocument/didChange",
                params={
                    "textDocument": {
                        "uri": self._path_to_uri(file_path),
                        "version": version,
                    },
                    "contentChanges": [{"text": file.read()}],
                },
            )
        self.open_documents[document_key] = version

    def collect_diagnostic_feedback(self) -> str:
        response = self.notifications(after=self.notification_cursor, timeout_ms=0)
        self.notification_cursor = response["cursor"]

        for notification in response["notifications"]:
            if notification.get("method") != "textDocument/publishDiagnostics":
                continue

            params = notification["params"]
            file_path = self._path_from_uri(params["uri"])
            document_key = self._document_key(file_path)
            version = params.get("version")
            if version is not None and version != self.open_documents.get(document_key):
                continue

            diagnostics = params["diagnostics"]
            self.current_diagnostics[document_key] = (file_path, diagnostics)

        new_issues: list[tuple[str, int, int, str]] = []
        for document_key, (file_path, diagnostics) in self.current_diagnostics.items():
            issue_keys = set()
            for diagnostic in diagnostics:
                start = diagnostic["range"]["start"]
                line = start["line"] + 1
                character = start["character"] + 1
                message = diagnostic["message"]
                issue_key = (line, character, message)
                issue_keys.add(issue_key)
                if issue_key not in self.shown_diagnostics.get(document_key, set()):
                    new_issues.append((file_path, line, character, message))

            self.shown_diagnostics[document_key] = issue_keys

        if not new_issues:
            return ""

        grouped_issues: dict[str, list[tuple[int, int, str]]] = {}
        for file_path, line, character, message in new_issues:
            relative_path = os.path.relpath(file_path)
            grouped_issues.setdefault(relative_path, []).append(
                (line, character, message)
            )

        lines = ["<new-diagnostics>The following new diagnostic issues were detected:"]
        for relative_path, diagnostics in sorted(grouped_issues.items()):
            lines.append(f"\n{relative_path}:")
            for line, character, message in diagnostics:
                lines.append(f"  [Line {line}:{character}] {message}")
        lines.append("</new-diagnostics>")
        return "\n".join(lines)

    def process_lsp_call(
        self, operation: str, file_path: str, line: int, character: int
    ) -> str:
        if operation == "goToDefinition":
            return self.goToDefinition(
                file_path=file_path, line=line, character=character
            )

        elif operation == "findReferences":
            return self.findReferences(
                file_path=file_path, line=line, character=character
            )

        elif operation == "notifyOpen":
            self.notifyOpen(file_path)

        elif operation == "notifyChange":
            self.notifyChange(file_path)

        return "LSP operation is not implemented yet"


_LSP_CLIENT: LSPClient | None = None


def initialize_lsp() -> LSPClient | None:
    global _LSP_CLIENT
    if _LSP_CLIENT is None:
        _LSP_CLIENT = LSPClient.from_environment()
    return _LSP_CLIENT
