from abc import ABC, abstractmethod
from typing import Any

from app.core.types import AgentResult, InvestigationContext


class BaseAgent(ABC):
    """A stateless specialist. Results must be serializable structured evidence."""

    name: str

    @abstractmethod
    async def investigate(self, context: InvestigationContext) -> AgentResult:
        raise NotImplementedError


class BaseConnector(ABC):
    """Provider boundary; implementations encapsulate provider auth and payload shapes."""

    provider: str

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        raise NotImplementedError


class IncidentRepository(ABC):
    @abstractmethod
    async def save_investigation(self, context: InvestigationContext, results: list[AgentResult]) -> None:
        raise NotImplementedError
