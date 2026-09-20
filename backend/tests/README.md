# backend/tests

**职责：后端自动化测试。**

每个业务 Issue 至少覆盖：

- 一条正常路径
- 一条关键异常路径

当前包含：health、metadata、schemas、service、repository、PostgreSQL integration、API tests。当前基线 88 passed（数量会随测试增长）。

在 `backend/` 下：

```text
uv run --locked pytest
```

完整本地说明见 [`backend/README.md`](../README.md)。
