import json

from .registry import Registry

TOOLS = Registry("tools")


@TOOLS.register("read_file")
def read_file(path: str) -> str:
    """Read a file from the local filesystem."""
    with open(path, "r") as f:
        return f.read()


@TOOLS.register("write_file")
def write_file(path: str, content: str) -> str:
    """Write content to a file on the local filesystem."""
    with open(path, "w") as f:
        f.write(content)

    return f"Successfully wrote to file {path}"


@TOOLS.register("Bash")
def run_bash_command(command: str) -> str:
    """Run a bash command and return the output."""
    import subprocess

    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
        )
        return result.stdout.decode("utf-8")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Error running command {command}: {e.stderr.decode('utf-8')}")


@TOOLS.register("Skill")
def load_skill(name: str, args: str = "", fork_runner=None) -> str:
    """Load a skill's instructions into the conversation."""
    from .skills import Skill

    skill = Skill(name, args=args.split() if args else [])
    if skill.context == "fork":
        if fork_runner is None:
            raise RuntimeError("A fork runner is required for fork-context skills")
        return fork_runner([{"role": "user", "content": skill.body}])
    return skill.prompt


@TOOLS.register("LSP")
def lsp(operation: str, filePath: str, line: int, character: int) -> str:
    """Finds and Returns the file, line, and character where a symbol is defined.
    Indices are 1 based"""
    from .main import initialize_lsp
    from os import path

    client = initialize_lsp()

    # TODO: Process filepath into uri like - no special characters like " " -> "%20"
    if operation == "goToDefinition":
        # step1: notify file to lsp
        if not path.exists(filePath):
            raise FileNotFoundError
        filePath = path.abspath(filePath)
        with open(filePath, "r") as file:
            client.notify(
                method="textDocument/didOpen",
                params={
                    "textDocument": {
                        "uri": "file://"+filePath,
                        "languageId": "python",
                        "version": 1,
                        "text": file.read(),
                    }
                },
            )

        definition = client.request(
            method="textDocument/definition",
            params={
                "textDocument": {"uri": "file://"+filePath},
                "position": {"line": line - 1, "character": character - 1},
            },
        )

        uri = definition.get("uri", None)
        location = definition.get("range", None)

        location = location.get("start")
        line, character = location.get("line") + 1, location.get("character") + 1

        if not path.exists(uri.replace("file://", "")):
            raise FileNotFoundError
        
        return f"{uri.replace('file://', '')} at {line}:{character} (1-based line:character)"


    return "LSP is not implemented yet"


def process_tool_call(tool_call, fork_runner=None):
    """Process a tool call and return the result."""
    if tool_call.function.name not in TOOLS:
        raise ValueError(f"Tool {tool_call.function.name} is not registered.")
    args_dict = json.loads(tool_call.function.arguments)
    tool = TOOLS.get(tool_call.function.name)
    if tool_call.function.name == "Skill":
        return tool(**args_dict, fork_runner=fork_runner)
    return tool(**args_dict)
