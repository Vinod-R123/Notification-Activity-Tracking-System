# Notification-Activity-Tracking-System
# Notification & Activity Tracking System

A robust Project Management API built with FastAPI, SQLAlchemy 2.0 (ORM), and SQLite. The application features an **Event-Driven Architecture** utilizing background task workers, automated field auditing, activity logging, custom user notification preferences, real-time WebSocket notifications, and CSV/PDF report exporting.

---

## Architecture & Design

This system leverages FastAPI's asynchronous pipeline and SQLAlchemy's relation modeling to achieve high performance. To prevent slow operations (like log writing, websocket broadcasting, and email rendering) from blocking the HTTP request-response cycle, the application uses an **Event-Driven Background Processing** design.

```
                  +-----------------------------------+
                  |        FastAPI HTTP Client        |
                  +-----------------+-----------------+
                                    |
                                    | HTTP Requests (e.g. POST, PUT, DELETE)
                                    v
                  +-----------------+-----------------+
                  |         Router / Controller       |
                  +-----------------+-----------------+
                                    |
                                    +---+ (1) Commits to Database
                                    |   |
                                    |   v
                                    | +-+-----------------------------+
                                    | |   SQLite Database (Primary)   |
                                    | +-------------------------------+
                                    |
                                    +---+ (2) Queues Background Event
                                        |
                                        v
                  +---------------------+-----------------------------+
                  |         Background Task Executor                  |
                  |         (app/services/event_system.py)            |
                  +--+----------------+---------------+------------+--+
                     |                |               |            |
                     | (a)            | (b)           | (c)        | (d)
                     v                v               v            v
              +------+-----+   +------+-----+  +------+-----+  +---+----+
              |Activity Log|   | Audit Log  |  |Notification|  |Email   |
              |   Writer   |   | (Field Diff|  | (Pref Filt)|  | (Mock) |
              +------------+   +------------+  +------+-----+  +--------+
                                                      |
                                                      v (Real-time Broadcast)
                                               +------+-----+
                                               | WebSockets |
                                               +------------+
```

---

## Database ER Diagram

The database relationships are represented by the following entity-relationship model:

```mermaid
erDiagram
    USERS {
        int id PK
        string email UNIQUE
        string hashed_password
        string full_name
        bool is_active
        json notification_preferences
        datetime created_at
        datetime deleted_at
    }
    PROJECTS {
        int id PK
        string title
        string description
        int creator_id FK
        datetime deadline
        datetime created_at
        datetime deleted_at
    }
    PROJECT_MEMBERS {
        int project_id PK, FK
        int user_id PK, FK
        datetime joined_at
    }
    TASKS {
        int id PK
        int project_id FK
        string title
        string description
        string status
        int assignee_id FK
        int creator_id FK
        datetime deadline
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }
    NOTIFICATIONS {
        int id PK
        int user_id FK
        string title
        string message
        bool is_read
        datetime created_at
    }
    ACTIVITY_LOGS {
        int id PK
        int user_id FK
        string action
        string entity_type
        int entity_id
        string description
        datetime created_at
    }
    AUDIT_LOGS {
        int id PK
        string entity_type
        int entity_id
        string field_name
        string old_value
        string new_value
        int changed_by FK
        datetime changed_at
    }

    USERS ||--o{ PROJECTS : "creates"
    USERS ||--o{ PROJECT_MEMBERS : "member of"
    PROJECTS ||--o{ PROJECT_MEMBERS : "has members"
    PROJECTS ||--o{ TASKS : "contains"
    USERS ||--o{ TASKS : "assigned to"
    USERS ||--o{ NOTIFICATIONS : "receives"
    USERS ||--o{ ACTIVITY_LOGS : "performs"
    USERS ||--o{ AUDIT_LOGS : "audited changes by"
```

---

## API Endpoints List

### Authentication
* `POST /auth/register` - Create a new user account.
* `POST /auth/login` - Authenticate credentials and return a bearer JWT token (logs User Login).
* `POST /auth/logout` - Invalidate user session (logs User Logout).
* `GET /auth/me` - Fetch details of the currently authenticated user.
* `PUT /auth/preferences` - Update user notification preferences (disable/enable triggers).

### Projects
* `GET /projects` - List all projects where the user is either the creator or a member.
* `POST /projects` - Create a new project (logs Project Creation).
* `GET /projects/{id}` - Fetch project details, including list of members.
* `PUT /projects/{id}` - Update a project (audits changes on fields and logs Project Update).
* `DELETE /projects/{id}` - Soft-delete a project and its associated tasks (logs Project Deletion).
* `POST /projects/{id}/members` - Add a member to a project (logs Member Addition & triggers Notification).
* `DELETE /projects/{id}/members/{user_id}` - Remove a member from a project.

### Tasks
* `POST /projects/{project_id}/tasks` - Create a task in a project (logs Task Creation).
* `GET /projects/{project_id}/tasks` - List all active tasks in a project.
* `GET /tasks/{id}` - Fetch task details.
* `PUT /tasks/{id}` - Update task details, status, or assignee (audits status transition `Pending -> In Progress -> Completed`, assignments, and deadlines, logs Task Update & triggers Notifications).
* `DELETE /tasks/{id}` - Soft-delete a task (logs Task Deletion).

### Notifications & Tracking
* `GET /notifications` - List notifications for the authenticated user.
* `GET /notifications/unread` - Fetch unread notifications.
* `PUT /notifications/{id}/read` - Mark a specific notification as read.
* `PUT /notifications/read-all` - Mark all user notifications as read.
* `DELETE /notifications/{id}` - Delete a notification.
* `GET /activities` - Query activity logs (supports filtering by `user_id`, `project_id`, `start_date`, `end_date`, and `action_type`).
* `GET /activities/user/{id}` - Retrieve activity logs for a specific user.
* `GET /activities/project/{id}` - Retrieve activity logs for a specific project (includes project and task events).
* `GET /audit-logs` - View change audit logs.
* `GET /audit-logs/{entity_type}/{entity_id}` - View the modification history of a specific entity.
* `GET /activities/export` - Export activity logs based on query filters to `CSV` or `PDF` formats.

---

## Getting Started

### 1. Requirements Installation
Create a virtual environment and install the required dependencies:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Initialization (Migrations)
Apply Alembic migrations to generate the database schema and initialize the SQLite database file:
```bash
.\venv\Scripts\alembic upgrade head
```

### 3. Running the Server
Start the development server:
```bash
.\venv\Scripts\uvicorn app.main:app --reload
```
* **Swagger Interactive Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 4. Running Automated Tests
To run the automated integration tests:
```bash
$env:PYTHONPATH="."; .\venv\Scripts\pytest -v
```

---

## WebSocket & Email Verification

### WebSockets (Real-Time Notifications)
To receive real-time notifications, client applications should connect to:
`ws://127.0.0.1:8000/ws/notifications?token=<JWT_TOKEN>`

When notifications are created (and target preferences are enabled), the payload is dispatched over the connection:
```json
{
  "event": "notification",
  "id": 4,
  "title": "Task Assigned",
  "message": "You have been assigned to the task 'Build API Prototype' by Alice Creator.",
  "created_at": "2026-07-22T15:30:00.123456",
  "is_read": false
}
```

### Email Notifications (Mock File)
Emails triggered by events (Task Assigned, Project Invitation, Task Deadline Updated) are mock-rendered and logged to:
`mock_emails.txt` in the root workspace folder. This file records the date, recipient, subject, and body format for evaluation.
