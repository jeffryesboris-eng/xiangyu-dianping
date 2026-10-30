# 秒杀订单幂等测试准备

已在课程库 hmdp_course / Redis DB 1 添加商户 1 的秒杀券 9001。
名称：幂等测试专用秒杀券；价格：1元抵50元；初始库存100；创建时已开始，有效期90天；每人限购一张，无真实兑换能力。
页面：http://127.0.0.1:8081/#/shop/1
账号：13800000001、13800000002、13800000003，验证码查看 .local/app.stdout.log。

准备脚本（重复运行不重置库存、不删除订单、不清空购买集合）：

```powershell
. ./scripts/course-env.ps1
./.test-env/python.exe scripts/add_seckill_fixture.py
```

## 建议验证

1. 同一账号连续或并发调用 POST /voucher-order/seckill/9001，最多受理一次，其余提示不能重复下单（库存耗尽时也可能返回库存不足）。
2. 查询 tb_voucher_order：相同 user_id + voucher_id 应只有1行；MySQL 库存、Redis hmdp:seckill:stock:9001 应只减少1。
3. 确认订单已落库后，把其 id、user_id、voucher_id 原样通过 XADD stream.orders * 再投递一次。消费完成后订单仍为1行，库存不再扣减，消费组 g1 的 pending 应回到0。
4. 使用另一账号下单，应新增1行且库存再减少1。验证依据是唯一用户订单数，不是接口调用次数。

测试前后记录库存与订单数差值；秒杀是异步落库，等待 /voucher-order/status/{order_id} 返回 confirmed 后再断言。
订单ID为64位整数，前端与测试客户端应按字符串保存，避免精度丢失。
本次仅创建数据并验证查询接口，没有预先下单，保留100份库存供测试。
