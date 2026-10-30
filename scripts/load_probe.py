"""Bounded local read/seckill probe, with independent disposable fixture."""
import concurrent.futures as cf,time,statistics,json,uuid,datetime as dt
from pathlib import Path
import requests,redis,pymysql
from sqlmodel import Session,select
from sqlalchemy import text
from db.mysql import engine
from core.config import settings
import models
assert settings.MYSQL_DATABASE=='hmdp_course' and settings.REDIS_DB==1
base='http://127.0.0.1:8081';r=redis.Redis(port=6380,db=1,decode_responses=True)
report={'workers':1,'db_pool_max':10,'request_threads':8,'read':[]}
def summarize(rows,elapsed):
 times=sorted(v[0] for v in rows)
 return {'requests':len(rows),'errors':sum(not v[1] for v in rows),'p50_ms':round(statistics.median(times)*1000,2),'p95_ms':round(times[int((len(times)-1)*.95)]*1000,2),'rps':round(len(rows)/elapsed,2)}
for concurrency in [1,8,24]:
 def read(i):
  start=time.perf_counter()
  try:
   res=requests.get(base+['/shop/of/name?name=演示','/blog/hot','/shop/of/type?typeId=4'][i%3],timeout=15)
   ok=res.status_code==200 and res.json()['success']
  except Exception:ok=False
  return time.perf_counter()-start,ok
 start=time.perf_counter()
 with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:rows=list(pool.map(read,range(90)))
 report['read'].append({'concurrency':concurrency,**summarize(rows,time.perf_counter()-start)})
vid=800000000+uuid.uuid4().int%10000000;tokens=[];accepted=[]
try:
 with Session(engine) as s:
  s.add(models.SeckillVoucher(voucher_id=vid,stock=10,begin_time=dt.datetime.now()-dt.timedelta(days=1),end_time=dt.datetime.now()+dt.timedelta(days=1)));s.commit()
 r.set(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(vid),10)
 for i in range(30):
  token='probe-'+uuid.uuid4().hex;tokens.append(token)
  r.hset(settings.LOGIN_USER_OBJ_KEY_PREFIX+token,mapping={'id':vid+i,'nick_name':'load-probe'});r.expire(settings.LOGIN_USER_OBJ_KEY_PREFIX+token,120)
 def order(i):
  start=time.perf_counter();res=requests.post(base+'/voucher-order/seckill/'+str(vid),headers={'authorization':tokens[i]},timeout=15)
  data=res.json()
  if data['success']:accepted.append(data['data'])
  return time.perf_counter()-start,res.status_code==200
 start=time.perf_counter()
 with cf.ThreadPoolExecutor(max_workers=24) as pool:rows=list(pool.map(order,range(30)))
 report['seckill']=summarize(rows,time.perf_counter()-start);report['seckill']['accepted']=len(accepted)
 deadline=time.monotonic()+15
 while True:
  with Session(engine) as s:orders=s.exec(select(models.VoucherOrder).where(models.VoucherOrder.voucher_id==vid)).all();stock=s.get(models.SeckillVoucher,vid).stock
  if len(orders)==len(accepted) or time.monotonic()>deadline:break
  time.sleep(.1)
 report['seckill'].update(persisted=len(orders),mysql_stock=stock,redis_stock=int(r.get(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(vid))),group_pending=r.xpending('stream.orders','g1')['pending'],groups=r.xinfo_groups('stream.orders'))
 assert len(orders)==len(accepted)==10 and stock==0
 # Root read-only metrics, application account cannot inspect performance_schema.
 admin=pymysql.connect(host='127.0.0.1',port=3307,user='root')
 with admin.cursor() as cur:
  cur.execute("SHOW GLOBAL STATUS WHERE Variable_name IN ('Innodb_row_lock_waits','Innodb_row_lock_time','Threads_connected')");report['mysql_cumulative_metrics']=dict(cur.fetchall())
  cur.execute('SELECT COUNT(*) FROM performance_schema.data_lock_waits');report['mysql_current_lock_waits']=cur.fetchone()[0]
 admin.close()
finally:
 with engine.begin() as c:
  c.execute(text('DELETE FROM tb_voucher_order WHERE voucher_id=:id'),{'id':vid});c.execute(text('DELETE FROM tb_seckill_voucher WHERE voucher_id=:id'),{'id':vid})
 for mid,fields in r.xrange('stream.orders'):
  if fields.get('voucher_id')==str(vid):r.xack('stream.orders','g1',mid);r.xdel('stream.orders',mid)
 r.delete(settings.CACHE_SECKILL_STOCK_KEY_PREFIX+str(vid),settings.CACHE_SECKILL_ORDER_KEY_PREFIX+str(vid),*[settings.LOGIN_USER_OBJ_KEY_PREFIX+t for t in tokens])
Path('.local/load-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
