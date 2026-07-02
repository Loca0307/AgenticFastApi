import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

import database_models
from database import SessionLocal

load_dotenv()


class ItemTaskState(TypedDict):
    task: str
    items: list[dict]
    draft_answer: str
    feedback: str
    final_answer: str


def get_llm() -> ChatOpenAI:
    """Create an OpenAI chat model for this graph."""

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set.")

    # ChatOpenAI reads OPENAI_API_KEY from the environment automatically.
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        temperature= 0.7,
    )

def check_item_data(state: ItemTaskState) -> dict:
    llm = get_llm()
    items_text = format_items_for_prompt(state["items"])

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the first agent. Answer the user's task using the item data "
                    "from the SQL database when it is relevant.\n\n"
                    f"Items:\n{items_text}"
                )
            ),
            HumanMessage(content=state["task"]),
        ]
    )
    return {"draft_answer": response.content}


def check_item_data_answer(state: ItemTaskState) -> dict:

    llm = get_llm()
    items_text = format_items_for_prompt(state["items"])

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the second agent. Given the SQL item data and the first "
                    "agent's draft, check whether the answer can be improved for "
                    "correctness, clarity, and simplicity.\n\n"
                    f"Items:\n{items_text}"
                )
            ),
            HumanMessage(
                content=(
                    f"User task:\n{state['task']}\n\n"
                    f"Draft answer:\n{state['draft_answer']}"
                )
            ),
        ]
    )
    return {"feedback": response.content}


def revise_answer(state: ItemTaskState) -> dict:
    llm = get_llm()
    items_text = format_items_for_prompt(state["items"])

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the first agent again. Given the SQL item data, user task, "
                    "original draft, and reviewer feedback, return only the final complete "
                    "answer with no introduction or comments.\n\n"
                    f"Items:\n{items_text}"
                )
            ),
            HumanMessage(
                content=(
                    f"User task:\n{state['task']}\n\n"
                    f"Your original draft answer:\n{state['draft_answer']}\n\n"
                    f"Feedback:\n{state['feedback']}"
                )
            ),
        ]
    )

    return {"final_answer": response.content}

graph_builder = StateGraph(ItemTaskState)

# Nodes
graph_builder.add_node("first agent", check_item_data)
graph_builder.add_node("second agent", check_item_data_answer)
graph_builder.add_node("revise agent", revise_answer)

# Edges
graph_builder.add_edge(START, "first agent")
graph_builder.add_edge("first agent", "second agent")
graph_builder.add_edge("second agent", "revise agent")

graph_builder. add_edge("revise agent", END)

item_feedback_graph = graph_builder.compile()


def format_items_for_prompt(items: list[dict]) -> str:
    """Convert database rows into readable prompt context."""

    if not items:
        return "No items found."

    return "\n".join(
        f"- id={item['id']}, name={item['name']}, description={item['description']}"
        for item in items
    )


def load_items_from_database() -> list[dict]:
    """Load item rows from the SQLAlchemy database session."""

    db = SessionLocal()
    try:
        db_items = db.query(database_models.Item).all()
        return [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description or "",
            }
            for item in db_items
        ]
    finally:
        db.close()


def run_item_agent(task: str) -> ItemTaskState:
    items = load_items_from_database()

    initial_state: ItemTaskState = {
        "task": task,
        "items": items,
        "draft_answer": "",
        "feedback": "",
        "final_answer":""
    }

    return item_feedback_graph.invoke(initial_state)
