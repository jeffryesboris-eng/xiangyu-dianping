from db.async_bridge import run_db
"""
    voucher_order
    ~~~

    

    :author: dilless(Huangbo)
    :date: 2022/7/10
"""
import asyncio
import concurrent.futures
import datetime
import multiprocessing
import queue
import signal
import threading
import time
import os
import uuid
import logging
from fastapi import APIRouter, Path, Depends
from sqlmodel import Session, select
import models
import schemas
from api import deps
from core.config import settings
from db.mysql import engine
from utils.lock import SimpleRedisLock
from utils.redis_ import aio_redis, redis
from utils.redis_id import redis_id_worker
router = APIRouter()
IS_RUNNING = True
executor = None
consumer_stop = threading.Event()
logger = logging.getLogger(__name__)

class VoucherOrderHandler:
    stream_name = 'stream.orders'
    group_name = 'g1'

    def __init__(self):
        self.consumer_name = f'{os.getpid()}-{uuid.uuid4().hex}'
        self.claim_cursor = '0-0'
        self.next_retry = 0.0

    def deliver(self, message_id, fields):
        try:
            self.process_message(message_id, fields)
        except Exception:
            logger.exception('Order delivery failed: %s', message_id)
            # Keep failed reservations pending: never silently drop an accepted order.
            redis.hincrby('stream.orders:retries', message_id, 1)

    def process_message(self, message_id, fields):
        voucher_order = models.VoucherOrder.parse_obj(fields)
        lock = redis.lock(name=settings.REDIS_LOCK_KEY_PREFIX + 'order:' + str(voucher_order.user_id), timeout=10)
        if not lock.acquire(blocking=False):
            return False
        try:
            self.create_voucher_order(voucher_order)
            redis.xack(self.stream_name, self.group_name, message_id)
            redis.hdel('stream.orders:retries', message_id)
            return True
        finally:
            from redis.exceptions import LockNotOwnedError
            try:
                lock.release()
            except LockNotOwnedError:
                pass

    def __call__(self) -> None:
        from redis.exceptions import ResponseError
        delay = .2
        while IS_RUNNING and not consumer_stop.is_set():
            try:
                try:
                    redis.xgroup_create(self.stream_name, self.group_name, id='0', mkstream=True)
                except ResponseError as exc:
                    if 'BUSYGROUP' not in str(exc):
                        raise
                if time.monotonic() >= self.next_retry:
                    self.handel_pending_list()
                    claimed = redis.xautoclaim(self.stream_name, self.group_name,
                        self.consumer_name, settings.ORDER_RECLAIM_MS,
                        start_id=self.claim_cursor, count=20)
                    self.claim_cursor = claimed[0]
                    for message_id, fields in claimed[1]:
                        self.deliver(message_id, fields)
                    self.next_retry = time.monotonic() + 2
                messages = redis.xreadgroup(self.group_name, self.consumer_name,
                    {self.stream_name: '>'}, 10, 1000)
                for _, entries in messages:
                    for message_id, fields in entries:
                        self.deliver(message_id, fields)
                delay = .2
            except Exception:
                logger.exception('Order consumer recovering')
                consumer_stop.wait(delay)
                delay = min(delay * 2, 5)

    def handel_pending_list(self):
        messages = redis.xreadgroup(self.group_name, self.consumer_name,
            {self.stream_name: '0'}, 20)
        for _, entries in messages:
            for message_id, fields in entries:
                self.deliver(message_id, fields)

    def create_voucher_order(self, voucher_order):
        with Session(engine) as sess:
            with sess.begin():
                voucher = sess.exec(select(models.SeckillVoucher).where(models.SeckillVoucher.voucher_id == voucher_order.voucher_id).with_for_update()).first()
                if voucher is None:
                    raise RuntimeError('优惠券不存在')
                existing = sess.exec(select(models.VoucherOrder).where(models.VoucherOrder.user_id == voucher_order.user_id).where(models.VoucherOrder.voucher_id == voucher_order.voucher_id)).first()
                if existing is not None:
                    return schemas.GenericResponseModel(data=existing.id)
                if voucher.stock <= 0:
                    raise RuntimeError('库存不足')
                voucher.stock -= 1
                sess.add(voucher)
                sess.add(voucher_order)
                sess.flush()
            return schemas.GenericResponseModel(data=voucher_order.id)

