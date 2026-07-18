from sqlalchemy.ext.asyncio import AsyncSession

from app.core.interfaces import IncidentRepository
from app.core.types import AgentResult, InvestigationContext
from app.models.entities import AgentResultModel, IncidentModel


class SqlAlchemyIncidentRepository(IncidentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_investigation(self, context: InvestigationContext, results: list[AgentResult]) -> None:
        self.session.add(IncidentModel(id=context.incident_id, organization_id=context.organization_id,
            repository=context.repository, service=context.service, query=context.query, intent=context.intent))
        self.session.add_all(AgentResultModel(incident_id=context.incident_id, agent=result.agent,
            confidence=result.confidence, payload=result.model_dump(mode="json")) for result in results)
        await self.session.commit()
