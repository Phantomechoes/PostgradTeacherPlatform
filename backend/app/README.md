# backend/app

后端的应用程序包。几乎所有后端代码都放在这个目录下的子层里。

程序入口是 `main.py`。请求链路是 Router → Service → Repository → Model → PostgreSQL。当前提供：

- `GET /health`（不查库）
- Master Data Public Read API
- Master Data Admin API
- AdmissionCatalog Admin API
- Teacher Admin API（`/api/v1/admin`，不是 Public Teacher API）
- 主数据 Models 与 Teacher Models（`models/`）
- 配置与数据库连接（`core/`）

没有 auth、Institution API、Demand API 或 Match API。

本地启动、测试、Ruff 命令见上级 [`backend/README.md`](../README.md)。
