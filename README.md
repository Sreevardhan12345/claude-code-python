[![progress-banner](https://backend.codecrafters.io/progress/claude-code/94ba29d1-a092-410b-8c4f-90d7653d064a)](https://app.codecrafters.io/users/Sreevardhan12345?r=2qF)

This is a starting point for Python solutions to the
["Build Your own Claude Code" Challenge](https://codecrafters.io/challenges/claude-code).

Claude Code is an AI coding assistant that uses Large Language Models (LLMs) to
understand code and perform actions through tool calls. In this challenge,
you'll build your own Claude Code from scratch by implementing an LLM-powered
coding assistant.

Along the way you'll learn about HTTP RESTful APIs, OpenAI-compatible tool
calling, agent loop, and how to integrate multiple tools into an AI assistant.

**Note**: If you're viewing this repo on GitHub, head over to
[codecrafters.io](https://codecrafters.io) to try the challenge.

# Run locally

## Requirements

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/)
- An [OpenRouter API key](https://openrouter.ai/keys)

Install the project dependencies:

```sh
uv sync
```

Set the API key in your shell. For macOS/Linux:

```sh
export OPENROUTER_API_KEY="your-api-key"
```

For PowerShell:

```powershell
$env:OPENROUTER_API_KEY = "your-api-key"
```

## Start the agent

Pass a prompt with the required `-p` option:

```sh
uv run --project . -m app.main -p "Explain the files in this project"
```

Alternatively, use the repository's local runner:

```sh
./your_program.sh -p "Explain the files in this project"
```

The agent sends requests to OpenRouter's OpenAI-compatible API using the
`anthropic/claude-haiku-4.5` model.

## Configuration

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | Yes | — | API key used to authenticate requests to the model provider. |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | OpenAI-compatible API base URL. |
| `CODECRAFTERS_LSP_URL` | No | — | Base URL for the optional Language Server Protocol service. |

If `CODECRAFTERS_LSP_URL` is not set, LSP operations are skipped; file, shell,
and skill tools remain available.

## Available tools

The model can call these tools during a conversation:

| Tool | Purpose |
| --- | --- |
| `read_file` | Read a file using its path. |
| `write_file` | Write content to a file. When LSP is enabled, notify it about the updated document. |
| `Bash` | Run a shell command and return its output. |
| `Skill` | Load a skill's instructions by name. |
| `LSP` | Go to a symbol's definition or find its references, when an LSP service is configured. |

For LSP calls, `filePath` can be absolute or relative to the agent's working
directory. `line` and `character` are 1-based positions.

## Skills

Project skills are read from `.claude/skills/<skill-name>/SKILL.md`. A skill
file uses YAML front matter containing `name` and `description`, followed by
the skill instructions.

If skills are present, their names and descriptions are included in the initial
conversation context. You can also start the prompt with a skill name and
arguments, for example:

```sh
uv run --project . -m app.main -p "/skill-name optional arguments"
```

Replace `skill-name` with a skill directory that exists in `.claude/skills`.

## Project layout

- `app/main.py` — command-line entry point and model/tool-call loop.
- `app/advertiseTool.py` — tool definitions advertised to the model.
- `app/tools.py` — file, shell, skill, and LSP tool handlers.
- `app/lsp_client.py` — HTTP transport and document state for LSP requests.
- `app/skills.py` — skill loading and prompt preparation.
- `your_program.sh` — local runner used by the CodeCrafters environment.

Run the linter with:

```sh
uv run ruff check app
```

## CodeCrafters

Submit your implementation and stream the test output with:

```sh
codecrafters submit
```
