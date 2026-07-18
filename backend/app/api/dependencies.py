from functools import lru_cache

from app.agents import DeploymentAgent, GitAgent, HistoricalIncidentAgent, KubernetesAgent, LogsAgent, MetricsAgent, PipelineAgent, SustainabilityAgent
from app.config.settings import get_settings
from app.integrations.argocd import ArgoCDConnector
from app.integrations.base import UnavailableConnector
from app.integrations.github.connector import GitHubConnector
from app.integrations.historical.chroma import ChromaIncidentConnector
from app.integrations.kubernetes.connector import KubernetesConnector
from app.integrations.loki.connector import LokiConnector
from app.integrations.pipelines.github_actions import GitHubActionsConnector
from app.integrations.prometheus.connector import PrometheusConnector
from app.planner.planner import Planner
from app.reasoning.root_cause import RootCauseAgent
from app.recommendation.engine import RecommendationEngine
from app.services.orchestrator import Orchestrator
from app.services.summary import SummaryAgent
from openai import AsyncOpenAI


@lru_cache
def get_orchestrator() -> Orchestrator:
    """Composition root. Only missing credentials/configuration create unavailable adapters."""
    settings = get_settings()
    github = GitHubConnector(settings.github_token, settings.github_api_url) if settings.github_token else UnavailableConnector("github")
    agents = {
        "logs": LogsAgent(LokiConnector(settings.loki_url) if settings.loki_url else UnavailableConnector("loki")),
        "metrics": MetricsAgent(PrometheusConnector(settings.prometheus_url) if settings.prometheus_url else UnavailableConnector("prometheus")),
        "deployment": DeploymentAgent(ArgoCDConnector(settings.argocd_url, settings.argocd_token) if settings.argocd_url and settings.argocd_token else UnavailableConnector("argocd")),
        "git": GitAgent(github),
        "kubernetes": KubernetesAgent(KubernetesConnector()),
        "pipeline": PipelineAgent(GitHubActionsConnector(settings.github_token, base_url=settings.github_api_url) if settings.github_token else UnavailableConnector("github_actions")),
        "sustainability": SustainabilityAgent(UnavailableConnector("cloud")),
        "historical": HistoricalIncidentAgent(ChromaIncidentConnector(settings.chroma_host, settings.chroma_port)),
    }
    planner_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
    return Orchestrator(Planner(planner_client, settings.openai_model if planner_client else None), agents, RootCauseAgent(), RecommendationEngine(), SummaryAgent(), None, settings.agent_timeout_seconds)
