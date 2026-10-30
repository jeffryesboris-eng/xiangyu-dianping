import datetime as dt
from unittest.mock import Mock
import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from app.api.endpoints import voucher_order as module
import models

@pytest.fixture
def db(monkeypatch, tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'orders.db'))
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(module, 'engine', engine)
    with Session(engine) as s:
        s.add(models.SeckillVoucher(voucher_id=1, stock=2, begin_time=dt.datetime.now(), end_time=dt.datetime.now()))
        s.commit()
    return engine

def order():
    return models.VoucherOrder(id=123, user_id=1, voucher_id=1)

@pytest.mark.abnormal
def test_insert_failure_rolls_back_stock(db):
    with Session(db) as s:
        s.add(models.VoucherOrder(id=123,user_id=2,voucher_id=2))
        s.commit()
    with pytest.raises(Exception):
        module.VoucherOrderHandler().create_voucher_order(order())
    with Session(db) as s:
        assert s.get(models.SeckillVoucher,1).stock == 2
        assert len(s.exec(select(models.VoucherOrder)).all()) == 1

@pytest.mark.normal
def test_redelivery_only_deducts_once(db):
    h=module.VoucherOrderHandler()
    h.create_voucher_order(order())
    h.create_voucher_order(order())
    with Session(db) as s:
        assert s.get(models.SeckillVoucher,1).stock == 1
        assert len(s.exec(select(models.VoucherOrder)).all()) == 1

@pytest.mark.concurrency
def test_lock_contention_never_creates_or_acks(monkeypatch):
    r=Mock(); r.lock.return_value.acquire.return_value=False
    monkeypatch.setattr(module,'redis',r)
    h=module.VoucherOrderHandler(); h.create_voucher_order=Mock()
    assert h.process_message('1-0',order().dict()) is False
    h.create_voucher_order.assert_not_called()
    r.xack.assert_not_called()
    r.lock.return_value.release.assert_not_called()

@pytest.mark.abnormal
def test_failure_releases_lock_without_ack(monkeypatch):
    r=Mock(); monkeypatch.setattr(module,'redis',r)
    h=module.VoucherOrderHandler(); h.create_voucher_order=Mock(side_effect=RuntimeError('fail'))
    with pytest.raises(RuntimeError): h.process_message('1-0',order().dict())
    r.xack.assert_not_called()
    r.lock.return_value.release.assert_called_once()

@pytest.mark.abnormal
def test_expired_lease_does_not_release_new_owner(monkeypatch):
    from redis.exceptions import LockNotOwnedError
    r=Mock(); r.lock.return_value.release.side_effect=LockNotOwnedError('expired')
    monkeypatch.setattr(module,'redis',r)
    h=module.VoucherOrderHandler(); h.create_voucher_order=Mock()
    assert h.process_message('1-0',order().dict())
    r.xack.assert_called_once()

@pytest.mark.boundary
def test_empty_pending_entries(monkeypatch):
    r=Mock(); r.xreadgroup.return_value=[('stream.orders',[])]
    monkeypatch.setattr(module,'redis',r)
    module.VoucherOrderHandler().handel_pending_list()
