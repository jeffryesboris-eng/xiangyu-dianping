# 课程配套数据

来源：https://github.com/cs001020/hmdp ，master 分支 hmdp.sql；init 分支 nginx 前端 imgs 目录。
本次下载原件保存在 `.local/course/`，课程图片提取至 `.local/uploads/`。

应用已切换至 MySQL `hmdp_course` 与 Redis DB 1。原 `hmdp_test` 数据库与 Redis DB 0 完整保留。
运行 `scripts/run-test-app.ps1` 默认加载 `scripts/course-env.ps1`；运行回归测试仍使用 `scripts/test-env.ps1`。

课程数据包含14家杭州商户、10个分类、4篇笔记、5个用户和1张普通代金券，没有秒杀券。商户、价格、图片网址与笔记均为历史课程演示资料，不代表当前营业信息。
附近商户可手动输入杭州样例位置：经度120.149192，纬度30.316078。
商户封面引用课程中的外部图片网址，是否可用取决于原图站点；笔记和分类图片使用已提取的本地文件。

初始化脚本：`scripts/import_course.py` 仅供首次创建数据库，重复运行会因数据库已存在而停止，以免覆盖数据。
缓存重建：加载 `scripts/course-env.ps1` 后运行 `.test-env/python.exe scripts/prepare_course.py`。
重新运行原 `seed_test.py` 不会改变课程数据库。
