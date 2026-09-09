# backend/app/models

**职责：描述数据库里有哪些表、每张表有哪些字段。**

以后这里放 SQLAlchemy 模型。一个模型通常对应一张 PostgreSQL 表，例如未来的院校、专业、上岸生档案。

这一层是“数据长什么样”，不是“业务允许怎么做”。  
表结构的正式变更必须走 Alembic 迁移（见 `backend/migrations/`），不能只改模型文件。
