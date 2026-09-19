"""
Shared state object passed between LangGraph nodes.

One graph (`build_graph` in graph.py) serves all three mandatory AI tools --
they differ only in which node the graph *enters* on and what's pre-filled
in the state:

  1. Log Complaint tool      -> entry: extract_fields   (raw_text set, existing_form empty)
  2. AI Edit Complaint tool  -> entry: apply_edit        (existing_form + edit_instruction set)
  3. Document Extraction     -> entry: extract_fields    (raw_text = parsed document text)

Keeping ONE graph (instead of three separate ad-hoc scripts) is the point:
it's what "AI Agent Framework: LangGraph" is meant to buy you -- a single,
inspectable, extensible pipeline of composable reasoning steps.
"""
from typing import TypedDict, Optional, List, Dict, Any


class ComplaintState(TypedDict, total=False):
    # --- inputs ---
    mode: str                      # "log" | "edit" | "document"
    raw_text: str                  # free text or parsed document text
    existing_form: Dict[str, Any]  # for edit mode: the form as it currently stands
    edit_instruction: str          # for edit mode: what the user asked to change
    complaint_id: Optional[int]

    # --- working data ---
    form_data: Dict[str, Any]
    completeness: Dict[str, Any]
    duplicate_check: Dict[str, Any]
    root_cause: Dict[str, Any]
    capa: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    summary: str

    # --- control flow / output ---
    needs_clarification: bool
    assistant_message: str
    candidate_complaints: List[Dict[str, Any]]  # for duplicate detection, loaded by the API layer
    offline_mode: bool
