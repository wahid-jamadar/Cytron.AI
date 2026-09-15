import asyncio
import json
import os
from modules.code_review.generator import job_manager, run_hybrid_generation, apply_fix_and_reanalyze

MULTI_FILE_PROJECT = {
    "router.py": """
from service import execute_user_command
def handle_request(req):
    command = req.get("command")
    execute_user_command(command)
""",
    "service.py": """
from repository import run_system_cmd
def execute_user_command(cmd):
    run_system_cmd(cmd)
""",
    "repository.py": """
import subprocess
def run_system_cmd(cmd):
    subprocess.run(cmd, shell=True)
"""
}

JS_CODE = """
function getUser(req) {
    const query = "SELECT * FROM users WHERE id = " + req.id;
    eval("console.log('test')");
    return query;
}
"""

WEAK_HASHING_CODE = """
import hashlib
def store_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_file(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()
"""

ARCHITECTURE_CODE = """
class MonolithHandler:
    def process_everything(self, http_request):
        # 1. HTTP Parsing
        body = http_request.read_body()
        
        # 2. Hardcoded DB Connection inside the request handler
        import sqlite3
        conn = sqlite3.connect('production_metrics.db')
        
        # 3. Business Logic mixed with DB access
        if body.get('metric') > 100:
            conn.execute("INSERT INTO alerts (val) VALUES (?)", (body['metric'],))
        else:
            conn.execute("INSERT INTO standard (val) VALUES (?)", (body['metric'],))
            
        # 4. HTTP Formatting returned directly
        return {"status": 200, "message": "Saved"}
"""

async def run_pipeline(files: dict, depth: str, is_fix=False, fix_data=None):
    if not is_fix:
        job_id = job_manager.create_job({"files": files, "depth": depth})
        await run_hybrid_generation(job_id)
    else:
        job_id = job_manager.create_job(fix_data)
        await apply_fix_and_reanalyze(job_id)
        
    job = job_manager.get_job(job_id)
    events = []
    while not job["queue"].empty():
        events.append(await job["queue"].get())
        
    report = None
    new_files = None
    for e in events:
        if e["event"] == "complete":
            data = json.loads(e["data"])
            report = data["report"]
            new_files = data.get("files")
    return report, new_files

async def run_tests():
    print("="*50)
    print("1. CROSS-FILE TAINT TRACKING (Multi-File)")
    print("="*50)
    report, _ = await run_pipeline(MULTI_FILE_PROJECT, "Standard")
    coverage_safe = [c.replace('✓', 'OK').replace('○', 'SKIP').replace('⚠', 'WARN') for c in report['review_metadata']['coverage']]
    print(f"Coverage: {', '.join(coverage_safe)}")
    sec_004_found = any(f['id'] == 'SEC-004' for f in report['findings'])
    if sec_004_found:
        print("PASS: Detected Command Injection across 3 files.")
    else:
        print("FAIL: Did not detect cross-file Command Injection.")

    print("\n" + "="*50)
    print("2. MULTI-LANGUAGE DETERMINISTIC (JavaScript)")
    print("="*50)
    js_report, _ = await run_pipeline({"app.js": JS_CODE}, "Standard")
    print(f"Language identified: {js_report['review_metadata']['language']}")
    sqli = any(f['id'] == 'SEC-005' for f in js_report['findings'])
    eval_f = any(f['id'] == 'SEC-002' for f in js_report['findings'])
    if sqli and eval_f:
        print("PASS: JavaScript deterministic rules triggered for SQLi and eval.")
    else:
        print("FAIL: JS parser missed vulnerabilities.")

    print("\n" + "="*50)
    print("3. WEAK PASSWORD HASHING")
    print("="*50)
    hash_report, _ = await run_pipeline({"hash.py": WEAK_HASHING_CODE}, "Standard")
    hash_findings = [f for f in hash_report['findings'] if f['id'] == 'SEC-006']
    if len(hash_findings) == 1:
        print("PASS: Detected weak hashing for password, but ignored file_bytes.")
    else:
        print(f"FAIL: Expected exactly 1 weak hash finding, got {len(hash_findings)}")

    print("\n" + "="*50)
    print("4. DEEP ARCHITECTURE MODE")
    print("="*50)
    arch_report, _ = await run_pipeline({"app.py": ARCHITECTURE_CODE}, "Deep")
    arch_findings = [f for f in arch_report['findings'] if f['category'] == 'architecture']
    if len(arch_findings) > 0:
        print(f"PASS: Generated {len(arch_findings)} architectural findings.")
        for a in arch_findings:
            print(f" - {a['title']}")
    else:
        print("FAIL: Did not generate architectural findings in Deep mode.")
        print("Actually returned categories:")
        for a in arch_report['findings']:
            print(f" - {a.get('category')}: {a.get('title')}")
        
    print("\n" + "="*50)
    print("5. FIX VALIDATION & UNIFIED DIFF")
    print("="*50)
    # We will pick a finding from hash_report and look at its patch
    f_hash = next((f for f in hash_report['findings'] if f['id'] == 'SEC-006'), None)
    if f_hash and f_hash.get('patch'):
        print("PASS: Unified Diff generated.")
        print(f_hash['patch'])
    else:
        print("FAIL: No patch generated.")

    print("\n" + "="*50)
    print("6. AUTONOMOUS FIX LOOP (Re-Review)")
    print("="*50)
    if f_hash and f_hash.get('suggested_fix'):
        fix_data = {
            "files": {"hash.py": WEAK_HASHING_CODE.replace(f_hash['source_excerpt'], f_hash['suggested_fix'])},
            "patch": f_hash['suggested_fix'],
            "filename": "hash.py",
            "finding_id": f_hash['id'],
            "depth": "Standard",
            "is_re_review": True
        }
        re_report, new_files = await run_pipeline(None, "Standard", True, fix_data)
        if not any(f['id'] == 'SEC-006' for f in re_report['findings']):
            print("PASS: Fix was applied and issue disappeared in re-review.")
            print(f"Score improved to {re_report['summary']['overall_score']}")
        else:
            print("FAIL: Re-review still flagged the issue after fix.")

if __name__ == "__main__":
    asyncio.run(run_tests())
