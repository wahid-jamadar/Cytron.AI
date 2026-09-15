import bcrypt
from sqlalchemy.orm import Session
from modules.database.connection import engine, Base, SessionLocal
from modules.database.models import User, Role, Permission, UserPreferences, FeatureFlag

def init_database():
    print("Creating all tables in MySQL...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # 1. Seed Permissions
        print("Seeding permissions...")
        permissions_list = [
            ("system.access", "Access the main system dashboard"),
            ("admin.access", "Access the administrative panel and APIs"),
            ("read:projects", "Read personal and organization projects"),
            ("write:projects", "Create and edit projects"),
            ("delete:projects", "Soft delete projects"),
            ("archive:projects", "Archive projects"),
            ("read:users", "Read user details and statistics"),
            ("write:users", "Suspend, ban or edit users"),
            ("impersonate:users", "Impersonate users for support troubleshooting"),
            ("read:admin_dashboard", "Access the central administration metrics"),
            ("write:system_settings", "Modify feature flags, billing, and system settings"),
            ("read:logs", "Read audit logs, activity timelines, and security logs"),
            ("read:analytics", "Read token consumption and cost tracking dashboards"),
        ]
        
        perms_db = {}
        for p_name, p_desc in permissions_list:
            perm = db.query(Permission).filter(Permission.name == p_name).first()
            if not perm:
                perm = Permission(name=p_name, description=p_desc)
                db.add(perm)
                db.flush()
            perms_db[p_name] = perm
            
        # 2. Seed Roles
        print("Seeding roles...")
        roles_list = {
            "SUPER_ADMIN": list(perms_db.keys()),
            "ADMIN": [
                "system.access", "admin.access",
                "read:projects", "write:projects", "delete:projects", "archive:projects",
                "read:users", "write:users", "impersonate:users", "read:admin_dashboard",
                "read:logs", "read:analytics"
            ],
            "SUPPORT": [
                "system.access", "admin.access",
                "read:projects", "read:users", "read:logs", "read:analytics"
            ],
            "READ_ONLY_ADMIN": [
                "system.access", "admin.access",
                "read:admin_dashboard", "read:analytics"
            ],
            "USER": [
                "system.access",
                "read:projects", "write:projects"
            ]
        }
        
        roles_db = {}
        for r_name, p_names in roles_list.items():
            role = db.query(Role).filter(Role.name == r_name).first()
            if not role:
                role = Role(name=r_name, description=f"Default {r_name} role")
                db.add(role)
                db.flush()
            
            # Associate permissions
            role.permissions = [perms_db[p] for p in p_names]
            db.flush()
            roles_db[r_name] = role
            
        # 3. Create default Super Admin User
        admin_email = "admin@etoagent.com"
        print(f"Checking default super admin user: {admin_email}...")
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            # Hash default password: AdminPassword123
            salt = bcrypt.gensalt()
            hashed_pwd = bcrypt.hashpw(b"AdminPassword123", salt).decode('utf-8')
            
            admin_user = User(
                email=admin_email,
                first_name="SaaS",
                last_name="Administrator",
                hashed_password=hashed_pwd,
                status="active"
            )
            db.add(admin_user)
            db.flush()
            
            # Map role
            admin_user.roles.append(roles_db["SUPER_ADMIN"])
            
            # Add default preferences
            prefs = UserPreferences(
                user_id=admin_user.id,
                preferred_provider="groq",
                preferred_language="python",
                ui_theme="dark",
                timezone="UTC"
            )
            db.add(prefs)
            db.flush()
            print(f"Default admin user created successfully: {admin_email} / AdminPassword123")
        else:
            print(f"Default admin user {admin_email} already exists.")
            
        # 3b. Create custom Super Admin User
        user_email = "wahidjamadar2020@gmail.com"
        print(f"Checking custom super admin user: {user_email}...")
        custom_user = db.query(User).filter(User.email == user_email).first()
        if not custom_user:
            # Hash password: pass123
            salt = bcrypt.gensalt()
            hashed_pwd = bcrypt.hashpw(b"pass123", salt).decode('utf-8')
            
            custom_user = User(
                email=user_email,
                first_name="Wahid",
                last_name="Jamadar",
                hashed_password=hashed_pwd,
                status="active"
            )
            db.add(custom_user)
            db.flush()
            
            # Map role
            custom_user.roles.append(roles_db["SUPER_ADMIN"])
            
            # Add default preferences
            prefs = UserPreferences(
                user_id=custom_user.id,
                preferred_provider="groq",
                preferred_language="python",
                ui_theme="dark",
                timezone="Asia/Kolkata"
            )
            db.add(prefs)
            db.flush()
            print(f"Custom super admin user created successfully: {user_email} / pass123")
        else:
            print(f"Custom super admin user {user_email} already exists.")
            
        # 4. Seed Default Feature Flags
        print("Seeding feature flags...")
        flags = [
            ("AI Requirement Analyzer", True, "Enable requirement analyzer agent node"),
            ("Autonomous Coding", True, "Enable code generator agent node"),
            ("Deployment", True, "Enable cloud deployment agent node"),
            ("Experimental Agents", False, "Enable beta/experimental agents"),
            ("New UI Components", True, "Enable new dashboard UI widgets"),
            ("Beta Features", False, "General beta-tested features access"),
        ]
        for name, enabled, desc in flags:
            flag = db.query(FeatureFlag).filter(FeatureFlag.name == name).first()
            if not flag:
                flag = FeatureFlag(name=name, is_enabled=enabled, description=desc)
                db.add(flag)
        
        db.commit()
        print("Database initialized successfully!")
    except Exception as e:
        db.rollback()
        print(f"Database initialization failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
