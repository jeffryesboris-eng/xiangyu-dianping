"""Deterministic, additive demo dataset. Never deletes rows or resets stock."""
import asyncio, datetime as dt, html, json, math
from pathlib import Path
from collections import Counter
from sqlmodel import Session, select
from sqlalchemy import text
import redis
import models
from core.config import settings
from db.mysql import engine
from utils.cache import CacheClient
from utils.redis_ import aio_redis
assert settings.MYSQL_DATABASE=='hmdp_course' and settings.REDIS_DB==1
now=dt.datetime.now()
asset=Path(settings.IMAGE_UPLOAD_DIR)/'demo';asset.mkdir(parents=True,exist_ok=True)
areas=[('运河商圈',120.149192,30.316078),('武林商圈',120.164,30.278),('西湖商圈',120.153,30.25),('滨江商圈',120.211,30.208)]
brands=['拾光','巷里','青禾','慢岛','木白','晴川','山间','橙光','云朵','松间','南风','白露','星野','初见','知夏','春山','向晚','四季','沐光','小满']
suffix={1:'小馆',2:'音乐空间',3:'剧场',4:'运动馆',5:'养生馆',6:'美学空间',7:'亲子乐园',8:'小酒馆',9:'汤泉',10:'研习社'}
colors=['#527560','#6b6488','#b37958','#4d7e8c','#688870','#ad7f8e','#bc9b55','#66739c','#599b9a','#8d775a']
created=Counter();shops=[];blogs=[];stocks=[];follows=[]
with Session(engine) as s:
    before={t:s.exec(text('SELECT COUNT(*) FROM '+t)).scalar() for t in ['tb_shop','tb_blog','tb_voucher','tb_voucher_order']}
    def add(row,identity):
        pk=row.voucher_id if isinstance(row,models.SeckillVoucher) else row.id
        old=s.get(type(row),pk)
        if old is not None:
            for field in identity:
                if getattr(old,field)!=getattr(row,field):raise RuntimeError(f'ID conflict: {type(row).__name__} {pk}')
        else:s.add(row);created[type(row).__name__]+=1
        return old or row
    types=s.exec(select(models.ShopType).order_by(models.ShopType.id)).all()
    assert len(types)==10
    for i in range(20):
        add(models.User(id=30001+i,phone=f'1399000{i:04}',password='',nick_name=f'演示·城市探索者{i+1:02}',icon=''),['phone','nick_name'])
    s.flush()
    for ti,t in enumerate(types):
        for j in range(20):
            n=ti*20+j;sid=20001+n;area,x,y=areas[j%4]
            name=f'演示·{brands[j]}{suffix[t.id]}'
            x+=math.cos(j*2.4)*(.001+(j//4)*.002);y+=math.sin(j*2.4)*(.001+(j//4)*.0015)
            pic=f'/imgs/demo/shop-{sid}.svg';color=colors[ti]
            # Locally generated vector illustration, with safe escaped labels.
            svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="650" viewBox="0 0 1000 650"><rect width="1000" height="650" fill="#ede9df"/><circle cx="810" cy="115" r="130" fill="{color}" opacity=".18"/><path d="M0 530 Q250 390 500 540 T1000 500V650H0" fill="{color}" opacity=".2"/><rect x="225" y="180" width="550" height="320" rx="12" fill="{color}"/><path d="M195 220L260 130H740L805 220Z" fill="#d9bb83"/><rect x="270" y="260" width="175" height="170" rx="8" fill="#f6efdf"/><rect x="555" y="260" width="175" height="170" rx="8" fill="#f6efdf"/><path d="M357 260V430M270 345H445M642 260V430M555 345H730" stroke="{color}" stroke-width="10"/><rect x="465" y="330" width="70" height="170" fill="#d9bb83"/><text x="500" y="303" text-anchor="middle" fill="white" font-size="23" font-family="Microsoft YaHei,sans-serif">{html.escape(brands[j]+suffix[t.id])}</text><text x="55" y="70" fill="{color}" font-size="25" font-family="Microsoft YaHei,sans-serif">{html.escape(t.name)} / XIANGYU</text><text x="55" y="600" fill="{color}" font-size="23" font-family="Microsoft YaHei,sans-serif">演示商户 · 非真实店铺</text></svg>'''
            (asset/f'shop-{sid}.svg').write_text(svg,encoding='utf-8')
            shop=add(models.Shop(id=sid,name=name,type_id=t.id,images=pic,area=area,address=f'演示地址·杭州{area}体验街{j+1}号',x=x,y=y,avg_price=[38,68,98,128,168][j%5],sold=30+j*29,comments=0,score=38+j%13,open_hours=['09:00-21:00','10:00-22:00','13:00-23:00'][j%3],create_time=now,update_time=now),['name','type_id']);shops.append(shop)
            for k in range(2):
                bid=40001+n*2+k;uid=30001+(n+k)%20
                blog=add(models.Blog(id=bid,shop_id=sid,user_id=uid,title=f'演示探店｜{brands[j]}{suffix[t.id]}'+('，周末慢下来' if k==0 else '，值得记录的小细节'),images=pic,content=f'【演示内容】这是一篇用于体验点评平台的虚构笔记，不是真实消费者评价。\n\n今天探索的是{area}的{brands[j]}{suffix[t.id]}。空间以舒适、放松为设计主题，适合约上朋友体验{t.name}。\n\n演示人均：{shop.avg_price}元；演示营业时间：{shop.open_hours}。页面的价格、评分与地址均为测试数据。\n\n本笔记用于测试浏览、点赞、关注和动态分页。',liked=0,comments=0,create_time=now-dt.timedelta(minutes=n*2+k),update_time=now),['title','shop_id','user_id']);blogs.append(blog)
            for kind in range(2):
                vid=(50001 if kind==0 else 60001)+n
                add(models.Voucher(id=vid,shop_id=sid,title=f'演示·{brands[j]}'+('到店代金券' if kind==0 else '限时秒杀体验券'),sub_title='仅供系统体验，不可真实兑换',rules='虚构演示活动，不涉及支付，不可到店核销。',pay_value=2900 if kind==0 else 990,actual_value=5000,type=kind,status=1,create_time=now,update_time=now),['shop_id','title','type'])
                if kind:
                    stocks.append(add(models.SeckillVoucher(voucher_id=vid,stock=50,begin_time=now-dt.timedelta(days=1),end_time=now+dt.timedelta(days=90),create_time=now,update_time=now),['voucher_id']))
    for i in range(20):
        f=add(models.Follow(id=70001+i,user_id=30001+i,follow_user_id=30001+(i+1)%20),['user_id','follow_user_id']);follows.append(f)
    s.commit()
    after={t:s.exec(text('SELECT COUNT(*) FROM '+t)).scalar() for t in before}
    assert before['tb_voucher_order']==after['tb_voucher_order']
    # Detach populated objects for async cache setup after committing.
    for row in shops+blogs+stocks+follows:s.refresh(row)
    s.expunge_all()
async def prepare():
    cache=CacheClient(aio_redis)
    for shop in shops:
        await cache.set_with_logical_expire(settings.CACHE_SHOP_KEY_PREFIX+str(shop.id),shop,1800)
        await aio_redis.geoadd(settings.SHOP_GEO_KEY_PREFIX+str(shop.type_id),[shop.x,shop.y,shop.id])
    for v in stocks:await aio_redis.set(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(v.voucher_id),v.stock,nx=True)
    for f in follows:
        await aio_redis.sadd(settings.FOLLOW_KEY_PREFIX+str(f.user_id),f.follow_user_id)
        for blog in blogs:
            if blog.user_id==f.follow_user_id:
                await aio_redis.zadd(settings.FEED_KEY_PREFIX+str(f.user_id),{blog.id:int(blog.create_time.timestamp()*1000)})
    await aio_redis.close()
asyncio.run(prepare())
report={'created':dict(created),'before':before,'after':after,'shop_ids':[20001,20200],'blog_ids':[40001,40400],'voucher_ids':[[50001,50200],[60001,60200]],'images':200}
Path('.local/demo-import-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
