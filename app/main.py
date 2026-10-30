"""
    main
    ~~~

    

    :author: dilless(Huangbo)
    :date: 2022/7/10
"""
import multiprocessing

from fastapi import FastAPI, Depends
from starsessions import SessionMiddleware, InMemoryBackend

from api.deps import refresh_user_obj_in_redis
from app.api.api import api_router
from core.config import settings

# app = FastAPI(dependencies=[Depends(refresh_user_obj_in_redis)])
app = FastAPI()

@app.on_event('startup')
async def configure_thread_pool():
    import anyio
    anyio.to_thread.current_default_thread_limiter().total_tokens = settings.THREAD_POOL_SIZE


app.include_router(api_router, prefix='')

@app.get('/health', include_in_schema=False)
async def health():
    from sqlalchemy import text
    from db.mysql import engine
    from db.async_bridge import run_db
    from utils.redis_ import aio_redis
    def check_database():
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
    await run_db(check_database)
    await aio_redis.ping()
    return {'status': 'ok'}

app.add_middleware(SessionMiddleware, backend=InMemoryBackend())

# Hash-based Vue routes keep the existing API paths available unchanged.
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
if frontend_dist.is_dir():
    app.mount('/assets', StaticFiles(directory=frontend_dist / 'assets'), name='assets')

    @app.get('/', include_in_schema=False)
    async def frontend_index():
        return FileResponse(frontend_dist / 'index.html')

upload_dir = Path(settings.IMAGE_UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount('/imgs', StaticFiles(directory=upload_dir), name='images')
