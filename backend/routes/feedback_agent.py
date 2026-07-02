from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db


from llm_feedback_graph import run_feedback_agent

router = APIRouter(prefix="/agent-review", tags=["agent-review"])


class FeedbackAgentRequest(BaseModel):
    task: str


@router.post("/run")
def run_feedback_review_agent(request: FeedbackAgentRequest, db: Session = Depends(get_db)):
    """Run a two-pass LLM graph: draft, feedback, revision."""

    try:
        return run_feedback_agent(request.task)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
