
import json
from .registry import Registry

TOOLS = Registry("tools")


@TOOLS.register("read_file")
def read_file(path: str) -> str:
    """Read a file from the local filesystem."""
    with open(path, "r") as f:
        return f.read()
    
    
@TOOLS.register("write_file")
def write_file(path: str, content: str) -> None:
    """Write content to a file on the local filesystem."""
    try:
        with open(path, "w") as f:
                f.write(content)
    except Exception as e:
        raise ValueError(f"Error writing to file {path}: {e}")
    
    return f"Successfully wrote to file {path}"


def process_tool_call(tool_call):
    """Process a tool call and return the result."""
    if tool_call.function.name not in TOOLS:
        raise ValueError(f"Tool {tool_call.function.name} is not registered.")
    args_dict = json.loads(tool_call.function.arguments)
    return TOOLS.get(tool_call.function.name)(**args_dict)