# backend/migrations

**职责：数据库结构变更的正式记录。**

每次改表结构都要留下可回放的记录，而不是只在数据库里手工改表。正式 Schema 只由 Alembic 管理。

约定流程：

```text
修改 Model → 生成 migration → 人工阅读 → 执行 → 测试
```

历史 empty baseline：`27d6bd3c881a`（只创建 `alembic_version`，没有业务表）。
当前 head：`44f5a70a766a`（create master data schema，7 张业务表）。

可能丢数据的迁移必须再次请负责人确认。
