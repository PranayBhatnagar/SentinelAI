import pytest

from app.core.types import InvestigationContext, InvestigationIntent
from app.planner.planner import Planner


@pytest.mark.asyncio
async def test_planner_selects_only_performance_agents_without_llm() -> None:
    context = InvestigationContext(organization_id="acme", query="Investigate checkout latency", intent=InvestigationIntent.SERVICE_FAILURE)
    agents = await Planner().plan(context)
    assert agents == ["metrics", "logs", "deployment", "git", "historical"]
    assert "pipeline" not in agents
