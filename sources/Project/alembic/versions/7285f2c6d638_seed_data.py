"""seed data

Revision ID: 7285f2c6d638
Revises: 167935963b67
Create Date: 2020-06-02 12:26:51.007827

"""
from alembic import op, context
import sqlalchemy as sa
import json

import sys
sys.path.append('.')

from db.models import Headers, Articles
from settings import PATH_TO_FIXTURES

# revision identifiers, used by Alembic.
revision = '7285f2c6d638'
down_revision = '167935963b67'
branch_labels = None
depends_on = None


def upgrade():
    if context.get_x_argument(as_dictionary=True).get('data'):
        tables = [Headers, Articles]
        for table in tables:
            with open(PATH_TO_FIXTURES / f'{table.__tablename__}.json', encoding='utf-8') as f:
                to_insert = json.load(f)
            op.bulk_insert(
                table.__table__,
                to_insert
            )


def downgrade():
    if context.get_x_argument(as_dictionary=True).get('data'):
        tables = [Articles.__tablename__, Headers.__tablename__]
        for table in tables:
            op.execute(f'delete from {table};')
