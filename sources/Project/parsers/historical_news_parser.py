"""news parsing script"""
from utils.executor_utils import Executor
from parsers.parsers_tools import ExampleParser

from datetime import datetime


def parse_news():
    st = datetime.now()
    parser = ExampleParser()
    executor = Executor(parser.parse_historical_news, 18, list(range(2003, st.year)))
    articles_list = executor.start_accumulation_request()
    print(f'headers finish in - {datetime.now() - st}')
    executor = Executor(parser.parse_articles, 36, articles_list)
    ready_to_insert_articles = executor.start_accumulation_request()
    parser.insert_in_articles(ready_to_insert_articles)
    print(f'articles finish in - {datetime.now() - st}')


if __name__ == '__main__':
    parse_news()