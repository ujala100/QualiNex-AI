"""
Builds the single LangGraph StateGraph that powers all three mandatory AI
tools. Only the ENTRY POINT differs between tools -- everything downstream
(completeness -> duplicate check -> root cause -> CAPA -> risk -> summary)
is shared, which is exactly the point of using a graph instead of three
copy-pasted scripts: one pipeline, three doors in.

    Log Complaint tool      ---> "extract_fields" ---\
    Document Extraction     ---> "extract_fields" ----+--> completeness_check --(conditional)--> ...
    AI Edit Complaint tool  ---> "apply_edit"      ---/

If completeness_check finds required fields missing, the graph short-circuits
straight to compose_message (asks a clarifying question) instead of wasting
LLM calls on risk/root-cause/CAPA for an incomplete record.
"""
from langgraph.graph import StateGraph, END

from .state import ComplaintState
from . import nodes


def _route_entry(state: ComplaintState) -> str:
    return "apply_edit" if state.get("mode") == "edit" else "extract_fields"


def _route_after_completeness(state: ComplaintState) -> str:
    return "compose_message" if state.get("needs_clarification") else "duplicate_check"


def build_graph():
    graph = StateGraph(ComplaintState)

    # NOTE: LangGraph forbids a node name that collides with a key already
    # present in the state schema (ComplaintState has "duplicate_check",
    # "root_cause", "capa", "summary" as *data* fields) -- so node ids below
    # are deliberately distinct from those state keys (e.g. "check_duplicates"
    # vs the state field "duplicate_check"), even though the underlying
    # functions still read/write the original field names.
    graph.add_node("extract_fields", nodes.extract_fields_node)
    graph.add_node("apply_edit", nodes.apply_edit_node)
    graph.add_node("completeness_check", nodes.completeness_check_node)
    graph.add_node("check_duplicates", nodes.duplicate_check_node)
    graph.add_node("analyze_root_cause", nodes.root_cause_node)
    graph.add_node("recommend_capa", nodes.capa_node)
    graph.add_node("risk_classification", nodes.risk_classification_node)
    graph.add_node("generate_summary", nodes.summary_node)
    graph.add_node("compose_message", nodes.compose_message_node)

    graph.set_conditional_entry_point(_route_entry, {
        "extract_fields": "extract_fields",
        "apply_edit": "apply_edit",
    })

    graph.add_edge("extract_fields", "completeness_check")
    graph.add_edge("apply_edit", "completeness_check")

    graph.add_conditional_edges("completeness_check", _route_after_completeness, {
        "compose_message": "compose_message",
        "duplicate_check": "check_duplicates",
    })

    graph.add_edge("check_duplicates", "analyze_root_cause")
    graph.add_edge("analyze_root_cause", "recommend_capa")
    graph.add_edge("recommend_capa", "risk_classification")
    graph.add_edge("risk_classification", "generate_summary")
    graph.add_edge("generate_summary", "compose_message")
    graph.add_edge("compose_message", END)

    return graph.compile()


# Compiled once at import time and reused across requests.
complaint_graph = build_graph()
