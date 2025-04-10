"""修改担保表status字段

Revision ID: 4773871d57bc
Revises: e05ec329d493
Create Date: 2025-04-11 21:03:44.773348

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4773871d57bc'
down_revision = 'e05ec329d493'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('responses', schema=None) as batch_op:
        batch_op.alter_column('player_name',
               existing_type=sa.TEXT(length=25),
               type_=sa.String(length=25),
               existing_nullable=False)
        batch_op.alter_column('player_uuid',
               existing_type=sa.TEXT(length=36),
               type_=sa.String(length=36),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('responses', schema=None) as batch_op:
        batch_op.alter_column('player_uuid',
               existing_type=sa.String(length=36),
               type_=sa.TEXT(length=36),
               existing_nullable=False)
        batch_op.alter_column('player_name',
               existing_type=sa.String(length=25),
               type_=sa.TEXT(length=25),
               existing_nullable=False)

    # ### end Alembic commands ###
