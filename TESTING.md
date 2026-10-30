# 本地测试环境

独立 Python 3.10 位于 `.test-env`。便携 MySQL 8.4.7 位于 `.local/mysql`，Redis 7.2.8 Windows 社区移植版位于 `.local/redis`。
测试服务只监听 127.0.0.1：MySQL 3307，Redis 6380（DB 0）。数据库为 `hmdp_test`，应用账号 `hmdp_test`，密码 `hmdp_test_local`。
MySQL 本地 root 空密码仅用于本测试实例的建库初始化；不应将该实例开放到网络。

在项目目录运行 PowerShell：

```powershell
./scripts/start-test-services.ps1
. ./scripts/test-env.ps1
./.test-env/python.exe scripts/seed_test.py
./.test-env/python.exe scripts/smoke_test.py
./scripts/run-test-app.ps1
```

浏览器访问 http://127.0.0.1:8081/docs 。配置由当前 PowerShell 环境变量传入，不修改原默认连接信息。
样例含用户 1/2/3、商户 1/2、博文 1、秒杀券 1（库存 10）、共同关注和 GEO 数据。
初始化同时预热商户逻辑过期缓存，创建 `stream.orders` 和消费组 `g1`；重复初始化不会删除已有订单或重置库存。
短信验证码从控制台输出或测试 Redis 获取，没有真实发送短信。
冒烟测试会真实执行签到和一次秒杀下单，重复运行已有订单时跳过创建。

安装依赖：`./.test-env/python.exe -m pip install -r requirements-test.txt`。
服务日志在 `.local/*.log`；数据与依赖目录均已加入 Git 忽略。
通过 MySQL 客户端 `mysqladmin -h127.0.0.1 -P3307 -uroot shutdown` 和 Redis 客户端 `redis-cli -p6380 shutdown` 停止对应测试实例。

## Vue 点评前端

完整页面入口：http://127.0.0.1:8081/ 。前端运行与功能说明见 `frontend/README.md`。
前端重新构建后需重启应用。验证码在 `.local/app.stdout.log`，开发服务器使用 `frontend` 目录的 `npm run dev`。
