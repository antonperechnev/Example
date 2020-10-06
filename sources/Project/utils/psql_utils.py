"""tools for sqlalchemy"""
from contextlib import contextmanager
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import logging

sys.path.append('.')
from settings import SCHEMA, ALCHEMY_URL

ENGINE = create_engine(
    ALCHEMY_URL, connect_args={'options': '-csearch_path={}'.format(SCHEMA)},
    poolclass=NullPool, executemany_mode='values'
)
SESSION = sessionmaker(ENGINE)


@contextmanager
def create_session():
    """
    session handler
    :return:
    """
    session = SESSION()
    try:
        yield session
        session.commit()
    except Exception as error:
        logging.exception(f'session exception - {error}')
        session.rollback()
        raise
    finally:
        session.close()
