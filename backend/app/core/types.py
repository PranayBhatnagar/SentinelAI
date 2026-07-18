from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InvestigationIntent(StrEnum):
    SERVICE_FAILURE = "service_failure"
    DEPLOYMENT = "deployment"
    PIPELINE = "pipeline"
    PULL_REQUEST = "pull_request"
    KUBERNETES = "kubernetes"
    LATENCY = "latency"
    INCIDENT_SUMMARY = "incident_summary"
    IMPACT = "impact"


class InvestigationContext(BaseModel):
    incident_id: UUID = Field(default_factory=uuid4)
    organization_id: str
    repository: str | None = None
    service: str | None = None
    query: str
    intent: InvestigationIntent
    time_range_minutes: int = Field(default=60, ge=1, le=10_080)
    metadata: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceItem(BaseModel):
    id: str | None = None
    source: str
    claim: str
    observed_at: datetime | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw_reference: str | None = None


class AgentResult(BaseModel):
    agent: str
    severity: Severity = Severity.INFO
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    unavailable: bool = False
    errors: list[str] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    incident_id: UUID
    results: list[AgentResult] = Field(default_factory=list)
    graph: "EvidenceGraph | None" = None

    def by_agent(self, name: str) -> AgentResult | None:
        return next((result for result in self.results if result.agent == name), None)


class EvidenceNode(BaseModel):
    id: str
    agent: str
    source: str
    finding: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvidenceEdge(BaseModel):
    source_id: str
    target_id: str
    relationship: str
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceGraph(BaseModel):
    nodes: list[EvidenceNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)


class RootCause(BaseModel):
    cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: list[str]
    evidence: list[EvidenceItem]


class Recommendation(BaseModel):
    action: str
    priority: Severity
    rationale: str
    automated: bool = False


class InvestigationResponse(BaseModel):
    incident_id: UUID
    summary: str
    evidence: EvidenceBundle
    root_causes: list[RootCause]
    recommendations: list[Recommendation]
    business_impact: str
    cloud_cost: str
    carbon_impact: str
    historical_incidents: list[dict[str, Any]] = Field(default_factory=list)
    github_markdown: str
