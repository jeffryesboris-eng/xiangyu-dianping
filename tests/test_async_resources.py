import asyncio,time
from unittest.mock import Mock
import pytest
from db.async_bridge import run_db
from app.api.endpoints import voucher_order as m

@pytest.mark.normal
def test_db_work_does_not_block_event_loop():
    async def exercise():
        ticks=[]
        async def heartbeat():
            for _ in range(5):
                await asyncio.sleep(.01);ticks.append(time.monotonic())
        start=time.monotonic()
        await asyncio.gather(run_db(time.sleep,.15),heartbeat())
        assert len(ticks)==5 and ticks[-1]-start<.13
    asyncio.run(exercise())

@pytest.mark.normal
def test_consumer_identity_is_unique():
    assert m.VoucherOrderHandler().consumer_name!=m.VoucherOrderHandler().consumer_name

@pytest.mark.abnormal
def test_delivery_failure_keeps_pending_and_counts_retry(monkeypatch):
    r=Mock();monkeypatch.setattr(m,'redis',r)
    handler=m.VoucherOrderHandler();handler.process_message=Mock(side_effect=RuntimeError('db unavailable'))
    handler.deliver('1-0',{})
    r.hincrby.assert_called_once_with('stream.orders:retries','1-0',1)
    r.xack.assert_not_called()
@pytest.mark.integration
@pytest.mark.abnormal
def test_abandoned_consumer_message_is_reclaimed(monkeypatch):
    import redis,uuid,threading
    r=redis.Redis(host='127.0.0.1',port=6380,db=15,decode_responses=True)
    stream='pytest:recover:'+uuid.uuid4().hex
    stop=threading.Event();monkeypatch.setattr(m,'consumer_stop',stop);monkeypatch.setattr(m,'redis',r);monkeypatch.setattr(m,'IS_RUNNING',True);monkeypatch.setattr(m.settings,'ORDER_RECLAIM_MS',0)
    handler=m.VoucherOrderHandler();handler.stream_name=stream
    seen=[]
    def save(order):seen.append(order.id);stop.set()
    monkeypatch.setattr(handler,'create_voucher_order',save)
    try:
        r.xgroup_create(stream,'g1',id='0',mkstream=True)
        mid=r.xadd(stream,{'id':'999','user_id':'987654321','voucher_id':'888'})
        r.xreadgroup('g1','crashed-worker',{stream:'>'},1)
        assert r.xpending(stream,'g1')['pending']==1
        thread=threading.Thread(target=handler,daemon=True);thread.start();thread.join(5)
        assert not thread.is_alive() and seen==[999]
        assert r.xpending(stream,'g1')['pending']==0
    finally:
        stop.set();r.delete(stream)
