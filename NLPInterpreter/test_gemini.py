"""Quick diagnostic — run this directly to verify the Gemini key and model work."""
import os
from dotenv import load_dotenv
load_dotenv()

from google import genai

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

print(f"Using model : {model_name}")
print(f"Key preview : {api_key[:12]}..." if api_key else "ERROR: GEMINI_API_KEY not set")

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model=model_name,
        contents="Say hello in one word.",
    )
    print(f"Response    : {response.text}")
    print("\n✅ Key and model are working fine.")
except Exception as e:
    print(f"\n❌ Error: {e}")
