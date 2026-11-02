from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base, UTCDateTime

def utcnow():
    return datetime.now(timezone.utc)

class Monitor(Base):
    __tablename__ = "monitored_apis"
    __table_args__ = (CheckConstraint("monitoring_interval >= 30 AND monitoring_interval <= 86400", name="valid_interval"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    monitoring_interval: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latest_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True), default=utcnow, onupdate=utcnow)
    checks: Mapped[list["HealthCheck"]] = relationship(back_populates="monitor", cascade="all, delete-orphan", passive_deletes=True)

class HealthCheck(Base):
    __tablename__ = "health_checks"
    __table_args__ = (Index("ix_checks_monitor_checked", "monitored_api_id", "checked_at"), Index("ix_checks_status_checked", "status", "checked_at"))
    id: Mapped[int] = mapped_column(primary_key=True)
    monitored_api_id: Mapped[int] = mapped_column(ForeignKey("monitored_apis.id", ondelete="CASCADE"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    http_status_code: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[float | None] = mapped_column(Float)
    error_message: Mapped[str | None] = mapped_column(Text)
    monitor: Mapped[Monitor] = relationship(back_populates="checks")
