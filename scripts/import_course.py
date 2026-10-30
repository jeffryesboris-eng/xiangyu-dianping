from pathlib import Path
import pymysql
from pymysql.constants import CLIENT
sql=Path('.local/course/hmdp.sql').read_text(encoding='utf-8-sig')
assert 'CREATE DATABASE' not in sql.upper() and '\nUSE ' not in sql.upper()
c=pymysql.connect(host='127.0.0.1',port=3307,user='root',charset='utf8mb4',client_flag=CLIENT.MULTI_STATEMENTS)
with c.cursor() as cur:
 cur.execute('CREATE DATABASE hmdp_course CHARACTER SET utf8mb4')
 cur.execute("GRANT ALL ON hmdp_course.* TO 'hmdp_test'@'localhost'")
 cur.execute('USE hmdp_course')
 cur.execute(sql)
 while cur.nextset():pass
 for table in ['tb_shop','tb_shop_type','tb_blog','tb_user','tb_voucher','tb_seckill_voucher']:
  cur.execute('SELECT COUNT(*) FROM '+table); print(table,cur.fetchone()[0])
c.commit();c.close()
