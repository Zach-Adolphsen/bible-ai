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


def _content_to_text(content) -> str:
    """
    LangChain message content can be:
      - str
      - list of parts (e.g., [{'type': 'text', 'text': '...'}, ...])
      - other structured payloads

    Normalize to a plain string for the API response model.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, str):
                chunks.append(part)
                continue
            if isinstance(part, dict):
                # Common multimodal/text part shape
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                    continue
                # Fallback: include a compact representation if no text field exists
                chunks.append(str(part))
                continue
            chunks.append(str(part))
        return "\n".join([c for c in chunks if c is not None])

    try:
        import json
        return json.dumps(content, ensure_ascii=False)
    except Exception:
        return str(content)


def send_prompt(prompt: str) -> str:
    result = app.invoke({
        "messages": [SYSTEM_PROMPT, HumanMessage(content=prompt)]
    })

    last_message = result["messages"][-1]
    content = getattr(last_message, "content", last_message)
    return _content_to_text(content)
