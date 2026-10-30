import datetime as dt
from unittest.mock import AsyncMock,Mock
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from sqlmodel import Session
from app.api.endpoints import voucher_order as m
from test_voucher_orders import db
import models

@pytest.fixture
def client(db,monkeypatch):
    app=FastAPI()
    app.include_router(m.router,prefix='/voucher-order')
    # TestClient without lifespan: do not start a background consumer.
    r=Mock();r.hgetall=AsyncMock(return_value={'id':'1','nick_name':'tester'})
    monkeypatch.setattr(m.deps,'aio_redis',r)
    ar=Mock();ar.eval=AsyncMock(return_value=0)
    monkeypatch.setattr(m,'aio_redis',ar)
    monkeypatch.setattr(m.redis_id_worker,'next_id',AsyncMock(return_value=9007199254740993))
    with Session(db) as s:
        v=s.get(models.SeckillVoucher,1);v.begin_time=dt.datetime.now()-dt.timedelta(days=1);v.end_time=dt.datetime.now()+dt.timedelta(days=1);s.add(v);s.commit()
    return TestClient(app),ar,r

@pytest.mark.normal
def test_accept_order_as_exact_string(client):
    c,r,_=client
    res=c.post('/voucher-order/seckill/1',headers={'authorization':'valid'})
    assert res.status_code==200 and res.json()['data']=='9007199254740993'
    r.eval.assert_awaited_once()

@pytest.mark.boundary
@pytest.mark.parametrize('value',['abc','1.5','null'])
def test_invalid_id(client,value):
    c,r,_=client
    assert c.post('/voucher-order/seckill/'+value,headers={'authorization':'valid'}).status_code==422
    r.eval.assert_not_awaited()

@pytest.mark.boundary
@pytest.mark.parametrize('value',['0','-1','999999'])
def test_absent_voucher(client,value):
    c,r,_=client
    res=c.post('/voucher-order/seckill/'+value,headers={'authorization':'valid'})
    assert res.json()['success'] is False and res.json()['errorMsg']=='优惠券不存在'
    r.eval.assert_not_awaited()

@pytest.mark.boundary
@pytest.mark.parametrize('phase',['future','expired'])
def test_time_window(client,db,phase):
    c,r,_=client
    with Session(db) as s:
        v=s.get(models.SeckillVoucher,1)
        if phase=='future':v.begin_time=dt.datetime.now()+dt.timedelta(days=1)
        else:v.end_time=dt.datetime.now()-dt.timedelta(days=1)
        s.add(v);s.commit()
    result=c.post('/voucher-order/seckill/1',headers={'authorization':'valid'}).json()
    assert result['success'] is False
    assert result['errorMsg']==('秒杀尚未开始' if phase=='future' else '秒杀已经结束')
    r.eval.assert_not_awaited()

@pytest.mark.boundary
@pytest.mark.parametrize('code,message',[(1,'库存不足'),(2,'不能重复下单')])
def test_rejection(client,code,message):
    c,r,_=client;r.eval.return_value=code
    result=c.post('/voucher-order/seckill/1',headers={'authorization':'valid'}).json()
    assert result['success'] is False and result['errorMsg']==message

@pytest.mark.permission
def test_no_header(client):
    c,r,_=client
    assert c.post('/voucher-order/seckill/1').status_code==422
    r.eval.assert_not_awaited()

@pytest.mark.permission
def test_invalid_token(client):
    c,r,auth=client;auth.hgetall.return_value={}
    assert c.post('/voucher-order/seckill/1',headers={'authorization':'invalid'}).status_code==401
    r.eval.assert_not_awaited()

@pytest.mark.permission
@pytest.mark.parametrize('owner,expected',[(1,'confirmed'),(2,'pending')])
def test_order_visibility(client,db,owner,expected):
    with Session(db) as s:
        s.add(models.VoucherOrder(id=123,user_id=owner,voucher_id=1));s.commit()
    c,_,_=client
    assert c.get('/voucher-order/status/123',headers={'authorization':'valid'}).json()['data']['status']==expected

@pytest.mark.abnormal
def test_redis_failure_is_visible(client):
    c,r,_=client;r.eval.side_effect=ConnectionError('redis unavailable')
    with pytest.raises(ConnectionError):c.post('/voucher-order/seckill/1',headers={'authorization':'valid'})
