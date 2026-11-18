import argparse
import os

from openai import OpenAI

from .advertiseTool import TOOLLIST
from .helpers.skill_helper import split_skills_from_arguments
from .skills import Skill
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

    if args.p.startswith("/"):
        skills, params = split_skills_from_arguments(args.p)

        skills = [Skill(skill, args=params) for skill in skills]

        conversation = [
            {
                "role": "system",
                "content": f"you have access to the following skills: {'\n'.join([skill.systemPrompt for skill in skills])}",
            },
        ]

        for skill in skills:
            conversation.append({"role": "user", "content": skill.prompt})
    else:
        conversation = [{"role": "user", "content": args.p}]

    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=conversation,
            tools=TOOLLIST,
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        response = chat.choices[
            0
        ].message  # only considering the first response for now
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
            print(response.content)
            break
        for tc in response.tool_calls:
            tc_response = process_tool_call(tc)
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tc_response,
                }
            )


if __name__ == "__main__":
    main()
