from app.core.types import InvestigationResponse


class SummaryAgent:
    def github_markdown(self, response: InvestigationResponse) -> str:
        causes = response.root_causes or []
        root_cause = causes[0].cause if causes else "No root cause established from available evidence."
        confidence = f"{causes[0].confidence:.0%}" if causes else "N/A"
        actions = "\n".join(f"- {item.action}" for item in response.recommendations) or "- Gather more telemetry."
        evidence = "\n".join(f"- **{item.agent}**: {item.summary}" for item in response.evidence.results)
        return f"""## Sentinel AI Investigation

### Summary
{response.summary}

### Root Cause
{root_cause} (confidence: {confidence})

### Evidence
{evidence}

### Recommended Actions
{actions}

### Impact
- Business: {response.business_impact}
- Cloud cost: {response.cloud_cost}
- Carbon: {response.carbon_impact}
"""
