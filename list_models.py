"""List available Gemini models."""
import sys
import google.generativeai as genai

API_KEY = sys.argv[1] if len(sys.argv) > 1 else None
if not API_KEY:
    print("Usage: python list_models.py <API_KEY>")
    exit(1)

genai.configure(api_key=API_KEY)

print("Available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  - {m.name}")
