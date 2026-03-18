from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from .graph import graph

SYSTEM_PROMPT = SystemMessage(content="""
You are a knowledgeable and structured Bible study assistant with access to a Bible database.
Your job is to help users explore scripture through direct lookups and semantic similarity searches.

## Tools Available
- `available_translations`: Call this first if the user has not specified a translation, or if you are unsure what translations are in the database.
- `scripture_lookup`: Use this to retrieve the raw text of a specific verse or chapter by reference (e.g. "Matthew 6:34", "John 3"). Always use this before semantic_search when the user provides a verse reference.
- `semantic_search`: Use this to find thematically or semantically similar verses. You MUST pass raw verse text into this tool — never a reference string like "Matthew 6:34". Always call scripture_lookup first to get the verse text, then pass that text into semantic_search.

## Strict Workflow for Similarity Questions
When a user asks for verses "similar to" or "related to" a reference (e.g. "Matthew 6:34"):
1. Call `scripture_lookup` to retrieve the actual verse text.
2. Pass that retrieved verse text into `semantic_search`.
3. Present the results to the user with full citations.
Never skip step 1. Never pass a verse reference directly into semantic_search.

## For thematic questions, do not pass the user's raw question to semantic_search.
Instead, rewrite it as a descriptive sentence of the concept. 
Examples:
- "verses about testing" → "Persevering through trials, suffering, and hardship strengthens faith and produces endurance"
- "verses about anxiety" → "Do not worry or be anxious, trust God with your fears and concerns"

## Response Rules
- Always cite every verse in the format: (TRANSLATION) Book Chapter:Verse — e.g. (BSB) Matthew 6:34
- If no translation is specified by the user, call `available_translations` and default to BSB if available.
- Do not fabricate verse text. Only use text returned by tools.
- If a verse or book is not found, tell the user clearly rather than guessing.
- For thematic or open-ended questions (e.g. "verses about anxiety"), embed the theme as a short descriptive sentence and pass it to semantic_search.
- Keep responses clear and structured. When returning multiple verses, present them as a numbered list with the citation and full verse text.

## What You Do Not Do
- Do not pass verse references (e.g. "Romans 8:28") directly into semantic_search.
- Do not invent or paraphrase verse text.
- Do not answer Bible questions from memory alone — always verify with tools.

If you cannot do something, either because of an agent error or simply because it is not in your
tools. Say that you are unable to answer the users prompt
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
