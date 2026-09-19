# AIVOA — AI-Powered Customer Complaint Management System

Pharmaceutical (API/FDF) manufacturing QMS — Customer Complaint intake module.
Built for the AIVOA Round 1 AI Product Engineer (Interns) assignment.

## Why this is one system, not three bolted-on features

The three mandatory AI tools — **Log Complaint**, **AI Edit Complaint**, and
**Document Extraction** — all run through **one shared LangGraph pipeline**
(`backend/app/agents/graph.py`). They differ only in how they *enter* the
graph:

```
Log Complaint tool  (free text)        ──┐
Document Extraction (PDF/DOCX/TXT/EML) ──┼──> extract_fields ──┐
AI Edit Complaint tool (edit instruction)─────> apply_edit ────┤
                                                                ▼
                                              completeness_check
                                          (missing required fields?)
                                          ───────┬────────────────
                                         yes ↓            ↓ no
                                  ask clarifying    duplicate_check
                                  question, STOP           ↓
                                                       root_cause
                                                            ↓
                                                          capa
                                                            ↓
                                                explanation risk_classification
                                                            ↓
                                                         summary
                                                            ↓
                                                    compose_message (→ chat)
```

This is the actual point of using an agent **framework** instead of three
separate scripts: one inspectable, extensible pipeline; a real conditional
branch (skip the expensive reasoning nodes if the record isn't complete
enough yet); and adding a new "bonus" AI feature is one new node + one new
edge, not a rewrite.

The **Log Customer Complaint form on the left is 100% AI-populated** — every
input in `LogComplaintForm.jsx` is hard-`disabled`, with no `onChange`
handler at all. The *only* way its Redux state changes is
`applyAIResult(...)`, dispatched after a response comes back from one of the
three tools. There is no code path for a human to type directly into that
form — this was a hard requirement, not a UI style choice.

## The 3 mandatory AI tools, mapped to code

| Tool | Frontend trigger | Backend endpoint | Graph entry node |
|---|---|---|---|
| **1. Log Complaint** | Paste text / type in chat before a complaint exists | `POST /api/copilot/log-complaint` | `extract_fields` |
| **2. Document Extraction** | Drag & drop / browse a PDF, DOCX, TXT, or EML | `POST /api/copilot/extract-document` | `extract_fields` (after `document_parser.py` pulls raw text) |
| **3. AI Edit Complaint** | Chat message after a complaint already exists | `POST /api/copilot/edit-complaint` | `apply_edit` (LLM patches only what the instruction mentions; the prompt explicitly forbids touching anything else) |

All three return the same `CopilotResult` shape, which the frontend applies
in one Redux action — that's what lets the AI Risk Assessment panel,
completeness score, duplicate flag, root cause, and CAPA suggestions update
consistently no matter which of the three tools produced the update.

## Bonus AI features (all implemented as graph nodes)

- **Complaint Completeness Checker** — `completeness_check_node`, also drives
  the conditional "ask a clarifying question instead of guessing" branch.
- **Duplicate Complaint Detection** — `duplicate_check_node`, compares
  against the last 25 complaints on file (product + batch/lot + description).
- **Root Cause Recommendation** — `root_cause_node`, GMP-style categories
  (raw material deviation, process deviation, cross-contamination, etc.)
- **CAPA Recommendation** — `capa_node`, preliminary corrective/preventive
  actions for the QA reviewer to refine.
