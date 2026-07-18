import asyncio
import json
from collections.abc import Mapping
from collections.abc import AsyncIterator

from app.core.interfaces import BaseAgent, IncidentRepository
from app.core.types import AgentResult, EvidenceBundle, InvestigationContext, InvestigationResponse
from app.planner.planner import Planner
from app.reasoning.root_cause import RootCauseAgent
from app.recommendation.engine import RecommendationEngine
from app.services.summary import SummaryAgent
from app.services.evidence_graph import EvidenceGraphBuilder


class Orchestrator:
    def __init__(self, planner: Planner, agents: Mapping[str, BaseAgent], root_cause: RootCauseAgent,
                 recommendations: RecommendationEngine, summary: SummaryAgent, repository: IncidentRepository | None,
                 agent_timeout_seconds: float, graph_builder: EvidenceGraphBuilder | None = None) -> None:
        self.planner, self.agents, self.root_cause = planner, agents, root_cause
        self.recommendations, self.summary, self.repository = recommendations, summary, repository
        self.agent_timeout_seconds = agent_timeout_seconds
        self.graph_builder = graph_builder or EvidenceGraphBuilder()

    async def investigate(self, context: InvestigationContext) -> InvestigationResponse:
        events: list[dict[str, str]] = []
        async for event in self.investigate_events(context):
            events.append(event)
        return InvestigationResponse.model_validate_json(events[-1]["data"])

    async def investigate_events(self, context: InvestigationContext) -> AsyncIterator[dict[str, str]]:
        graph = await self.planner.plan(context)
        yield {"event": "progress", "data": json.dumps({"message": "Investigation planned", "agents": graph})}
        async def execute(agent_name: str) -> AgentResult:
            # This event is emitted before scheduling so the caller can show live work.
            try:
                return await asyncio.wait_for(self.agents[agent_name].investigate(context), self.agent_timeout_seconds)
            except TimeoutError:
                return AgentResult(agent=agent_name, summary="Agent timed out", confidence=0.0, unavailable=True, errors=["timeout"])
        tasks = {asyncio.create_task(execute(name)): name for name in graph}
        results: list[AgentResult] = []
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            yield {"event": "progress", "data": json.dumps({"agent": result.agent, "message": result.summary, "unavailable": result.unavailable})}
        evidence = EvidenceBundle(incident_id=context.incident_id, results=results)
        evidence.graph = self.graph_builder.build(evidence)
        yield {"event": "progress", "data": json.dumps({"message": "Correlating evidence graph"})}
        causes = await self.root_cause.analyze(evidence)
        historical = (evidence.by_agent("historical").findings if evidence.by_agent("historical") else [])
        response = InvestigationResponse(
            incident_id=context.incident_id,
            summary="Investigation completed from available connected telemetry.", evidence=evidence,
            root_causes=causes, recommendations=self.recommendations.generate(causes),
            business_impact="Not established from available evidence.", cloud_cost="Not established from available evidence.",
            carbon_impact="Not established from available evidence.", historical_incidents=historical, github_markdown="",
        )
        response.github_markdown = self.summary.github_markdown(response)
        if self.repository:
            await self.repository.save_investigation(context, results)
        yield {"event": "complete", "data": response.model_dump_json()}
