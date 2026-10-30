from db.async_bridge import run_db
'\n    follow\n    ~~~\n\n    \n\n    :author: dilless(Huangbo)\n    :date: 2022/7/10\n'
from typing import List
from fastapi import APIRouter, Path, Depends
from pydantic import parse_obj_as
from sqlmodel import Session, select, col
import models
import schemas
from api import deps
from db.mysql import engine
from utils.redis_ import FollowUtils
router = APIRouter()

@router.get('/common/{target_user_id}', response_model=schemas.GenericResponseModel)
async def get_common_follows(*, target_user_id: int=Path(), user: schemas.UserBaseModel=Depends(deps.verify_user)):
    common_ids = await FollowUtils.get_common_follow(user.id, target_user_id)
    if not common_ids:
        return schemas.GenericResponseModel()

    def _db_unit_1():
        with Session(engine) as sess:
            common_users = sess.exec(select(models.User).where(col(models.User.id).in_(common_ids))).all()
            users = parse_obj_as(List[schemas.UserBaseModel], common_users)
        locals_map = locals()
        return (False, None, tuple((locals_map.get(k) for k in ['common_users', 'users'])))
    _early, _value, _values = await run_db(_db_unit_1)
    if _early:
        return _value
    common_users, users = _values
    return schemas.GenericResponseModel(data=users)

@router.get('/or/not/{follow_user_id}', response_model=schemas.GenericResponseModel)
async def is_followed(*, follow_user_id: int=Path(), user: schemas.UserBaseModel=Depends(deps.verify_user)):

    def _db_unit_2():
        with Session(engine) as sess:
            follow_model = sess.exec(select(models.Follow).where(models.Follow.user_id == user.id).where(models.Follow.follow_user_id == follow_user_id)).all()
        locals_map = locals()
        return (False, None, tuple((locals_map.get(k) for k in ['follow_model'])))
    _early, _value, _values = await run_db(_db_unit_2)
    if _early:
        return _value
    follow_model, = _values
    return schemas.GenericResponseModel(data=len(follow_model) > 0)

@router.put('/{follow_user_id}/{is_follow}', response_model=schemas.GenericResponseModel)
async def follow(*, follow_user_id: int=Path(), is_follow: bool=Path(), user: schemas.UserBaseModel=Depends(deps.verify_user)):

    def change_follow():
        with Session(engine) as sess:
            existing = sess.exec(select(models.Follow).where(models.Follow.user_id == user.id).where(models.Follow.follow_user_id == follow_user_id)).first()
            if is_follow and existing:
                return False
            if is_follow:
                sess.add(models.Follow(user_id=user.id, follow_user_id=follow_user_id))
            elif existing:
                sess.delete(existing)
            sess.commit()
            return True
    if not await run_db(change_follow):
        return schemas.GenericResponseModel(success=False, error_msg='不能重复关注')
    if is_follow:
        await FollowUtils.add_follow(user.id, follow_user_id)
    else:
        await FollowUtils.remove_follow(user.id, follow_user_id)
    return schemas.GenericResponseModel()
