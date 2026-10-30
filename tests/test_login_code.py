from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from app.api.endpoints import user as module

@pytest.mark.normal
@pytest.mark.parametrize('enabled',[True,False])
def test_demo_code_only_when_enabled(monkeypatch,enabled):
    monkeypatch.setattr(module.settings,'DEMO_LOGIN',enabled)
    fake=AsyncMock();monkeypatch.setattr(module,'aio_redis',fake)
    app=FastAPI();app.include_router(module.router,prefix='/user');client=TestClient(app)
    result=client.post('/user/code?phone=13990000000').json()
    assert result['success']
    code=fake.setex.await_args.args[2]
    assert len(code)==6 and code.isdigit()
    assert result['data']==({'demoCode':code} if enabled else None)

@pytest.mark.boundary
@pytest.mark.parametrize('phone',['123','abcdefghijk','23990000000'])
def test_code_rejects_invalid_phone(monkeypatch,phone):
    fake=AsyncMock();monkeypatch.setattr(module,'aio_redis',fake)
    app=FastAPI();app.include_router(module.router,prefix='/user')
    assert TestClient(app).post('/user/code?phone='+phone).status_code==422
    fake.setex.assert_not_awaited()
