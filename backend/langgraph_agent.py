import os
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

load_dotenv()

TaskType = Literal["quick_answer", "planning"]


class TaskState(TypedDict):
    """The shared state object that LangGraph passes between every node."""

    task: str
    task_type: TaskType
    prompt_instruction: str
    answer: str


def classify_task(state: TaskState) -> dict:
    """Decide which path the graph should take for the current task."""

    task = state["task"].lower()
    planning_words = ["plan", "steps", "build", "create", "implement", "project"]

    if any(word in task for word in planning_words):
        task_type = "planning"
    else:
        task_type = "quick_answer"

    # LangGraph nodes return only the state fields they want to update.
    return {"task_type": task_type}

def quick_answer_task(state: TaskState) -> dict:
    """Add prompt guidance for quick_answer tasks."""

    # This node does not answer the user; it prepares instructions for the LLM node.
    return {"prompt_instruction": "Answer quickly and directly."}

def planning_task(state: TaskState) -> dict:
    """Add prompt guidance for planning tasks."""

    # This node does not answer the user; it prepares instructions for the LLM node.
    return {"prompt_instruction": "Plan and explain the steps to solve this task."}


def call_ai_agent(state: TaskState) -> dict:
    """Call the OpenAI chat model to produce the agent's final answer."""

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set.")

    # ChatOpenAI reads OPENAI_API_KEY from the environment automatically.
    # OPENAI_MODEL is optional, so you can switch models without editing code.
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        temperature=0.7,
    )

    system_prompt = (
        "You are a helpful AI agent inside a FastAPI and LangGraph learning project. "
        "Follow the user's request directly. If they ask for a specific format or count, "
        "obey it exactly."
    )

    if state["prompt_instruction"]:
        system_prompt += f" {state['prompt_instruction']}"

    # LangChain message objects are passed to the OpenAI chat model.
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["task"]),
        ]
    )

    # LangGraph merges this returned dict into the shared state.
    return {"answer": response.content}


def choose_next_node(state: TaskState) -> Literal["quick_answer_task", "planning_task"]:
    """Route execution based on the state created by classify_task()."""

    # Conditional edges use this return value to choose the next graph node.
    if state["task_type"] == "planning":
        return "planning_task"
    return "quick_answer_task"


# StateGraph defines the shape of the agent workflow and the state it carries.
graph_builder = StateGraph(TaskState)

# Each node is a normal Python function that receives state and returns updates.
graph_builder.add_node("classify_task", classify_task)
graph_builder.add_node("quick_answer_task", quick_answer_task)
graph_builder.add_node("planning_task", planning_task)
graph_builder.add_node("call_ai_agent", call_ai_agent)

# START is LangGraph's virtual entry point; it sends execution into the first node.
graph_builder.add_edge(START, "classify_task")

# Conditional edges let the graph choose a path at runtime from current state.
graph_builder.add_conditional_edges(
    "classify_task",
    choose_next_node,
    {
        "quick_answer_task": "quick_answer_task",
        "planning_task": "planning_task",
    },
)

# Both task-specific nodes feed into the same AI model node.
graph_builder.add_edge("quick_answer_task", "call_ai_agent")
graph_builder.add_edge("planning_task", "call_ai_agent")

# END is LangGraph's virtual finish point; reaching it stops the workflow.
graph_builder.add_edge("call_ai_agent", END)

# compile() turns the graph definition into a runnable object with invoke().
agent_graph = graph_builder.compile()


def run_basic_agent(task: str) -> TaskState:
    """Run the compiled LangGraph agent for one task."""

    initial_state: TaskState = {
        "task": task,
        "task_type": "quick_answer",
        "prompt_instruction": "",
        "answer": "",
    }

    # invoke() executes the graph from START until it reaches END.
    return agent_graph.invoke(initial_state)
