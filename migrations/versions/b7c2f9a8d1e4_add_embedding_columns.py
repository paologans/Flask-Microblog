"""add embedding columns

Revision ID: b7c2f9a8d1e4
Revises: 443f8b095aa1
Create Date: 2026-05-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c2f9a8d1e4'
down_revision = '443f8b095aa1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding', sa.Text(), nullable=True))

    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_column('embedding')

    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_column('embedding')
