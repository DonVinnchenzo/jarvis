"""initial schema

Revision ID: 3a2a16c50c46
Revises:
Create Date: 2026-06-09 10:59:22.206833

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3a2a16c50c46'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('contacts',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('relationship_type', sa.String(length=100), nullable=False),
    sa.Column('visibility', sa.String(length=20), server_default='shared', nullable=False),
    sa.Column('created_by', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contacts_name', 'contacts', ['name'], unique=False)
    op.create_table('contact_children',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('contact_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('contact_notes',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('contact_id', sa.Uuid(), nullable=False),
    sa.Column('note_text', sa.Text(), nullable=False),
    sa.Column('created_by', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('contact_events',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('contact_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=True),
    sa.Column('child_id', sa.Uuid(), nullable=True),
    sa.Column('day', sa.Integer(), nullable=False),
    sa.Column('month', sa.Integer(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('recurring', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('day >= 1 AND day <= 31', name='ck_event_day'),
    sa.CheckConstraint('month >= 1 AND month <= 12', name='ck_event_month'),
    sa.ForeignKeyConstraint(['child_id'], ['contact_children.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contact_events_month_day', 'contact_events', ['month', 'day'], unique=False)
    op.create_table('reminder_configs',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=True),
    sa.Column('days_before', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['contact_events.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sent_reminders',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('reminder_config_id', sa.Uuid(), nullable=False),
    sa.Column('event_date', sa.Date(), nullable=False),
    sa.Column('sent_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column(
        'telegram_message_ids',
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    ),
    sa.ForeignKeyConstraint(['event_id'], ['contact_events.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reminder_config_id'], ['reminder_configs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id', 'reminder_config_id', 'event_date', name='uq_sent_reminder_event_config_date')
    )

    # GIN index for full-text search on contact_notes.note_text
    op.execute(
        "CREATE INDEX ix_contact_notes_note_text_gin "
        "ON contact_notes USING gin (to_tsvector('english', note_text))"
    )


def downgrade() -> None:
    op.drop_table('sent_reminders')
    op.drop_table('reminder_configs')
    op.drop_index('ix_contact_events_month_day', table_name='contact_events')
    op.drop_table('contact_events')
    op.drop_index('ix_contact_notes_note_text_gin', table_name='contact_notes')
    op.drop_table('contact_notes')
    op.drop_table('contact_children')
    op.drop_index('ix_contacts_name', table_name='contacts')
    op.drop_table('contacts')
