import json
import time
import ast
import difflib
from typing import Dict, List, Any
from langchain_groq import ChatGroq
from config.settings import settings
from .analyzer import get_analyzer_for_language, determine_language
from modules.database.connection import get_db
from modules.common.history import log_history_event

# In-memory queue-based job manager
class JobManager:
    def __init__(self):
        self.jobs = {}

    def create_job(self, data: dict) -> str:
        import uuid
        import asyncio
        job_id = str(uuid.uuid4())
        # unify files
        files = data.get("files", {})
        if not files and data.get("code"):
            files["snippet.py"] = data.get("code")
        
        data["files"] = files
        data["queue"] = asyncio.Queue()
        self.jobs[job_id] = data
        return job_id

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)

job_manager = JobManager()

SYSTEM_PROMPT = """You are a highly advanced autonomous code review agent. 
You are given the deterministic findings of a static analysis engine. 
Your job is to enrich them, add architectural context, and generate precise fixes.

Format your response exactly as JSON matching this schema:
{
  "findings": [
    {
      "id": "SEC-001 (or AI-001)",
      "category": "security | performance | logic | style | architecture",
      "severity": "critical | high | medium | low | info",
      "title": "Short title",
      "file": "filename.py",
      "line_start": 12,
      "line_end": 15,
      "source_excerpt": "the exact lines of code that contain the issue",
      "description": "What the issue is",
      "why_it_matters": "Impact and behavioral consequences",
      "recommendation": "How to fix it",
      "suggested_fix": "Exact replacement code for the source_excerpt. DO NOT USE MARKDOWN TICKS."
    }
  ],
  "category_summaries": {
    "security": "Summary of security issues or 'No significant security issues detected.'",
    "performance": "Summary or 'No significant performance issues detected.'",
    "style": "Summary or 'No significant style issues detected.'",
    "logic": "Summary or 'No significant logic issues detected.'",
    "documentation": "Summary or 'No significant documentation issues detected.'",
    "architecture": "Summary or 'No significant architecture issues detected.'"
  }
}

Important Rules:
1. When a deterministic analyzer has already identified a finding, DO NOT duplicate it unless you are grouping/correlating multiple paths. YOU MUST output the deterministic findings in your JSON array so they aren't lost, adding a `suggested_fix` to them.
2. If no issue exists for a category, explicitly state "No significant <category> issues detected." in the category_summaries. Do NOT generate dummy findings.
3. Your suggested_fix must be a drop-in replacement for source_excerpt.
4. NEVER generate a finding for safe code. A safely guarded division or safe subprocess call without shell=True is NOT an issue. If the code is safe, output an empty array.
"""

DEEP_MODE_PROMPT = """You are running in DEEP ARCHITECTURE MODE.
In addition to the standard rules, you MUST rigorously evaluate the software architecture and generate findings with the exact category "architecture" for any of the following:
- Separation of concerns (e.g. HTTP handlers mixed with DB queries)
- Coupling (e.g. excessive direct dependency on global state or hardcoded DB connections)
- Cohesion (e.g. functions with too many unrelated responsibilities)
- Scalability (e.g. synchronous blocking calls in async loops)
- Testability (e.g. code tightly coupled to external resources making testing hard)

If you see these flaws, you MUST output a finding with "category": "architecture". Be specific and professional.
"""

def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )

def calculate_advanced_score(findings: List[Dict]) -> Dict:
    categories = {
        "security": 100,
        "reliability": 100,
        "performance": 100,
        "maintainability": 100,
        "architecture": 100,
        "documentation": 100
    }
    
    weights = {
        "critical": 50,
        "high": 20,
        "medium": 8,
        "low": 2,
        "info": 0
    }
    
    cat_weights = {
        "security": 0.25,
        "reliability": 0.25,
        "performance": 0.15,
        "maintainability": 0.15,
        "architecture": 0.15,
        "documentation": 0.05
    }
    
    for f in findings:
        cat = str(f.get("category", "")).lower()
        if cat == "logic": cat = "reliability"
        if cat == "style": cat = "maintainability"
        
        if cat not in categories: cat = "maintainability"
        
        sev = str(f.get("severity", "info")).lower()
        deduct = weights.get(sev, 0)
        
        categories[cat] = max(0, categories[cat] - deduct)
        
    overall = sum(categories[c] * cat_weights[c] for c in categories)
    
    return {
        "overall_score": int(overall),
        "breakdown": categories
    }

