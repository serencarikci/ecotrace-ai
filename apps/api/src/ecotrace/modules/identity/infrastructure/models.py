from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
if TYPE_CHECKING:
    from ecotrace.modules.organizations.infrastructure.models import OrganizationMembership

class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('normalized_email', name='uq_users_normalized_email'), Index('ix_users_normalized_email', 'normalized_email'))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    roles: Mapped[list[Role]] = relationship(secondary='user_roles', back_populates='users', lazy='selectin')
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates='user', cascade='all, delete-orphan')
    memberships: Mapped[list[OrganizationMembership]] = relationship(back_populates='user', cascade='all, delete-orphan')

class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'roles'
    __table_args__ = (UniqueConstraint('code', name='uq_roles_code'),)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    users: Mapped[list[User]] = relationship(secondary='user_roles', back_populates='roles', lazy='selectin')

class UserRole(Base):
    __tablename__ = 'user_roles'
    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='uq_user_roles_user_role'), Index('ix_user_roles_user_id', 'user_id'), Index('ix_user_roles_role_id', 'role_id'))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class RefreshToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = 'refresh_tokens'
    __table_args__ = (Index('ix_refresh_tokens_user_id', 'user_id'), Index('ix_refresh_tokens_expires_at', 'expires_at'), Index('ix_refresh_tokens_token_hash', 'token_hash'))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('refresh_tokens.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user: Mapped[User] = relationship(back_populates='refresh_tokens')

class AuditLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = 'audit_logs'
    __table_args__ = (Index('ix_audit_logs_actor_user_id', 'actor_user_id'), Index('ix_audit_logs_organization_id', 'organization_id'), Index('ix_audit_logs_created_at', 'created_at'))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
