import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid
import pytest
from sqlmodel import Session,select
from sqlalchemy import text
from db.mysql import engine
from core.config import settings
from app.api.endpoints import voucher_order as m
import models

pytestmark=[pytest.mark.integration,pytest.mark.concurrency]

@pytest.fixture
def fixture(monkeypatch):
    assert settings.MYSQL_DATABASE=='hmdp_test', 'Integration tests only run against hmdp_test'
    ident=1000000000+uuid.uuid4().int%1000000000
    monkeypatch.setattr(m,'engine',engine)
    with Session(engine) as s:
        s.add(models.SeckillVoucher(voucher_id=ident,stock=3,begin_time=dt.datetime.now(),end_time=dt.datetime.now()));s.commit()
    try:yield ident
    finally:
        with engine.begin() as c:
            c.execute(text('DELETE FROM tb_voucher_order WHERE voucher_id=:id'),{'id':ident})
            c.execute(text('DELETE FROM tb_seckill_voucher WHERE voucher_id=:id'),{'id':ident})

@pytest.mark.parametrize('same_user',[True,False])
def test_database_concurrency(fixture,same_user):
    barrier=Barrier(12)
    def submit(i):
        barrier.wait(timeout=10)
        try:
            m.VoucherOrderHandler().create_voucher_order(models.VoucherOrder(id=fixture*100+i,user_id=fixture if same_user else fixture+i,voucher_id=fixture))
            return True
        except RuntimeError as e:
            assert str(e)=='库存不足'
            return False
    with ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(submit,range(12)))
    with Session(engine) as s:
        orders=s.exec(select(models.VoucherOrder).where(models.VoucherOrder.voucher_id==fixture)).all()
        assert len(orders)==(1 if same_user else 3)
        assert s.get(models.SeckillVoucher,fixture).stock==3-len(orders)
        assert len({o.user_id for o in orders})==len(orders)
    if not same_user:assert sum(results)==3
