import argparse
import os
import sys, json

from openai import OpenAI
from .advertiseTool import TOOLLIST
from .tools import TOOLS

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    chat = client.chat.completions.create(
        model="anthropic/claude-haiku-4.5",
        messages=[{"role": "user", "content": args.p}],
        tools=TOOLLIST
    )

    if not chat.choices or len(chat.choices) == 0:
        raise RuntimeError("no choices in response")


    response = chat.choices[0].message.tool_calls
    if response:
        for tool_call in response:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            if tool_name not in TOOLS:
                raise RuntimeError(f"tool {tool_name} not found")

            tool_func = TOOLS.get(tool_name)
            result = tool_func(**json.loads(tool_args))
            print(result)
    else:        
        print(chat.choices[0].message.content)


if __name__ == "__main__":
    main()
