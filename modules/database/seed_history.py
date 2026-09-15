from sqlalchemy.orm import Session
from modules.database.connection import SessionLocal, Base, engine
from modules.database.models import HistoryEvent, User
from modules.common.history import log_history_event
import random
from datetime import datetime, timedelta

def seed_history():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "wahidjamadar2020@gmail.com").first()
        if not user:
            user = db.query(User).first()
            
        if not user:
            print("No users found to attach history to. Please run init_db.py first.")
            return

        print(f"Seeding history for user {user.email}")
        
        agents = [
            ("AI Requirement Analyzer", "Requirement Analysis", "AGENT"),
            ("Build Complete Project", "Project Generation", "AGENT"),
            ("Test Case Generator", "Test Generation", "AGENT"),
            ("Code Review Agent", "Code Review", "AGENT"),
            ("Document Generator", "Documentation Generation", "AGENT"),
            ("System", "File Upload", "USER"),
            ("System", "Project Execution", "SYSTEM")
        ]
        
        statuses = ["COMPLETED", "FAILED", "RUNNING", "QUEUED"]
        projects = ["E-Commerce Platform", "Hospital Management System", "AI Chatbot", "Portfolio Website"]
        
        for i in range(20):
            agent = random.choice(agents)
            status = random.choice(statuses)
            
            created_at = datetime.utcnow() - timedelta(minutes=random.randint(1, 1440))
            completed_at = created_at + timedelta(seconds=random.randint(10, 300)) if status in ["COMPLETED", "FAILED"] else None
            
            error = None
            error_code = None
            if status == "FAILED":
                error = "Dependency Resolution Failed in phase 2."
                error_code = "ERR_DEP_02"
                
            log_history_event(
                db=db,
                activity_type=agent[1],
                action_type=agent[2],
                status=status,
                user_id=user.id,
                agent_name=agent[0],
                project_name=random.choice(projects),
                execution_id=f"RUN-100{i}",
                workflow_id=f"WF-20{i}",
                error=error,
                error_code=error_code,
                started_at=created_at,
                completed_at=completed_at,
                duration_ms=random.randint(10000, 300000) if status in ["COMPLETED", "FAILED"] else None,
                input_summary="Build an application with React and Node.js.",
                output_summary="Completed successfully with minor warnings." if status == "COMPLETED" else None,
                files_generated=["src/index.js", "src/App.css", "package.json"] if status == "COMPLETED" else None
            )
            
        print("Successfully seeded 20 history events.")
        
    except Exception as e:
        print(f"Failed to seed history: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_history()
