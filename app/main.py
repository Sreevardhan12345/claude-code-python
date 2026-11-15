import argparse
import os

from openai import OpenAI

from .advertiseTool import TOOLLIST
from .helpers.skill_helper import get_skill_details
from .tools import process_tool_call

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    conversation = [{"role": "user", "content": args.p}]

    if args.p.startswith("/"):
        skill_path = ".claude/skills" + args.p + "/SKILL.md"
        _, skill_context = get_skill_details(skill_path)

        conversation = [
            {
                "role": "system",
                "content": f"you have access to the following skill: {skill_context['name']}. The description of the skill is: {skill_context['description']}",
            },
            {
                "role": "user",
                "content": args.p,
            },
        ]

    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=conversation,
            tools=TOOLLIST,
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        response = chat.choices[0].message
        response_message = chat.choices[0].message
        message_dict = {
            "role": response_message.role,
            "content": response_message.content,
        }

        if hasattr(response_message, "tool_calls") and response_message.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response_message.tool_calls
            ]
        conversation.append(message_dict)
        if not message_dict.get("tool_calls"):
            print(response.content)
            break
        for tc in response.tool_calls:
            tc_reponse = process_tool_call(tc)
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tc_reponse,
                }
            )


if __name__ == "__main__":
    main()
