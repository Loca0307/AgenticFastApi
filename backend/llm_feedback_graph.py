import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

load_dotenv()


class FeedbackState(TypedDict):
    """State shared by the draft, feedback, and revision nodes."""

    task: str
    draft_answer: str
    feedback: str
    final_answer: str


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """Create an OpenAI chat model for this graph."""

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set.")

    # ChatOpenAI reads OPENAI_API_KEY from the environment automatically.
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        temperature=temperature,
    )


def draft_answer(state: FeedbackState) -> dict:
    """First LLM call: create an initial answer for the user's task."""

    writer_llm = get_llm(temperature=0.7)

    response = writer_llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the first AI agent. Write a useful first draft answer. "
                    "Do not mention that another model will review it and don't make a introduction, just answer the question directly."
                )
            ),
            HumanMessage(content=state["task"]),
        ]
    )

    # LangGraph merges this field into the shared graph state.
    return {"draft_answer": response.content}


def review_answer(state: FeedbackState) -> dict:
    """Second LLM call: review the first LLM's draft and give feedback."""

    reviewer_llm = get_llm(temperature=0.2)

    response = reviewer_llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the second AI agent. Review the draft answer. "
                    "Give concise, actionable feedback. Focus on correctness, clarity, "
                    "missing details, and whether it followed the user's request. Just write the" \
                    " feedback, do not rewrite the answer or give a summary or introduction." \
                    "Check also that the first model doesn't add a introduction to the answer, it should answer the question directly."
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

    # This feedback is passed back to the first agent in the next node.
    return {"feedback": response.content}


def revise_answer(state: FeedbackState) -> dict:
    """First LLM call again: revise the draft using the feedback."""

    writer_llm = get_llm(temperature=0.7)

    response = writer_llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the first AI agent again. Improve your original answer "
                    "using the reviewer feedback. Return only the final improved answer."
                )
            ),
            HumanMessage(
                content=(
                    f"User task:\n{state['task']}\n\n"
                    f"Your original draft:\n{state['draft_answer']}\n\n"
                    f"Reviewer feedback:\n{state['feedback']}"
                )
            ),
        ]
    )

    return {"final_answer": response.content}


# StateGraph declares the data shape passed from node to node.
graph_builder = StateGraph(FeedbackState)

# Each node is one step in the multi-LLM feedback workflow.
graph_builder.add_node("draft_answer", draft_answer)
graph_builder.add_node("review_answer", review_answer)
graph_builder.add_node("revise_answer", revise_answer)

# START is LangGraph's virtual entry point.
graph_builder.add_edge(START, "draft_answer")

# These fixed edges force the draft -> feedback -> revision order.
graph_builder.add_edge("draft_answer", "review_answer")
graph_builder.add_edge("review_answer", "revise_answer")

# END stops graph execution after the revised answer is ready.
graph_builder.add_edge("revise_answer", END)

# compile() turns the graph definition into a runnable object.
feedback_graph = graph_builder.compile()


def run_feedback_agent(task: str) -> FeedbackState:
    """Run the draft, feedback, and revision graph for one task."""

    initial_state: FeedbackState = {
        "task": task,
        "draft_answer": "",
        "feedback": "",
        "final_answer": "",
    }

    # invoke() executes all graph nodes from START to END.
    return feedback_graph.invoke(initial_state)
