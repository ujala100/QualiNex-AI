# QualiNex-AI — AI-Powered Customer Complaint Management System

An AI-powered customer complaint intake and quality-assurance system designed for pharmaceutical **API (Active Pharmaceutical Ingredient)** and **FDF (Finished Dosage Form)** manufacturing environments.

QualiNex-AI automates complaint intake, document extraction, complaint editing, completeness checking, duplicate detection, risk classification, root-cause recommendation, CAPA suggestions, and complaint summarization through a unified AI workflow.

---

## Overview

Customer complaints in pharmaceutical manufacturing can arrive through emails, documents, PDFs, or unstructured text. Converting these inputs into structured complaint records requires manual data extraction and assessment.

**QualiNex-AI** provides an AI-assisted workflow that converts unstructured complaint information into a structured complaint record and generates preliminary quality-assurance insights.

The system supports:

* Free-text complaint intake
* PDF, DOCX, TXT and EML document extraction
* AI-powered complaint field extraction
* AI-assisted complaint editing
* Complaint completeness analysis
* Duplicate complaint detection
* AI risk classification
* Root-cause recommendations
* CAPA recommendations
* Complaint summarization
* Clarification questions for incomplete complaints
* AI-generated QA insights

---

## Key Features

### 1. AI Complaint Intake

Users can paste complaint text, emails, or messages into the AI Copilot.

The system extracts relevant information such as:

* Complaint source
* Customer name
* Product name
* Product strength/grade
* Batch/lot number
* Manufacturing date
* Expiry date
* Quantity affected
* Complaint type
* Complaint date
* Detailed complaint description
* Initial severity
* Priority

The extracted information is then used to populate the complaint record.

---

### 2. Document Extraction

Users can upload:

* PDF
* DOCX
* TXT
* EML

The document-processing layer extracts the available text and sends it into the same AI complaint-processing workflow.

The system also provides handling for:

* Text-based PDFs
* Empty-password PDFs
* Password-protected PDFs
* Corrupt documents
* Scanned/image-based PDFs through OCR support

Production-grade document intelligence is outside the scope of this project, but the architecture is designed so more advanced document-processing components can be added later.

---

### 3. AI Edit Complaint

Once a complaint exists, users can provide natural-language instructions such as:

> Change the priority to High and update the batch number to AMX-7734.

The AI interprets the instruction and modifies only the fields relevant to the request.

The edit workflow is designed to preserve existing complaint information that was not mentioned by the user.

---

## Unified LangGraph Architecture

One of the main design decisions in QualiNex-AI is that the AI functionality is implemented as a **shared LangGraph workflow** rather than independent scripts.

The three main entry points are:

**Log Complaint**

Free-text complaint → field extraction → validation → AI analysis

**Document Extraction**

Document → text extraction → field extraction → validation → AI analysis

**AI Edit Complaint**

Edit instruction → targeted field modification → validation → AI analysis

All three workflows ultimately use the same downstream reasoning pipeline.

### High-Level Workflow

User Input
↓
Complaint Extraction / AI Edit
↓
Completeness Check
↓
Is sufficient information available?
├── No → Generate clarification question
└── Yes
↓
Duplicate Detection
↓
Root Cause Recommendation
↓
CAPA Recommendation
↓
Risk Classification
↓
Complaint Summary
↓
Compose AI Response
↓
Update Complaint UI + Risk Assessment

This architecture makes the system easier to extend because additional AI capabilities can be implemented as new LangGraph nodes instead of creating separate AI pipelines.

---

## AI Features

### Complaint Completeness Checker

Evaluates whether the complaint contains sufficient information for further processing.

If important information is missing, the system can request clarification instead of blindly generating missing information.

Example:

> "We received a complaint about some tablets looking discolored."

The system can identify missing information such as product name, batch number, customer details, and complaint date.

---

### Duplicate Complaint Detection

Checks the complaint against recent complaint records using information such as:

* Product
* Batch/lot
* Complaint description

The system identifies potential duplicate complaints and provides a duplicate indicator for further review.

This is intended as an AI-assisted screening mechanism rather than a definitive regulatory determination.

---

### AI Risk Classification

The system generates an initial risk assessment containing:

* Risk level
* Risk score
* Rationale
* Regulatory/quality-related flags

For example, a complaint describing a possible adverse event can be flagged for additional review.

The generated classification is intended to support QA review and does not replace qualified regulatory or pharmacovigilance decisions.

---

### Root Cause Recommendation

The system generates preliminary possible root-cause categories based on the complaint information.

Examples include:

