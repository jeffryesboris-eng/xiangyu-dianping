# 巷遇 Vue 前端

技术栈：Vue 3 + TypeScript、Vite、Vue Router、Pinia、Axios、原生 CSS。

## 运行

在项目根目录启动后端：`./scripts/run-test-app.ps1`。

开发前端：

```powershell
cd frontend
npm ci
npm run dev
```

打开 Vite 输出的本地地址。开发模式 `/api` 代理至本机 8081，图片 `/imgs` 也代理至后端。

生产构建：

```powershell
cd frontend
npm run build
```

重启 FastAPI 后打开 http://127.0.0.1:8081/ 。使用 Hash 路由，原有业务接口路径保持可用。

## 页面

- `/#/` 首页、分类入口、精选商户、热门笔记
- `/#/shops` 名称搜索、分类、附近五公里、分页；定位失败可手动输入经纬度
- `/#/shop/1` 商户详情、店铺笔记、优惠券、秒杀倒计时与订单确认
- `/#/notes`、`/#/note/1` 笔记列表、详情、点赞与关注作者
- `/#/feed` 关注动态、游标分页
- `/#/me` 登录用户资料、签到、我的笔记、退出登录
- `/#/write` 发布文字与照片笔记

登录使用手机号与六位验证码。当前未接入短信供应商，验证码从 `.local/app.stdout.log` 获取。测试手机号为 13800000001、13800000002、13800000003。

秒杀返回受理订单号后轮询服务端确认落库，未确认会保留“后台正在处理”提示，不将接口受理误报为成功。普通优惠券目前只展示，不提供未实现的购买行为。

数据来自真实后端，空列表显示空状态，没有图片时使用占位设计。定位需要浏览器授权；样例商户经纬度为 121.4737、31.2304。

## 源码

`src/App.vue`：导航、登录弹窗；`src/Page.vue`：业务页面；`src/Card.vue`：商户与笔记卡片；`src/api.ts`：请求及错误处理；`src/session.ts`：Pinia 登录状态；`src/style.css`：响应式样式。

`npm run build` 同时执行 TypeScript 检查和生产构建。依赖精确版本由 package-lock.json 固定。
