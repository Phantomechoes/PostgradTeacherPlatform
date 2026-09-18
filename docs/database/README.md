# docs/database

**数据库设计文档。**

这里说明有哪些表、表之间如何关联、关键字段含义。
正式表结构以 PostgreSQL 为准；schema 由 SQLAlchemy Models 与 Alembic migration 管理，本目录只放给人读的设计说明。

S1-01 主数据 Schema 设计：[`s1-01-master-data-schema.md`](./s1-01-master-data-schema.md)。对应 revision：`44f5a70a766a`。
