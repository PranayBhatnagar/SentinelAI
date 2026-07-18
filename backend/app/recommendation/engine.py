from app.core.types import Recommendation, RootCause, Severity


class RecommendationEngine:
    """Conservative suggestions; never performs mutating remediation without approval."""

    def generate(self, causes: list[RootCause]) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        for cause in causes:
            normalized = cause.cause.lower()
            if any(token in normalized for token in ("deployment", "regression", "release")):
                recommendations.append(Recommendation(action="Review and, if validated, roll back the implicated deployment.", priority=Severity.HIGH, rationale="Deployment evidence correlates with the failure.", automated=False))
            elif any(token in normalized for token in ("oom", "memory", "capacity", "scaling")):
                recommendations.append(Recommendation(action="Validate resource limits and scale the affected workload.", priority=Severity.HIGH, rationale="Resource-related evidence was observed.", automated=False))
            elif any(token in normalized for token in ("timeout", "latency")):
                recommendations.append(Recommendation(action="Inspect upstream dependency latency and timeout budgets.", priority=Severity.MEDIUM, rationale="Latency/timeout evidence was observed.", automated=False))
        if not recommendations and causes:
            recommendations.append(Recommendation(action="Collect additional correlated telemetry before changing production.", priority=Severity.MEDIUM, rationale="Current evidence identifies symptoms but no safe prescriptive fix.", automated=False))
        return recommendations
