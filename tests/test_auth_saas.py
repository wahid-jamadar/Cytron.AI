import pytest
from fastapi.testclient import TestClient
from ui.main import app
from modules.database.connection import SessionLocal
from modules.database.models import User, Role

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_saas_workflow(db_session):
    # 1. Clean up test email if exists from previous runs
    test_email = "tester_saas@example.com"
    existing = db_session.query(User).filter(User.email == test_email).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    # 2. Register new user
    register_payload = {
        "first_name": "SaaS",
        "last_name": "Tester",
        "email": test_email,
        "password": "Password123" # contains lower, upper, and number
    }
    
    response = client.post("/api/auth/register", json=register_payload)
    assert response.status_code == 201
    assert response.json()["message"] == "User registered successfully"

    # 3. Duplicate email registration block
    response_dup = client.post("/api/auth/register", json=register_payload)
    assert response_dup.status_code == 400
    assert "already registered" in response_dup.json()["detail"]

    # 4. Login with correct credentials
    login_payload = {
        "email": test_email,
        "password": "Password123"
    }
    response_login = client.post("/api/auth/login", json=login_payload)
    assert response_login.status_code == 200
    login_data = response_login.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["user"]["email"] == test_email

    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # 5. Access private preferences
    headers = {"Authorization": f"Bearer {access_token}"}
    response_prefs = client.put(
        "/api/auth/preferences",
        json={"preferred_language": "typescript", "ui_theme": "oled"},
        headers=headers
    )
    assert response_prefs.status_code == 200
    assert response_prefs.json()["message"] == "Preferences updated successfully"

    # 6. Normal user access to admin endpoints (Should return 403 Forbidden)
    response_admin = client.get("/api/admin/dashboard/metrics", headers=headers)
    assert response_admin.status_code == 403

    # 7. Admin login verification
    admin_login_payload = {
        "email": "admin@etoagent.com",
        "password": "AdminPassword123"
    }
    response_admin_login = client.post("/api/auth/login", json=admin_login_payload)
    assert response_admin_login.status_code == 200
    admin_access_token = response_admin_login.json()["access_token"]

    # 8. Admin access to metrics (Should return 200 OK)
    admin_headers = {"Authorization": f"Bearer {admin_access_token}"}
    response_metrics = client.get("/api/admin/dashboard/metrics", headers=admin_headers)
    assert response_metrics.status_code == 200
    metrics = response_metrics.json()
    assert "users" in metrics
    assert "system" in metrics

    # 9. Clean up test user
    test_user = db_session.query(User).filter(User.email == test_email).first()
    if test_user:
        db_session.delete(test_user)
        db_session.commit()