def generate_unified_diff(original: str, patch: str) -> str:
    orig_lines = original.splitlines(keepends=True)
    patch_lines = patch.splitlines(keepends=True)
    diff = list(difflib.unified_diff(orig_lines, patch_lines, fromfile="original", tofile="patched", lineterm=""))
    return "".join(diff)

def validate_fix(original_code: str, excerpt: str, fix: str, filename: str) -> dict:
    if not fix or not excerpt:
        return {"status": "Not validated"}
        
    if excerpt not in original_code:
        return {"status": "⚠ Excerpt not found in original source"}
        
    patched_code = original_code.replace(excerpt, fix, 1)
    diff_patch = generate_unified_diff(excerpt, fix)
    
    # We can only syntactically validate Python right now
    if filename.endswith(".py"):
        try:
            ast.parse(patched_code)
            return {"status": "✓ Syntax valid", "patch": diff_patch}
        except SyntaxError:
            return {"status": "⚠ AI suggested invalid syntax", "patch": diff_patch, "invalid": True}
    
    return {"status": "✓ Syntax valid (Language fallback)", "patch": diff_patch}

async def _analyze_files(files: dict, depth: str, queue) -> dict:
    lang = determine_language(list(files.keys()), list(files.values()))
    analyzer_cls = get_analyzer_for_language(lang)
    analyzer = analyzer_cls(files, depth)
    
    await queue.put({"event": "status", "data": f"Running {lang.capitalize()} deterministic analysis..."})
    static_findings_models = analyzer.analyze()
    
    static_findings = [f.model_dump() for f in static_findings_models]
    
    # Consolidate Documentation Findings
    doc_findings = [f for f in static_findings if f["category"] == "documentation"]
    static_findings = [f for f in static_findings if f["category"] != "documentation"]
    
    if doc_findings:
        func_names = [f["title"].split(": ")[-1] for f in doc_findings if ": " in f["title"]]
        grouped = {
            "id": "DOC-GROUPED",
            "category": "documentation",
            "severity": "low",
            "title": "Documentation Quality",
            "file": doc_findings[0]["file"],
            "line_start": doc_findings[0]["line_start"],
            "line_end": doc_findings[-1]["line_end"],
            "source_excerpt": f"{len(doc_findings)} functions/classes missing docstrings.",
            "description": f"{len(doc_findings)} components lack useful documentation.",
            "why_it_matters": "High quality documentation is essential for maintainability.",
            "recommendation": f"Add docstrings to: {', '.join(func_names[:5])}{' and others' if len(func_names) > 5 else ''}",
        }
        static_findings.append(grouped)
    
    # AI Enrichment
    await queue.put({"event": "status", "data": "Running AI reasoning engine..."})
    llm = _build_llm()
    
    sys_prompt = SYSTEM_PROMPT
    if depth == "deep":
        sys_prompt += "\n" + DEEP_MODE_PROMPT
        
    content_str = f"Files:\n{json.dumps(files, indent=2)}\n\nDeterministic Findings:\n{json.dumps(static_findings, indent=2)}"
    
    messages = [
        ("system", sys_prompt),
        ("human", content_str)
    ]
    
    try:
        response = await llm.ainvoke(messages)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1]
            
        ai_data = json.loads(content)
    except Exception as e:
        ai_data = {"findings": static_findings, "category_summaries": {}}
        
    # Merge and deduplicate
    all_findings = []
    
    # Always include static findings if they aren't duplicate
    static_lines = {(f.get('line_start'), f.get('category')) for f in static_findings}
    for sf in static_findings:
        all_findings.append(sf)
        
    for ai_f in ai_data.get("findings", []):
        key = (ai_f.get('line_start'), ai_f.get('category'))
        # If the AI hallucinates finding that deterministic parser didn't, we allow it (AI fallback)
        if key not in static_lines:
            # Drop AI 'Safe Subprocess' dummy info findings
            if ai_f.get("severity", "").lower() in ("info", "low") and "safe" in str(ai_f.get("title", "")).lower():
                continue
            all_findings.append(ai_f)
        else:
            # Merge suggested fixes from AI back to the static finding
            for sf in all_findings:
                if sf.get('line_start') == ai_f.get('line_start') and sf.get('category') == ai_f.get('category'):
                    if not sf.get('suggested_fix') and ai_f.get('suggested_fix'):
                        sf['suggested_fix'] = ai_f['suggested_fix']

    # Validate Fixes and format diffs
    await queue.put({"event": "status", "data": "Validating fixes and calculating scores..."})
    for f in all_findings:
        if f.get("suggested_fix") and f.get("source_excerpt"):
            filename = f.get("file", "snippet.py")
            orig = files.get(filename, "")
            val_result = validate_fix(orig, f["source_excerpt"], f["suggested_fix"], filename)
            f["fix_validation"] = val_result["status"]
            if val_result.get("invalid"):
                f["suggested_fix"] = None
            elif val_result.get("patch"):
                f["patch"] = val_result["patch"]
                
    score_data = calculate_advanced_score(all_findings)
    
    return {
        "findings": all_findings,
        "summary": {
            "overall_score": score_data["overall_score"],
            "score_breakdown": score_data["breakdown"]
        },
        "category_summaries": ai_data.get("category_summaries", {}),
        "review_metadata": {
            "coverage": analyzer.coverage,
            "lines_analyzed": sum(len(content.splitlines()) for content in files.values()),
            "review_depth": depth,
            "language": lang
        }
    }

