from __future__ import annotations
import uuid
from datetime import date, datetime
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class ReportingPeriod(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'reporting_periods'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_reporting_periods_org_code'), Index('ix_reporting_periods_organization_id', 'organization_id'), Index('ix_reporting_periods_start_date', 'start_date'), Index('ix_reporting_periods_end_date', 'end_date'), Index('ix_reporting_periods_status', 'status'), CheckConstraint('start_date <= end_date', name='period_dates'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    period_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='open')
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
