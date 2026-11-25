import json
import os

from .lsp_client import initialize_lsp
from .registry import Registry

TOOLS = Registry("tools")


@TOOLS.register("read_file")
def read_file(path: str) -> str:
    """Read a file or list the contents of a directory."""
    if os.path.isdir(path):
        with os.scandir(path) as entries:
            listing = sorted(
                (
                    f"{entry.name}/" if entry.is_dir() else entry.name
                    for entry in entries
                ),
                key=str.casefold,
            )
        return "\n".join(listing) if listing else "(empty directory)"

    with open(path, "r") as f:
        return f.read()


@TOOLS.register("write_file")
def write_file(path: str, content: str) -> str:
    """Write content to a file on the local filesystem."""
    with open(path, "w") as f:
        f.write(content)

    lsp("notifyChange", path, 1, 1)
    return f"Successfully wrote to file {path}"


@TOOLS.register("Bash")
def run_bash_command(command: str) -> str:
    """Run a bash command and return the output."""
    import subprocess

    result = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        env={
            key: value for key, value in os.environ.items() if key != "PYTHONSAFEPATH"
        },
    )
    stdout = result.stdout.decode("utf-8")
    stderr = result.stderr.decode("utf-8")
    if result.returncode != 0:
        return (
            f"Command exited with status {result.returncode}.\n"
            f"stdout:\n{stdout or '(empty)'}\n"
            f"stderr:\n{stderr or '(empty)'}"
        )
    return stdout + stderr


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

    client = initialize_lsp()
    if client is None:
        return "LSP server is not configured; skipped the operation."
    return client.process_lsp_call(operation, filePath, line, character)


def process_tool_call(tool_call, fork_runner=None):
    """Process a tool call and return the result."""
    if tool_call.function.name not in TOOLS:
        raise ValueError(f"Tool {tool_call.function.name} is not registered.")
    args_dict = json.loads(tool_call.function.arguments)
    tool = TOOLS.get(tool_call.function.name)
    if tool_call.function.name == "Skill":
        return tool(**args_dict, fork_runner=fork_runner)
    return tool(**args_dict)
