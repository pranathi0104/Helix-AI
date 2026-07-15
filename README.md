# Helix AI

**Agentic AI Healthcare Companion**
IBM SkillsBuild Project

---

## Overview

Helix AI is an advanced, AI-powered healthcare companion designed for chronic disease monitoring and personalized health guidance. Driven by a multi-agent AI architecture, the system provides real-time symptom assessment, comprehensive vitals tracking, personalized lifestyle recommendations, treatment and medication support, and detailed AI-generated health reports.

The platform provides robust monitoring support for chronic conditions such as:
- **Diabetes**
- **Hypertension**
- **Heart Disease**

## Problem Statement

Managing chronic diseases requires continuous monitoring, personalized guidance, and timely intervention. Traditional healthcare systems often leave patients isolated between clinic visits, lacking immediate, trustworthy answers to health concerns. This disconnect can lead to poor medication adherence, unrecognized symptom escalation, and anxiety.

## Proposed Solution

Helix AI bridges this gap by offering a continuous, intelligent healthcare companion. Leveraging state-of-the-art Generative AI and a multi-agent architecture, Helix AI delivers accurate, personalized insights based on a patient's real-time vitals and historical health profile. It securely combines a trusted medical knowledge base with empathetic AI to support patients in managing their health effectively.

---

## Key Features

- **Agentic AI Architecture**: Powered by IBM watsonx Orchestrate and Granite LLM.
- **RAG Medical Knowledge Base**: Grounded responses using trusted clinical guidelines.
- **Deterministic Risk Analysis**: Real-time evaluation of logged vitals to classify health risk accurately.
- **Personalized Lifestyle Recommendations**: Actionable advice tailored to current health data.
- **Treatment and Medication Support**: Tracking adherence and providing medication insights.
- **AI Health Reports**: Comprehensive, narrative-driven summaries of a user's health status.

---

## Watsonx Orchestrate Multi-Agent System

Helix AI operates on a sophisticated multi-agent system managed by IBM watsonx Orchestrate. When a user interacts with the chat assistant, a Supervisor Agent dynamically routes the request to the most appropriate specialized agent:

- **Supervisor Agent**: The central orchestration layer that evaluates user intent and delegates tasks.
- **Clinical Assessment Agent**: Evaluates symptoms and provides safe, grounded clinical guidance without diagnosing.
- **Chronic Monitoring Agent**: Analyzes recorded vitals and monitors for trends or abnormalities.
- **Lifestyle Agent**: Generates contextual, personalized lifestyle and wellness recommendations based on the patient's profile and current vitals.
- **Treatment Agent**: Answers questions regarding current active medications and tracks treatment adherence.
- **Health Report Agent**: Synthesizes profile data, risk factors, and vitals into a cohesive, easily digestible health report snapshot.

All agent responses are strictly grounded using **IBM watsonx.ai and the Granite LLM**, integrated with a robust **RAG (Retrieval-Augmented Generation)** medical knowledge base to ensure reliability and safety.

---

## High-Level System Workflow

```
User → Helix AI Chat Assistant
           ↓
   watsonx Orchestrate (Supervisor Agent)
           ↓ routes by intent
┌──────────────────────────────────────────┐
│  Clinical Assessment Agent               │
│  Chronic Monitoring Agent                │
│  Lifestyle Agent                         │
│  Treatment Agent                         │
│  Health Report Agent                     │
└──────────────────────────────────────────┘
           ↓
   IBM Granite LLM (via watsonx.ai)
   (grounded with RAG medical knowledge)
           ↓
   Secure Render Backend API (Vitals, Risk, Profile)
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask · SQLAlchemy |
| Database | SQLite (Local) / PostgreSQL (Deployed) |
| Auth | Flask-Login · Flask-Bcrypt |
| Frontend | Bootstrap 5 · HTML · CSS · Vanilla JavaScript |
| AI Foundation | IBM watsonx.ai · IBM Granite |
| Orchestration | IBM watsonx Orchestrate |
| Infrastructure | Render |

---

## Current Project Structure

```
Helix_AI/
│
├── app.py                         # Application factory and entry point
├── config.py                      # Development and Production configuration
├── extensions.py                  # SQLAlchemy, LoginManager, Bcrypt instances
├── requirements.txt
├── .env.example                   # Template for environment variables
│
├── models/                        # Database models (User, Profile, Vitals, Reports, etc.)
├── routes/                        # Blueprints for Auth, Dashboard, Chat, and API endpoints
├── services/                      # Core logic for Report Generation, Risk Analysis, RAG, and LLM
├── orchestrate/                   # OpenAPI definitions for Watsonx Orchestrate tools
├── scripts/                       # Deployment and Orchestrate setup scripts
├── rag_docs/                      # Trusted medical knowledge base text files
│
├── templates/                     # Jinja2 HTML Templates (Auth, Dashboard, Profile, Reports)
└── static/                        # CSS, JS, and image assets
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

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` to include your configuration placeholders. **Do not expose real API keys or secrets in version control.**

```
SECRET_KEY=your-secret-key
IBM_API_KEY=your-ibm-api-key
WATSONX_PROJECT_ID=your-watsonx-project-id
WATSONX_URL=your-watsonx-url
GRANITE_MODEL_ID=your-granite-model-id
ORCHESTRATE_API_KEY=your-orchestrate-api-key
ORCHESTRATE_INSTANCE_URL=your-orchestrate-url
```

### 5. Run the Application Locally

```bash
python app.py
```

The application will be available at: **http://localhost:5000**

---

## Deployment Information: Render

Helix AI is configured for deployment on **Render**. 
- The backend API securely serves Watsonx Orchestrate tools.
- PostgreSQL can be configured for production via the `DATABASE_URL` environment variable.
- Ensure that the Watsonx Orchestrate OpenAPI server URL is updated to the live Render endpoint when deploying.

---

## Future Scope

While the current system represents a complete foundational agentic architecture, future enhancements may include:
- Integration with wearable devices for automated continuous vitals logging.
- Advanced predictive analytics for early detection of chronic disease progression.
- Support for a wider range of chronic conditions and specialized treatment agents.
- Multilingual support for global accessibility.

---

## Medical Disclaimer

Helix AI is an educational IBM SkillsBuild project. It is **not** a medical device. Helix AI **does not** diagnose diseases, and it does not provide medical advice, definitive diagnosis, or treatment. Always consult a qualified healthcare professional or emergency services for medical guidance.
