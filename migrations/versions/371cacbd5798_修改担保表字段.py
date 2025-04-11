"""修改担保表字段

Revision ID: 371cacbd5798
Revises: 4773871d57bc
Create Date: 2025-04-11 23:12:02.033945

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '371cacbd5798'
down_revision = '4773871d57bc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('guarantees', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expiration_time', sa.DateTime()))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('guarantees', schema=None) as batch_op:
        batch_op.drop_column('expiration_time')

    # ### end Alembic commands ###
