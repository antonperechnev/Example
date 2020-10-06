"""init db

Revision ID: 507ca94fb4f3
Revises: 
Create Date: 2020-05-28 11:17:26.632993

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '507ca94fb4f3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('headers',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('heading', sa.VARCHAR(), nullable=False),
    sa.Column('link', sa.VARCHAR(), nullable=False),
    sa.Column('published_date', sa.TIMESTAMP(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('articles',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('headers_id', sa.BigInteger(), nullable=True),
    sa.Column('article_text', sa.VARCHAR(), nullable=True),
    sa.ForeignKeyConstraint(['headers_id'], ['headers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('articles')
    op.drop_table('headers')
    # ### end Alembic commands ###
