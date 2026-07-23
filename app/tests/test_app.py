import pytest
from fastapi.testclient import TestClient

def test_full_system_workflow(client: TestClient):
    # 1. Register User A (Project Creator)
    register_res_a = client.post("/auth/register", json={
        "email": "creator@example.com",
        "password": "password123",
        "full_name": "Alice Creator"
    })
    assert register_res_a.status_code == 201
    user_a_id = register_res_a.json()["id"]

    # 2. Register User B (Project Member)
    register_res_b = client.post("/auth/register", json={
        "email": "member@example.com",
        "password": "password123",
        "full_name": "Bob Member"
    })
    assert register_res_b.status_code == 201
    user_b_id = register_res_b.json()["id"]

    # 3. Log in User A
    login_res_a = client.post("/auth/login", data={
        "username": "creator@example.com",
        "password": "password123"
    })
    assert login_res_a.status_code == 200
    token_a = login_res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 4. Log in User B
    login_res_b = client.post("/auth/login", data={
        "username": "member@example.com",
        "password": "password123"
    })
    assert login_res_b.status_code == 200
    token_b = login_res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 5. Create Project (User A)
    proj_res = client.post("/projects", headers=headers_a, json={
        "title": "Alpha Project",
        "description": "Initial design project.",
        "deadline": "2026-12-31T23:59:59"
    })
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 6. Verify User B cannot access project details (403)
    proj_view_b = client.get(f"/projects/{project_id}", headers=headers_b)
    assert proj_view_b.status_code == 403

    # 7. Add User B to Project Members (User A)
    add_mem_res = client.post(f"/projects/{project_id}/members", headers=headers_a, json={
        "user_id": user_b_id
    })
    assert add_mem_res.status_code == 200

    # 8. Verify User B can now view project details
    proj_view_b2 = client.get(f"/projects/{project_id}", headers=headers_b)
    assert proj_view_b2.status_code == 200
    assert len(proj_view_b2.json()["members"]) == 1
    assert proj_view_b2.json()["members"][0]["id"] == user_b_id

    # 9. Update Project Title and verify audit trail (User A)
    update_proj_res = client.put(f"/projects/{project_id}", headers=headers_a, json={
        "title": "Omega Project",
        "description": "Initial design project.",
        "deadline": "2026-12-31T23:59:59"
    })
    assert update_proj_res.status_code == 200
    assert update_proj_res.json()["title"] == "Omega Project"

    # 10. Create Task (User A)
    task_res = client.post(f"/projects/{project_id}/tasks", headers=headers_a, json={
        "title": "Build API Prototype",
        "description": "Build working endpoints.",
        "assignee_id": None
    })
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # 11. Assign Task to User B (User A)
    task_assign_res = client.put(f"/tasks/{task_id}", headers=headers_a, json={
        "assignee_id": user_b_id
    })
    assert task_assign_res.status_code == 200
    assert task_assign_res.json()["assignee_id"] == user_b_id

    # 12. Update Task Status to "In Progress" (User B)
    task_status_res1 = client.put(f"/tasks/{task_id}", headers=headers_b, json={
        "status": "In Progress"
    })
    assert task_status_res1.status_code == 200

    # 13. Update Task Status to "Completed" (User B)
    task_status_res2 = client.put(f"/tasks/{task_id}", headers=headers_b, json={
        "status": "Completed"
    })
    assert task_status_res2.status_code == 200

    # 14. Verify Notifications for User B
    # User B was added to project and assigned to task, should have notifications.
    notifs_b = client.get("/notifications", headers=headers_b)
    assert notifs_b.status_code == 200
    b_json = notifs_b.json()
    assert len(b_json) >= 2 # Project invitation and Task Assignment

    # Extract invitation notification id
    invitation_notif = next((n for n in b_json if "Project Invitation" in n["title"]), None)
    assert invitation_notif is not None

    # Mark invitation as read
    read_res = client.put(f"/notifications/{invitation_notif['id']}/read", headers=headers_b)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # 15. Check User Unread Notifications
    unread_notifs_b = client.get("/notifications/unread", headers=headers_b)
    assert unread_notifs_b.status_code == 200
    assert any(n["id"] == invitation_notif["id"] for n in unread_notifs_b.json()) is False

    # 16. Verify Activity Logs
    activities = client.get("/activities", headers=headers_a)
    assert activities.status_code == 200
    act_json = activities.json()
    assert len(act_json) > 0
    # Check project-specific activities
    proj_activities = client.get(f"/activities/project/{project_id}", headers=headers_a)
    assert proj_activities.status_code == 200
    assert len(proj_activities.json()) > 0

    # 17. Verify Audit Trails
    audits = client.get("/audit-logs", headers=headers_a)
    assert audits.status_code == 200
    audit_json = audits.json()
    assert len(audit_json) > 0
    
    # Check that task status transitions are audited
    status_audits = [a for a in audit_json if a["field_name"] == "status" and a["entity_type"] == "Task"]
    assert len(status_audits) == 2
    assert any(a["old_value"] == "Pending" and a["new_value"] == "In Progress" for a in status_audits)
    assert any(a["old_value"] == "In Progress" and a["new_value"] == "Completed" for a in status_audits)

    # 18. Verify CSV & PDF Export Endpoints
    csv_export = client.get("/activities/export?format=csv", headers=headers_a)
    assert csv_export.status_code == 200
    assert "ID,User ID,User Name,Action" in csv_export.text

    pdf_export = client.get("/activities/export?format=pdf", headers=headers_a)
    assert pdf_export.status_code == 200
    assert pdf_export.headers["content-type"] == "application/pdf"
