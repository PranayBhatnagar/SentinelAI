from itertools import combinations

from app.core.types import EvidenceBundle, EvidenceEdge, EvidenceGraph, EvidenceNode


class EvidenceGraphBuilder:
    """Produces an inspectable correlation graph without inferring causal links as facts."""

    def build(self, evidence: EvidenceBundle) -> EvidenceGraph:
        nodes: list[EvidenceNode] = []
        for result in evidence.results:
            for index, item in enumerate(result.evidence):
                category = str(item.attributes.get("category", "observed_failure"))
                nodes.append(EvidenceNode(
                    id=item.id or f"{result.agent}:{index}", agent=result.agent, source=item.source,
                    finding=item.claim, category=category, confidence=min(result.confidence, item.confidence),
                    timestamp=item.observed_at, attributes=item.attributes,
                ))
        edges: list[EvidenceEdge] = []
        for left, right in combinations(nodes, 2):
            if left.agent == right.agent:
                continue
            if left.category == right.category:
                edges.append(EvidenceEdge(source_id=left.id, target_id=right.id,
                                          relationship="corroborates", confidence=min(left.confidence, right.confidence)))
            elif self._temporally_related(left.timestamp, right.timestamp):
                edges.append(EvidenceEdge(source_id=left.id, target_id=right.id,
                                          relationship="temporally_correlated", confidence=min(left.confidence, right.confidence) * 0.6))
        return EvidenceGraph(nodes=nodes, edges=edges)

    @staticmethod
    def _temporally_related(left, right) -> bool:
        return bool(left and right and abs((left - right).total_seconds()) <= 900)