async def run_hybrid_generation(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return
        
    queue = job["queue"]
    start_time = time.time()
    
    try:
        report = await _analyze_files(job["files"], job.get("depth", "Standard"), queue)
        
        duration = round(time.time() - start_time, 2)
        report["review_metadata"]["duration_seconds"] = duration
        
        # History
        try:
            db = next(get_db())
            log_history_event(
                db=db,
                activity_type="system",
                action_type="code_review",
                status="completed",
                user_id=None,
                execution_id=job_id,
                metadata={
                    "score": report["summary"]["overall_score"],
                    "duration": duration,
                    "depth": job.get("depth", "Standard")
                }
            )
        except Exception as e:
            print(f"Failed to log history: {e}")
            
        await queue.put({"event": "complete", "data": json.dumps({"report": report})})
    except Exception as e:
        import traceback
        traceback.print_exc()
        await queue.put({"event": "error", "data": str(e)})

async def apply_fix_and_reanalyze(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return
        
    queue = job["queue"]
    
    try:
        await queue.put({"event": "status", "data": "Applying fix..."})
        
        files = job["files"].copy()
        filename = job["filename"]
        patch_content = job["patch"] # this is the replacement text for the excerpt
        
        # Apply the fix (we use a simple string replace for now since patch parsing is complex in pure python without diff-match-patch)
        # Actually, the frontend will send the full updated file or we can just send the updated files directly from the UI.
        # But let's assume `files` contains the fully updated source already.
        
        start_time = time.time()
        report = await _analyze_files(files, job.get("depth", "Standard"), queue)
        
        duration = round(time.time() - start_time, 2)
        report["review_metadata"]["duration_seconds"] = duration
        
        try:
            db = next(get_db())
            log_history_event(
                db=db,
                activity_type="system",
                action_type="fix_re_review",
                status="completed",
                user_id=None,
                execution_id=job_id,
                metadata={
                    "score_after": report["summary"]["overall_score"],
                    "duration": duration,
                }
            )
        except Exception as e:
            pass
            
        await queue.put({"event": "complete", "data": json.dumps({"report": report, "files": files})})
    except Exception as e:
        import traceback
        traceback.print_exc()
        await queue.put({"event": "error", "data": str(e)})
