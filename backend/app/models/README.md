# backend/app/models

**职责：描述数据库里有哪些表、每张表有哪些字段。**

S1-01 已放置院校招生主数据 Model（尚未 Alembic upgrade）。一个模型对应一张 PostgreSQL 表。Model 只依赖 `app.core.db_base.Base`，不在 import 时连接数据库。

这一层是“数据长什么样”，不是“业务允许怎么做”。  
表结构的正式变更必须走 Alembic 迁移（见 `backend/migrations/`），不能只改模型文件。