@router.on_event('startup')
async def run_voucher_order_handler():
    global IS_RUNNING, executor
    IS_RUNNING = True
    consumer_stop.clear()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=settings.ORDER_CONSUMERS, thread_name_prefix="orders")
    for _ in range(settings.ORDER_CONSUMERS):
        executor.submit(VoucherOrderHandler())

@router.on_event('shutdown')
async def shutdown_thread_pool_executor():
    global IS_RUNNING
    IS_RUNNING = False
    consumer_stop.set()
    if executor is not None:
        await run_db(executor.shutdown, wait=True)

@router.post('/seckill/{voucher_id}', response_model=schemas.GenericResponseModel)
async def seckill_voucher(*, voucher_id: int=Path(), user: schemas.UserBaseModel=Depends(deps.verify_user)):
    lua_script = "\n        -- seckill\n        local stock_key = KEYS[1]\n        local order_key = KEYS[2]\n        \n        local user_id = ARGV[1]\n        local voucher_id = ARGV[2]\n        local order_id = ARGV[3]\n        \n        -- 判断库存是否充足\n        if (tonumber(redis.call('get', stock_key)) <= 0) then\n            return 1\n        end\n        \n        -- 是否已经秒杀了\n        if (redis.call('sismember', order_key, user_id) == 1) then\n            return 2\n        end\n        \n        -- 到这说明可以下单\n        redis.call('incrby', stock_key, -1)\n        redis.call('sadd', order_key, user_id)\n        -- 发送消息到队列\n        redis.call('xadd', 'stream.orders', '*', 'user_id', user_id, 'voucher_id', voucher_id, 'id', order_id)\n        return 0\n    "

    def _db_unit_1():
        with Session(engine) as sess:
            statement = select(models.SeckillVoucher).where(models.SeckillVoucher.voucher_id == voucher_id)
            sk_voucher = sess.exec(statement).first()
            now = datetime.datetime.now()
            if not sk_voucher:
                return (True, schemas.GenericResponseModel(success=False, error_msg='优惠券不存在'), None)
            if sk_voucher.begin_time > now:
                return (True, schemas.GenericResponseModel(success=False, error_msg='秒杀尚未开始'), None)
            if sk_voucher.end_time < now:
                return (True, schemas.GenericResponseModel(success=False, error_msg='秒杀已经结束'), None)
        locals_map = locals()
        return (False, None, tuple((locals_map.get(k) for k in ['now', 'sk_voucher', 'statement'])))
    _early, _value, _values = await run_db(_db_unit_1)
    if _early:
        return _value
    now, sk_voucher, statement = _values
    order_id = await redis_id_worker.next_id('order:')
    response = await aio_redis.eval(lua_script, 2, settings.CACHE_SECKILL_STOCK_KEY_PREFIX + str(voucher_id), settings.CACHE_SECKILL_ORDER_KEY_PREFIX + str(voucher_id), user.id, voucher_id, order_id)
    if response != 0:
        return schemas.GenericResponseModel(success=False, error_msg='库存不足' if response == 1 else '不能重复下单')
    return schemas.GenericResponseModel(data=str(order_id))

@router.get('/status/{order_id}', response_model=schemas.GenericResponseModel)
async def order_status(order_id: int, user: schemas.UserBaseModel=Depends(deps.verify_user)):

    def _db_unit_2():
        with Session(engine) as sess:
            order = sess.exec(select(models.VoucherOrder).where(models.VoucherOrder.id == order_id).where(models.VoucherOrder.user_id == user.id)).first()
            return (True, schemas.GenericResponseModel(data={'status': 'confirmed' if order else 'pending'}), None)
        locals_map = locals()
        return (False, None, tuple((locals_map.get(k) for k in ['order'])))
    _early, _value, _values = await run_db(_db_unit_2)
    if _early:
        return _value
    order, = _values
