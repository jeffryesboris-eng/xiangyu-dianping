from db.async_bridge import run_db
"""
    voucher
    ~~~

    

    :author: dilless(Huangbo)
    :date: 2022/7/10
"""
from typing import Optional, List
from fastapi import APIRouter, Path, Query
from sqlmodel import Session, select
from starlette.requests import Request
import crud
import models
from app import schemas
from core.config import settings
from db.mysql import engine
from utils.redis_ import aio_redis
router = APIRouter()

@router.get('/list/{shop_id}', response_model=schemas.GenericResponseModel[List[schemas.SeckillVoucherModel]])
async def query_voucher_of_shop(*, shop_id: int=Path):

    def _db_unit_1():
        with Session(engine) as sess:
            statement = select(models.Voucher, models.SeckillVoucher).join(models.SeckillVoucher, models.Voucher.id == models.SeckillVoucher.voucher_id, isouter=True).where(models.Voucher.shop_id == shop_id)
            results = sess.exec(statement).all()
        locals_map = locals()
        return (False, None, tuple((locals_map.get(k) for k in ['results', 'statement'])))
    _early, _value, _values = await run_db(_db_unit_1)
    if _early:
        return _value
    results, statement = _values
    data = []
    for voucher, seckill_voucher in results:
        d = voucher.dict()
        if seckill_voucher:
            d.update(**seckill_voucher.dict(exclude={'create_time', 'update_time'}))
        data.append(schemas.SeckillVoucherModel.parse_obj(d).dict(exclude_unset=True, by_alias=True))
    return schemas.GenericResponseModel(data=data)

@router.post('', response_model=schemas.GenericResponseModel)
async def add_voucher(*, model: models.Voucher):
    model = await run_db(crud.voucher_crud.create, model)
    return schemas.GenericResponseModel(data=model.id)

@router.post('/seckill', response_model=schemas.GenericResponseModel)
async def add_seckill_voucher(*, model: schemas.SeckillVoucherCreateModel):
    voucher, seckill_voucher = await run_db(crud.voucher_crud.create_seckill, model)
    await aio_redis.set(settings.CACHE_SECKILL_STOCK_KEY_PREFIX + str(voucher.id), seckill_voucher.stock)
    return schemas.GenericResponseModel(data=voucher.id)
