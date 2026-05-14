import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyB6qQbHQ5IvN0sjfhULX9_9v1JbqT3w6X0"
genai.configure(api_key=GEMINI_API_KEY)

print("Listing models...")
try:
    models = genai.list_models()
    for m in models:
        print(f"Model: {m.name}, Supported Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error: {e}")
