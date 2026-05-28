from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    nbfc_type: Mapped[str] = mapped_column(String(50))
    product_lines: Mapped[str] = mapped_column(Text, default="")
    aum_band: Mapped[str] = mapped_column(String(50), default="")
    geographies: Mapped[str] = mapped_column(Text, default="")
    compliance_risk_areas: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    documents: Mapped[list["OrgDocument"]] = relationship(back_populates="org")
    users: Mapped[list["User"]] = relationship(back_populates="org")
    digest_settings: Mapped["DigestSettings"] = relationship(back_populates="org", uselist=False)


class OrgDocument(Base):
    __tablename__ = "org_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    filename: Mapped[str] = mapped_column(String(255))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    org: Mapped["Organisation"] = relationship(back_populates="documents")


class DigestSettings(Base):
    __tablename__ = "digest_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), unique=True)
    recipient_emails: Mapped[str] = mapped_column(Text, default="")
    send_time_ist: Mapped[str] = mapped_column(String(5), default="08:00")
    enabled: Mapped[bool] = mapped_column(default=True)
    org: Mapped["Organisation"] = relationship(back_populates="digest_settings")
