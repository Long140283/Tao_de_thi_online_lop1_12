import google.generativeai as genai
import PIL.Image as Image
import os

GEMINI_API_KEY = "AIzaSyB6qQbHQ5IvN0sjfhULX9_9v1JbqT3w6X0"

def get_best_model(api_key, vision_required=False):
    try:
        genai.configure(api_key=api_key)
        available = []
        try:
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    available.append(m.name)
        except:
            available = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"]

        if vision_required:
            preferred = ["models/gemini-3.1-flash", "models/gemini-3-flash-preview", "models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash", "models/gemini-flash-latest", "models/gemini-1.5-pro"]
        else:
            preferred = ["models/gemini-3.1-flash", "models/gemini-3-pro", "models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash", "models/gemini-flash-latest", "models/gemini-pro"]
        
        for p in preferred:
            if p in available: return p
            p_short = p.replace("models/", "")
            if p_short in available: return p_short
        return available[0] if available else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

print(f"Best model (text): {get_best_model(GEMINI_API_KEY, False)}")
print(f"Best model (vision): {get_best_model(GEMINI_API_KEY, True)}")
