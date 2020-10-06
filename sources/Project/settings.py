"""project settings"""
from dotenv import load_dotenv
from pathlib import Path
import os

base_dir = Path(__file__).resolve().parent
load_dotenv(dotenv_path=base_dir / '.env')

# APP
PATH_TO_FIXTURES = base_dir / 'Fixtures'
BASE_URL = os.getenv('BASE_URL')
RSS_URL = os.getenv('RSS_URL')
DOMAIN = os.getenv('DOMAIN')
# DB
DB = os.getenv('POSTGRES_DB')
HOST = os.getenv('POSTGRES_HOST')
USER = os.getenv('POSTGRES_USER')
PASSWORD = os.getenv('POSTGRES_PASSWORD')
DRIVER = os.getenv('DRIVER')
ALCHEMY_URL = f'{DRIVER}://{USER}:{PASSWORD}@{HOST}/{DB}'
SCHEMA = os.getenv('SCHEMA', 'public')
# API
API_PORT = os.getenv('API_PORT')
PAGINATION_LIMIT = int(os.getenv('PAGINATION_LIMIT'))
API_HOST = os.getenv('API_HOST')
API_URL = f"{API_HOST}:{API_PORT}/"

