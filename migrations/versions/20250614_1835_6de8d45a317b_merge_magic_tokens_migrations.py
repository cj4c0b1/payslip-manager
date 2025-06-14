"""merge magic tokens migrations

Revision ID: 6de8d45a317b
Revises: 20250614_add_used_at_to_magic_tokens, 20250614_add_used_at_to_magic_tokens_manual
Create Date: 2025-06-14 18:35:00.399478

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6de8d45a317b'
down_revision = ('20250614_add_used_at_to_magic_tokens', '20250614_add_used_at_to_magic_tokens_manual')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
