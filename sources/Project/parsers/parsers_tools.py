"""parser tools"""
import json
import random
from typing import List
from datetime import datetime
from random import SystemRandom
import logging

import backoff
import requests
from requests.exceptions import RequestException

import sqlalchemy
from bs4 import BeautifulSoup as bs, NavigableString

from sqlalchemy.dialects.postgresql import insert

from settings import BASE_URL, base_dir, DOMAIN
from utils.psql_utils import create_session

from db.models import Headers, Articles


with open(base_dir / 'proxy.json') as file:
    DATA = json.load(file)


def give_up(e: RequestException):
    """
    func for backoff callback
    :param e: exception instance
    :return:
    """
    if isinstance(e, RequestException):
        return e.response.status_code != 200
    else:
        return False


class ExampleParser:
    """tools for parse resource; change class name for anonymize)"""
    def __init__(self):
        self.url = BASE_URL
        self.proxy = self._get_proxy()

    @staticmethod
    def _get_proxy():
        """
        create proxy for requests library
        :return: dict in requests proxy format
        """
        crypto_random = SystemRandom()
        hosts = DATA[1]
        crypto_random.shuffle(hosts)
        login, password, proxy_address, port = DATA[0][0], DATA[0][1], hosts[random.randint(0, 47)], DATA[0][2]
        useful_proxy = {'https': f'https://{login}:{password}@{proxy_address}:{port}/'}
        return useful_proxy

    @staticmethod
    def current_date(year=1970):
        """
        return dict with current date info
        :param year:
        :return:
        """
        date = datetime.now()
        current_year, current_month = date.year, date.month
        months = range(1, 13) if year != current_year else range(1, current_month + 1)

        return {'months_range': months, 'year': current_year, 'month': current_month}

    @backoff.on_exception(backoff.expo, (ConnectionError, RequestException), max_tries=3, giveup=give_up)
    def request(self, url, params):
        """
        send request to site
        raise error if response is not valid or return empty list if page hasn't
        contains desired content
        :param url: resource url
        :param params: parameters that bs4 need find in html
        :return: list content or empty list
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        }
        proxy = self._get_proxy()
        try:
            resp = requests.get(
                url,
                proxies=proxy,
                headers=headers,
                timeout=10
            )
        except Exception as e:
            logging.error(f'request: url - {url}; exception:{e}')
            raise ConnectionError
        if resp.status_code != 200:
            logging.error(f'status code: url - {url}')
            raise ConnectionError
        text = resp.text
        html = bs(text, 'html.parser')
        content = html.find(**params)

        return content

    @staticmethod
    def parse_headers(list_with_news: list) -> List[dict]:
        """
        create list that insert into table
        :param list_with_news: info from tag html tag news-list
        :return: list of dict
        """
        to_insert = []
        for news in list_with_news:
            a_tag = news.find('a')

            relative_article_link: str = a_tag.get('href')
            published_date: str = news.find(class_='date').get_text()
            article_index = relative_article_link.strip('.html').split('/')[-1]

            if len(article_index) == 1:
                article_index = f'0{article_index}'

            hash_from_link = f"{''.join(reversed(published_date.split('.')))}{article_index}"
            to_insert.append(
                {
                    'heading': a_tag.get_text(),
                    'link': DOMAIN + relative_article_link,
                    'published_date': datetime.strptime(published_date, '%d.%m.%Y'),
                    'hash_from_link': int(hash_from_link)
                }
            )

        return to_insert

    @staticmethod
    def insert_in_headers(to_insert: list) -> list:
        """
        insert data in Headers and return (id, link)
        :param to_insert:
        :return:
        """
        with create_session() as session:
            stmt = insert(Headers).values(to_insert).returning(Headers.id, Headers.link)
            stmt_on_conflict = stmt.on_conflict_do_nothing(
                index_elements=['hash_from_link']
            )
            try:
                articles = session.execute(stmt_on_conflict).fetchall()
            except sqlalchemy.exc.IntegrityError:
                articles = []

        return articles

    def parse_articles(self, articles: list) -> list:
        """
        parse articles by the accepted list
        :param articles: list with tuples inside (id, link_to_article)
        :return:
        """

        def clean_article(article_to_clean: list):
            """
            cleaned parsed data
            :param article_to_clean:
            :return:
            """
            articles_part_list = []
            for element in article_to_clean:
                if isinstance(element, NavigableString):
                    continue
                elif element.p and element.p.get('class', 'no date')[0] == 'date':
                    continue
                else:
                    articles_part_list.append(str(element))
            return articles_part_list

        articles_obj_to_insert = []
        for each_article in articles:
            try:
                raw_article = self.request(
                    each_article[1],
                    dict(name='div', class_='news-article')
                )
            except ConnectionError:
                continue

            if raw_article:
                articles_obj_to_insert.append(
                    {
                        'headers_id': each_article[0],
                        'article_text': ''.join(clean_article(raw_article))
                    }
                )
            else:
                continue

        return articles_obj_to_insert

    @staticmethod
    def insert_in_articles(articles_list: list):

        with create_session() as session:
            if articles_list:
                stmt = insert(Articles).values(articles_list)  # Articles.__table__.insert()
                stmt_on_conflict = stmt.on_conflict_do_nothing(
                    index_elements=['headers_id']
                )
                session.execute(stmt_on_conflict)
                return True
            else:
                return False

    def parse_historical_news(self, year):
        """
        method to first parser execute; parse all news up to this day
        :param year:
        :return:
        """
        months = self.current_date(year)['months_range']
        articles_list = []
        for month in months:
            url = BASE_URL + str(year) + f"/{month}/"
            try:
                news_list = self.request(url, dict(name='div', class_='news-list'))
            except ConnectionError:
                continue
            headers = self.parse_headers(news_list)
            articles_per_month = self.insert_in_headers(headers)
            articles_list.extend(articles_per_month)

        return articles_list

    def parse_new_news(self, last_db_news: datetime):
        """
        func for use in last_news_parser
        :param last_db_news: last header published date in db
        :return:
        """
        date = self.current_date()
        url = BASE_URL + str(date['year']) + f"/{date['month']}/"
        news_list = self.request(url=url, params=dict(name='div', class_='news-list'))
        if news_list:
            last_month_news = self.parse_headers(news_list)
            new_news = list(filter(
                lambda x: x['published_date'] > last_db_news,
                last_month_news
            ))

            articles_list = self.insert_in_headers(new_news)

            return articles_list

        else:
            return []

    def parse_one_month(self, year: int, month: int):
        """
        parse only one month news
        :param year:
        :param month:
        :return: news headers per month
        """
        url = BASE_URL + str(year) + f"/{month}/"
        news_list = self.request(url, dict(name='div', class_='news-list'))
        headers = self.parse_headers(news_list)

        return headers


if __name__ == '__main__':
    logger = logging.getLogger('root')
    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(format=FORMAT)
    logger.setLevel(logging.DEBUG)
