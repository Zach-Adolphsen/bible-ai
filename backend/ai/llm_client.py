from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, max_tokens=1000)

def send_prompt(prompt: str):
    """Send a prompt to Gemini and return the response."""
    try:
        response = model.invoke(prompt)
        return response.text
    except Exception as e:
        raise e
