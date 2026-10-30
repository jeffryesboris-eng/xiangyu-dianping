"""Exercise real MySQL/Redis through the app, including stream order persistence."""
import time
import hashlib
import redis
from sqlmodel import Session, select
from starlette.testclient import TestClient
from core.config import settings
from db.mysql import engine
import models
from app.main import app

assert settings.MYSQL_DATABASE == 'hmdp_test' and settings.REDIS_PORT == 6380
r = redis.Redis(host='127.0.0.1', port=6380, decode_responses=True)
with TestClient(app) as client:
    for path in ('/shop/1', '/shop/of/type?typeId=1&x=121.4737&y=31.2304', '/blog/hot'):
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)
        assert response.json()['success'], (path, response.text)
        print('PASS', path)
    client.post('/user/code?phone=13800000002').raise_for_status()
    code = r.get(settings.LOGIN_CODE_KEY_PREFIX+'13800000002')
    response = client.post('/user/login', json={'phone':'13800000002', 'code':code})
    assert response.status_code == 200, response.text
    token = response.json()['data']
    headers = {'authorization':token}
    for method, path in [('GET','/user/me'), ('POST','/user/sign'), ('GET','/user/sign/count'), ('GET','/follow/common/2')]:
        response = client.request(method, path, headers=headers)
        assert response.status_code == 200 and response.json()['success'], (path, response.text)
        print('PASS', path)
    with Session(engine) as s:
        existing = s.exec(select(models.VoucherOrder).where(models.VoucherOrder.user_id==2)).first()
    if existing is None:
        response = client.post('/voucher-order/seckill/1', headers=headers)
        assert response.status_code == 200 and response.json()['success'], response.text
        order_id = response.json()['data']
        for _ in range(50):
            with Session(engine) as s:
                if s.get(models.VoucherOrder, order_id):
                    break
            time.sleep(.1)
        else:
            raise AssertionError('Order not persisted by stream consumer')
        print('PASS stream order persisted', order_id)
print('SMOKE OK')
