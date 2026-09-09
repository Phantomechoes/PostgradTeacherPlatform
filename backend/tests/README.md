# backend/tests

**职责：后端自动化测试。**

以后这里放 pytest 测试。每个业务 Issue 至少覆盖：

- 一条正常路径
- 一条关键异常路径

当前已有 `test_health.py`，覆盖 `GET /health`。在 `backend/` 下执行：`uv run pytest`。完整 Windows 说明见 [`backend/README.md`](../README.md)。
