from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class ImportJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'import_jobs'
    __table_args__ = (Index('ix_import_jobs_organization_id', 'organization_id'), Index('ix_import_jobs_status', 'status'), Index('ix_import_jobs_created_at', 'created_at'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='uploaded')
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ImportJobRow(Base, UUIDPrimaryKeyMixin):
    __tablename__ = 'import_job_rows'
    __table_args__ = (UniqueConstraint('import_job_id', 'row_number', name='uq_import_job_rows_job_row'), Index('ix_import_job_rows_import_job_id', 'import_job_id'))
    import_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('import_jobs.id', ondelete='CASCADE'), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    normalized_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default='pending')
    validation_errors_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    activity_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_records.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default='now()')
