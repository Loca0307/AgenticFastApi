from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langgraph_agent import run_basic_agent
from item_agent import run_item_agent as run_item_feedback_agent

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
    

@router.post("/item-run")
def run_item_agent_with_items(request: AgentRequest):
    try:
        return run_item_feedback_agent(request.task)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    
