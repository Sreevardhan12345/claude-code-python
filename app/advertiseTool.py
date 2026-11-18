TOOLLIST = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the local filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to read",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file on the local filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Bash",
            "description": "Run a bash command and return the output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to run",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Skill",
            "description": "Load a skill's instructions into the conversation",
            "parameters": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the skill to use",
                    },
                    "args": {
                        "type": "string",
                        "description": "Optional arguments for the skill",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "LSP",
            "description": "Returns the file, line, and character where a symbol is defined.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["goToDefinition"]},
                    "filePath": {
                        "type": "string",
                        "description": "Absolute path, or a path relative to the agent's current working directory.",
                    },
                    "line": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "1-based line number of the symbol.",
                    },
                    "character": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "1-based character offset in UTF-16 code units (same as character count for ASCII).",
                    },
                },
                "required": ["operation", "filePath", "line", "character"],
            },
        },
    },
]
