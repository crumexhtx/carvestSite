"""Manual OpenAI connectivity smoke test. Do not import from application code."""

import os
import sys

from openai import OpenAI


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set the OPENAI_API_KEY environment variable before running this script.")
        return 1

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4o-mini",
        input="write a haiku about ai",
        store=False,
    )
    print(response.output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
