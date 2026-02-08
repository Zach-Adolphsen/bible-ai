# calls the prompt builder in bible_qa.py
# call send_prompt in llm_client.py
# return response.text
from backend.ai.llm_client import send_prompt
from backend.ai.prompts.bible_qa import create_prompt


def create_response(question: str, verses: list[str]):
    # creates prompt
    llm_prompt = create_prompt(question, verses)

    # sends prompt to LLM, gets response
    llm_response = send_prompt(llm_prompt)

    return llm_response