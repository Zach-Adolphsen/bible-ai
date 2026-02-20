from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from backend.ai.graph import graph

SYSTEM_PROMPT = SystemMessage(content="""
You are a structured Bible study assistant.
Use tools when necessary.
Always cite verses.
Prefer verse_lookup for direct references.
Prefer semantic_search for thematic questions.
""")

load_dotenv()

app = graph.compile()

def send_prompt(prompt: str):
    try:
        result = app.invoke({
            "messages": [SYSTEM_PROMPT, HumanMessage(content=prompt)]
        })

        return result["messages"][-1].content

    except Exception as e:
        raise e
