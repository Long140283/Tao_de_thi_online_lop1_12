import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyC2OQP9mUG9TywR-aiR-C6cnwqC_IPzvcw"
genai.configure(api_key=GEMINI_API_KEY)

print("Listing models...")
try:
    for m in genai.list_models():
        print(f"Model: {m.name}, Supported Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error: {e}")
