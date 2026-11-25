import argparse
import os

from openai import OpenAI

from .advertiseTool import TOOLLIST
from .helpers.skill_helper import split_skills_from_arguments
from .lsp_client import initialize_lsp
from .skills import Skill
from .tools import process_tool_call

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def run_agent_loop(client, conversation):
    lsp_client = initialize_lsp()
    while True:
        if lsp_client is not None:
            diagnostic_feedback = lsp_client.collect_diagnostic_feedback()
            if diagnostic_feedback:
                for message in reversed(conversation):
                    if message["role"] in ("tool", "user"):
                        content = message.get("content") or ""
                        message["content"] = (
                            f"{content}\n\n{diagnostic_feedback}"
                            if content
                            else diagnostic_feedback
                        )
                        break

        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=conversation,
            tools=TOOLLIST,
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        response = chat.choices[0].message
        message_dict = {
            "role": response.role,
            "content": response.content,
        }

        if hasattr(response, "tool_calls") and response.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.tool_calls
            ]
        conversation.append(message_dict)
        if not message_dict.get("tool_calls"):
            return response.content
        pending_feedback = ""
        wrote_file = False
        for tc in response.tool_calls:
            if lsp_client is not None and not pending_feedback:
                pending_feedback = lsp_client.collect_diagnostic_feedback()
            if pending_feedback:
                tc_response = (
                    "Tool call not executed because new diagnostics require review. "
                    "Review the diagnostics and retry if needed."
                )
            elif (
                lsp_client is not None
                and wrote_file
                and tc.function.name == "write_file"
            ):
                tc_response = (
                    "Write not executed: only one file write is performed per turn "
                    "while LSP analysis is enabled. Retry this write on the next turn."
                )
            else:
                tc_response = process_tool_call(
                    tc,
                    fork_runner=lambda messages: run_agent_loop(client, messages),
                )
                if tc.function.name == "write_file":
                    wrote_file = True
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tc_response,
                }
            )

        if pending_feedback:
            conversation[-1]["content"] += f"\n\n{pending_feedback}"


def main():
    initialize_lsp()
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    # load all skill anmes and descriptions into the conversation
    systemPrompt = ""
    try:
        if os.path.exists("./.claude/skills"):
            skillsList = [Skill(name) for name in os.listdir("./.claude/skills")]
            systemPrompt = "\n".join([skill.systemPrompt for skill in skillsList])

    except OSError:
        print("Skills cannot be loaded")

    conversation = [
        {
            "role": "system",
            "content": (
                f"you have access to the following skills: {systemPrompt}\n\n"
                "If a skill matches the user's request, call the Skill tool with "
                "its name and follow the instructions it returns. Follow the user's "
                "requested output format exactly, without extra punctuation or text."
            ),
        },
    ]

    if args.p.startswith("/"):
        skills, params = split_skills_from_arguments(args.p)

        # convert skill names to Skill objects with parameters for called skills
        skills = [Skill(skill, args=params) for skill in skills]

        for skill in skills:
            conversation.append({"role": "user", "content": skill.prompt})
    else:
        conversation.append({"role": "user", "content": args.p})

    print(run_agent_loop(client, conversation))


if __name__ == "__main__":
    main()
