# NexusTiq24 Hackathon — Problem Statement PS01: Healthcare Patient Intake Triage Assistant.

** Health Care — Patient Intake Triage Assistant**

An AI-assisted intake tool for healthcare front-desk / triage staff. It has a strict, non-negotiable
boundary: **it never diagnoses a disease.** It only collects information, asks relevant follow-up
questions, applies deterministic triage rules, recommends an urgency level and department, explains
its reasoning with citations to the exact rule(s) used, and escalates any case it cannot classify
safely.

---

## 1. Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ (only needed once, to build the frontend — not required to run the app afterwards)

### Steps

```bash
# 1. Clone / unzip the project, then from the project root:
pip install -r requirements.txt

# 2. Build the frontend (one-time; the built assets are committed to frontend/dist,
#    so you can skip this step if dist/ is already present)
cd frontend
npm install
npm run build
cd ..

# 3. Copy the environment template and (optionally) add your Gemini API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=... if you have one.
# The app runs fully offline with deterministic fallbacks if you leave it blank.

# 4. (Optional) generate 100 sample cases so the dashboard has data immediately
python scripts/generate_sample_data.py
```

## 2. Running

```bash
python app.py
```

The app starts on **http://localhost:8000** — API and frontend are served from the same FastAPI
process, so no separate frontend dev server is required.

## 3. Environment variables

| Variable          | Default            | Description                                                                 |
|--------------------|--------------------|-------------------------------------------------------------------------------|
| `GEMINI_API_KEY`   | *(empty)*          | Google Gemini API key. If unset, chat phrasing and RAG embeddings fall back to deterministic offline logic — the app remains fully functional. |
| `DATABASE_PATH`    | `data/triage.db`   | SQLite database file location.                                                |
| `HOST`             | `0.0.0.0`          | Bind host.                                                                    |
| `PORT`             | `8000`             | Bind port.                                                                    |

## 4. Architecture

```
                       ┌─────────────────────────┐
                       │   React SPA (frontend)  │
                       │  Dashboard / Intake /    │
                       │  History / Reports /     │
                       │  Analytics               │
                       └────────────┬─────────────┘
                                    │  fetch /api/*
                                    ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                        FastAPI (app.py)                      │
 │  ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐ │
 │  │ symptom_      │──▶│ TriageEngine  │──▶│  case_service     │ │
 │  │ extractor.py  │   │ (deterministic│   │  (orchestration,  │ │
 │  │ (keyword/     │   │  rules.json)  │   │   persistence)    │ │
 │  │ regex, no LLM)│   └───────────────┘   └─────────┬────────┘ │
 │  └──────────────┘                                  │          │
 │  ┌──────────────┐   ┌───────────────┐               │         │
 │  │ Gemini chat   │   │ FAISS RAG      │◀─────────────┘         │
 │  │ service       │   │ (guideline     │                       │
 │  │ (phrasing     │   │  retrieval)    │                       │
 │  │  only)        │   └───────────────┘                       │
 │  └──────────────┘                                             │
 │  ┌──────────────┐                                              │
 │  │ PDF/JSON      │                                              │
 │  │ report export │                                              │
 │  └──────────────┘                                              │
 └──────────────────────────────┬─────────────────────────────────┘
                                 ▼
                        SQLite (data/triage.db)
             patients · cases · conversations · triage_results · reports
```

**Key design decision:** the LLM (Gemini) is used *only* to phrase acknowledgements, follow-up
questions, and plain-language explanations of a result that has already been decided. The urgency
level, department, and escalation decision always come from the deterministic rule engine in
`src/triage/engine.py`, which evaluates boolean flags against `data/triage_rules/rules.json`. This
separation means every recommendation is reproducible and auditable, and the system can run (in a
reduced but fully functional mode) with zero external API calls.

## 5. Folder structure

```
app.py                        # entry point — python app.py
requirements.txt
.env.example
src/
├── api/routes.py              # /chat /triage /cases /reports /analytics /export/*
├── services/
│   ├── gemini_service.py      # LLM phrasing only, never decides triage
│   └── pdf_service.py         # reportlab PDF + JSON report generation
├── triage/
│   ├── symptom_extractor.py   # deterministic keyword/regex flag extraction
│   ├── engine.py               # rule evaluation against rules.json
│   └── case_service.py         # orchestration + SQLite persistence
├── rag/vector_store.py         # FAISS index over medical_guidelines/, Gemini or offline embeddings
├── models/schemas.py           # Pydantic request/response models
├── database/db.py              # SQLite schema + connection helpers
└── utils/logger.py
frontend/                       # React + Tailwind SPA, built into frontend/dist
data/
├── triage_rules/rules.json     # the deterministic rule set (E1, E2, F1, F2, I1, A1, ...)
├── medical_guidelines/*.md     # source documents for the RAG system
└── sample_cases/sample_cases.json  # generated by scripts/generate_sample_data.py
scripts/generate_sample_data.py # creates 100 synthetic cases
```

## 6. API endpoints

| Method | Path             | Description                                          |
|--------|------------------|-------------------------------------------------------|
| POST   | `/api/chat`      | Send a patient message, get follow-ups or triage result |
| POST   | `/api/triage`    | Re-run triage evaluation for an existing case          |
| GET    | `/api/cases`     | List cases                                             |
| GET    | `/api/cases/{id}`| Full case detail (conversation + triage)               |
| GET    | `/api/reports`   | List generated report exports                          |
| GET    | `/api/analytics` | Aggregate counts and distributions                     |
| POST   | `/api/export/pdf`| Generate + download a PDF triage report                |
| POST   | `/api/export/json`| Generate + download a JSON triage report              |

## 7. Demo scenarios

- **Normal:** "I have had a fever for 2 days." → follow-up questions asked; once answered with no
  red flags, resolves to **STANDARD**, General Medicine (rule S1).
- **Urgent:** "I have a fever of 104°F." → **URGENT**, rule **F1** triggered.
- **Emergency:** "I have chest pain and difficulty breathing." → **EMERGENCY** immediately, rule
  **E1** triggered (emergency-level rules bypass waiting on follow-ups).
- **Uncertain:** "I don't feel well." → assistant asks clarifying questions; if no rule can be
  matched, the case returns *"Unable to determine safely. Human review required."* and is escalated.

## 8. Engineering notes

- All triage decisions are deterministic and rule-cited (see `src/triage/engine.py`); the rule
  engine never guesses — if no rule matches, the case is escalated rather than assigned a level.
- Symptom extraction includes negation handling ("no chest pain" is not read as chest pain present).
- RAG and chat gracefully degrade to offline logic without a Gemini API key, so the whole app is
  demoable without any external network access.
- Logging is centralized in `src/utils/logger.py` (`nexustiq24.*` loggers).

## 9. Screenshots

<img width="1364" height="681" alt="3" src="https://github.com/user-attachments/assets/1a419272-7866-4658-bf98-0bdc17541388" />
<img width="1366" height="768" alt="1" src="https://github.com/user-attachments/assets/2724f4c0-ef02-4332-b11e-6dbe32aa2049" />
<img width="1366" height="768" alt="2" src="https://github.com/user-attachments/assets/5ecd15e2-af9a-40dd-854c-4f9bc314b795" />

<img width="1366" height="768" alt="4" src="https://github.com/user-attachments/assets/1bbfb6f9-b94d-4ba4-99bc-183990045168" />

## 10. Demo video

https://drive.google.com/file/d/1mS9FG6OwSsFQoNqoQ3LaRJ3uOgInarcS/view?usp=sharing
