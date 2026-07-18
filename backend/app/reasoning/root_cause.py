from collections import defaultdict

from app.core.interfaces import BaseAgent
from app.core.types import AgentResult, EvidenceBundle, RootCause


class RootCauseAgent(BaseAgent):
    name = "root_cause"

    async def investigate(self, context):  # pragma: no cover - invoked through analyze
        raise NotImplementedError("RootCauseAgent requires a complete EvidenceBundle")

    async def analyze(self, evidence: EvidenceBundle) -> list[RootCause]:
        """Evidence-first correlation. It cannot assert a cause with no supporting observation."""
        clusters: dict[str, list[AgentResult]] = defaultdict(list)
        nodes_by_category = defaultdict(list)
        for node in (evidence.graph.nodes if evidence.graph else []):
            nodes_by_category[node.category].append(node)
        for result in evidence.results:
            if result.unavailable:
                continue
            for finding in result.findings:
                category = str(finding.get("category", finding.get("type", "observed_failure")))
                clusters[category].append(result)

        causes: list[RootCause] = []
        for category, supporting in clusters.items():
            unique_agents = {item.agent for item in supporting}
            confidence = min(0.95, sum(item.confidence for item in supporting) / len(supporting))
            if len(unique_agents) > 1:
                confidence = min(0.95, confidence + 0.1)
            observed = [evidence_item for item in supporting for evidence_item in item.evidence if str(evidence_item.attributes.get("category", "observed_failure")) == category]
            if not observed:
                observed = [evidence_item for item in supporting for evidence_item in item.evidence]
            corroborations = sum(1 for edge in (evidence.graph.edges if evidence.graph else []) if edge.relationship == "corroborates" and any(node.id in {edge.source_id, edge.target_id} for node in nodes_by_category[category]))
            causes.append(RootCause(
                cause=category.replace("_", " "), confidence=round(confidence, 2),
                reasoning=[f"Observed by {', '.join(sorted(unique_agents))}; evidence graph has {corroborations} corroborating links.", *[item.summary for item in supporting]],
                evidence=observed,
            ))
        return sorted(causes, key=lambda cause: cause.confidence, reverse=True)[:3]
