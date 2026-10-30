"""Add a dedicated seckill fixture without resetting existing orders or stock."""
import datetime as dt
import redis
from sqlmodel import Session, select
from core.config import settings
from db.mysql import engine
import models
assert settings.MYSQL_DATABASE == 'hmdp_course' and settings.REDIS_DB == 1
voucher_id = 9001
with Session(engine) as s:
    with s.begin():
        existing = s.get(models.Voucher, voucher_id)
        if existing and existing.title != '幂等测试专用秒杀券':
            raise RuntimeError('Voucher ID 9001 is occupied')
        if not existing:
            s.add(models.Voucher(id=voucher_id, shop_id=1, title='幂等测试专用秒杀券',
                sub_title='仅供本地学习测试，每人限购一张', rules='测试券，不可真实兑换',
                pay_value=100, actual_value=5000, type=1, status=1))
            s.add(models.SeckillVoucher(voucher_id=voucher_id, stock=100,
                begin_time=dt.datetime.now()-dt.timedelta(minutes=5),
                end_time=dt.datetime.now()+dt.timedelta(days=90)))
        for i in range(1, 4):
            phone=f'1380000000{i}'
            if s.exec(select(models.User).where(models.User.phone==phone)).first() is None:
                s.add(models.User(phone=phone, password='', nick_name=f'秒杀测试用户{i}'))
    stock = s.get(models.SeckillVoucher,voucher_id).stock
r=redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, decode_responses=True)
r.set(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(voucher_id), stock, nx=True)
try:r.xgroup_create('stream.orders','g1',id='0',mkstream=True)
except redis.ResponseError as e:
    if 'BUSYGROUP' not in str(e):raise
print('Voucher:',voucher_id,'MySQL stock:',stock,'Redis stock:',r.get(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(voucher_id)))
print('Accounts: 13800000001 / 13800000002 / 13800000003')
