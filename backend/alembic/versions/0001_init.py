"""init

Revision ID: 0001
Revises:
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('phone_e164', sa.String(length=20), nullable=False),
        sa.Column('language', sa.String(length=5), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('opt_in_status', sa.Boolean(), nullable=False),
        sa.Column('opt_in_source', sa.String(length=255), nullable=True),
        sa.Column('opt_in_time', sa.DateTime(), nullable=True),
        sa.Column('opt_in_text', sa.Text(), nullable=True),
        sa.Column('last_inbound_time', sa.DateTime(), nullable=True),
        sa.Column('last_outbound_time', sa.DateTime(), nullable=True),
        sa.Column('blocked', sa.Boolean(), nullable=False),
    )
    op.create_index('ix_contacts_phone_e164', 'contacts', ['phone_e164'], unique=True)
    op.create_table('campaigns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('segment_query', sa.JSON(), nullable=False),
        sa.Column('template_name', sa.String(length=255), nullable=False),
        sa.Column('variables_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('dry_run', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
    )
    op.create_table('templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('body_draft', sa.Text(), nullable=False),
        sa.Column('approved_template_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
    )
    op.create_table('messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('contact_id', sa.Integer(), sa.ForeignKey('contacts.id'), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('template_name', sa.String(length=255), nullable=True),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('send_after', sa.DateTime(), nullable=True),
        sa.Column('wa_message_id', sa.String(length=120), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
    )
    op.create_table('opt_outs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('contact_id', sa.Integer(), sa.ForeignKey('contacts.id'), nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
    )
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('opt_outs')
    op.drop_table('messages')
    op.drop_table('templates')
    op.drop_table('campaigns')
    op.drop_index('ix_contacts_phone_e164', table_name='contacts')
    op.drop_table('contacts')
