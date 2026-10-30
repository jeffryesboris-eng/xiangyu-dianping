# Docker 部署与 GitHub

## 本机启动

需要 Docker Engine / Docker Desktop（Linux containers）及 Docker Compose v2。

```powershell
Copy-Item .env.example .env
# 编辑 .env，替换两个数据库密码；本机体验可设置 DEMO_LOGIN=true
# APP_PORT=8082 可避免与当前本机8081服务冲突

docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 300
docker compose ps
```

打开 http://127.0.0.1:8082/ （端口以.env为准）。健康检查：`/health`；接口文档：`/docs`。

初始化任务自动创建表、10个分类、200家演示商户、400篇笔记、400张优惠券与本地图片。它不包含本机的14家课程商户、课程图片或已有订单；本机数据库不参与构建，也不会被覆盖。重复运行初始化不重置库存或购买记录。

默认 DEMO_LOGIN=false 不向页面返回验证码，且没有真实短信供应商。仅在本机演示时改为true，方可在页面直接获取演示验证码。真实公网登录需接入短信并关闭该开关。

## 服务与数据

- app：FastAPI与Vue构建产物，非root用户运行。
- mysql：MySQL 8.4，mysql-data持久卷。
- redis：Redis 7.2，AOF启用，redis-data持久卷。
- init：等待数据库就绪，再初始化演示数据；完成后才启动app。
- uploads：图片持久卷，初始化与app共享。

数据库端口不映射到宿主机，应用端口默认绑定127.0.0.1。镜像不包含.env、.git、本地数据库、日志或虚拟环境。

```powershell
docker compose logs -f app
docker compose logs init
docker compose stop
docker compose up -d
# 修改代码后重新构建
docker compose up --build -d
```

普通停止/重建保留卷。不要在保留数据的部署中随意使用 `down -v`，该参数会删除数据库和上传图片。MySQL初始化密码只在空数据卷首次创建时生效，之后仅修改.env不会修改已有数据库账号密码。

## 公网部署

GitHub保存代码，不会自动托管本项目的Python/MySQL/Redis服务。需要单独的Linux服务器或容器平台；可在服务器上运行同一Compose，再通过Nginx/Caddy反向代理本机映射端口并配置域名与HTTPS。当前会话尚未提供目标服务器，因此没有配置或执行公网发布。

这是学习项目的容器化部署基线，不是已审计的生产系统。上线前需替换演示凭证与SECRET_KEY、关闭DEMO_LOGIN、接入真实短信，并进一步完善鉴权令牌、上传校验、发送限流与数据备份。

## GitHub

GitHub Actions包含快速pytest测试和Docker Compose构建/启动/健康检查。CI使用一次性数据库密码，不依赖本机.local资源。

不要提交.env、数据库文件、日志、上传文件或访问令牌。当前origin指向原作者仓库；应将改动推送至你自己的仓库或fork。目标账号、仓库及可见性需由你指定。

## 当前验证状态

本机未安装Docker，尚不能在本机执行镜像构建与Compose运行。提供的CI工作流会在GitHub上执行容器验证，但推送前不能将其视为已通过。本地可继续执行Python测试与前端构建。
