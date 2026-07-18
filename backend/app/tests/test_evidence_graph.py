from app.core.types import AgentResult, EvidenceBundle, EvidenceItem
from app.services.evidence_graph import EvidenceGraphBuilder


def test_evidence_graph_links_cross_agent_corroboration() -> None:
    evidence = EvidenceBundle.model_validate({"incident_id": "00000000-0000-0000-0000-000000000001", "results": [
        AgentResult(agent="logs", summary="error", confidence=0.9, evidence=[EvidenceItem(source="loki", claim="OOM", attributes={"category": "oom_killed"})]),
        AgentResult(agent="kubernetes", summary="pod", confidence=0.9, evidence=[EvidenceItem(source="k8s", claim="OOM", attributes={"category": "oom_killed"})]),
    ]})
    graph = EvidenceGraphBuilder().build(evidence)
    assert len(graph.nodes) == 2
    assert graph.edges[0].relationship == "corroborates"
