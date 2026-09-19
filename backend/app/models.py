"""
ORM model for a stored complaint + Pydantic schemas that mirror the
"Log Customer Complaint" form fields shown in the reference UI, plus the
AI Risk Assessment payload the copilot produces.

The field names here map 1:1 to the reference screenshot sections:
  1. ORIGIN & CUSTOMER DETAILS
  2. PRODUCT & BATCH IDENTIFICATION
  3. COMPLAINT DETAILS
  4. INITIAL ASSESSMENT & PRIORITY
"""
from datetime import datetime, date
from typing import Optional, List, Literal
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON
from pydantic import BaseModel, Field

from .database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)

    # 1. Origin & Customer
    complaint_source = Column(String(120))
    customer_name = Column(String(200))

    # 2. Product & Batch
    product_name = Column(String(200))
    product_strength_grade = Column(String(120))
    batch_lot_number = Column(String(120))
    manufacturing_date = Column(String(40))
    expiry_date = Column(String(40))
    quantity_affected = Column(String(60))

    # 3. Complaint Details
    complaint_type = Column(String(120))
    complaint_date = Column(String(40))
    detailed_complaint_description = Column(Text)

    # 4. Initial Assessment & Priority
    initial_severity = Column(String(40))
    priority = Column(String(40))

    # AI-derived data (stored as JSON blobs so the pipeline can evolve
    # without needing schema migrations for every new AI feature)
    ai_risk_assessment = Column(JSON)
    ai_completeness = Column(JSON)
    ai_duplicate_check = Column(JSON)
    ai_root_cause = Column(JSON)
    ai_capa = Column(JSON)
    ai_summary = Column(Text)

    raw_source_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ComplaintFormData(BaseModel):
    """Exactly the fields the left-hand 'Log Customer Complaint' form shows."""
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None

    product_name: Optional[str] = None
    product_strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity_affected: Optional[str] = None

    complaint_type: Optional[str] = None
    complaint_date: Optional[str] = None
    detailed_complaint_description: Optional[str] = None

    initial_severity: Optional[str] = None
    priority: Optional[str] = None


class RiskAssessment(BaseModel):
    risk_level: Optional[str] = None            # Critical / Major / Minor
    risk_score: Optional[int] = None            # 0-100
    rationale: Optional[str] = None
    recommended_priority: Optional[str] = None
    recommended_severity: Optional[str] = None
    regulatory_flags: List[str] = Field(default_factory=list)  # e.g. "Possible adverse event - notify PV"


class CompletenessCheck(BaseModel):
    is_complete: bool = False
    missing_fields: List[str] = Field(default_factory=list)
    completeness_score: int = 0                 # 0-100
    clarifying_question: Optional[str] = None


class DuplicateCheck(BaseModel):
    is_possible_duplicate: bool = False
    matched_complaint_ids: List[int] = Field(default_factory=list)
    rationale: Optional[str] = None


class RootCauseSuggestion(BaseModel):
    likely_categories: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None


class CapaRecommendation(BaseModel):
    corrective_actions: List[str] = Field(default_factory=list)
    preventive_actions: List[str] = Field(default_factory=list)


class CopilotResult(BaseModel):
    """Unified response shape returned by all three AI tools."""
    form_data: ComplaintFormData
    risk_assessment: RiskAssessment
    completeness: CompletenessCheck
    duplicate_check: DuplicateCheck
    root_cause: RootCauseSuggestion
    capa: CapaRecommendation
    summary: Optional[str] = None
    assistant_message: str
    needs_clarification: bool = False
    complaint_id: Optional[int] = None


class LogComplaintRequest(BaseModel):
    text: str


class EditComplaintRequest(BaseModel):
    current_form: ComplaintFormData
    instruction: str
    complaint_id: Optional[int] = None


class SaveComplaintRequest(BaseModel):
    form_data: ComplaintFormData
    risk_assessment: Optional[RiskAssessment] = None
    completeness: Optional[CompletenessCheck] = None
    duplicate_check: Optional[DuplicateCheck] = None
    root_cause: Optional[RootCauseSuggestion] = None
    capa: Optional[CapaRecommendation] = None
    summary: Optional[str] = None
    complaint_id: Optional[int] = None
