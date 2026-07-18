from typing import Any

from app.core.interfaces import BaseAgent, BaseConnector
from app.core.types import AgentResult, EvidenceItem, InvestigationContext, Severity


class ConnectorAgent(BaseAgent):
    """Common resilient integration behavior; specialists own their operation and normalization."""

    operation: str
    severity: Severity = Severity.INFO

    def __init__(self, connector: BaseConnector) -> None:
        self.connector = connector

    async def investigate(self, context: InvestigationContext) -> AgentResult:
        try:
            payload = await self.connector.query(
                self.operation, service=context.service, repository=context.repository,
                time_range_minutes=context.time_range_minutes, query=context.query,
            )
            return self.normalize(payload, context)
        except (ConnectionError, TimeoutError, ValueError) as error:
            return AgentResult(
                agent=self.name, summary=f"{self.connector.provider} data unavailable",
                confidence=0.0, unavailable=True, errors=[str(error)],
            )

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        findings = payload.get("findings", [])
        evidence = [EvidenceItem(**item) for item in payload.get("evidence", [])]
        return AgentResult(
            agent=self.name, severity=Severity(payload.get("severity", self.severity)),
            summary=payload.get("summary", f"{len(findings)} {self.name} findings"),
            confidence=float(payload.get("confidence", 0.5 if findings else 0.0)),
            findings=findings, evidence=evidence,
        )


class LogsAgent(ConnectorAgent):
    name, operation, severity = "logs", "search_errors", Severity.HIGH

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        streams = payload.get("data", {}).get("result", [])
        messages = [value for stream in streams for _, value in stream.get("values", [])]
        findings = [{"category": self._category(message), "message": message} for message in messages]
        evidence = [EvidenceItem(source="loki", claim=item["message"], attributes={"category": item["category"]}) for item in findings]
        return AgentResult(agent=self.name, severity=Severity.HIGH if findings else Severity.INFO,
                           summary=f"Found {len(findings)} matching log events.", confidence=0.85 if findings else 0.0,
                           findings=findings, evidence=evidence)

    @staticmethod
    def _category(message: str) -> str:
        lower = message.lower()
        for name, marker in (("oom_killed", "oomkilled"), ("timeout", "timeout"), ("authentication_failure", "auth"), ("exception", "exception")):
            if marker in lower:
                return name
        return "error"


class MetricsAgent(ConnectorAgent):
    name, operation, severity = "metrics", "metrics_anomalies", Severity.HIGH

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        series = payload.get("data", {}).get("result", [])
        findings: list[dict[str, Any]] = []
        for item in series:
            values = [float(value) for _, value in item.get("values", []) if value not in {"NaN", "+Inf", "-Inf"}]
            if len(values) < 3:
                continue
            baseline = sum(values[:-1]) / len(values[:-1])
            latest = values[-1]
            if baseline and abs(latest - baseline) / abs(baseline) >= 0.5:
                findings.append({"category": "metric_anomaly", "metric": item.get("metric", {}), "latest": latest, "baseline": baseline})
        evidence = [EvidenceItem(source="prometheus", claim=f"Metric changed from {item['baseline']:.3f} to {item['latest']:.3f}", attributes=item) for item in findings]
        return AgentResult(agent=self.name, severity=Severity.HIGH if findings else Severity.INFO,
                           summary=f"Detected {len(findings)} metric anomalies.", confidence=0.8 if findings else 0.0,
                           findings=findings, evidence=evidence)


class DeploymentAgent(ConnectorAgent):
    name, operation, severity = "deployment", "deployment_history", Severity.MEDIUM

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        data = payload.get("data", {})
        revisions = data.get("status", {}).get("history", [])
        health = data.get("status", {}).get("health", {}).get("status")
        sync = data.get("status", {}).get("sync", {}).get("status")
        findings = [{"category": "deployment", "revision": item.get("revision"), "deployed_at": item.get("deployedAt")} for item in revisions[-3:]]
        if health and health != "Healthy":
            findings.append({"category": "deployment_health", "health": health, "sync": sync})
        evidence = [EvidenceItem(source="argocd", claim=str(item), attributes=item) for item in findings]
        return AgentResult(agent=self.name, severity=Severity.HIGH if health and health != "Healthy" else Severity.INFO,
                           summary=f"Deployment health is {health or 'unknown'}; {len(revisions)} revisions examined.", confidence=0.8 if findings else 0.0, findings=findings, evidence=evidence)


