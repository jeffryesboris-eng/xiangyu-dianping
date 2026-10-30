"""Add visible demo seckill vouchers to course shops without resetting purchases."""
import datetime as dt
import redis
from sqlmodel import Session, select
from core.config import settings
from db.mysql import engine
import models
assert settings.MYSQL_DATABASE=='hmdp_course' and settings.REDIS_DB==1
r=redis.Redis(host=settings.REDIS_HOST,port=settings.REDIS_PORT,db=settings.REDIS_DB,decode_responses=True)
now=dt.datetime.now()
with Session(engine) as s:
    shops=s.exec(select(models.Shop)).all()
    for shop in shops:
        vid=10000+shop.id
        title=f'{shop.name} · 限时体验券'
        existing=s.get(models.Voucher,vid)
        if existing and existing.title!=title:raise RuntimeError(f'Voucher ID conflict: {vid}')
        if not existing:
            s.add(models.Voucher(id=vid,shop_id=shop.id,title=title,
                sub_title='演示专享 · 每人限购一张',rules='仅供本地项目体验，不可到店兑换，不涉及真实支付。',
                pay_value=990 if shop.id%2 else 1990,actual_value=5000 if shop.id%2 else 10000,type=1,status=1))
            s.add(models.SeckillVoucher(voucher_id=vid,stock=50,begin_time=now-dt.timedelta(minutes=5),end_time=now+dt.timedelta(days=90)))
    s.commit()
    for shop in shops:
        vid=10000+shop.id
        v=s.get(models.SeckillVoucher,vid)
        r.set(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(vid),v.stock,nx=True)
        print(shop.id,vid,v.stock)
try:r.xgroup_create('stream.orders','g1',id='0',mkstream=True)
except redis.ResponseError as e:
    if 'BUSYGROUP' not in str(e):raise
print('Imported demo vouchers:',len(shops))
