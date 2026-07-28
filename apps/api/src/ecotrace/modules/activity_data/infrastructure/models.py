from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActivityRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "activity_records"
    __table_args__ = (
        Index("ix_activity_records_organization_id", "organization_id"),
        Index("ix_activity_records_facility_id", "facility_id"),
        Index("ix_activity_records_production_line_id", "production_line_id"),
        Index("ix_activity_records_equipment_id", "equipment_id"),
        Index("ix_activity_records_activity_type_id", "activity_type_id"),
        Index("ix_activity_records_reporting_period_id", "reporting_period_id"),
        Index("ix_activity_records_activity_date", "activity_date"),
        Index("ix_activity_records_period_start", "period_start"),
        Index("ix_activity_records_period_end", "period_end"),
        Index("ix_activity_records_status", "status"),
        Index("ix_activity_records_created_at", "created_at"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("row_version >= 1", name="row_version_positive"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=True
    )
    production_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_lines.id", ondelete="SET NULL"), nullable=True
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True
    )
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    activity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_types.id", ondelete="RESTRICT"), nullable=False
    )
    reporting_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reporting_periods.id", ondelete="RESTRICT"), nullable=False
    )
    activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    normalized_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class ActivityRecordRevision(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "activity_record_revisions"
    __table_args__ = (
        UniqueConstraint(
            "activity_record_id", "revision_number", name="uq_activity_revisions_record_rev"
        ),
        Index("ix_activity_record_revisions_activity_record_id", "activity_record_id"),
    )

    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )


class ActivityAttachment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "activity_attachments"
    __table_args__ = (
        Index("ix_activity_attachments_organization_id", "organization_id"),
        Index("ix_activity_attachments_activity_record_id", "activity_record_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
