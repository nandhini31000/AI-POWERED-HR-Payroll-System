# AI HR Assistant with Payroll Management System

A modular Flask + MySQL HRMS with an **Agentic AI Assistant** (LangChain +
tool calling) for payroll, attendance, and leave queries.

> **Status:** Module 1 of N complete — Project Setup + Authentication.
> This README grows with each module.

---

## ✅ Completed so far (Module 1)

- Professional folder structure (Blueprints, MVC-style)
- Flask application factory (`app/__init__.py`)
- MySQL connection via SQLAlchemy (`config.py`)
- `User` model with hashed passwords + roles (`admin` / `employee`)
- Minimal `Employee` model (stub — full fields come in the Employee Module)
- Secure login / logout (Flask-Login, CSRF protection, session timeout)
- Role-based access control decorators (`@admin_required`, `@employee_required`)
- Admin Dashboard & Employee Dashboard placeholders
- Blue & white Bootstrap 5 UI, sidebar + top navbar, dark mode toggle
- Seed script creating one admin + one demo employee login

## 🔜 Coming next (in order, one module at a time)

1. Department Module
2. Employee Module (full CRUD, photo upload, search/filter/pagination)
3. Attendance Module
4. Leave Module
5. Salary Structure Module
6. Payroll Module
7. Payslip Module (PDF via ReportLab)
8. Reports Module (PDF/Excel/CSV export)
9. AI HR Assistant (LangChain agent + tool calling)
10. AI Logging + Notifications
11. REST APIs
12. Sample data seeding (20 employees, 5 departments, 6 months of records)

---

## Tech Stack

| Layer      | Technology |
|------------|------------|
| Frontend   | HTML5, CSS3, Bootstrap 5, Vanilla JS |
| Backend    | Python Flask, Blueprints, Flask-Login, SQLAlchemy |
| Database   | MySQL |
| AI         | LangChain + OpenAI/Gemini/OpenRouter, Tool Calling |
| PDFs       | ReportLab |
| Reports    | Pandas, Chart.js |

## Folder Structure

```
Payroll_AI_System/
├── app/
│   ├── routes/          # Blueprints (auth_routes.py, main_routes.py, ...)
│   ├── models/          # SQLAlchemy models (user_model.py, employee_model.py, ...)
│   ├── services/        # Business logic (payroll calculations, PDF generation, ...)
│   ├── ai/              # LangChain agent + tools (added in AI module)
│   ├── utils/           # Decorators, helpers
│   ├── templates/       # Jinja templates (auth/, admin/, employee/, partials/)
│   └── static/          # css/, js/, images/
├── database/            # Generated payslips/reports output
├── config.py            # Environment-based configuration
├── run.py               # App entry point
├── seed_data.py          # DB table creation + demo data
├── requirements.txt
├── .env.example
└── README.md
```

## Database Schema (so far)

**users**
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| username | VARCHAR(80) UNIQUE | |
| email | VARCHAR(120) UNIQUE | |
| password_hash | VARCHAR(255) | hashed, never plain text |
| role | VARCHAR(20) | 'admin' or 'employee' |
| employee_id | INT FK -> employees.id | nullable |
| is_active_account | BOOLEAN | |
| last_login_at | DATETIME | |
| created_at | DATETIME | |

**employees** (stub — expands in Employee Module)
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| employee_code | VARCHAR(20) UNIQUE | e.g. EMP0001 |
| first_name | VARCHAR(50) | |
| last_name | VARCHAR(50) | |
| email | VARCHAR(120) UNIQUE | |
| created_at | DATETIME | |

More tables (`departments`, `attendance`, `leave_requests`, `salary_structure`,
`payroll`, `payslips`, `notifications`, `chat_logs`, `ai_logs`) are added as
their modules are built.

---

## Installation

### 1. Prerequisites
- Python 3.10+
- MySQL Server 8.x running locally (or a remote instance)

### 2. Clone / copy the project, then create a virtual environment
```bash
cd Payroll_AI_System
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Create `.env` from `.env.example` and fill in your local MySQL credentials.

On Windows PowerShell:
```powershell
Copy-Item .env.example .env
```

On macOS/Linux:
```bash
cp .env.example .env
```

The app reads `.env` automatically through `python-dotenv`. Keep credentials in
`.env`; do not hardcode them in `config.py`.

### 5. Create the MySQL database
The startup preflight can create the configured database automatically when the
MySQL user has permission. To create it manually, run:
```sql
CREATE DATABASE IF NOT EXISTS `payroll_ai_system`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

The same SQL is available in `database/create_database.sql`.

### 6. Create tables + seed demo login
```bash
python seed_data.py
```

### 7. Run the app
```bash
python run.py
```

Visit **http://localhost:5000**

**Demo logins**
| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Employee | `jdoe` | `Employee@123` |

---

## Architecture Diagram

```
┌─────────────┐      HTTP       ┌──────────────────┐      SQLAlchemy      ┌────────────┐
│  Browser    │ <────────────>  │   Flask App       │ <──────────────────> │   MySQL    │
│ (Bootstrap  │                 │  (Blueprints/MVC)  │                       │  Database  │
│  + JS)      │                 │  ┌──────────────┐  │                       └────────────┘
└─────────────┘                 │  │ AI Assistant │  │
                                 │  │ (LangChain + │  │      Tool Calling
                                 │  │ Tool Calling)│──┼───► get_salary(), get_leave_balance(), etc.
                                 │  └──────────────┘  │
                                 └──────────────────┘
```

## Screenshots
_Placeholder — add screenshots here after running the app locally._

## Future Enhancements
- Multi-currency payroll
- Biometric attendance integration
- Mobile app companion
- Voice-based AI assistant
