"""sqlalchemy models"""
from sqlalchemy import Table, Column, String, MetaData, BigInteger, JSON, INTEGER, TEXT, ForeignKey,\
    LargeBinary, Boolean, DATETIME, VARCHAR, Float, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine

from settings import ALCHEMY_URL, SCHEMA

engine = create_engine(ALCHEMY_URL,
                       connect_args={'options': '-csearch_path={}'.format(SCHEMA)})


meta = MetaData(engine)
base = declarative_base()


class Headers(base):
    """
    Headers table store info from all news page
    """
    __tablename__ = 'headers'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    heading = Column(VARCHAR, nullable=False)
    link = Column(VARCHAR, nullable=False)
    published_date = Column(TIMESTAMP, nullable=False)
    hash_from_link = Column(BigInteger, nullable=False, unique=True)

    article = relationship('Articles', backref='headers')


class Articles(base):
    """
    Articles store main text
    """
    __tablename__ = 'articles'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    headers_id = Column(BigInteger, ForeignKey('headers.id'), unique=True)
    article_text = Column(VARCHAR)