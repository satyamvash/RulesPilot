"""Quick diagnostic — run this to verify the Anthropic key works."""
import os
from dotenv import load_dotenv
load_dotenv()

import anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

print(f"Using model : {model}")
print(f"Key preview : {api_key[:15]}..." if api_key else "ERROR: ANTHROPIC_API_KEY not set")

client = anthropic.Anthropic(api_key=api_key)

try:
    response = client.messages.create(
        model=model,
        max_tokens=32,
        messages=[{"role": "user", "content": "Say hello in one word."}],
    )
    print(f"Response    : {response.content[0].text}")
    print(f"Tokens used : input={response.usage.input_tokens} output={response.usage.output_tokens}")
    print("\n✅ Key and model are working fine.")
except Exception as e:
    print(f"\n❌ Error: {e}")
