"""
Individual LangGraph nodes. Each node:
  - reads what it needs from ComplaintState
  - calls Groq (extraction model for cheap tasks, reasoning model for
    judgment-heavy tasks)
  - falls back to a deterministic offline heuristic if Groq is unavailable
    (no API key / network error) so the graph never hard-fails
  - returns a partial state dict (LangGraph merges it into the running state)
"""
import json
import re
import logging
from datetime import date
from typing import Dict, Any, List

from ..groq_client import call_groq_extraction, call_groq_reasoning, GroqError
from . import prompts

logger = logging.getLogger("aivoa.nodes")

EMPTY_FORM = {
    "complaint_source": None, "customer_name": None,
    "product_name": None, "product_strength_grade": None,
    "batch_lot_number": None, "manufacturing_date": None, "expiry_date": None,
    "quantity_affected": None, "complaint_type": None, "complaint_date": None,
    "detailed_complaint_description": None, "initial_severity": None, "priority": None,
}


# ---------------------------------------------------------------------------
# 1. Field extraction (Log Complaint tool + Document Extraction tool)
# ---------------------------------------------------------------------------

def extract_fields_node(state: Dict[str, Any]) -> Dict[str, Any]:
    text = state.get("raw_text", "")
    try:
        data = call_groq_extraction(prompts.EXTRACTION_SYSTEM_PROMPT, text)
        form = {**EMPTY_FORM, **{k: v for k, v in data.items() if k in EMPTY_FORM}}
        return {"form_data": form, "offline_mode": False}
    except GroqError:
        return {"form_data": _offline_extract(text), "offline_mode": True}


