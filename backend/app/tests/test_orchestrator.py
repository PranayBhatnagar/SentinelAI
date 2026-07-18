import asyncio

from app.core.interfaces import BaseAgent
from app.core.types import AgentResult, EvidenceItem, InvestigationContext, InvestigationIntent
from app.planner.planner import Planner
from app.reasoning.root_cause import RootCauseAgent
from app.recommendation.engine import RecommendationEngine
from app.services.orchestrator import Orchestrator
from app.services.summary import SummaryAgent


class FakeAgent(BaseAgent):
    def __init__(self, name: str) -> None:
        self.name = name

    async def investigate(self, context: InvestigationContext) -> AgentResult:
        await asyncio.sleep(0.01)
        return AgentResult(agent=self.name, summary="Observed deployment regression", confidence=0.8,
            findings=[{"category": "deployment_regression"}], evidence=[EvidenceItem(source=self.name, claim="Release coincides with errors")])


def test_orchestrator_aggregates_parallel_structured_evidence() -> None:
    agent_names = Planner().create_execution_graph(InvestigationContext(organization_id="acme", query="why failing", intent=InvestigationIntent.SERVICE_FAILURE))
    orchestrator = Orchestrator(Planner(), {name: FakeAgent(name) for name in agent_names}, RootCauseAgent(), RecommendationEngine(), SummaryAgent(), None, 1)
    response = asyncio.run(orchestrator.investigate(InvestigationContext(organization_id="acme", query="why failing", intent=InvestigationIntent.SERVICE_FAILURE)))
    assert len(response.evidence.results) == len(agent_names)
    assert response.root_causes[0].cause == "deployment regression"
    assert "Sentinel AI Investigation" in response.github_markdown
