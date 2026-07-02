from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm_feedback_graph import run_feedback_agent

router = APIRouter(prefix="/agent-review", tags=["agent-review"])


class FeedbackAgentRequest(BaseModel):
    task: str


@router.post("/run")
def run_feedback_review_agent(request: FeedbackAgentRequest):
    """Run a two-pass LLM graph: draft, feedback, revision."""

    try:
        return run_feedback_agent(request.task)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
