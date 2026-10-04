# backend/migrations

**职责：数据库结构变更的正式记录。**

每次改表结构都要留下可回放的记录，而不是只在数据库里手工改表。正式 Schema 只由 Alembic 管理。

约定流程：

```text
修改 Model → 生成 migration → 人工阅读 → 执行 → 测试
```

历史 empty baseline：`27d6bd3c881a`（只创建 `alembic_version`，没有业务表）。
S1-01：`44f5a70a766a`（7 张主数据表）。
当前 head：`695107900fc3`（create teacher data schema，再加 3 张师资表，业务表共 10 张）。

可能丢数据的迁移必须再次请负责人确认。