def _offline_extract(text: str) -> Dict[str, Any]:
    """Deterministic keyword/regex heuristic used only when no Groq key is
    configured, so the app is still fully demoable offline."""
    form = dict(EMPTY_FORM)
    t = text

    batch = re.search(r"(?:batch|lot)\s*(?:no\.?|number)?\s*[:#]?\s*([A-Za-z0-9\-\/]{3,20})", t, re.I)
    if batch:
        form["batch_lot_number"] = batch.group(1)

    product = re.search(r"(?:product|drug|medicine)\s*[:\-]?\s*([A-Za-z0-9 \-]{3,40})", t, re.I)
    if product:
        form["product_name"] = product.group(1).strip().rstrip(".")

    qty = re.search(r"(\d+[\d,]*\s?(?:tablets?|capsules?|kg|units?|vials?|bottles?))", t, re.I)
    if qty:
        form["quantity_affected"] = qty.group(1)

    for pat, val in [
        (r"\bemail\b", "Email"), (r"\bcall\b|\bphone\b", "Customer Call"),
        (r"\bdistributor\b", "Distributor"), (r"\bregulator\b|\bFDA\b", "Regulatory Authority"),
    ]:
        if re.search(pat, t, re.I):
            form["complaint_source"] = val
            break

    for pat, val in [
        (r"discolor|colou?r change", "Discoloration"),
        (r"particle|particulate|foreign matter", "Foreign Particulate"),
        (r"leak|broken|crack|damage", "Packaging Defect"),
        (r"label", "Labeling Error"),
        (r"reaction|adverse|side effect|illness|harm", "Adverse Event"),
        (r"weak|ineffective|sub-?potent", "Sub-potency"),
        (r"contaminat", "Contamination"),
    ]:
        if re.search(pat, t, re.I):
            form["complaint_type"] = val
            break

    dates = re.findall(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b", t)
    if dates:
        form["complaint_date"] = dates[0]
        if len(dates) > 1:
            form["expiry_date"] = dates[1]

    form["detailed_complaint_description"] = t.strip()[:400]

    severe = re.search(r"reaction|adverse|harm|hospital|contaminat|sub-?potent", t, re.I)
    form["initial_severity"] = "Critical" if severe else "Minor"
    form["priority"] = "High" if severe else "Low"

    form["complaint_date"] = form["complaint_date"] or date.today().isoformat()
    return form


# ---------------------------------------------------------------------------
# 2. Apply edit (AI Edit Complaint tool)
# ---------------------------------------------------------------------------

def apply_edit_node(state: Dict[str, Any]) -> Dict[str, Any]:
    existing = {**EMPTY_FORM, **(state.get("existing_form") or {})}
    instruction = state.get("edit_instruction", "")

    payload = json.dumps({"current_form": existing, "instruction": instruction})
    try:
        data = call_groq_reasoning(prompts.EDIT_SYSTEM_PROMPT, payload)
        merged = {**existing, **{k: v for k, v in data.items() if k in EMPTY_FORM and v is not None}}
        return {"form_data": merged, "offline_mode": False}
    except GroqError:
        return {"form_data": _offline_edit(existing, instruction), "offline_mode": True}


def _offline_edit(existing: Dict[str, Any], instruction: str) -> Dict[str, Any]:
    """Very small heuristic editor for offline mode: looks for
    'field = value' / 'set field to value' style instructions and a few
    common synonyms so demos still work without a live LLM key."""
    updated = dict(existing)
    synonyms = {
        "severity": "initial_severity", "priority": "priority",
        "batch": "batch_lot_number", "lot": "batch_lot_number",
        "product": "product_name", "customer": "customer_name",
        "quantity": "quantity_affected", "type": "complaint_type",
        "description": "detailed_complaint_description",
        "source": "complaint_source",
    }
    m = re.search(r"(set\s+)?(\w+)\s*(?:=|to|as)\s*(.+)", instruction, re.I)
    if m:
        key_word, value = m.group(2).lower(), m.group(3).strip().strip(".")
        field = synonyms.get(key_word, key_word if key_word in EMPTY_FORM else None)
        if field:
            updated[field] = value
    return updated


# ---------------------------------------------------------------------------
# 3. Completeness check
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["product_name", "batch_lot_number", "complaint_type",
                    "detailed_complaint_description", "complaint_source"]


def completeness_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    form = state.get("form_data", {})
    try:
        data = call_groq_reasoning(prompts.COMPLETENESS_SYSTEM_PROMPT, json.dumps(form))
        return {"completeness": data, "needs_clarification": not data.get("is_complete", True)}
    except GroqError:
        missing = [f for f in REQUIRED_FIELDS if not form.get(f)]
        score = int(100 * (len(REQUIRED_FIELDS) - len(missing)) / len(REQUIRED_FIELDS))
        result = {
            "is_complete": not missing,
            "missing_fields": missing,
            "completeness_score": score,
            "clarifying_question": (
                f"Could you provide the {missing[0].replace('_', ' ')}?" if missing else None
            ),
        }
        return {"completeness": result, "needs_clarification": bool(missing), "offline_mode": True}


# ---------------------------------------------------------------------------
# 4. Duplicate detection
# ---------------------------------------------------------------------------

def duplicate_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    form = state.get("form_data", {})
    candidates: List[Dict[str, Any]] = state.get("candidate_complaints", [])
    if not candidates:
        return {"duplicate_check": {"is_possible_duplicate": False, "matched_complaint_ids": [],
                                     "rationale": "No prior complaints on file to compare against."}}
    payload = json.dumps({"new_complaint": form, "existing_complaints": candidates})
    try:
        data = call_groq_reasoning(prompts.DUPLICATE_SYSTEM_PROMPT, payload)
        return {"duplicate_check": data}
    except GroqError:
        matches = [
            c["id"] for c in candidates
            if c.get("product_name") == form.get("product_name")
            and c.get("batch_lot_number") == form.get("batch_lot_number")
            and form.get("batch_lot_number")
        ]
        return {
            "duplicate_check": {
                "is_possible_duplicate": bool(matches),
                "matched_complaint_ids": matches,
                "rationale": "Offline heuristic: matched on identical product name + batch/lot number.",
            },
            "offline_mode": True,
        }


# ---------------------------------------------------------------------------
# 5. Root cause suggestion
# ---------------------------------------------------------------------------

def root_cause_node(state: Dict[str, Any]) -> Dict[str, Any]:
    form = state.get("form_data", {})
    try:
        data = call_groq_reasoning(prompts.ROOT_CAUSE_SYSTEM_PROMPT, json.dumps(form))
        return {"root_cause": data}
    except GroqError:
        mapping = {
            "Foreign Particulate": ["Cross-contamination", "Process deviation"],
            "Discoloration": ["Raw material deviation", "Storage/stability issue"],
            "Packaging Defect": ["Packaging/labeling error", "Equipment malfunction"],
            "Labeling Error": ["Human error", "Packaging/labeling error"],
            "Adverse Event": ["Insufficient information -- requires investigation"],
            "Sub-potency": ["Process deviation", "Raw material deviation"],
            "Contamination": ["Cross-contamination", "Supplier/vendor issue"],
        }
        cats = mapping.get(form.get("complaint_type"), ["Insufficient information -- requires investigation"])
        return {
            "root_cause": {
                "likely_categories": cats,
                "rationale": "Offline heuristic mapping based on complaint type only; formal investigation required.",
            },
            "offline_mode": True,
        }


# ---------------------------------------------------------------------------
# 6. CAPA recommendation
# ---------------------------------------------------------------------------

def capa_node(state: Dict[str, Any]) -> Dict[str, Any]:
    form = state.get("form_data", {})
    root_cause = state.get("root_cause", {})
    try:
        data = call_groq_reasoning(prompts.CAPA_SYSTEM_PROMPT,
                                    json.dumps({"complaint": form, "root_cause": root_cause}))
        return {"capa": data}
    except GroqError:
        return {
            "capa": {
                "corrective_actions": [
                    "Quarantine remaining stock from the implicated batch/lot pending investigation.",
                    "Retain a sample of the returned/complaint unit for lab analysis.",
                ],
                "preventive_actions": [
                    "Review in-process controls for the implicated process step.",
                    "Assess need for CAPA-linked training or SOP update.",
                ],
            },
            "offline_mode": True,
        }


# ---------------------------------------------------------------------------
# 7. Risk classification (AI Risk Assessment)
# ---------------------------------------------------------------------------

def risk_classification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "form": state.get("form_data", {}),
        "duplicate_check": state.get("duplicate_check", {}),
        "root_cause": state.get("root_cause", {}),
    }
    try:
        data = call_groq_reasoning(prompts.RISK_SYSTEM_PROMPT, json.dumps(payload))
        return {"risk_assessment": data}
    except GroqError:
        form = state.get("form_data", {})
        severe = form.get("initial_severity") == "Critical"
        return {
            "risk_assessment": {
                "risk_level": "Critical" if severe else "Minor",
                "risk_score": 85 if severe else 25,
                "rationale": "Offline heuristic based on the initial severity extracted from the complaint text.",
                "recommended_priority": "High" if severe else "Low",
                "recommended_severity": "Critical" if severe else "Minor",
                "regulatory_flags": (
                    ["Possible adverse event - notify Pharmacovigilance"]
                    if form.get("complaint_type") == "Adverse Event" else []
                ),
            },
            "offline_mode": True,
        }


# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------

def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    form = state.get("form_data", {})
    try:
        data_text = call_groq_reasoning(
            prompts.SUMMARY_SYSTEM_PROMPT + '\nReturn ONLY JSON: {"summary": string}',
            json.dumps(form),
        )
        return {"summary": data_text.get("summary", "")}
    except GroqError:
        parts = [
            f"{form.get('complaint_type', 'Complaint')} reported",
            f"for {form.get('product_name', 'an unspecified product')}",
            f"(batch {form.get('batch_lot_number')})" if form.get("batch_lot_number") else "",
            f"via {form.get('complaint_source', 'an unspecified source')}.",
        ]
        return {"summary": " ".join(p for p in parts if p), "offline_mode": True}


# ---------------------------------------------------------------------------
# 9. Assistant message composer (what shows up in the chat panel)
# ---------------------------------------------------------------------------

def compose_message_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("needs_clarification"):
        q = state.get("completeness", {}).get("clarifying_question") or \
            "Could you share a bit more detail about this complaint?"
        msg = f"I've pre-filled what I could find. {q}"
    else:
        risk = state.get("risk_assessment", {})
        msg = (
            f"Done -- I've populated the complaint form and classified this as "
            f"{risk.get('risk_level', 'an')} risk (score {risk.get('risk_score', '?')}/100). "
            f"See the AI Risk Assessment panel below for root cause and CAPA suggestions."
        )
        if state.get("duplicate_check", {}).get("is_possible_duplicate"):
            ids = state["duplicate_check"].get("matched_complaint_ids", [])
            msg += f" Note: this looks like a possible duplicate of complaint(s) #{ids}."
    return {"assistant_message": msg}
