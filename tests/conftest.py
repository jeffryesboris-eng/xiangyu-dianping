import os
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'app')]
os.environ.setdefault('MYSQL_HOST','127.0.0.1')
os.environ.setdefault('MYSQL_PORT','3307')
os.environ.setdefault('MYSQL_USER','hmdp_test')
os.environ.setdefault('MYSQL_PASSWORD','hmdp_test_local')
os.environ.setdefault('MYSQL_DATABASE','hmdp_test')
os.environ.setdefault('REDIS_HOST','127.0.0.1')
os.environ.setdefault('REDIS_PORT','6380')
import pytest

def pytest_addoption(parser):
    parser.addoption('--integration',action='store_true',help='Run real MySQL concurrency tests')

def pytest_collection_modifyitems(config,items):
    if not config.getoption('--integration'):
        for item in items:
            if 'integration' in item.keywords:item.add_marker(pytest.mark.skip(reason='requires --integration'))
