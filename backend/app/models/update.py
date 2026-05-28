from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class RegulatoryUpdate(Base):
    __tablename__ = "regulatory_updates"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    regulator: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(50))
    document_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(Text)
    date: Mapped[str] = mapped_column(String(20), default="")
    page_url: Mapped[str] = mapped_column(Text, default="")
    pdf_url: Mapped[str] = mapped_column(Text, default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="unreviewed")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    analysis: Mapped["AIAnalysis"] = relationship(back_populates="update", uselist=False)


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    update_id: Mapped[str] = mapped_column(ForeignKey("regulatory_updates.id"))
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    summary: Mapped[str] = mapped_column(Text, default="")
    applicability: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    implementation_json: Mapped[list] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String(10), default="Low")
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update: Mapped["RegulatoryUpdate"] = relationship(back_populates="analysis")


class FetchRun(Base):
    __tablename__ = "fetch_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    source: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updates_found: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
