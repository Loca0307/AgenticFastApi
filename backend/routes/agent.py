from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langgraph_agent import run_basic_agent

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    task: str


@router.post("/run")
def run_agent(request: AgentRequest):
    """Run the sample LangGraph workflow from an API request."""

    try:
        return run_basic_agent(request.task)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
