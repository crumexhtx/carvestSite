import os

from openai import OpenAI

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Set the OPENAI_API_KEY environment variable before running this script.")

client = OpenAI(api_key=api_key)

response = client.responses.create(
    model="gpt-4o-mini",
    input="write a haiku about ai",
    store=True,
)

print(response.output_text)
