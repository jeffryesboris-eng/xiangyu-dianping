import asyncio
from sqlmodel import Session,select
import models
from db.mysql import engine
from utils.redis_ import aio_redis,GeoUtils
from utils.cache import CacheClient
from core.config import settings
assert settings.MYSQL_DATABASE=='hmdp_course' and settings.REDIS_DB==1
async def main():
 try:await aio_redis.xgroup_create('stream.orders','g1',id='0',mkstream=True)
 except Exception as e:
  if 'BUSYGROUP' not in str(e):raise
 with Session(engine) as s:
  cache=CacheClient(aio_redis)
  for shop in s.exec(select(models.Shop)).all():await cache.set_with_logical_expire(settings.CACHE_SHOP_KEY_PREFIX+str(shop.id),shop,1800)
  for v in s.exec(select(models.SeckillVoucher)).all():await aio_redis.set(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(v.voucher_id),v.stock,nx=True)
  for f in s.exec(select(models.Follow)).all():await aio_redis.sadd(settings.FOLLOW_KEY_PREFIX+str(f.user_id),f.follow_user_id)
 await GeoUtils.load_shop_geo_data()
 await aio_redis.close()
 print('Course cache and GEO ready')
asyncio.run(main())
