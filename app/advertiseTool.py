
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
]
