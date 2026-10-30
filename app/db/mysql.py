"""
    mysql
    ~~~

    

    :author: dilless(Huangbo)
    :date: 2022/7/11
"""
from sqlmodel import create_engine

from core.config import settings

engine = create_engine(
    f'mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}'
    f':{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}',
    pool_size=settings.DB_POOL_SIZE, max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT, pool_pre_ping=True, pool_recycle=1800,
    connect_args={'connect_timeout': 5, 'read_timeout': 10, 'write_timeout': 10})
