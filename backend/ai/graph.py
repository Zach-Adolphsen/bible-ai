from typing import Sequence, Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from backend.ai.agent_tools import agent_tools

# One LLM call per request, then (optionally) tools, then END.
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.1, max_tokens=1000)
model_with_tools = model.bind_tools(agent_tools)
tool_node = ToolNode(agent_tools)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def agent_node(state: AgentState):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []

    if tool_calls:
        return "tools"

    return END


graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")

graph.add_conditional_edges("agent",
                            should_continue,
                            {
                                "tools": "tools",
                                END: END
                            },
                            )

graph.add_edge("tools", "agent")
