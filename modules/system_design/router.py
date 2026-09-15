from fastapi import APIRouter, Request
from pydantic import BaseModel
from modules.common.utils import templates
from agents.system_design_agent import SystemDesignAgent

router = APIRouter(prefix="/system-design", tags=["system-design"])
sys_design_agent = SystemDesignAgent()

class DesignRequest(BaseModel):
    requirements: str

@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse("system_design.html", {"request": request})

@router.post("/api/generate")
async def generate_design(req: DesignRequest):
    result = await sys_design_agent.generate_design(req.requirements)
    return result
