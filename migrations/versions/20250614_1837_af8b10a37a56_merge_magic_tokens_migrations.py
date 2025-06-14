"""merge magic tokens migrations

Revision ID: af8b10a37a56
Revises: 20250614_1636_add_used_at_to_magic_tokens_fix, 6de8d45a317b
Create Date: 2025-06-14 18:37:53.109832

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af8b10a37a56'
down_revision = ('20250614_1636_add_used_at_to_magic_tokens_fix', '6de8d45a317b')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
