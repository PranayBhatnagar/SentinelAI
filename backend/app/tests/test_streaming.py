import asyncio
import json

from app.core.interfaces import BaseAgent
from app.core.types import AgentResult, InvestigationContext, InvestigationIntent
from app.planner.planner import Planner
from app.reasoning.root_cause import RootCauseAgent
from app.recommendation.engine import RecommendationEngine
from app.services.orchestrator import Orchestrator
from app.services.summary import SummaryAgent


class StreamingAgent(BaseAgent):
    name = "historical"

    async def investigate(self, context: InvestigationContext) -> AgentResult:
        await asyncio.sleep(0)
        return AgentResult(agent=self.name, summary="No similar incidents", confidence=0)


def test_investigation_events_end_with_serialized_response() -> None:
    orchestrator = Orchestrator(Planner(), {"historical": StreamingAgent()}, RootCauseAgent(), RecommendationEngine(), SummaryAgent(), None, 2)
    context = InvestigationContext(organization_id="acme", query="summarize incidents", intent=InvestigationIntent.INCIDENT_SUMMARY)

    async def collect():
        return [event async for event in orchestrator.investigate_events(context)]

    events = asyncio.run(collect())
    assert events[0]["event"] == "progress"
    assert events[-1]["event"] == "complete"
    assert json.loads(events[-1]["data"])["summary"]
