"""Initialize container-owned demo DB; never import or replace local data."""
import subprocess
import sys
from sqlmodel import SQLModel,Session
from sqlalchemy import text
import models
from db.mysql import engine
from core.config import settings
assert settings.MYSQL_DATABASE=='hmdp_course'
SQLModel.metadata.create_all(engine)
# Serialize repeated bootstrap operations against the same persistent database.
with engine.connect() as connection:
    assert connection.execute(text("SELECT GET_LOCK('xiangyu-bootstrap', 60)")).scalar()==1
    try:
        with Session(engine) as s:
            names=['美食','KTV','丽人·美发','健身运动','按摩·足疗','美容SPA','亲子游乐','酒吧','洗浴汗蒸','培训·教育']
            for i,name in enumerate(names,1):
                if s.get(models.ShopType,i) is None:
                    s.add(models.ShopType(id=i,name=name,icon='',sort=i))
            s.commit()
        subprocess.run([sys.executable,'scripts/import_full_demo.py'],check=True)
    finally:
        connection.execute(text("SELECT RELEASE_LOCK('xiangyu-bootstrap')"))
