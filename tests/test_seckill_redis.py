from concurrent.futures import ThreadPoolExecutor
import uuid
import redis
import pytest
from app.api.endpoints import voucher_order as m

@pytest.mark.integration
@pytest.mark.concurrency
@pytest.mark.parametrize('same_user',[True,False])
def test_real_lua_reservation(same_user):
    # Reuse the endpoint's actual Lua, with a unique test stream name.
    lua=next(c for c in m.seckill_voucher.__code__.co_consts if isinstance(c,str) and '-- seckill' in c)
    prefix='pytest:seckill:'+uuid.uuid4().hex
    stock,orders,stream=prefix+':stock',prefix+':orders',prefix+':stream'
    lua=lua.replace("'stream.orders'",repr(stream))
    r=redis.Redis(host='127.0.0.1',port=6380,db=15,decode_responses=True)
    try:
        r.set(stock,3)
        def reserve(i):return r.eval(lua,2,stock,orders,1 if same_user else i+1,123,str(100+i))
        with ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(reserve,range(12)))
        accepted=1 if same_user else 3
        assert results.count(0)==accepted
        assert int(r.get(stock))==3-accepted
        assert r.scard(orders)==accepted
        assert r.xlen(stream)==accepted
    finally:r.delete(stock,orders,stream)