* Raw material deviation
* Manufacturing/process deviation
* Packaging issue
* Cross-contamination
* Storage/transport issue
* Equipment-related issue
* Labeling issue
* Other potential quality-system causes

These are recommendations for investigation rather than confirmed root causes.

---

### CAPA Recommendation

The system generates preliminary corrective and preventive action suggestions based on the complaint.

Potential recommendations may include:

* Batch investigation
* Manufacturing record review
* Equipment inspection
* Raw material review
* Additional testing
* Packaging investigation
* Supplier investigation
* Process review
* Preventive-control improvements

Final CAPA decisions remain with the appropriate quality team.

---

### Complaint Summary

The system generates a concise complaint summary that can be used for review and downstream QA workflows.

---

## Technology Stack

### Frontend

* React
* Redux Toolkit
* JavaScript
* HTML/CSS
* Google Inter font

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy

### AI / LLM

* LangGraph
* Groq API
* Gemma 2 9B IT
* Llama 3.3 70B Versatile

### Database

* SQLite for simple local development
* PostgreSQL supported through configuration
* MySQL supported through configuration

### Document Processing

* PDF parsing
* DOCX parsing
* TXT processing
* EML processing
* OCR support for scanned documents using Tesseract

---

## Project Architecture

```
backend/
├── app/
│   ├── agents/
│   │   ├── state.py
│   │   ├── prompts.py
│   │   ├── nodes.py
│   │   └── graph.py
│   │
│   ├── main.py
│   ├── models.py
│   ├── groq_client.py
│   ├── document_parser.py
│   └── config.py
│
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── components/
│   │   ├── LogComplaintForm.jsx
│   │   ├── AICopilotPanel.jsx
│   │   └── RiskAssessmentPanel.jsx
│   │
│   ├── store/
│   │   ├── complaintSlice.js
│   │   └── copilotSlice.js
│   │
│   └── api/
│       └── api.js
│
├── package.json
└── public/
```

---

## Backend AI Architecture

The main AI workflow is implemented in:

`backend/app/agents/graph.py`

The LangGraph state is defined in:

`backend/app/agents/state.py`

AI processing nodes are implemented in:

`backend/app/agents/nodes.py`

Prompt definitions and domain-oriented instructions are maintained in:

`backend/app/agents/prompts.py`

The architecture separates:

* State
* Prompts
* AI processing nodes
* Graph orchestration
* API routes
* Database models
* Document parsing
* LLM communication

This separation makes the system easier to test, debug, and extend.

---

## API Endpoints

### Log Complaint

`POST /api/copilot/log-complaint`

Accepts complaint text and processes it through the AI workflow.

### Document Extraction

`POST /api/copilot/extract-document`

Accepts supported complaint documents and extracts/processes their contents.

### AI Edit Complaint

`POST /api/copilot/edit-complaint`

Accepts a natural-language editing instruction and updates the relevant complaint fields.

The frontend uses the returned structured result to update the complaint state and AI assessment.

---

## Frontend State Management

Redux Toolkit is used as the application's state-management layer.

The main complaint state is handled through:

`complaintSlice.js`

AI-generated complaint results are applied through a centralized update mechanism so that extracted fields and AI assessment results remain synchronized.

The Copilot interaction and progress state are handled separately through:

`copilotSlice.js`

This keeps UI interaction state separate from complaint/business data.

---

## AI Response Flow

A typical complaint-processing request follows this flow:

**Frontend**

User enters complaint text or uploads a document.

↓

**React + Redux**

The frontend sends the request to FastAPI.

↓

**FastAPI**

The appropriate endpoint validates and processes the request.

↓

**Document Parser / AI Extraction**

If required, the document is converted into usable text.

↓

**LangGraph**

The complaint enters the appropriate graph node.

↓

**LLM**

Groq-hosted models process extraction, reasoning, classification, and recommendations.

↓

**Graph Nodes**

The system performs:

* Completeness checking
* Duplicate detection
* Root-cause recommendation
* CAPA recommendation
* Risk classification
* Summary generation

↓

**FastAPI Response**

A structured result is returned to the frontend.

↓

**Redux**

Complaint fields and AI assessment state are updated.

↓

**UI**

The complaint form and AI Risk Assessment panel reflect the generated result.

---

## Offline / Fallback Mode

The application includes a fallback mechanism when a Groq API key is unavailable.

Instead of crashing, selected processing functions can use deterministic heuristic logic based on:

* Regular expressions
* Keyword matching
* Rule-based extraction

The API can indicate when processing is operating in offline mode.

