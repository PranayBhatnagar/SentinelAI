from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IncidentModel(Base):
    __tablename__ = "incidents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    repository: Mapped[str | None] = mapped_column(String(255))
    service: Mapped[str | None] = mapped_column(String(255), index=True)
    query: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentResultModel(Base):
    __tablename__ = "agent_results"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), index=True)
    agent: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)


class EvidenceModel(Base):
    __tablename__ = "evidence"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), index=True)
    agent_result_id: Mapped[UUID | None] = mapped_column(ForeignKey("agent_results.id"))
    source: Mapped[str] = mapped_column(String(128))
    claim: Mapped[str] = mapped_column(Text)
    attributes: Mapped[dict] = mapped_column(JSON)


class EmbeddingModel(Base):
    __tablename__ = "embeddings"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[UUID] = mapped_column(index=True)
    vector_store_key: Mapped[str] = mapped_column(String(512), unique=True)


class ConversationModel(Base):
    __tablename__ = "conversations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    github_thread_id: Mapped[str] = mapped_column(String(255), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class HistoricalIncidentModel(Base):
    __tablename__ = "historical_incidents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    service: Mapped[str | None] = mapped_column(String(255), index=True)
    resolution: Mapped[str] = mapped_column(Text)
    embedding_reference: Mapped[str | None] = mapped_column(String(512))


class RecommendationModel(Base):
    __tablename__ = "recommendations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
