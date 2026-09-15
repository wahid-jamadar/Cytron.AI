import re
import logging
from json_repair import loads

logger = logging.getLogger(__name__)

def parse_llm_json(raw: str) -> dict:
    """
    Robustly parses JSON from LLM outputs using json_repair.
    Strips markdown wrappers (e.g. ```json ... ```).
    """
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        raw = match.group(1)
        
    try:
        # json_repair gracefully handles missing delimiters, trailing commas, 
        # and unescaped characters.
        parsed = loads(raw)
        if isinstance(parsed, dict):
            return parsed
        elif isinstance(parsed, list):
            # In case the LLM returned a list, wrap it or return as is if the caller expects it
            return {"data": parsed}
        else:
            logger.warning("Parsed JSON is not a dict or list.")
            return {}
    except Exception as exc:
        logger.error(f"json_repair failed to parse output: {exc}")
        raise
