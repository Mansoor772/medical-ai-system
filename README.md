# MedAI — Clinical Intelligence System

An AI-assisted medical diagnosis and records management system for clinics and hospitals in Pakistan. Built for multi-tenant SaaS deployment — each hospital gets its own isolated database.

---

## Features

- **AI Diagnosis** — Doctor queries GPT-4o with patient data + medical literature (RAG pipeline)
- **Citation Snapshotting** — Evidence frozen at time of suggestion (not a live pointer)
- **Knowledge Base** — Upload medical PDFs; auto-chunked, embedded, and indexed via pgvector
- **Lab Alerts** — Doctor flags abnormal results → approves → email sent to hospital contact
- **Patient Chatbot** — Patient asks questions; AI answers strictly from their own doctor-entered records
- **PDPA Compliance** — Patient data export, anonymization, hospital offboarding export
- **Audit Logs** — Every action logged with actor, role, resource, and timestamp
- **Multi-tenant** — Separate PostgreSQL database per hospital, global registry for routing

---

## Roles

| Role | Access |
|------|--------|
| **Creator Admin** | Registers hospitals, deactivates/reactivates, exports hospital data |
| **Super Admin** | Manages doctors and patients within their hospital, views audit log |
| **Doctor** | Views patients, enters lab results, runs AI diagnosis, manages knowledge base |
| **Patient** | Chat with AI about their own records, view medications/labs/diagnoses |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL 16 + pgvector extension |
| Cache | Redis |
| AI | OpenAI GPT-4o + text-embedding-3-small |
| Frontend | React 18 + Vite + Tailwind CSS |
| Auth | JWT (python-jose) |
| Containerization | Docker + Docker Compose |

---

## Prerequisites

Make sure you have these installed on your machine:

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- [Git](https://git-scm.com/)
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A Gmail account with [App Password](https://myaccount.google.com/apppasswords) (for lab alert emails — optional)

---

## Setup on a New Machine

### 1. Clone the repository

```bash
git clone https://github.com/Mansoor772/medical-ai-system.git
cd medical-ai-system
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
POSTGRES_USER=meduser
POSTGRES_PASSWORD=choose_a_strong_password
SECRET_KEY=generate_with_python_-c_"import secrets; print(secrets.token_hex(32))"
OPENAI_API_KEY=sk-your_openai_key_here

# Optional — for lab alert emails
SMTP_USER=your_gmail@gmail.com
SMTP_PASSWORD=your_gmail_app_password
```

Generate a secure `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start all services

```bash
docker compose up --build -d
```

This starts 4 containers: **postgres**, **redis**, **fastapi**, **frontend**

Wait ~15 seconds, then verify all are running:
```bash
docker compose ps
```

### 4. Create the Creator Admin account (run once only)

```bash
docker compose exec fastapi python scripts/create_creator_admin.py
```

This creates the developer/owner account that can register hospitals.

---

## Accessing the System

| Interface | URL |
|-----------|-----|
| Frontend UI | http://localhost:5173 |
| API + Swagger docs | http://localhost:8000/docs |

---

## First-Time Usage Flow

```
Creator Admin logs in
    └── Creates a hospital (sets Super Admin credentials)
            └── Super Admin logs in
                    ├── Registers doctors
                    └── Registers patients
                            ├── Doctor logs in
                            │       ├── Uploads medical PDFs to knowledge base
                            │       ├── Enters lab results
                            │       ├── Runs AI diagnosis queries
                            │       └── Records clinical decisions
                            └── Patient logs in
                                    ├── Chats with AI about their records
                                    └── Views medications, labs, diagnoses
```

---

## Stopping and Restarting

```bash
# Stop all containers
docker compose down

# Start again (data is preserved in Docker volumes)
docker compose up -d

# Wipe everything including database (fresh start)
docker compose down -v
```

---

## Project Structure

```
medical-ai-system/
├── backend/
│   ├── core/
│   │   ├── config.py          # Environment settings
│   │   ├── database.py        # Multi-tenant DB engine management
│   │   ├── dependencies.py    # JWT auth, role guards, tenant session
│   │   ├── security.py        # Password hashing, JWT creation/decode
│   │   ├── rag.py             # PDF extraction, chunking, embeddings, retrieval
│   │   ├── llm.py             # GPT-4o diagnosis + patient chatbot prompts
│   │   └── email.py           # Gmail SMTP alert emails
│   ├── models/
│   │   ├── global_models.py   # CreatorAdmin, Hospital, StaffLookup
│   │   └── tenant_models.py   # Doctor, Patient, Diagnosis, LabResult, etc.
│   ├── routers/
│   │   ├── auth.py            # Login endpoint
│   │   ├── hospitals.py       # Hospital CRUD (Creator Admin)
│   │   ├── doctors.py         # Doctor management (Super Admin)
│   │   ├── patients.py        # Patient management + medications
│   │   ├── knowledge.py       # PDF upload + knowledge base
│   │   ├── diagnosis.py       # AI diagnosis queries + clinical decisions
│   │   ├── lab.py             # Lab results + alert workflow
│   │   ├── chatbot.py         # Patient chatbot
│   │   └── compliance.py      # PDPA export + anonymization
│   ├── schemas/               # Pydantic request/response models
│   ├── scripts/
│   │   └── create_creator_admin.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/             # LoginPage, CreatorAdmin, SuperAdmin, Doctor, Patient
│   │   ├── components/        # Sidebar, Modal, Spinner, ConfirmDialog
│   │   ├── context/           # AuthContext (JWT storage + role routing)
│   │   └── api/               # Axios client with auth interceptors
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `SECRET_KEY` | Yes | JWT signing key (min 32 chars) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o + embeddings |
| `SMTP_USER` | No | Gmail address for alert emails |
| `SMTP_PASSWORD` | No | Gmail App Password (not your main password) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT expiry (default: 480 = 8 hours) |

---

## Compliance

This system implements **Pakistan PDPA (Personal Data Protection Act)** requirements:
- Consent recorded at patient registration
- Full audit log of all actions (immutable, insert-only)
- Patient data export on request (`GET /compliance/patients/{id}/export`)
- Patient anonymization on request (`POST /compliance/patients/{id}/anonymize`)
- Hospital data offboarding export (`GET /compliance/hospitals/{id}/export`)

---

## Important Notes

- The AI diagnosis is **advisory only** — the treating physician must make all clinical decisions
- Medical records are preserved even after patient anonymization (legal retention requirement)
- Each hospital's data is in a completely separate PostgreSQL database
- Never commit your `.env` file — it contains secrets
