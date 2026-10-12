# backend/app/core

**职责：后端的公共基础设施，不是具体业务。**

这里已经有跨模块的基础能力，没有业务规则：

- `config.py`：读取环境变量（`Settings`）
- `db_base.py`：SQLAlchemy 声明式 `Base`
- `database.py`：`engine`、`SessionLocal`，以及请求依赖 `get_db` / `get_write_db`

`get_db` 只提供 Session，结束时关闭，不提交写事务。`get_write_db` 在成功结束时 `commit`，异常时 `rollback`。这里没有缓存、认证中间件、消息队列或权限系统。
