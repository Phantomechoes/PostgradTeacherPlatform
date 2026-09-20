# backend/app

后端的应用程序包。几乎所有后端代码都放在这个目录下的子层里。

程序入口是 `main.py`。当前提供：

- `GET /health`（不查库）
- S1-02 只读主数据 API（`api/`、`schemas/`、`services/`、`repositories/`）
- S1-01 主数据 Models（`models/`）
- 配置与数据库连接（`core/`）

本地启动、测试、Ruff 命令见上级 [`backend/README.md`](../README.md)。
