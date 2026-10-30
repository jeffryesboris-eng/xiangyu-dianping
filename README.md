# 巷遇点评 · FastAPI + Vue 3 + Redis

一个基于黑马点评 Redis 实战课程扩展的本地生活演示平台。后端使用 Python / FastAPI，前端使用 Vue 3 + TypeScript，支持商户发现、附近搜索、探店笔记、关注动态、验证码登录、签到和优惠券秒杀。

本项目用于学习、演示和并发正确性验证。课程资料与新增演示数据不代表真实商户的最新营业信息；演示优惠券不涉及真实支付或到店兑换。

> 已提供 Dockerfile、Docker Compose 和 GitHub Actions 验证流程。Docker部署步骤见 [DOCKER.md](DOCKER.md)；本机尚无Docker，容器构建与运行仍待验证。GitHub上传与公网服务部署是两个独立步骤。

## 功能

| 模块 | 已实现 |
| --- | --- |
| 商户发现 | 首页、10 个分类、按名称搜索、分页 |
| 附近商户 | Redis GEO、5 公里范围查询、距离排序、浏览器定位及手动经纬度 |
| 商户详情 | 地址、营业时间、价格、店铺笔记、优惠券 |
| 探店笔记 | 热门与个人笔记、详情、文字及图片发布、点赞 |
| 社交 | 关注 / 取消关注、共同关注、关注动态与游标分页 |
| 用户 | 手机验证码登录、自动注册、个人中心、退出登录 |
| 签到 | Bitmap 签到及本月连续签到统计 |
| 秒杀 | Redis Lua 原子预扣、防重复购买、Stream 异步下单、订单确认查询 |
| 一致性 | 库存与订单同事务、重复消费幂等、Redis 锁归属验证、数据库行锁 |
| 消息恢复 | 独立消费者身份、pending 重试、超时消息接管、连接失败退避 |

当前验证码为本地演示模式：点击“获取验证码”后显示并自动填入验证码，未接入真实短信服务。UV 的 HyperLogLog 代码为独立示例，未接入请求访问统计。没有在线支付、退款或商户后台。

## 技术栈

| 层 | 技术与用途 |
| --- | --- |
| 前端 | Vue 3 + TypeScript：组件与类型检查 |
| 构建与路由 | Vite、Vue Router，使用 Hash 路由 |
| 状态与请求 | Pinia 管理登录状态，Axios 统一请求及错误处理 |
| 样式 | 原生 CSS，适配桌面与手机 |
| Web 服务 | FastAPI、Uvicorn；同时托管前端构建产物 |
| 数据库 | MySQL、SQLModel、SQLAlchemy、PyMySQL |
| 缓存与消息 | Redis：缓存、GEO、Bitmap、集合、Sorted Set、Stream、Lua |
| 测试 | pytest、临时 SQLite、真实 MySQL / Redis 集成测试 |

当前验证环境：Python 3.10、Node.js 24、MySQL 8.4.7、Redis 7.2.8。后端沿用课程时期的 FastAPI 0.78.0、SQLModel 0.0.6 等依赖；建议使用 `requirements-test.txt` 中的兼容约束，不要直接在 Python 3.13 环境安装运行。

## 项目结构

```text
app/
  api/endpoints/       用户、商户、笔记、关注、优惠券、秒杀接口
  core/config.py      环境变量配置
  db/                 MySQL 连接与同步数据库操作的异步隔离
  models/             数据表模型
  schemas/            请求和响应模型
  crud/               数据访问
  utils/              Redis、缓存、锁、ID、上传工具
frontend/
  src/                Vue 页面、组件、Pinia、Axios 和样式
  package-lock.json    前端依赖锁定
scripts/              本地启动、数据导入与负载测试
tests/                pytest 用例
```

`.local/` 保存本地数据库、图片、下载资源、日志和测试报告，`.test-env/` 保存独立 Python 环境，两者均不提交 Git。`frontend/node_modules/` 和 `frontend/dist/` 也已忽略，克隆项目后需要重新安装、构建。

## 本机快速启动

