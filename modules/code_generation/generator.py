import asyncio
import uuid
import json
from typing import Dict, Any

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, params: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "params": params,
            "queue": asyncio.Queue(),
            "status": "starting"
        }
        return job_id

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)

    async def emit_event(self, job_id: str, event_type: str, data: Any):
        job = self.jobs.get(job_id)
        if job:
            await job["queue"].put({"event": event_type, "data": json.dumps(data)})

job_manager = JobManager()

STAGES = [
    "Analyzing requirements...",
    "Identifying code patterns...",
    "Applying best practices...",
    "Writing source code...",
    "Checking syntax and types...",
    "Formatting code output..."
]

def generate_mock_code(params: Dict[str, Any]) -> str:
    language = params.get("language", "Python").lower()
    requirements = params.get("requirements", "")
    inc_comments = params.get("inc_comments", False)
    inc_tests = params.get("inc_tests", False)
    
    # Simple heuristic to generate mock code based on requirement
    # We will generate a palindrome function if the word "palindrome" is in requirements
    
    code = ""
    
    if "python" in language:
        if inc_comments:
            code += '"""\nAuto-generated Python script based on requirements.\n"""\n\n'
        
        if "palindrome" in requirements.lower():
            code += "def is_palindrome(s: str) -> bool:\n"
            if inc_comments:
                code += "    # Remove spaces and convert to lowercase\n"
            code += "    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n"
            if inc_comments:
                code += "    # Check if string equals its reverse\n"
            code += "    return cleaned == cleaned[::-1]\n"
            
            if inc_tests:
                code += "\n\nif __name__ == '__main__':\n"
                code += "    assert is_palindrome('A man a plan a canal Panama') == True\n"
                code += "    assert is_palindrome('hello') == False\n"
                code += "    print('All tests passed!')\n"
        else:
            code += "def generated_function():\n"
            if inc_comments:
                code += "    # TODO: Implement the logic based on requirements\n"
            code += f"    print('Generated for: {requirements[:20]}...')\n    pass\n"

    elif "javascript" in language or "typescript" in language:
        if inc_comments:
            code += "// Auto-generated JavaScript/TypeScript based on requirements\n\n"
            
        if "palindrome" in requirements.lower():
            code += "function isPalindrome(s) {\n"
            if inc_comments:
                code += "  // Remove non-alphanumeric characters and convert to lowercase\n"
            code += "  const cleaned = s.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();\n"
            if inc_comments:
                code += "  // Check if string equals its reverse\n"
            code += "  return cleaned === cleaned.split('').reverse().join('');\n"
            code += "}\n"
            
            if inc_tests:
                code += "\n// Unit Tests\n"
                code += "console.assert(isPalindrome('A man a plan a canal Panama') === true, 'Test 1 Failed');\n"
                code += "console.assert(isPalindrome('hello') === false, 'Test 2 Failed');\n"
                code += "console.log('Tests completed.');\n"
        else:
            code += "function generatedFunction() {\n"
            if inc_comments:
                code += "  // TODO: Implement the logic based on requirements\n"
            code += f"  console.log('Generated for: {requirements[:20]}...');\n}}\n"
            
    else:
        # Fallback for other languages
        code += f"// Generated code for {language}\n// Requirements: {requirements}\n"
        code += "\nfunction main() {\n  // Implementation here\n}\n"

    return code

async def run_mock_generation(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return

    try:
        # Stage progression
        for stage in STAGES:
            await job_manager.emit_event(job_id, "stage_change", {"stage": stage})
            await asyncio.sleep(1.5) # Simulate time taken for each stage

        # Generate mock code
        mock_code = generate_mock_code(job["params"])

        # Emit complete event with the code
        await job_manager.emit_event(job_id, "complete", {
            "code": mock_code,
            "language": job["params"].get("language", "text").lower().split("/")[0] # e.g. javascript/typescript -> javascript
        })
        job["status"] = "completed"

    except Exception as e:
        await job_manager.emit_event(job_id, "error", {"message": str(e)})
        job["status"] = "error"
