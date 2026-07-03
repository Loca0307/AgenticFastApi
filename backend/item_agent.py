from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
# import os
# from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

import dynamodb_items
from llm_config import get_chat_model

load_dotenv()

ItemTaskType = Literal["get_items", "add_data", "update_data", "delete_data"]


class ItemTaskState(TypedDict):
    task: str
    task_type: ItemTaskType
    items: list[dict]
    draft_answer: str
    feedback: str
    final_answer: str


class ItemCreateRequest(BaseModel):
    """Structured data the LLM must extract before writing to DynamoDB."""

    name: str = Field(description="The item name to save in the database.")
    description: str = Field(default="", description="A short item description.")


class ItemDeleteRequest(BaseModel):
    """Structured data the LLM must extract before deleting from DynamoDB."""

    name: str = Field(description="The item name to delete from the database.")


def get_llm():
    """Create a chat model for this graph."""

    # Previous ChatGPT/OpenAI setup:
    #
    # if not os.getenv("OPENAI_API_KEY"):
    #     raise ValueError("OPENAI_API_KEY is not set.")
    #
    # return ChatOpenAI(
    #     model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
    #     temperature=0.7,
    # )

    return get_chat_model(temperature=0.7)


def classify_item_task(state: ItemTaskState) -> dict:
    """Decide whether the user wants to read items or add a new item."""

    task = state["task"].lower()
    add_words = ["add", "create", "insert", "save", "new item"]
    update_words = ["update", "modify", "change", "edit", "replace"]
    delete_words = ["delete", "remove", "erase", "discard", "drop"]

    if any(word in task for word in add_words):
        return {"task_type": "add_data"}
    
    if any(word in task for word in update_words):
        return {"task_type": "update_data"}
    
    if any(word in task for word in delete_words):
        return {"task_type": "delete_data"}
    

    return {"task_type": "get_items"}


def choose_item_path(state: ItemTaskState) -> Literal["add item", "update item", "delete item", "first agent"]:
    """Route to the add-data node or the item-answer feedback chain."""


    if state["task_type"] == "add_data":
        return "add item"

    if state["task_type"] == "update_data":
        return "update item"

    if state["task_type"] == "delete_data":
        return "delete item"
    
    return "first agent"


def check_item_data(state: ItemTaskState) -> dict:
    llm = get_llm()
    items_text = format_items_for_prompt(state["items"])

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the first agent. Answer the user's task using the item data "
                    "from the database when it is relevant.\n\n"
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
                    "You are the second agent. Given the database item data and the first "
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
                    "You are the first agent again. Given the database item data, user task, "
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


def add_data(state: ItemTaskState) -> dict:
    """Extract item data from the task and insert it into DynamoDB."""

    llm = get_llm()

    # with_structured_output makes the LLM return data matching ItemCreateRequest.
    structured_llm = llm.with_structured_output(ItemCreateRequest)

    item_data = structured_llm.invoke(
        [
            SystemMessage(
                content=(
                    "Extract exactly one item to add to the database from the user's task. "
                    "Return only the structured item fields. If no description is given, "
                    "come up with a short description based on the item name."
                )
            ),
            HumanMessage(content=state["task"]),
        ]
    )

    created_item = create_item_in_database(
        name=item_data.name,
        description=item_data.description,
    )
    updated_items = load_items_from_database()

    return {
        "items": updated_items,
        "draft_answer": (
            f"Added item name={created_item['name']}, "
            f"description={created_item['description']}"
        ),
        "final_answer": f"Added {created_item['name']} to the database.",
    }



def update_data(state: ItemTaskState) -> dict:
    """Update data from the db."""

    llm = get_llm()
    
    # llm returns data precisly matching ItemCreateRequest.
    structured_llm = llm.with_structured_output(ItemCreateRequest)

    item_data = structured_llm.invoke(
        [
            SystemMessage(
                content=(
                    "From the user task, extract a set of name and description and update the database with" \
                    "the new data, either matching the id or name of the item. Return only the structured item fields."
                )
            ),
            HumanMessage(content=state["task"]),
        ]
    )

    updated_item = update_item_in_database(
        name=item_data.name,
        description=item_data.description,
    )
    updated_items = load_items_from_database()

    return {
        "items": updated_items,
        "draft_answer": (
            f"Updated item name={updated_item['name']}, "
            f"description={updated_item['description']}"
        ),
        "final_answer": f"Updated {updated_item['name']} in the database.",
    }


def delete_data(state: ItemTaskState) -> dict:
    """delete data from the db."""

    llm = get_llm()
    
    # llm returns data precisely matching ItemDeleteRequest.
    structured_llm = llm.with_structured_output(ItemDeleteRequest)

    item_data = structured_llm.invoke(
        [
            SystemMessage(
                content=(
                    "From the user task, extract the name of the item to delete from the database. "
                    "Return only the structured item field."
                )
            ),
            HumanMessage(content=state["task"]),
        ]
    )

    deleted_item = delete_item_in_database(
        name=item_data.name,
    )
    updated_items = load_items_from_database()

    return {
        "items": updated_items,
        "draft_answer": (
            f"Deleted item name={deleted_item['name']}, "
            f"description={deleted_item['description']}"
        ),
        "final_answer": f"Deleted {deleted_item['name']} from the database.",
    }
graph_builder = StateGraph(ItemTaskState)

# Nodes
graph_builder.add_node("classify item task", classify_item_task)
graph_builder.add_node("first agent", check_item_data)
graph_builder.add_node("second agent", check_item_data_answer)
graph_builder.add_node("revise agent", revise_answer)
graph_builder.add_node("add item", add_data)
graph_builder.add_node("update item", update_data)
graph_builder.add_node("delete item", delete_data)

# Edges
graph_builder.add_edge(START, "classify item task")
graph_builder.add_conditional_edges(
    "classify item task",
    choose_item_path,
    {
        "add item": "add item",
        "first agent": "first agent",
        "update item": "update item",
        "delete item": "delete item",
    },
)
graph_builder.add_edge("first agent", "second agent")
graph_builder.add_edge("second agent", "revise agent")

graph_builder.add_edge("add item", END)
graph_builder.add_edge("revise agent", END)
graph_builder.add_edge("update item", END)
graph_builder.add_edge("delete item", END)

item_feedback_graph = graph_builder.compile()


def format_items_for_prompt(items: list[dict]) -> str:
    """Convert database rows into readable prompt context."""

    if not items:
        return "No items found."

    return "\n".join(
        f"- name={item['name']}, description={item['description']}"
        for item in items
    )


def load_items_from_database() -> list[dict]:
    """Load item rows from the active DynamoDB table."""

    return dynamodb_items.list_items()


def create_item_in_database(name: str, description: str = "") -> dict:
    """Insert one item into the active DynamoDB table."""

    return dynamodb_items.create_item(name=name, description=description)


def update_item_in_database(name: str, description: str = "") -> dict:
    """Update one item in the active DynamoDB table."""

    return dynamodb_items.update_item(name=name, description=description)


def delete_item_in_database(name: str) -> dict:
    """Delete one item from the active DynamoDB table."""

    return dynamodb_items.delete_item(name=name)


def run_item_agent(task: str) -> ItemTaskState:
    items = load_items_from_database()

    initial_state: ItemTaskState = {
        "task": task,
        "task_type": "get_items",
        "items": items,
        "draft_answer": "",
        "feedback": "",
        "final_answer":""
    }

    return item_feedback_graph.invoke(initial_state)