以下命令在项目根目录使用 PowerShell 执行，适用于当前已经初始化好的本地环境。

```powershell
# 启动本地 MySQL 3307 / Redis 6380
./scripts/start-test-services.ps1

# 安装前端依赖并构建
npm --prefix frontend ci
npm --prefix frontend run build

# 启动 FastAPI，默认加载课程与演示数据配置
./scripts/run-test-app.ps1
```

- 平台首页：[http://127.0.0.1:8081/](http://127.0.0.1:8081/)
- 商户列表：[http://127.0.0.1:8081/#/shops](http://127.0.0.1:8081/#/shops)
- 接口文档：[http://127.0.0.1:8081/docs](http://127.0.0.1:8081/docs)

开发前端时，先启动后端，再运行：

```powershell
npm --prefix frontend run dev
```

打开 Vite 输出的地址。开发模式将 `/api` 和 `/imgs` 请求代理到本机 8081；生产构建由 FastAPI 同源提供。前端构建产物首次生成后需重启后端，以注册静态资源路由。

### 首次在另一台电脑安装

1. 安装 Python 3.10 和 Node.js，创建项目内环境，例如 `py -3.10 -m venv .test-env`。
2. 执行 `./.test-env/Scripts/python.exe -m pip install -r requirements-test.txt`。当前电脑的 Conda 环境 Python 位于 `.test-env/python.exe`；使用 venv 时，运行脚本中的 Python 路径也要改为 `.test-env/Scripts/python.exe`。
3. 准备 MySQL 和 Redis。现有 `start-test-services.ps1` **不负责下载软件**，要求提前将便携 MySQL、Redis 分别解压到 `.local/mysql`、`.local/redis`，脚本会递归查找服务端程序。Windows Redis 使用社区移植版，生产部署建议采用官方支持的 Linux 环境。
4. 启动服务，先加载 `scripts/test-env.ps1` 并运行 `scripts/seed_test.py` 创建本地测试库与账号。
5. 准备课程 SQL 与图片，按下一节初始化课程库，再安装和构建前端。

启动脚本仅监听本机。便携 MySQL 的本地 root 初始化为空密码，应用测试账号使用脚本中的演示密码；这些配置只用于隔离的本地学习环境，不能直接作为公网部署配置。

## 数据与初始化

应用默认使用 **MySQL `hmdp_course` / Redis DB 1**；pytest 集成测试使用 **`hmdp_test` / Redis DB 0**，部分 Redis 用例使用 DB 15 和随机键。

课程资源来自 [cs001020/hmdp](https://github.com/cs001020/hmdp)：master 分支的 `hmdp.sql`，以及 init 分支 `src/main/resources/nginx-1.18.0` 下的图片。它是课程资料的公开整理仓库。

首次准备课程数据：

1. 将 SQL 保存到 `.local/course/hmdp.sql`；将课程 `imgs` 目录的内容复制到 `.local/uploads/`。
2. 本地服务运行后执行：

```powershell
# 只用于首次创建 hmdp_course，数据库已存在时会停止
./.test-env/python.exe scripts/import_course.py

. ./scripts/course-env.ps1
./.test-env/python.exe scripts/prepare_course.py

# 可选：导入完整演示数据
./.test-env/python.exe scripts/import_full_demo.py

# 可选：原课程商户体验券、专用幂等测试券
./.test-env/python.exe scripts/import_demo_vouchers.py
./.test-env/python.exe scripts/add_seckill_fixture.py
```

完整演示数据脚本新增：

- 每个分类 20 家，共 200 家虚构商户；加上原课程 14 家，共 214 家。
- 400 篇探店笔记、200 张普通券、200 张秒杀券。
- 200 张本地 SVG 插画、20 个演示作者及配套关注动态。

新增数据明确标为演示，覆盖杭州运河、武林、西湖和滨江几个区域。重复执行不会重置已有库存、购买集合或订单。独立测试券 ID 为 `9001`，完整演示数据的秒杀券 ID 为 `60001–60200`。活动按首次创建时间设置有效期，不会自动延期。

体验账号：`13990000000` 至 `13990000019`，使用正常的演示验证码登录。也可以输入新的有效手机号自动注册。

附近搜索示例坐标：经度 `120.149192`，纬度 `30.316078`。浏览器获取的真实位置如果距离杭州较远，附近列表为空是正常结果。

## 配置

后端从进程环境变量读取配置。`scripts/run-test-app.ps1` 加载 `scripts/course-env.ps1`，后者继承 `scripts/test-env.ps1` 后覆盖数据库、Redis DB 和演示登录开关。

| 配置 | 当前本地应用值 / 默认资源限制 |
| --- | --- |
| MYSQL_HOST / MYSQL_PORT | 127.0.0.1 / 3307 |
| MYSQL_DATABASE | hmdp_course |
| MYSQL_USER | hmdp_test |
| REDIS_HOST / REDIS_PORT / REDIS_DB | 127.0.0.1 / 6380 / 1 |
| IMAGE_UPLOAD_DIR | .local/uploads 对应的绝对路径 |
| DEMO_LOGIN | 本地脚本启用；代码默认 False |
| DB_POOL_SIZE / DB_MAX_OVERFLOW | 8 / 2，每进程最多 10 个连接 |
| DB_POOL_TIMEOUT | 5 秒 |
| THREAD_POOL_SIZE | 8 |
| ORDER_CONSUMERS | 1 |
| ORDER_RECLAIM_MS | 30000 毫秒 |

当前默认单 worker、HTTP 并发上限 128。同步数据库操作通过受限线程池隔离，Session 在线程内创建和关闭；并未整体迁移为异步 ORM。增加 worker 会相应增加连接池、线程池和消费者数量，应先测量再调整。

## 测试

```powershell
# 快速测试：默认跳过真实服务集成用例
./.test-env/python.exe -m pytest

# 完整测试：需要测试 MySQL / Redis 已启动且测试库已初始化
. ./scripts/test-env.ps1
./.test-env/python.exe -m pytest --integration --junitxml=.local/pytest-results.xml

# 按类别选择
./.test-env/python.exe -m pytest -m permission
./.test-env/python.exe -m pytest --integration -m concurrency
```

当前完整套件 **35 项通过**，覆盖正常流程、参数边界、异常、权限、并发、事务回滚、重复消费、事件循环隔离和消费者故障接管。测试会使用隔离数据，不消耗页面上的课程秒杀券。

## 本地负载测试

先启动应用，再运行：

```powershell
. ./scripts/course-env.ps1
./.test-env/python.exe scripts/load_probe.py
```

脚本执行有界读请求与独立临时券秒杀测试，结果保存到 `.local/load-report.json`，正常完成后清理本次秒杀数据。

已有一次本机测量：270 次读请求无错误，24 并发档 P95 约 294ms；30 个秒杀请求争抢 10 份库存，受理与落库均为 10 单，MySQL / Redis 库存均为 0，最终 pending / lag 为 0。

这是短时本机结果，没有优化前的同条件基线，不能视为生产吞吐承诺或性能提升证明。锁等待报告同时包含瞬时采样和服务启动以来累计值，具体解释见下方文档。

## 文档索引

- [前端开发与页面说明](frontend/README.md)
- [本地测试环境](TESTING.md)
- [课程数据来源与隔离](COURSE_DATA.md)
- [完整演示数据](DEMO_DATA.md)
- [秒杀幂等测试步骤](SECKILL_TESTING.md)
- [pytest 用例设计](PYTEST_CASES.md)
- [资源限制、消息恢复与压测说明](PERFORMANCE.md)

## 来源与许可

本项目最初是[黑马程序员 Redis 实战课程](https://www.bilibili.com/video/BV1cr4y1671t?p=24)的 Python 后端实现，在此基础上增加了 Vue 前端、演示数据、回归测试和并发优化。原 Python 项目：[boh5/hmdp_for_learn_redis_by_fastapi](https://github.com/boh5/hmdp_for_learn_redis_by_fastapi)。

仓库代码许可见 [LICENSE](LICENSE)。课程图片、商户资料和外部图片网址的使用条件应分别确认，不能将代码许可证直接视为第三方素材的授权。
