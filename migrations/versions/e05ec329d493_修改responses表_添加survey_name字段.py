"""修改responses表，添加survey_name字段

Revision ID: e05ec329d493
Revises: df2477415a0c
Create Date: 2025-04-07 23:44:43.561318

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e05ec329d493'
down_revision = 'df2477415a0c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('responses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('survey_name', sa.String(length=200), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('responses', schema=None) as batch_op:
        batch_op.drop_column('survey_name')

    # ### end Alembic commands ###
