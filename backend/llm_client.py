import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_AI_API_KEY")
client = genai.Client(api_key=api_key)

def send_prompt(prompt: str):
    """Send a prompt to Gemini and return the response."""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

result = send_prompt("Hello")
print(result)