- **AI Risk Classification** — `risk_classification_node`, produces
  risk level, 0–100 score, rationale, and regulatory flags (e.g. "possible
  adverse event — notify Pharmacovigilance").
- **Complaint Summary** — `summary_node`, a QA-dashboard-ready one-liner.

## Tech stack (per the mandatory list)

- **Frontend:** React + Redux (Redux Toolkit) — no other state library.
- **Backend:** Python + FastAPI.
- **AI Agent Framework:** LangGraph (`backend/app/agents/graph.py`).
- **LLMs:** Groq — `gemma2-9b-it` for fast field extraction,
  `llama-3.3-70b-versatile` for reasoning (risk/root-cause/CAPA/duplicate/edit).
- **Database:** SQLAlchemy, defaults to SQLite for zero-setup local
  grading; one env var (`DATABASE_URL`) switches to Postgres or MySQL.
- **Font:** Google Inter (loaded in `frontend/public/index.html`).

## Running it locally

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your real GROQ_API_KEY in .env
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start                   # runs on http://localhost:3000, proxies API calls to :8000
```

Then open http://localhost:3000, drop in a sample complaint PDF/email or
paste text, and watch the form + AI Risk Assessment populate.

### PDF extraction and scanned documents

The API handles normal text PDFs, empty-password PDFs, password-protected-PDF
feedback, corrupt-file feedback, and scanned/image-only PDFs through OCR. For
OCR support, install the backend requirements and the native [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
executable on the machine running FastAPI. Text PDFs do not require Tesseract.

### Running without a Groq key
If `GROQ_API_KEY` is unset, every node falls back to a small deterministic
heuristic (regex/keyword based) instead of crashing — see `offline_mode`
in the API response and `_offline_*` functions in `backend/app/agents/nodes.py`.
This means the whole app is demoable end-to-end even with no API key, and
it's a deliberate resilience decision worth calling out in the interview,
not a hidden shortcut.

## Suggested demo video structure (per the "Deliverables" requirement)

1. **Tool 1 — Log Complaint:** paste a realistic complaint email → show the
   left form and AI Risk Assessment panel populate live.
2. **Tool 2 — Document Extraction:** drag a sample complaint PDF → same
   pipeline, different entry point.
3. **Tool 3 — AI Edit Complaint:** type "change the priority to High and
   update the batch number to X" → show only those fields change, everything
   else is preserved.
4. **Code walkthrough:** frontend `AICopilotPanel.jsx` → API call →
   `main.py` endpoint → `graph.py` routing → each node in `nodes.py` →
   response → `complaintSlice.applyAIResult` → form + risk panel re-render.
5. **Bonus features:** trigger a duplicate (log the same batch/product
   twice) and an incomplete complaint (missing product name) to show the
   clarifying-question branch.

## Sample test complaints (for your demo video / interview)

Paste these into the "Paste Complaint Text / Email" box to exercise
different paths:

**Complete, high-severity (full pipeline runs):**
> Customer service received a call on 2026-03-02 from a hospital pharmacist
> reporting a severe allergic reaction after administering Amoxicillin
> 500mg Tablets, batch AMX-7734, manufactured 2025-05-10, expiry
> 2027-05-10. Approximately 40 tablets from the batch are affected.

**Incomplete (triggers the clarifying-question branch):**
> We got an email about some tablets looking discolored.

**Duplicate test:** log the complaint above twice — the second run should
flag `is_possible_duplicate: true`.

## Project structure

```
backend/
  app/
    agents/
      state.py      # LangGraph state schema
      prompts.py     # all system prompts (domain knowledge lives here)
      nodes.py       # 9 graph nodes + offline fallbacks
      graph.py        # graph wiring / conditional routing
    main.py           # FastAPI routes (the 3 tools + CRUD)
    models.py          # Pydantic schemas + SQLAlchemy ORM model
    groq_client.py     # Groq API wrapper (JSON-mode + robust parsing)
    document_parser.py # PDF/DOCX/TXT/EML -> plain text
    config.py            # env-driven configuration
frontend/
  src/
    components/
      LogComplaintForm.jsx    # AI-only, fully disabled inputs
      AICopilotPanel.jsx        # upload / paste / chat -- routes to the 3 tools
      RiskAssessmentPanel.jsx    # renders all AI reasoning outputs
    store/
      complaintSlice.js          # form + AI results; applyAIResult is the only writer
      copilotSlice.js              # chat/progress UI state
    api/api.js                     # fetch wrappers for the 3 endpoints + CRUD
```
#   Q u a l i N e x - A I  
 