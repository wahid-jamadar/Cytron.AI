from fastapi import APIRouter, Request
from pydantic import BaseModel
from modules.common.utils import templates
from agents.sql_query_agent import SQLQueryAgent

router = APIRouter(prefix="/sql-query-generator", tags=["sql-query-generator"])
sql_agent = SQLQueryAgent()

class QueryRequest(BaseModel):
    requirements: str

@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse("sql_query_generator.html", {"request": request})

@router.post("/api/generate")
async def generate_query(req: QueryRequest):
    result = await sql_agent.generate_query(req.requirements)
    return result