class GitAgent(ConnectorAgent):
    name, operation, severity = "git", "repository_risk", Severity.MEDIUM

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        commits = payload.get("data", [])
        findings = [{"category": "recent_commit", "sha": item.get("sha"), "author": item.get("commit", {}).get("author", {}).get("name"), "message": item.get("commit", {}).get("message", "").splitlines()[0]} for item in commits]
        risk = min(1.0, len(findings) / 20)
        evidence = [EvidenceItem(source="github", claim=f"Recent commit {item['sha']}: {item['message']}", attributes=item) for item in findings]
        return AgentResult(agent=self.name, severity=Severity.MEDIUM if findings else Severity.INFO,
                           summary=f"Analyzed {len(findings)} recent commits (change-volume risk {risk:.0%}).", confidence=0.75 if findings else 0.0,
                           findings=findings, evidence=evidence)


class KubernetesAgent(ConnectorAgent):
    name, operation, severity = "kubernetes", "workload_health", Severity.HIGH

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        pods = payload.get("data", [])
        findings = [{"category": "kubernetes_workload", **pod} for pod in pods if pod.get("restart_count", 0) or pod.get("waiting_reasons") or pod.get("terminated_reasons") or pod.get("phase") != "Running"]
        evidence = [EvidenceItem(source="kubernetes", claim=f"Pod {item['name']} is {item['phase']}", attributes=item) for item in findings]
        return AgentResult(agent=self.name, severity=Severity.HIGH if findings else Severity.INFO,
                           summary=f"Inspected {len(pods)} pods; {len(findings)} unhealthy.", confidence=0.9 if findings else 0.0,
                           findings=findings, evidence=evidence)


class PipelineAgent(ConnectorAgent):
    name, operation, severity = "pipeline", "pipeline_failures", Severity.MEDIUM

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        runs = payload.get("data", {}).get("workflow_runs", [])
        findings = [{"category": "pipeline_failure", "name": run.get("name"), "conclusion": run.get("conclusion"), "run_id": run.get("id"), "duration": (run.get("updated_at"), run.get("created_at"))} for run in runs if run.get("conclusion") not in {"success", None}]
        evidence = [EvidenceItem(source="github_actions", claim=f"Workflow {item['name']} concluded {item['conclusion']}", attributes=item) for item in findings]
        return AgentResult(agent=self.name, severity=Severity.HIGH if findings else Severity.INFO,
                           summary=f"Found {len(findings)} failed workflow runs.", confidence=0.9 if findings else 0.0,
                           findings=findings, evidence=evidence)


class SustainabilityAgent(ConnectorAgent):
    name, operation, severity = "sustainability", "sustainability_impact", Severity.INFO

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        result = super().normalize(payload, context)
        # Connectors provide measured/provider-derived inputs. This agent retains the formula transparently.
        for finding in result.findings:
            power_watts = finding.get("power_watts")
            duration_seconds = finding.get("duration_seconds")
            intensity = finding.get("carbon_intensity_gco2_per_kwh")
            retries = finding.get("retry_count", 0)
            if all(value is not None for value in (power_watts, duration_seconds, intensity)):
                energy_kwh = power_watts * duration_seconds / 3_600_000
                finding["energy_kwh"] = energy_kwh
                finding["carbon_gco2"] = energy_kwh * intensity
                finding["retry_waste_gco2"] = energy_kwh * intensity * retries
        return result


class HistoricalIncidentAgent(ConnectorAgent):
    name, operation, severity = "historical", "similar_incidents", Severity.INFO

    def normalize(self, payload: dict[str, Any], context: InvestigationContext) -> AgentResult:
        data = payload.get("data", {})
        documents = (data.get("documents") or [[]])[0]
        metadatas = (data.get("metadatas") or [[]])[0]
        distances = (data.get("distances") or [[]])[0]
        findings = [{"category": "historical_incident", "summary": document, "metadata": metadata, "similarity": round(1 - distance, 3)} for document, metadata, distance in zip(documents, metadatas, distances, strict=False)]
        evidence = [EvidenceItem(source="chromadb", claim=item["summary"], attributes=item) for item in findings]
        return AgentResult(agent=self.name, summary=f"Found {len(findings)} similar incidents.", confidence=0.7 if findings else 0.0, findings=findings, evidence=evidence)
