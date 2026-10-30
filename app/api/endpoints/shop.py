from db.async_bridge import run_db
"""
    shop
    ~~~

    

    :author: dilless(Huangbo)
    :date: 2022/7/10
"""
import asyncio
import datetime
import functools
import threading
from concurrent import futures
from typing import Optional
from fastapi import APIRouter, Path, Query, HTTPException, Body
from pydantic import parse_obj_as
from sqlmodel import Session, select, col
from starlette.requests import Request
from fastapi.background import BackgroundTasks
import crud
import models
from app import schemas
from core.config import settings
from db.mysql import engine
from utils.cache import CacheClient
from utils.redis_ import aio_redis, get_cache_shop_key, lock, get_cache_lock_shop_key, unlock, save_shop_2_redis, GeoUtils
router = APIRouter()
cache_client = CacheClient(aio_redis)

async def query_shop_with_mutex(id):
    shop_json_str = await aio_redis.get(get_cache_shop_key(id))
    if shop_json_str is None:
        try:
            lock_status = await lock(get_cache_lock_shop_key(id))
            if not lock_status:
                await asyncio.sleep(50 / 1000)
                return await query_shop_with_mutex(id)

            def _db_unit_1():
                with Session(engine) as sess:
                    statement = select(models.Shop).where(models.Shop.id == id)
                    shop = sess.exec(statement).first()
                    print('!!!打到数据库了!!!')
                locals_map = locals()
                return (False, None, tuple((locals_map.get(k) for k in ['shop', 'statement'])))
            _early, _value, _values = await run_db(_db_unit_1)
            if _early:
                return _value
            shop, statement = _values
            if shop:
                await aio_redis.setex(get_cache_shop_key(id), settings.CACHE_EXPIRE, shop.json())
            else:
                await aio_redis.setex(get_cache_shop_key(id), settings.CACHE_NONE_EXPIRE, '')
        finally:
            await unlock(get_cache_lock_shop_key(id))
    else:
        print('query_shop_by_id 没有打到mysql')
        if not shop_json_str:
            shop = None
        else:
            shop = models.Shop.parse_raw(shop_json_str)
    return shop

@router.get('/{id}', response_model=schemas.GenericResponseModel)
async def query_shop_by_id(*, id: int=Path, background_tasks: BackgroundTasks):
    shop = await cache_client.query_shop_with_logical_expire(key_prefix=settings.CACHE_SHOP_KEY_PREFIX, pk=id, model_class=models.Shop, db_fallback=crud.shop_crud.get, expire=10)
    if shop:
        return schemas.GenericResponseModel(data=shop)
    else:
        return schemas.GenericResponseModel(success=False, error_msg='店铺不存在')

@router.get('/of/type', response_model=schemas.GenericResponseModel)
async def query_shop_by_type(*, type_id: int=Query(alias='typeId'), page: int=Query(1, alias='current'), x: Optional[float]=Query(None, description='longitude'), y: Optional[float]=Query(None, description='latitude')):
    if page <= 0:
        page = 1
    limit = settings.MAX_PAGE_SIZE
    offset = (page - 1) * settings.MAX_PAGE_SIZE
    if not x or not y:

        def _db_unit_2():
            with Session(engine) as sess:
                statement = select(models.Shop).where(models.Shop.type_id == type_id).limit(limit).offset(offset)
                shops = sess.exec(statement).all()
                return (True, schemas.GenericResponseModel(data=shops), None)
            locals_map = locals()
            return (False, None, tuple((locals_map.get(k) for k in ['shops', 'statement'])))
        _early, _value, _values = await run_db(_db_unit_2)
        if _early:
            return _value
        shops, statement = _values
    else:
        shop_geo = await GeoUtils.search_by_shop_type(shop_type_id=type_id, x=x, y=y, limit=limit, offset=offset)
        shop_id_geo_order = [int(i[0]) for i in shop_geo]
        shop_distance_geo_order = [i[1] for i in shop_geo]
        shops = await run_db(crud.shop_crud.get_by_id_in, shop_id_geo_order)
        shops.sort(key=functools.cmp_to_key(lambda i, j: shop_id_geo_order.index(i.id) - shop_id_geo_order.index(j.id)))
        shops_with_distance = []
        for i in range(len(shops)):
            model = schemas.ShopWithDistanceModel.parse_obj(shops[i])
            model.distance = shop_distance_geo_order[i]
            shops_with_distance.append(model)
        return schemas.GenericResponseModel(data=shops_with_distance)

@router.get('/of/name', response_model=schemas.GenericResponseModel)
async def query_shop_by_name(*, name: str=Query(''), page: int=Query(1, alias='current')):
    if page <= 0:
        page = 1

    def _db_unit_3():
        with Session(engine) as sess:
            statement = select(models.Shop).where(col(models.Shop.name).contains(name)).limit(settings.MAX_PAGE_SIZE).offset(page * settings.MAX_PAGE_SIZE - settings.MAX_PAGE_SIZE)
            results = sess.exec(statement).all()
        locals_map = locals()
        return (False, None, tuple((locals_map.get(k) for k in ['results', 'statement'])))
    _early, _value, _values = await run_db(_db_unit_3)
    if _early:
        return _value
    results, statement = _values
    data = [r.dict(by_alias=True) for r in results]
    return schemas.GenericResponseModel(data=data)

@router.put('', response_model=schemas.GenericResponseModel)
async def update_shop(*, shop: models.Shop):
    if shop.id is None:
        return schemas.GenericResponseModel(success=False, error_msg='店铺id不能为空')

    def _db_unit_4():
        with Session(engine) as sess:
            statement = select(models.Shop).where(models.Shop.id == shop.id)
            shop_in_db = sess.exec(statement).one()
            if not shop_in_db:
                return (True, schemas.GenericResponseModel(success=False, error_msg='该店铺不存在'), None)
            for field, value in shop.dict(exclude={'id', 'create_time', 'update_time'}).items():
                shop_in_db.__setattr__(field, value)
            try:
                sess.add(shop_in_db)
                sess.commit()
            except Exception as e:
                print(e)
                sess.rollback()
        locals_map = locals()
        return (False, None, tuple((locals_map.get(k) for k in ['field', 'shop_in_db', 'statement', 'value'])))
    _early, _value, _values = await run_db(_db_unit_4)
    if _early:
        return _value
    field, shop_in_db, statement, value = _values
    await aio_redis.delete(get_cache_shop_key(shop.id))
    return schemas.GenericResponseModel()
