# 秒杀 pytest 测试方案

## 用例分类

| 分类 / marker | 验证点 | 实现 |
|---|---|---|
| normal | 下单受理、64位ID字符串精度；消息重复处理只扣一次库存 | test_seckill_api.py / test_voucher_orders.py |
| boundary | 非整数ID、0/负数/不存在ID；未开始/已结束；库存不足；重复购买；空pending | test_seckill_api.py / test_voucher_orders.py |
| abnormal | 订单插入失败库存回滚；数据库处理失败不ACK；过期锁释放；Redis连接故障暴露 | test_voucher_orders.py / test_seckill_api.py |
| permission | 无令牌、无效令牌；他人订单不返回confirmed | test_seckill_api.py |
| concurrency | 抢锁失败不下单不ACK；12线程同用户只生成1单；12用户抢3库存无超卖；真实Lua下同用户/不同用户预扣与消息数一致 | test_voucher_orders.py / test_seckill_concurrency.py / test_seckill_redis.py |

## 执行

在项目根目录 PowerShell：

```powershell
# 快速测试，无需连接外部服务
./.test-env/python.exe -m pytest
# 全量：真实 MySQL 与 Redis 必须已启动
. ./scripts/test-env.ps1
./.test-env/python.exe -m pytest --integration --junitxml=.local/pytest-results.xml
# 按分类筛选
./.test-env/python.exe -m pytest -m permission
./.test-env/python.exe -m pytest --integration -m concurrency
```

pytest.ini 统一收集 tests/、定义分类和临时目录。默认跳过 integration；真实服务不可用时全量测试失败，不自动跳过。

## 隔离与断言

接口测试使用临时SQLite和模拟Redis，不启动后台消费者；真实事务与行锁并发使用 hmdp_test，随机专用券ID，finally清理本次订单和券。Redis并发使用6380端口DB15和随机前缀，只清理本次键，不执行FLUSHDB。课程库hmdp_course、Redis DB1、券9001均不参与。

并发通过实际库存、订单行数、唯一用户数、Redis集合成员数及Stream消息数断言。MySQL测试绕过Redis锁，专门验证租约失效后的数据库安全；Redis测试运行接口实际Lua，专门验证原子预扣。

## 当前契约与限制

- 缺失Authorization当前返回422，无效令牌返回401；他人订单状态返回pending，不暴露订单内容。
- Redis连接失败目前会向上抛异常（线上为500），用例验证失败可见，不能视为已具备503降级或自动补偿。
- 本套件重点覆盖秒杀；未把整个点评平台所有接口都纳入验收。
- 并发测试为12线程功能验证，不是吞吐量压测；未模拟进程断电、Redis主从切换或网络分区。
- 现有依赖有弃用/SQL编译缓存警告，不影响断言。JUnit XML可接入CI。
