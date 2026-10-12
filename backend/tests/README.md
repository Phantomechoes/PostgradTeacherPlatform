# backend/tests

**职责：后端自动化测试。**

每个业务 Issue 至少覆盖：

- 一条正常路径
- 一条关键异常路径

当前包含：health、metadata、主数据与 Admin 的 schema / service / repository / API、PostgreSQL integration、importer、S2-01 teacher schema/constraint，以及 Teacher Admin 的 schema（`test_admin_teacher_schemas.py`）、repository、service、HTTP integration（`test_admin_teacher_api.py`）。数量会随测试增长，不在这里写死总数。

在 `backend/` 下：

```text
uv run --locked pytest
```

完整本地说明见 [`backend/README.md`](../README.md)。
