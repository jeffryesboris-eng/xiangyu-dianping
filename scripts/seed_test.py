"""Create isolated local test tables and seed data; never flush existing data."""
import asyncio
import datetime as dt
import pymysql
from sqlmodel import SQLModel, Session, select
from core.config import settings

assert settings.MYSQL_DATABASE == 'hmdp_test'
assert settings.MYSQL_HOST == settings.REDIS_HOST == '127.0.0.1'
assert settings.MYSQL_PORT == 3307 and settings.REDIS_PORT == 6380
connection = pymysql.connect(host='127.0.0.1', port=3307, user='root')
with connection.cursor() as c:
    c.execute('CREATE DATABASE IF NOT EXISTS hmdp_test CHARACTER SET utf8mb4')
    c.execute("CREATE USER IF NOT EXISTS 'hmdp_test'@'localhost' IDENTIFIED BY 'hmdp_test_local'")
    c.execute("GRANT ALL ON hmdp_test.* TO 'hmdp_test'@'localhost'")
connection.close()
import models
from db.mysql import engine
from utils.redis_ import aio_redis, GeoUtils
from utils.cache import CacheClient

SQLModel.metadata.create_all(engine)
with engine.begin() as conn:
    conn.exec_driver_sql('ALTER TABLE tb_voucher_order MODIFY COLUMN id BIGINT NOT NULL')
now = dt.datetime.now()
rows = [
    models.User(id=1, phone='13800000001', password='', nick_name='测试用户甲'),
    models.User(id=2, phone='13800000002', password='', nick_name='测试用户乙'),
    models.User(id=3, phone='13800000003', password='', nick_name='测试用户丙'),
    models.UserInfo(user_id=1, city='上海'),
    models.ShopType(id=1, name='美食', icon='', sort=1),
    models.Shop(id=1, name='测试咖啡店', type_id=1, images='', address='上海测试路1号', x=121.4737, y=31.2304, sold=0, comments=0, score=50),
    models.Shop(id=2, name='测试面馆', type_id=1, images='', address='上海测试路2号', x=121.4747, y=31.2314, sold=0, comments=0, score=45),
    models.Blog(id=1, shop_id=1, user_id=1, title='测试探店', images='', content='本地测试样例'),
    models.Follow(id=1, user_id=1, follow_user_id=3),
    models.Follow(id=2, user_id=2, follow_user_id=3),
    models.Voucher(id=1, shop_id=1, title='测试秒杀券', pay_value=5000, actual_value=10000, type=1, status=1),
    models.SeckillVoucher(voucher_id=1, stock=10, begin_time=now-dt.timedelta(days=1), end_time=now+dt.timedelta(days=30)),
]
with Session(engine) as s:
    for row in rows:
        pk = row.voucher_id if isinstance(row, models.SeckillVoucher) else row.user_id if isinstance(row, models.UserInfo) else row.id
        if s.get(type(row), pk) is None:
            s.add(row)
    s.commit()

async def main():
    assert await aio_redis.ping()
    try:
        await aio_redis.xgroup_create('stream.orders', 'g1', id='0', mkstream=True)
    except Exception as e:
        if 'BUSYGROUP' not in str(e):
            raise
    with Session(engine) as s:
        stock = s.get(models.SeckillVoucher, 1).stock
        await aio_redis.set(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+'1', stock, nx=True)
        cache = CacheClient(aio_redis)
        for shop in s.exec(select(models.Shop)).all():
            await cache.set_with_logical_expire(settings.CACHE_SHOP_KEY_PREFIX+str(shop.id), shop, 1800)
    await GeoUtils.load_shop_geo_data()
    for uid in (1, 2):
        await aio_redis.sadd(settings.FOLLOW_KEY_PREFIX+str(uid), 3)
    print('Seed OK: 10 tables, users 1/2/3, shops 1/2, voucher 1, stream.orders/g1')
    await aio_redis.close()

asyncio.run(main())
