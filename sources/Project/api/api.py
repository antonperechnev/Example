"""project api"""
import json
import math
import logging
from datetime import datetime
from sqlalchemy import desc, func

from flask import Flask
from flask import request, Response
from flasgger import Swagger
from flask_caching import Cache
from flask_cors import CORS

from dateutil.relativedelta import relativedelta
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from settings import API_PORT, PAGINATION_LIMIT, API_URL

from parsers.parsers_tools import ExampleParser
from utils.psql_utils import create_session

from db.models import Headers, Articles

app = Flask(__name__)
Swagger(app)
CORS(app)

cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

app.config['headers'] = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Credentials': True,
    'Access-Control-Allow-Methods': ['GET', 'DELETE', 'HEAD', 'OPTIONS', 'POST', 'PUT'],
    'Access-Control-Allow-Headers': [
        'Access-Control-Allow-Headers', 'Origin', 'Accept', 'X-Requested-With',
        'Content-Type', 'Access-Control-Request-Method', 'Access-Control-Request-Headers',
        'X-CSRF-TOKEN', 'Authorization'
    ]
}


cache_opts = {
    'cache.type': 'memory',
    'cache.lock_dir': '/tmp/cache/lock'
}
func_cache = CacheManager(**parse_cache_config_options(cache_opts))


@func_cache.cache('select', expire=3600)
def news_in_period(session, start: datetime, finish: datetime):
    """
    return news in select period
    :param session:
    :param start:
    :param finish:
    :return:
    """
    headers = session.query(func.count(Headers.published_date)).filter(
        Headers.published_date >= start,
        Headers.published_date < finish
    )

    return headers.scalar()


@app.route('/headers/<int:year>/<int:month>', methods=['GET'])
@cache.cached(timeout=86400, query_string=True)
def return_headers(year, month):
    """
            API
            ---
            tags:
              - Return Headers json(list of dicts)
            parameters:
              - name: year
                in: path
                type: integer
                default: '2020'
                description: year in int format
                required: True
              - name: month
                in: path
                type: integer
                default: '5'
                description: month in int format
                required: True
              - name: page
                in: query
                type: integer
                default: '1'
                description: page
                required: False
              - name: per_page
                in: query
                type: integer
                default: '30'
                description: records per page
                required: False
            responses:
              400:
                description: Bad request
              200:
                description: OK
                schema:
                  id: headers
                  properties:
                    pagination:
                        type: object
                        description: article text
                        properties:
                            last_page:
                                type: string
                                description: last page uri
                            next_page:
                                type: string
                                description: next page uri
                            current:
                                type: integer
                                description: current page number
                            total:
                                type: integer
                                description: total pages number
                            next:
                                type: integer
                                description: next page number
                    data:
                        type: object
                        description: article id
                        properties:
                            id:
                                type: integer
                                description: header id
                            heading:
                                type: string
                                description: header text
                            published_at:
                                type: string
                                description: date when article was published
              500:
                description: INTERNAL SERVER ERROR
              401:
                description: Unauthorized


    """
    month_start = datetime(year, month, 1)
    month_end = month_start + relativedelta(months=1)

    page = int(request.args.get('page', 1))
    records_per_page = int(request.args.get('per_page', PAGINATION_LIMIT))

    with create_session() as session:
        headers_count = news_in_period(session, month_start, month_end)

        headers = session.query(Headers).filter(
            Headers.published_date >= month_start,
            Headers.published_date < month_end
        ).order_by(
            desc(Headers.published_date),
            desc(Headers.id)
        ).limit(
            records_per_page
        ).offset(
            (page - 1)*records_per_page
        ).all()

        news = [
            {
                'id': header.id,
                'heading': header.heading,
                'published_at': header.published_date.isoformat()
            } for header in headers
        ]
    if news:
        pages_count = math.ceil(headers_count / records_per_page)
        next_page = page + 1 if page + 1 < pages_count else pages_count
        result_dict = {
            'pagination': {
                'last_page': f"{API_URL}headers/{year}/{month}?page={pages_count}",
                'next_page': f"{API_URL}headers/{year}/{month}?page={next_page}",
                'current': page,
                'total': pages_count,
                'next': next_page
            },
            'data': news
        }
        return Response(
            json.dumps(result_dict), content_type='application/json', headers=app.config['headers']
        )

    else:
        return Response(
            status=404
        )


@app.route('/articles/<int:header_id>/', methods=['GET'])
@cache.cached(timeout=86400)
def return_article(header_id):
    """
            API
            ---
            tags:
              - Return Articles json(list of dicts)
            parameters:
              - name: header_id
                in: path
                type: integer
                default: '194069'
                description: id that return from /headers/ method
                required: True
            responses:
              400:
                description: Bad request
              200:
                description: OK
                schema:
                  id: articles
                  properties:
                    content:
                        type: string
                        description: article text
                    id:
                        type: integer
                        description: article id
                    heading:
                        type: string
                        description: header text
                    published_at:
                        type: string
                        description: date when published article
              500:
                description: INTERNAL SERVER ERROR
              401:
                description: Unauthorized
    """
    with create_session() as session:
        try:
            # pylint: disable=maybe-no-member
            data = list(session.query(Articles, Headers).join(
                Headers, Articles.headers_id == Headers.id
            ).filter(
                Articles.headers_id == header_id
            ).values(
                Articles.article_text, Headers.id,
                Headers.heading, Headers.published_date
            ))[0]

            article_info = {
                'content': data.article_text,
                'id': header_id,
                'heading': data.heading,
                'published_at': data.published_date.isoformat()
            }
        except IndexError as error:
            logging.exception(error)

            article_info = session.query(Headers).filter(
                Headers.id == header_id
            ).first()
            parser = ExampleParser()

            article = parser.parse_articles([(article_info.id, article_info.link)])
            if article:
                return article[0].get('article_text')
            else:
                return Response(status=404)
    return Response(json.dumps(article_info), content_type='application/json',
                    headers=app.config['headers'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=API_PORT)
