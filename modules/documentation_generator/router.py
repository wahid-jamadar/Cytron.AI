import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config.settings import settings
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from modules.common.utils import templates
from modules.documentation_generator.strategies import get_strategy
from modules.documentation_generator.exporters import get_exporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documentation-generator", tags=["documentation-generator"])

# Directory to save generated documents
OUTPUT_DIR = Path("output/generated_docs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class DocGenerateRequest(BaseModel):
    type: str = Field(..., description="The type of documentation to generate")
    format: str = Field(..., description="The output file format")
    tone: str = Field(..., description="The style and tone of the document")
    source: str = Field(..., description="The source code, API schemas, or reference materials")
    instructions: Optional[str] = Field(None, description="Specific formatting or content instructions")


class DocGenerateResponse(BaseModel):
    status: str
    filename: Optional[str] = None
    content: Optional[str] = None
    format: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


def get_extension(format_name: str) -> str:
    """Helper to map format names to file extensions."""
    fmt = format_name.lower().strip()
    if "markdown" in fmt or ".md" in fmt:
        return "md"
    if "html" in fmt:
        return "html"
    if "pdf" in fmt:
        return "pdf"
    if "docx" in fmt or "word" in fmt:
        return "docx"
    if "txt" in fmt or "plain text" in fmt:
        return "txt"
    if "yaml" in fmt or "yml" in fmt:
        return "yaml"
    if "json" in fmt:
        return "json"
    if "xml" in fmt:
        return "xml"
    if "drawio" in fmt or "draw.io" in fmt:
        return "drawio"
    if "pptx" in fmt or "powerpoint" in fmt:
        return "pptx"
    return "txt"


@router.get("/")
async def page(request: Request):
    """Serves the Documentation Generator page."""
    return templates.TemplateResponse("documentation_generator.html", {"request": request})


@router.post("/api/generate", response_model=DocGenerateResponse)
async def generate_documentation(req: DocGenerateRequest):
    """
    E2E endpoint that validates parameters, chooses the strategy, invokes LLM,
    exports using the exporter factory, and returns download details.
    """
    logger.info(f"Generating documentation: type='{req.type}', format='{req.format}', tone='{req.tone}'")
    
    try:
        # 1. Resolve strategy
        try:
            strategy = get_strategy(req.type)
        except Exception as e:
            logger.error(f"Strategy resolution failed for '{req.type}': {e}")
            raise HTTPException(status_code=400, detail=f"Unsupported documentation type: {req.type}")

        # 2. Resolve exporter
        try:
            exporter = get_exporter(req.format)
        except Exception as e:
            logger.error(f"Exporter resolution failed for '{req.format}': {e}")
            raise HTTPException(status_code=400, detail=f"Unsupported format: {req.format}")

        # 3. Formulate prompts
        system_prompt = strategy.get_system_prompt(req.tone)
        user_prompt = strategy.get_user_prompt(req.source, req.instructions)

        # 4. Invoke LLM (Groq Llama)
        if not settings.groq_api_key:
            raise ValueError("Groq API key is not configured in environment settings.")

        llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.3
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        logger.info("Calling Groq LLM chain...")
        response = await llm.ainvoke(messages)
        generated_md = response.content
        
        if not generated_md or not generated_md.strip():
            raise RuntimeError("LLM returned empty output")

        # 5. Export to target file
        ext = get_extension(req.format)
        filename = f"doc_{uuid.uuid4().hex[:8]}.{ext}"
        output_path = OUTPUT_DIR / filename
        
        metadata = {
            "title": f"Generated {req.type}",
            "type": req.type,
            "tone": req.tone,
            "date": datetime.utcnow().strftime("%Y-%m-%d")
        }
        
        logger.info(f"Exporting to format '{req.format}' path='{output_path}'")
        exporter.export(generated_md, metadata, output_path)

        # 6. Read preview if text-based format
        content = ""
        is_text = ext in ("md", "html", "txt", "json", "yaml", "xml", "drawio")
        if is_text and output_path.exists():
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as read_err:
                logger.warning(f"Could not read text preview for '{filename}': {read_err}")
                content = generated_md # Fallback to raw markdown

        return DocGenerateResponse(
            status="success",
            filename=filename,
            content=content,
            format=req.format,
            download_url=f"/documentation-generator/api/download/{filename}"
        )

    except Exception as exc:
        logger.exception("Documentation generation engine failure")
        return DocGenerateResponse(
            status="error",
            error=str(exc)
        )


@router.get("/api/download/{filename}")
async def download_file(filename: str):
    """Endpoint to download generated files."""
    file_path = OUTPUT_DIR / filename
    
    # Simple path traversal protection
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        logger.error(f"Download request failed: file not found at '{file_path}'")
        raise HTTPException(status_code=404, detail="File not found")
        
    media_type = "application/octet-stream"
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        media_type = "application/pdf"
    elif ext == ".html":
        media_type = "text/html"
    elif ext == ".txt":
        media_type = "text/plain"
    elif ext in (".json", ".swagger"):
        media_type = "application/json"
    elif ext in (".yaml", ".yml"):
        media_type = "application/yaml"
    elif ext == ".xml":
        media_type = "application/xml"
        
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )
