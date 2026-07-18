"""LangGraph representation of the investigation lifecycle.

Distributed executors can use the same state contract while routing individual
specialist nodes through Celery or another queue-backed task runner.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class InvestigationGraphState(TypedDict, total=False):
    context_id: str
    planned_agents: list[str]
    evidence_id: str
    root_cause_id: str


def build_investigation_graph() -> StateGraph:
    graph = StateGraph(InvestigationGraphState)
    graph.add_node("plan", lambda state: state)
    graph.add_node("dispatch", lambda state: state)
    graph.add_node("aggregate_evidence", lambda state: state)
    graph.add_node("reason", lambda state: state)
    graph.add_node("recommend", lambda state: state)
    graph.add_node("summarize", lambda state: state)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "dispatch")
    graph.add_edge("dispatch", "aggregate_evidence")
    graph.add_edge("aggregate_evidence", "reason")
    graph.add_edge("reason", "recommend")
    graph.add_edge("recommend", "summarize")
    graph.add_edge("summarize", END)
    return graph
