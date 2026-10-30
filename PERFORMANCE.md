# 后端并发优化与本地测量

## 已落实

同步 SQLModel / PyMySQL 仍保留，但异步接口的完整数据库操作在 run_db 中交由 AnyIO 线程池执行，Session 在同一个工作线程创建、使用和关闭。异步 Redis 请求继续在事件循环执行；图片文件接口使用同步端点，交给 FastAPI 线程池。逻辑过期缓存重建的数据库回源也移入线程池。

每进程默认：DB_POOL_SIZE=8、DB_MAX_OVERFLOW=2、DB_POOL_TIMEOUT=5秒、THREAD_POOL_SIZE=8；连接预检查、1800秒回收、连接5秒/读写10秒超时。HTTP并发限制128，过载时由Uvicorn返回503。worker保持1，消费者默认1；增加进程后数据库连接上限会按进程数相乘。

消费者使用进程ID+随机UUID身份。每2秒重试自己最多20条pending，并用XAUTOCLAIM接管闲置30秒的消息，扫描游标保留；Redis需6.2+。成功事务后ACK；锁竞争不ACK；处理失败保留消息，记录stream.orders:retries；连接故障采用0.2至5秒退避。退出时停止读新消息并等待消费线程收尾；未完成消息可由新消费者接管。原c1消费者的遗留pending同样可回收。

ORDER_CONSUMERS可配置独立消费者数量，默认仍为1。没有自动丢弃或补偿失败订单，持续失败应检查日志、pending与重试计数并处理原因，避免错误补偿造成重复库存。

## 验证

pytest覆盖事件循环心跳、消费者唯一身份、失败记录、真实Redis模拟旧消费者崩溃与新消费者接管，及原事务、权限、并发套件。

```powershell
. ./scripts/test-env.ps1
./.test-env/python.exe -m pytest --integration
```

## 本机压测

```powershell
. ./scripts/course-env.ps1
./.test-env/python.exe scripts/load_probe.py
```

测量结果在.local/load-report.json。读请求混合搜索、热门笔记、商户分类，各并发档90次；秒杀30个独立账号抢10库存，使用临时券，结束清理，不消耗原券。

| 读并发 | 请求 | 错误 | P50 ms | P95 ms | req/s |
|---|---|---|---|---|---|
| 1 | 90 | 0 | 32.59 | 42.62 | 32.66 |
| 8 | 90 | 0 | 37.30 | 101.23 | 154.62 |
| 24 | 90 | 0 | 82.99 | 293.83 | 170.50 |

秒杀24并发、30请求：P95 136.47ms，受理10单、落库10单，MySQL/Redis库存均0，最终pending=0、lag=0。最后采样的MySQL锁等待数为0；报告的Innodb_row_lock_waits/time为服务器启动以来累计值，包含之前测试，不能当成本次压测增量。不是持续采样，也不能据此声称过程中无等待。

这些是本机短时功能负载，没有优化前的同环境基线，不代表生产容量或已证实的性能提升。并发从8升到24时吞吐增长有限且尾延迟明显增加，暂不增加worker。下一步应进行更长时间负载、持续采样DB锁等待增量与连接占用、队列lag峰值和事件循环延迟，再评估消费者与worker数量。
