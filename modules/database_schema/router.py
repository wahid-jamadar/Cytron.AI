from fastapi import APIRouter, Request
from modules.common.utils import templates

router = APIRouter(prefix="/database-schema", tags=["database-schema"])

@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse("database_schema.html", {"request": request})
