from .registry import Registry

TOOLS = Registry("tools")

@TOOLS.register("read_file")
def read_file(path: str) -> str:
    """Read a file from the local filesystem."""
    with open(path, "r") as f:
        return f.read()