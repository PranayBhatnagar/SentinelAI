import json
from collections.abc import Sequence

from openai import AsyncOpenAI

from app.core.types import InvestigationContext, InvestigationIntent


class Planner:
    """Maps intents to capabilities, leaving execution placement to the task dispatcher."""

    _plans: dict[InvestigationIntent, tuple[str, ...]] = {
        InvestigationIntent.SERVICE_FAILURE: ("logs", "metrics", "deployment", "git", "kubernetes", "historical", "sustainability"),
        InvestigationIntent.DEPLOYMENT: ("deployment", "git", "metrics", "kubernetes", "historical"),
        InvestigationIntent.PIPELINE: ("pipeline", "git", "historical", "sustainability"),
        InvestigationIntent.PULL_REQUEST: ("git", "pipeline", "historical"),
        InvestigationIntent.KUBERNETES: ("kubernetes", "metrics", "logs", "deployment"),
        InvestigationIntent.LATENCY: ("metrics", "logs", "deployment", "kubernetes", "historical"),
        InvestigationIntent.INCIDENT_SUMMARY: ("historical",),
        InvestigationIntent.IMPACT: ("metrics", "sustainability", "historical"),
    }

    available_agents = frozenset({agent for plan in _plans.values() for agent in plan})

    def __init__(self, client: AsyncOpenAI | None = None, model: str | None = None) -> None:
        self._client, self._model = client, model

    def create_execution_graph(self, context: InvestigationContext) -> list[str]:
        return list(self._plans[context.intent])

    async def plan(self, context: InvestigationContext) -> list[str]:
        """Uses constrained LLM planning; validation prevents arbitrary agent dispatch."""
        if self._client is None or self._model is None:
            return self._heuristic_plan(context)
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You route engineering investigations. Return JSON only: {\"agents\":[...]}. Select only necessary agents from: logs, metrics, deployment, git, kubernetes, pipeline, sustainability, historical. Never include an agent without a direct investigative purpose."},
                    {"role": "user", "content": context.query},
                ],
            )
            selected = json.loads(completion.choices[0].message.content or "{}").get("agents", [])
            valid = [agent for agent in selected if agent in self.available_agents]
            return list(dict.fromkeys(valid)) or self._heuristic_plan(context)
        except (json.JSONDecodeError, IndexError, ValueError):
            return self._heuristic_plan(context)

    def _heuristic_plan(self, context: InvestigationContext) -> list[str]:
        """Availability-safe classifier used only if the LLM is unavailable or malformed."""
        if context.intent == InvestigationIntent.INCIDENT_SUMMARY:
            return self.create_execution_graph(context)
        query = context.query.lower()
        categories: Sequence[tuple[tuple[str, ...], tuple[str, ...]]] = (
            (("pipeline", "workflow", "build", "test"), ("pipeline", "git", "historical", "sustainability")),
            (("latency", "slow", "performance"), ("metrics", "logs", "deployment", "git", "historical")),
            (("kubernetes", "pod", "crashloop", "oom", "cluster"), ("kubernetes", "logs", "metrics", "deployment")),
            (("deployment", "release", "rollback", "argocd"), ("deployment", "git", "metrics", "historical")),
            (("carbon", "sustainability", "cost", "cloud impact"), ("sustainability", "pipeline", "historical")),
        )
        for keywords, agents in categories:
            if any(keyword in query for keyword in keywords):
                return list(agents)
        return self.create_execution_graph(context)