This makes the application easier to demonstrate locally and provides a basic resilience mechanism when external LLM services are unavailable.

---

## Database Configuration

SQLite can be used for zero-configuration local development.

The database can be changed through the `DATABASE_URL` environment variable.

Example configuration:

`DATABASE_URL=sqlite:///./complaints.db`

For PostgreSQL or MySQL deployments, the corresponding SQLAlchemy database URL can be configured through the environment.

---

## Installation

### Backend

```
cd backend

python -m venv venv
```

Activate the virtual environment on Windows:

```
venv\Scripts\activate
```

Install dependencies:

```
pip install -r requirements.txt
```

Create the environment file:

```
copy .env.example .env
```

Add the required Groq API key to `.env`.

Start the backend:

```
uvicorn app.main:app --reload --port 8000
```

---

### Frontend

Open another terminal:

```
cd frontend
```

Install dependencies:

```
npm install
```

Start the frontend:

```
npm start
```

Open:

`http://localhost:3000`

---

## Environment Variables

Create a `.env` file in the backend directory.

Example:

```
GROQ_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./complaints.db
```

Never commit the actual `.env` file or API keys to GitHub.

Use `.env.example` to document required environment variables without exposing secrets.

---

## Example Workflow

### Example 1 — Complete Complaint

Input:

> Customer service received a call from a hospital pharmacist reporting a severe allergic reaction after administering Amoxicillin 500mg Tablets, batch AMX-7734, manufactured 2025-05-10, expiry 2027-05-10. Approximately 40 tablets from the batch are affected.

The system can extract:

* Customer/source information
* Product
* Strength
* Batch
* Manufacturing date
* Expiry date
* Quantity affected
* Complaint description

The complaint can then proceed through completeness checking and the downstream AI assessment workflow.

---

### Example 2 — Incomplete Complaint

Input:

> We received an email about some tablets looking discolored.

The system can identify missing information and generate a clarification request rather than inventing unknown complaint details.

---

### Example 3 — AI Complaint Editing

Existing complaint:

> Priority: Low

User instruction:

> Change the priority to High.

The AI Edit workflow updates the requested field while preserving the other complaint information.

---

## Error Handling and Resilience

The system is designed to handle common failure conditions including:

* Invalid document formats
* Corrupt documents
* Password-protected PDFs
* Missing API credentials
* Missing complaint information
* LLM response parsing failures
* Unsupported uploads
* Empty documents
* OCR-related failures

The objective is to provide useful feedback instead of allowing individual failures to crash the entire application.

---

## Security Considerations

This project is designed as a development/demo application and is **not intended to be used directly with real patient, customer, or regulated pharmaceutical data without additional security controls**.

Important production considerations would include:

* Authentication and authorization
* Role-based access control
* Encryption
* Audit logging
* Secrets management
* Data retention policies
* PII protection
* PHI handling where applicable
* Regulatory compliance
* Model-output validation
* Human approval workflows
* Secure document storage
* Database access controls

API keys and credentials should always be stored in environment variables or a dedicated secrets-management system.

---

## Limitations

* AI-generated risk classifications are preliminary recommendations.
* Root-cause suggestions do not represent confirmed investigation findings.
* CAPA recommendations require qualified human review.
* Duplicate detection is an AI-assisted screening mechanism.
* OCR quality depends on document quality and the installed OCR engine.
* LLM outputs can contain errors or incomplete information.
* Production deployment would require stronger security, authentication, auditability, validation, monitoring, and regulatory controls.

---

## Future Improvements

Potential future extensions include:

* Role-based authentication
* QA approval workflow
* Pharmacovigilance integration
* Advanced semantic duplicate detection
* Vector database for historical complaint retrieval
* Retrieval-Augmented Generation (RAG)
* Complaint trend analytics
* Batch-level complaint clustering
* Automated escalation workflows
* Advanced OCR/document vision models
* Human-in-the-loop approval
* Full audit trail
* Model evaluation framework
* LLM observability and tracing
* Production PostgreSQL deployment
* Docker-based deployment
* CI/CD pipeline
* Automated testing
* Model and prompt versioning
* Monitoring and alerting

---
## Project Status

**Status: Functional AI application / portfolio project**

The current implementation focuses on demonstrating an end-to-end AI-powered complaint-management workflow, including frontend interaction, backend APIs, LangGraph orchestration, LLM processing, document extraction, database integration, and AI-generated QA assistance.

It should not be considered a validated pharmaceutical QMS or production regulatory system.

---

## License

This project is intended for educational, portfolio, and demonstration purposes.
