"""news updater"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy import desc
import logging

from parsers.parsers_tools import ExampleParser
from utils.psql_utils import create_session

from db.models import Headers, Articles

scheduler = BlockingScheduler(gconfig={'default': ThreadPoolExecutor(1)})


@scheduler.scheduled_job('cron', hour='*', minute=40)  # , start_date=datetime.datetime.now())
def parse_last_news():
    """
    declarative func for last news parsing
    :return:
    """
    with create_session() as session:
        newest_news = session.query(
            Headers
        ).order_by(
            desc(Headers.published_date)
        ).first()

        lost_articles = session.query(
            Headers
        ).join(
            Articles, Headers.id == Articles.headers_id, isouter=True
        ).filter(
            Articles.headers_id.is_(None)
        ).values(
            Headers.id,
            Headers.link
        )

        date = newest_news.published_date
        lost_articles = [(header.id, header.link) for header in lost_articles]
    parser = ExampleParser()
    try:
        new_news = parser.parse_new_news(date)
        new_news.extend(lost_articles)
    except ConnectionError:
        logging.error('server not allowed')
        return 0

    ready_to_insert_articles = parser.parse_articles(new_news)
    parser.insert_in_articles(ready_to_insert_articles)

    return 1


if __name__ == '__main__':
    FORMAT = "%(asctime)-15s %(filename)s:%(lineno)s - %(funcName)10s() %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.INFO)
    logging.getLogger('backoff').setLevel(logging.ERROR)
    scheduler.start()
