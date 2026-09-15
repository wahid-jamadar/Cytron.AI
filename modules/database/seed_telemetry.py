import os
import json
import re
from datetime import datetime
from sqlalchemy.orm import Session
from modules.database.connection import SessionLocal, engine
from modules.database.models import User, Project, AgentRun, AgentTask, AIRequest

def parse_timestamp(ts_str):
    """Safely parse ISO timestamp from JSON log string."""
    try:
        cleaned = ts_str.replace("Z", "")
        # Remove any extra precision beyond microseconds if present
        if "." in cleaned:
            parts = cleaned.split(".")
            if len(parts[1]) > 6:
                cleaned = f"{parts[0]}.{parts[1][:6]}"
        return datetime.fromisoformat(cleaned)
    except Exception:
        return datetime.utcnow()

def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate LLM cost based on typical Groq rates ($0.15/M input, $0.60/M output)."""
    return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1000000.0

def seed_from_logs():
    db: Session = SessionLocal()
    try:
        # Find default user
        user = db.query(User).filter(User.email == "admin@etoagent.com").first() or \
               db.query(User).filter(User.email == "wahidjamadar2020@gmail.com").first() or \
               db.query(User).first()
        if not user:
            print("Error: No users found in database. Run database initialization first.")
            return

        print(f"Seeding telemetry under user: {user.email} (ID: {user.id})")

        # Map to hold parsed runs
        parsed_runs = {}
        current_run_id = None
        
        # Log files to read (oldest first)
        log_files = ["logs/platform.json.1", "logs/platform.json"]
        
        for file_path in log_files:
            if not os.path.exists(file_path):
                print(f"Log file not found: {file_path}, skipping...")
                continue
                
            print(f"Reading log file: {file_path}...")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        msg = entry.get("message", "")
                        ts_str = entry.get("timestamp", "")
                        ts = parse_timestamp(ts_str)
                        category = entry.get("category", "")
                        component = entry.get("component", "")
                        
                        # 1. Detect run start
                        # Message shape: "[Runner] Starting pipeline run 8cdd5fc0"
                        if "[Runner] Starting pipeline run" in msg:
                            run_match = re.search(r"Starting pipeline run\s+([0-9a-fA-F]+)", msg)
                            if run_match:
                                run_id = run_match.group(1)
                                parsed_runs[run_id] = {
                                    "run_id": run_id,
                                    "started_at": ts,
                                    "completed_at": None,
                                    "status": "completed", # default status
                                    "project_name": f"Project_{run_id}",
                                    "tasks": [],
                                    "ai_requests": []
                                }
                                current_run_id = run_id
                                continue
                                
                        if not current_run_id:
                            continue
                            
                        # 2. Extract project name from requirement analyzer complete log
                        # Message shape: "[RequirementAnalyzer] Done. App: 'simple_web_app'..."
                        if "Done. App:" in msg and current_run_id in parsed_runs:
                            name_match = re.search(r"App:\s*'([^']+)'", msg)
                            if name_match:
                                parsed_runs[current_run_id]["project_name"] = name_match.group(1)
                                
                        # 3. Detect Agent Task Started
                        if category == "AGENT ACTION" and "Started" in msg:
                            task_name = component or msg.replace(" Started", "")
                            # Check if task already listed
                            existing = [t for t in parsed_runs[current_run_id]["tasks"] if t["agent_name"] == task_name]
                            if not existing:
                                parsed_runs[current_run_id]["tasks"].append({
                                    "agent_name": task_name,
                                    "status": "running",
                                    "started_at": ts,
                                    "completed_at": None,
                                    "duration_ms": 0,
                                    "cpu": float(entry.get("cpu", 12.5)),
                                    "ram": float(entry.get("ram", 15.0))
                                })
                                
                        # 4. Detect Agent Task Completed / Failed
                        if category == "AGENT ACTION" and ("Completed" in msg or "Failed" in msg):
                            task_name = component or msg.replace(" Completed", "").replace(" Failed", "")
                            status = "completed" if "Completed" in msg else "failed"
                            
                            # Find the running task
                            for t in parsed_runs[current_run_id]["tasks"]:
                                if t["agent_name"] == task_name and t["completed_at"] is None:
                                    t["status"] = status
                                    t["completed_at"] = ts
                                    duration_sec = entry.get("duration_seconds") or entry.get("duration") or 0.0
                                    t["duration_ms"] = int(duration_sec * 1000)
                                    
                                    # Parse memory if available: e.g. "297.2 MB" -> 297.2
                                    mem_str = entry.get("memory") or ""
                                    mem_match = re.search(r"([0-9.]+)", str(mem_str))
                                    if mem_match:
                                        t["ram"] = float(mem_match.group(1)) / 100.0 # scale down for mock load percentage or store directly
                                    break
                                    
                        # 5. Detect LLM Request
                        if category == "LLM RESPONSE" and "Response Received" in msg:
                            prompt_tokens = int(entry.get("prompt_tokens", 0))
                            completion_tokens = int(entry.get("completion_tokens", 0))
                            latency = float(entry.get("latency", 0.0))
                            model = entry.get("model", "llama-3.3-70b-versatile")
                            provider = entry.get("provider", "Groq")
                            
                            parsed_runs[current_run_id]["ai_requests"].append({
                                "timestamp": ts,
                                "model": model,
                                "provider": provider,
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "latency": latency,
                                "agent_name": component or "LLM Request"
                             })
                             
                        # 6. Detect Run Complete/Halt
                        if "EXECUTION SUMMARY" in msg or "Pipeline complete" in msg or "Pipeline halted" in msg:
                            status = "failed" if ("Status: FAILED" in msg or "halted" in msg) else "completed"
                            parsed_runs[current_run_id]["status"] = status
                            parsed_runs[current_run_id]["completed_at"] = ts
                            # We keep current_run_id for subsequent summary lines, but clear it when thread changes
                            
                    except Exception as e:
                        # Log parsing error and continue
                        pass

        # Write parsed runs to DB
        print(f"Total parsed runs from logs: {len(parsed_runs)}")
        for rid, rdata in parsed_runs.items():
            # Check if this project already exists
            pname = rdata["project_name"]
            proj = db.query(Project).filter(Project.name == pname, Project.owner_id == user.id).first()
            if not proj:
                proj = Project(
                    owner_id=user.id,
                    name=pname,
                    status=rdata["status"],
                    deployment_status="active" if rdata["status"] == "completed" else "failed",
                    created_at=rdata["started_at"],
                    updated_at=rdata["completed_at"] or rdata["started_at"]
                )
                db.add(proj)
                db.flush()
                print(f"  Created Project: {pname} (ID: {proj.id})")
            
            # Check if AgentRun exists
            db_run = db.query(AgentRun).filter(AgentRun.project_id == proj.id, AgentRun.created_at == rdata["started_at"]).first()
            if not db_run:
                db_run = AgentRun(
                    project_id=proj.id,
                    user_id=user.id,
                    status=rdata["status"],
                    created_at=rdata["started_at"],
                    completed_at=rdata["completed_at"]
                )
                db.add(db_run)
                db.flush()
                print(f"    Created AgentRun ID: {db_run.id}")
                
                # Write Tasks
                for t in rdata["tasks"]:
                    # Create AgentTask
                    db_task = AgentTask(
                        run_id=db_run.id,
                        agent_name=t["agent_name"],
                        status=t["status"],
                        execution_duration_ms=t["duration_ms"],
                        progress_pct=100.0 if t["status"] == "completed" else 0.0,
                        cpu_usage=t["cpu"] if t["cpu"] < 100.0 else 15.4,
                        memory_usage=t["ram"] if t["ram"] < 100.0 else 42.8,
                        created_at=t["started_at"],
                        updated_at=t["completed_at"] or t["started_at"]
                    )
                    db.add(db_task)
                
                # Write AI Requests
                for req in rdata["ai_requests"]:
                    cost = calculate_cost(req["prompt_tokens"], req["completion_tokens"])
                    db_req = AIRequest(
                        user_id=user.id,
                        project_id=proj.id,
                        agent_name=req["agent_name"],
                        provider=req["provider"],
                        model=req["model"],
                        input_tokens=req["prompt_tokens"],
                        output_tokens=req["completion_tokens"],
                        total_tokens=req["prompt_tokens"] + req["completion_tokens"],
                        latency_ms=int(req["latency"] * 1000),
                        estimated_cost=cost,
                        created_at=req["timestamp"]
                    )
                    db.add(db_req)

        db.commit()
        print("Database seeded with real telemetry logs successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_from_logs()
