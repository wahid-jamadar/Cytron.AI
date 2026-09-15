from fastapi import APIRouter, Request
from pydantic import BaseModel
from modules.common.utils import templates
from agents.requirement_analyzer import requirement_analyzer_node
from state.pipeline_state import initial_state

router = APIRouter(prefix="/requirement-analyzer", tags=["requirement-analyzer"])

class AnalyzeRequest(BaseModel):
    requirements: str

@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse("requirement_analyzer.html", {"request": request})

@router.post("/api/analyze")
async def analyze_requirements(req: AnalyzeRequest):
    state = initial_state(user_input=req.requirements)
    result_state = requirement_analyzer_node(state)
    
    if result_state.get("should_halt"):
        return {"status": "error", "errors": result_state.get("errors", [])}
        
    return {"status": "success", "data": result_state.get("structured_spec")}
