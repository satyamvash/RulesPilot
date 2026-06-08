"""List all models available on this Anthropic API key."""
import os
from dotenv import load_dotenv
load_dotenv()

import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

models = client.models.list()
for m in models.data:
    print(m.id)
