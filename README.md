# Helix AI

**Agentic AI Healthcare Companion**
IBM SkillsBuild Project

---

## Overview

Helix AI is an AI-powered healthcare companion for chronic disease monitoring and personalised health guidance. It combines symptom assessment, vitals tracking, medication management, and AI-generated health reports.

The system supports three chronic conditions:
- **Diabetes**
- **Hypertension**
- **Heart Disease**

**Current state:** Milestone 1 — Project Foundation (authentication, profile, dashboard shell)

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask · SQLAlchemy |
| Database | SQLite (development) |
| Auth | Flask-Login · Flask-Bcrypt |
| Frontend | Bootstrap 5 · HTML · CSS · JavaScript |
| AI (future) | IBM watsonx.ai · IBM Granite · RAG · watsonx Orchestrate |

---

## Folder Structure

```
Helix_AI/
│
├── app.py                         # Application factory and entry point
├── config.py                      # Dev / Prod configuration classes
├── extensions.py                  # SQLAlchemy, LoginManager, Bcrypt instances
├── requirements.txt
├── database.db                    # SQLite database (auto-created, gitignored)
├── .env                           # Environment secrets (gitignored)
├── .env.example                   # Template for required environment variables
│
├── models/
│   ├── __init__.py                # Model discovery for Flask-Migrate
│   ├── user.py                    # User authentication model
│   └── user_profile.py            # Health profile model
│
├── routes/
│   ├── auth.py                    # Register, login, logout
│   ├── dashboard.py               # Health Command Center
│   ├── profile.py                 # Profile view and edit
│   └── modules.py                 # Placeholder module pages
│
├── services/                      # Service layer (AI integrations added per milestone)
│   ├── granite_service.py         # IBM Granite LLM — Milestone 4
│   ├── rag_service.py             # RAG knowledge retrieval — Milestone 5
│   └── orchestrator_service.py    # watsonx Orchestrate routing — Milestone 6
│
├── agents/                        # AI agent modules (implemented per milestone)
│   └── __init__.py                # Agent package with future roadmap documented
│
├── templates/
│   ├── base.html                  # Bootstrap 5 layout with sidebar
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── dashboard/
│   │   └── index.html             # Health Command Center
│   ├── profile/
│   │   ├── view.html
│   │   └── edit.html
│   └── modules/
│       └── placeholder.html       # Shared placeholder for all future modules
│
├── static/
│   ├── css/helix.css              # Custom IBM-style healthcare theme
│   ├── js/helix.js                # Sidebar, charts, AJAX helpers
│   └── images/
│
└── utils/
    └── helpers.py                 # Shared utility functions (BMI, date formatting)
```

---

## Setup Instructions

### Prerequisites
- Python 3.10 or higher
- pip

### 1. Clone or extract the project

```bash
cd Helix_AI
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the environment file

Copy `.env.example` to `.env` (no IBM credentials are needed for Milestone 1):

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`:

```
SECRET_KEY=your-random-secret-key-here
```

### 5. Run the application

```bash
python app.py
```

The application will be available at: **http://localhost:5000**

The SQLite database (`database.db`) is created automatically on first run.

---

## Environment Variables (`.env.example`)

```
# Flask
SECRET_KEY=

# Future Milestone 4 — IBM watsonx.ai / Granite
# WATSONX_API_KEY=
# WATSONX_PROJECT_ID=
# WATSONX_URL=https://us-south.ml.cloud.ibm.com
# GRANITE_MODEL_ID=ibm/granite-13b-chat-v2

# Future Milestone 5 — RAG
# (no additional variables needed beyond watsonx credentials above)

# Future Milestone 6 — watsonx Orchestrate
# ORCHESTRATE_API_KEY=
# ORCHESTRATE_INSTANCE_URL=
```

---

## Running Locally — First Use

1. Open **http://localhost:5000** in your browser
2. Click **Create Account** and register
3. Complete your **Health Profile** (you will be redirected automatically)
4. Explore the **Health Command Center** dashboard
5. Click any module card to see the placeholder page for that milestone

---

## Milestone Roadmap

| Milestone | Description | IBM APIs Required |
|---|---|---|
| **M1 ✅** | Project Foundation — Auth, Profile, Dashboard | None |
| M2 | Health Command Center — Timeline, Health Score shell | None |
| M3 | AI Clinical Assessment + Chronic Disease Monitoring | None (placeholder AI) |
| M4 | IBM Granite Integration — live AI responses | IBM watsonx.ai |
| M5 | RAG Knowledge Base — trusted medical sources | IBM watsonx.ai (embeddings) |
| M6 | watsonx Orchestrate — multi-agent chat routing | IBM watsonx Orchestrate |
| M7 | AI Health Reports + Final Testing | All of the above |

---

## Future AI Architecture

When IBM integrations are added, Helix AI will use a multi-agent system:

```
User → AI Health Companion Chat
           ↓
   watsonx Orchestrate (Health Orchestrator)
           ↓ routes by intent
┌──────────────────────────────────────────┐
│  Symptom Assessment Agent       (M3/M4)  │
│  Chronic Disease Agent          (M3/M4)  │
│  Risk Prediction Agent          (M4)     │
│  Treatment Companion Agent      (M4/M5)  │
│  Lifestyle Recommendation Agent (M5)     │
│  RAG Knowledge Agent            (M5)     │
│  Health Report Generator        (M7)     │
└──────────────────────────────────────────┘
           ↓
   IBM Granite LLM
   (grounded with RAG medical knowledge)
```

---

## Medical Disclaimer

Helix AI is an educational IBM SkillsBuild project. It is not a medical device and does not provide medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional for medical guidance.
