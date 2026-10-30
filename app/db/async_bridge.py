import asyncio
from functools import partial
from starlette.concurrency import run_in_threadpool

async def run_db(fn, *args, **kwargs):
    """Run a complete synchronous DB unit in the bounded AnyIO worker pool."""
    return await run_in_threadpool(partial(fn, *args, **kwargs))
