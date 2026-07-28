from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
revision: str = '0001_initial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table('roles', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('code', sa.String(length=64), nullable=False), sa.Column('name', sa.String(length=128), nullable=False), sa.Column('description', sa.Text(), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')), sa.UniqueConstraint('code', name='uq_roles_code'))
    op.create_table('users', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('email', sa.String(length=320), nullable=False), sa.Column('normalized_email', sa.String(length=320), nullable=False), sa.Column('full_name', sa.String(length=255), nullable=False), sa.Column('hashed_password', sa.String(length=255), nullable=False), sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False), sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False), sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.PrimaryKeyConstraint('id', name=op.f('pk_users')), sa.UniqueConstraint('normalized_email', name='uq_users_normalized_email'))
    op.create_index('ix_users_normalized_email', 'users', ['normalized_email'], unique=False)
    op.create_table('organizations', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('name', sa.String(length=255), nullable=False), sa.Column('slug', sa.String(length=128), nullable=False), sa.Column('legal_name', sa.String(length=255), nullable=True), sa.Column('country_code', sa.String(length=2), nullable=False), sa.Column('timezone', sa.String(length=64), nullable=False), sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.CheckConstraint('char_length(country_code) = 2', name='ck_organizations_country_code_length'), sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations')), sa.UniqueConstraint('slug', name='uq_organizations_slug'))
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=False)
    op.create_table('user_roles', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='CASCADE'), sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f('pk_user_roles')), sa.UniqueConstraint('user_id', 'role_id', name='uq_user_roles_user_role'))
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'], unique=False)
    op.create_table('refresh_tokens', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('token_hash', sa.String(length=64), nullable=False), sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False), sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True), sa.Column('replaced_by_token_id', postgresql.UUID(as_uuid=True), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('user_agent', sa.String(length=512), nullable=True), sa.Column('ip_address', sa.String(length=45), nullable=True), sa.ForeignKeyConstraint(['replaced_by_token_id'], ['refresh_tokens.id'], name=op.f('fk_refresh_tokens_replaced_by_token_id_refresh_tokens'), ondelete='SET NULL'), sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')), sa.UniqueConstraint('token_hash', name=op.f('uq_refresh_tokens_token_hash')))
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'], unique=False)
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=False)
    op.create_table('organization_memberships', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False), sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_organization_memberships_organization_id_organizations'), ondelete='CASCADE'), sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_organization_memberships_role_id_roles'), ondelete='RESTRICT'), sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_organization_memberships_user_id_users'), ondelete='CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f('pk_organization_memberships')), sa.UniqueConstraint('organization_id', 'user_id', name='uq_organization_memberships_org_user'))
    op.create_index('ix_organization_memberships_user_id', 'organization_memberships', ['user_id'], unique=False)
    op.create_index('ix_organization_memberships_organization_id', 'organization_memberships', ['organization_id'], unique=False)
    op.create_table('audit_logs', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True), sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True), sa.Column('action', sa.String(length=128), nullable=False), sa.Column('entity_type', sa.String(length=128), nullable=True), sa.Column('entity_id', sa.String(length=64), nullable=True), sa.Column('request_id', sa.String(length=64), nullable=True), sa.Column('ip_address', sa.String(length=45), nullable=True), sa.Column('user_agent', sa.String(length=512), nullable=True), sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_audit_logs_actor_user_id_users'), ondelete='SET NULL'), sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_audit_logs_organization_id_organizations'), ondelete='SET NULL'), sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs')))
    op.create_index('ix_audit_logs_actor_user_id', 'audit_logs', ['actor_user_id'], unique=False)
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_organization_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_actor_user_id', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index('ix_organization_memberships_organization_id', table_name='organization_memberships')
    op.drop_index('ix_organization_memberships_user_id', table_name='organization_memberships')
    op.drop_table('organization_memberships')
    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_index('ix_user_roles_user_id', table_name='user_roles')
    op.drop_table('user_roles')
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_table('organizations')
    op.drop_index('ix_users_normalized_email', table_name='users')
    op.drop_table('users')
    op.drop_table('roles')
