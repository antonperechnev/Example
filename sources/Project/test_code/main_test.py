"""script with test code for this project"""
from datetime import datetime

import requests
import json
import pickle
import inspect
import logging
import pandas as pd

from dateutil.relativedelta import relativedelta
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.util import KeyedTuple
from sqlalchemy.inspection import inspect
from sqlalchemy import desc, func

from apscheduler.schedulers.blocking import BlockingScheduler
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup as bs
from bs4 import NavigableString

from Utils.parsers_utils import ExampleParser
from Utils.psql_utils import create_session
from settings import BASE_URL, DOMAIN

from DB.models import Headers, Articles


def parse_month():
    parser = ExampleParser()
    month = parser.parse_one_month(2019, 6)

    return month


def insert_empty():
    to_insert = []
    with create_session() as session:
        stmt = insert(Articles).values(to_insert)  # Articles.__table__.insert()
        stmt_on_conflict = stmt.on_conflict_do_nothing(
            index_elements=['headers_id']
        )
        session.execute(stmt_on_conflict)

    return 1


insert_empty()


def parse_news():
    resp = requests.get('https://alfabank.ru/custody_news/corporate/2020/5/29/56.html')
    # resp.encoding = 'utf-8'
    text = resp.text

    html = bs(text, 'html.parser')
    params = dict(name='div', class_='news-article')
    script_tag = html.find(**params)
    without_table = []
    for element in script_tag:
        if isinstance(element, NavigableString):
            continue
        elif element.p and element.p['class'][0] == 'date':
            print(element)
            continue
        else:
            without_table.append(str(element))

        # print(dir(element))
    return ''.join(without_table)


def test_alchemy_returning():
    to_insert = [
        {
            'id': ids,
            'heading': 'ffff',
            'link': 'sssss',
            'published_date': '31.07.2005'
        } for ids in range(36431, 36441)
    ]
    stmt = insert(Headers).values().returning(Headers.id, Headers.link)
    stmt_conflict = stmt.on_conflict_do_nothing(
        index_elements=['id']
    )
    with create_session() as session:
        data = session.execute(stmt_conflict).fetchall()
    return data


def try_except():
    try:
        print(1/0)
    except ZeroDivisionError:
        print('exception')
        raise
    finally:
        print('finally')


def test_name():
    func = inspect.currentframe().f_back.f_code
    print(func.co_name, func.co_filename)


def speed_test_on_conflict(to_insert):
    st = datetime.now()
    with create_session() as session:
        stmt = insert(Headers).values(to_insert).returning(Headers.id, Headers.link)
        stmt_on_conflict = stmt.on_conflict_do_nothing(
            index_elements=['hash_from_link']
        )
        try:
            articles = session.execute(stmt_on_conflict).fetchall()
        except UnboundLocalError:
            logging.exception('no content ')
            return []
    print(f'upsert - {datetime.now() - st}')
    return articles


def speed_test_filter(all_news):
    st = datetime.now()
    new_news = list(filter(
        lambda x: datetime.strptime(x['published_date'], '%Y-%m-%d %H:%M:%S.%f') >
        datetime(2020, 5, 28),
        all_news
    ))
    with create_session() as session:
        stmt = insert(Headers).values(new_news).returning(Headers.id, Headers.link)
        stmt_on_conflict = stmt.on_conflict_do_nothing(
            index_elements=['hash_from_link']
        )
        try:
            articles = session.execute(stmt).fetchall()
        except UnboundLocalError:
            logging.exception('no content ')
            return []
    print(f'filter - {datetime.now() - st}')
    return articles


def result_api_create():
    month_start = datetime(2020, 5, 1)
    month_end = month_start + relativedelta(months=1)
    with create_session() as session:
        headers = session.query(Headers).filter(
            Headers.published_date >= month_start,
            Headers.published_date < month_end
        ).all()
        result = [{
            'id': header.id,
            'heading': header.heading,
            'published_at': header.published_date.isoformat()
        } for header in headers]

    return result


def speed_test():
    with open('alfa_public_headers.json', encoding='utf-8') as f:
        data = json.load(f)
    last_month = list(
        filter(lambda x: datetime.strptime(x['published_date'], '%Y-%m-%d %H:%M:%S.%f') >
               datetime(2020, 5, 1), data)
                      )
    last_month.append({
        "heading": "(INTR) О предстоящем корпоративном действии «Выплата купона» - Облигации СистемаАФК серии 001Р-05 (RU000A0JWZY6)",
        "link": "https://alfabank.ru/custody_news/corporate/2020/1/31/44.html",
        "published_date": "2020-05-29 00:00:00.000000",
        "hash_from_link": 20205291
    })
# speed_test_filter(last_month)
# speed_test_on_conflict(last_month)
# filter - 0:00:00.045028
# upsert - 0:00:00.134383


def change_article(x):
    with open('alfa_public_articles.json') as f:
        data = json.load(f)
    for record in data:
        record['article_text'].strip('')


def speed_comparison():
    """
    comparison between 2x select and select with list slice
    :return:
    """
    st = datetime.now()
    with create_session() as session:
        headers = session.query(func.count(Headers.published_date)).filter(
            Headers.published_date >= datetime(2019, 2, 1),
            Headers.published_date < datetime(2020, 5, 31)
        )
        print(datetime.now() - st)
        print(headers.scalar())
        data1 = session.query(Headers).filter(
            Headers.published_date >= datetime(2019, 2, 1),
            Headers.published_date < datetime(2020, 5, 31)
        ).order_by(
            desc(Headers.published_date)
        ).values(
            Headers.id,
            Headers.heading,
            Headers.published_date
        )
        print(datetime.now() - st)
        st = datetime.now()
        data2 = session.query(Headers).filter(
            Headers.published_date >= datetime(2019, 2, 1),
            Headers.published_date < datetime(2020, 5, 31)
        ).order_by(
            desc(Headers.published_date)
            #Headers.id
        ).limit(
            30
        ).offset(
            0
        ).values(
            Headers.id,
            Headers.heading,
            Headers.published_date
        )
        # all_len = len(data2)
        result = [
            {
                'id': header.id,
                'heading': header.heading,
                'published_at': header.published_date.isoformat()
            } for header in data2
        ]
        print('cache', result)
        print(datetime.now() - st)
        st = datetime.now()
    # with create_session() as session:
        """data3 = session.query(Headers).filter(
            Headers.published_date >= datetime(2019, 2, 1),
            Headers.published_date < datetime(2020, 5, 31)
        ).order_by(
            desc(Headers.published_date)
            #Headers.id
        ).values(
            Headers.id,
            Headers.heading,
            Headers.published_date
        )"""
        result = [
            {
                'id': header.id,
                'heading': header.heading,
                'published_at': header.published_date.isoformat()
            } for header in data1
        ]
        print(len(result), result[:30])
    print(datetime.now() - st)


# print(speed_comparison())
