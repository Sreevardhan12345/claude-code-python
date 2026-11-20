# Only needed for the LSP extension.
# You can ignore this file until you reach that extension.
"""Course-supplied LSP transport client. Document state belongs in your agent."""

import json
import os
import urllib.error
import urllib.request


class LSPClient:
    @classmethod
    def from_environment(cls):
        if "CODECRAFTERS_LSP_URL" not in os.environ:
            return None
        return cls()

    def __init__(self):
        self.url = os.environ["CODECRAFTERS_LSP_URL"]
        self.extension_to_language = self.call("configuration", {})[
            "extensionToLanguage"
        ]

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
        with open(file_path, "r") as file:
            self.notify(
                method="textDocument/didOpen",
                params={
                    "textDocument": {
                        "uri": "file://" + file_path,
                        "languageId": "python",
                        "version": 1,
                        "text": file.read(),
                    }
                },
            )

        definition = self.request(
            method="textDocument/definition",
            params={
                "textDocument": {"uri": "file://" + file_path},
                "position": {"line": line - 1, "character": character - 1},
            },
        )

        uri = definition.get("uri", None)
        location = definition.get("range", None)

        location = location.get("start")
        line, character = location.get("line") + 1, location.get("character") + 1

        if not os.path.exists(uri.replace("file://", "")):
            raise FileNotFoundError

        return f"{uri.replace('file://', '')} at {line}:{character} (1-based line:character)"

    def findReferences(self, file_path: str, line: int, character: int) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError

        file_path = os.path.abspath(file_path)
        with open(file_path, "r") as file:
            self.notify(
                method="textDocument/didOpen",
                params={
                    "textDocument": {
                        "uri": "file://" + file_path,
                        "languageId": "python",
                        "version": 1,
                        "text": file.read(),
                    }
                },
            )

        references = self.request(
            method="textDocument/references",
            params={
                "textDocument": {"uri": "file://" + file_path},
                "position": {"line": line - 1, "character": character - 1},
                "context": {"includeDeclaration": True},
            },
        )

        returnStr = ""
        if len(references) == 0:
            return "No references found."

        for reference in references:
            uri = reference.get("uri", None)
            location = reference.get("range", None)

            location = location.get("start")
            line, character = location.get("line") + 1, location.get("character") + 1

            if not os.path.exists(uri.replace("file://", "")):
                raise FileNotFoundError

            returnStr += f"{uri.replace('file://', '')} at {line}:{character} (1-based line:character)"

        return returnStr

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

        return "LSP operation is not implemented yet"
