from app.core.types import InvestigationIntent


def infer_intent(command: str) -> InvestigationIntent:
    normalized = command.lower()
    if "pipeline" in normalized:
        return InvestigationIntent.PIPELINE
    if "pull request" in normalized or normalized.startswith("investigate pr"):
        return InvestigationIntent.PULL_REQUEST
    if "kubernetes" in normalized or "k8s" in normalized:
        return InvestigationIntent.KUBERNETES
    if "deploy" in normalized:
        return InvestigationIntent.DEPLOYMENT
    if "latency" in normalized:
        return InvestigationIntent.LATENCY
    if "carbon" in normalized or "cloud impact" in normalized or "cost" in normalized:
        return InvestigationIntent.IMPACT
    if "similar incident" in normalized or "summarize incidents" in normalized:
        return InvestigationIntent.INCIDENT_SUMMARY
    return InvestigationIntent.SERVICE_FAILURE
