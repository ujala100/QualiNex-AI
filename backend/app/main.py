"""
FastAPI entrypoint.

Exposes exactly the three mandatory AI tools, each calling into the same
LangGraph pipeline (see agents/graph.py):

  POST /api/copilot/log-complaint       -> "Log Complaint" tool (free text)
  POST /api/copilot/extract-document    -> "Document Extraction" tool (file upload)
  POST /api/copilot/edit-complaint      -> "AI Edit Complaint" tool

Plus supporting CRUD so the left-hand form has somewhere to persist to,
and so duplicate-detection has real history to check against:

  POST   /api/complaints                -> save/update a complaint record
  GET    /api/complaints                -> list complaints (for duplicate check + history)
  GET    /api/complaints/{id}           -> fetch one
  DELETE /api/complaints/{id}           -> delete (maps to the form's "Reset" if desired)
"""
import logging
from typing import List, Optional

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import Base, engine, get_db
from . import models
from .config import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_MB
from .document_parser import DocumentExtractionError, extract_text_from_bytes
from .agents.graph import complaint_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aivoa.main")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIVOA AI Complaint Copilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo/dev only -- lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recent_complaints_for_dup_check(db: Session, limit: int = 25) -> List[dict]:
    rows = db.query(models.Complaint).order_by(desc(models.Complaint.id)).limit(limit).all()
    return [
        {
            "id": r.id,
            "product_name": r.product_name,
            "batch_lot_number": r.batch_lot_number,
            "complaint_type": r.complaint_type,
            "detailed_complaint_description": r.detailed_complaint_description,
        }
        for r in rows
    ]


def _graph_result_to_response(result: dict, complaint_id: Optional[int] = None) -> models.CopilotResult:
    return models.CopilotResult(
        form_data=models.ComplaintFormData(**result.get("form_data", {})),
        risk_assessment=models.RiskAssessment(**result.get("risk_assessment", {})),
        completeness=models.CompletenessCheck(**result.get("completeness", {})),
        duplicate_check=models.DuplicateCheck(**result.get("duplicate_check", {})),
        root_cause=models.RootCauseSuggestion(**result.get("root_cause", {})),
        capa=models.CapaRecommendation(**result.get("capa", {})),
        summary=result.get("summary"),
        assistant_message=result.get("assistant_message", ""),
        needs_clarification=bool(result.get("needs_clarification", False)),
        complaint_id=complaint_id,
    )


# ---------------------------------------------------------------------------
# Tool 1: Log Complaint (AI Complaint Intake Assistant - free text entry)
# ---------------------------------------------------------------------------

@app.post("/api/copilot/log-complaint", response_model=models.CopilotResult)
def log_complaint(req: models.LogComplaintRequest, db: Session = Depends(get_db)):
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Please provide complaint text.")

    initial_state = {
        "mode": "log",
        "raw_text": req.text,
        "candidate_complaints": _recent_complaints_for_dup_check(db),
    }
    result = complaint_graph.invoke(initial_state)
    return _graph_result_to_response(result)


# ---------------------------------------------------------------------------
# Tool 2: Document Extraction (drag & drop PDF/DOCX/TXT/EML)
# ---------------------------------------------------------------------------

@app.post("/api/copilot/extract-document", response_model=models.CopilotResult)
async def extract_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "Please choose a document to upload.")
    ext = "." + file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_UPLOAD_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {MAX_UPLOAD_MB}MB limit.")

    try:
        text = extract_text_from_bytes(file.filename, content)
    except DocumentExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not text.strip():
        raise HTTPException(422, "Could not extract any text from the uploaded document.")

    initial_state = {
        "mode": "document",
        "raw_text": text,
        "candidate_complaints": _recent_complaints_for_dup_check(db),
    }
    result = complaint_graph.invoke(initial_state)
    return _graph_result_to_response(result)


# ---------------------------------------------------------------------------
# Tool 3: AI Edit Complaint (chat-driven edits, preserves untouched fields)
# ---------------------------------------------------------------------------

@app.post("/api/copilot/edit-complaint", response_model=models.CopilotResult)
def edit_complaint(req: models.EditComplaintRequest, db: Session = Depends(get_db)):
    if not req.instruction or not req.instruction.strip():
        raise HTTPException(400, "Please provide an edit instruction.")

    initial_state = {
        "mode": "edit",
        "existing_form": req.current_form.model_dump(),
        "edit_instruction": req.instruction,
        "complaint_id": req.complaint_id,
        "candidate_complaints": _recent_complaints_for_dup_check(db),
    }
    result = complaint_graph.invoke(initial_state)
    return _graph_result_to_response(result, complaint_id=req.complaint_id)


# ---------------------------------------------------------------------------
# CRUD: persist / list / fetch / delete
# ---------------------------------------------------------------------------

@app.post("/api/complaints", response_model=dict)
def save_complaint(req: models.SaveComplaintRequest, db: Session = Depends(get_db)):
    if req.complaint_id:
        record = db.query(models.Complaint).get(req.complaint_id)
        if not record:
            raise HTTPException(404, "Complaint not found.")
    else:
        record = models.Complaint()
        db.add(record)

    for k, v in req.form_data.model_dump().items():
        setattr(record, k, v)

    if req.risk_assessment:
        record.ai_risk_assessment = req.risk_assessment.model_dump()
    if req.completeness:
        record.ai_completeness = req.completeness.model_dump()
    if req.duplicate_check:
        record.ai_duplicate_check = req.duplicate_check.model_dump()
    if req.root_cause:
        record.ai_root_cause = req.root_cause.model_dump()
    if req.capa:
        record.ai_capa = req.capa.model_dump()
    if req.summary:
        record.ai_summary = req.summary

    db.commit()
    db.refresh(record)
    return {"complaint_id": record.id, "status": "saved"}


@app.get("/api/complaints", response_model=List[dict])
def list_complaints(db: Session = Depends(get_db)):
    rows = db.query(models.Complaint).order_by(desc(models.Complaint.id)).all()
    return [
        {
            "id": r.id, "product_name": r.product_name, "batch_lot_number": r.batch_lot_number,
            "complaint_type": r.complaint_type, "initial_severity": r.initial_severity,
            "priority": r.priority, "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@app.get("/api/complaints/{complaint_id}")
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    record = db.query(models.Complaint).get(complaint_id)
    if not record:
        raise HTTPException(404, "Complaint not found.")
    return {c.name: getattr(record, c.name) for c in record.__table__.columns}


@app.delete("/api/complaints/{complaint_id}")
def delete_complaint(complaint_id: int, db: Session = Depends(get_db)):
    record = db.query(models.Complaint).get(complaint_id)
    if not record:
        raise HTTPException(404, "Complaint not found.")
    db.delete(record)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
