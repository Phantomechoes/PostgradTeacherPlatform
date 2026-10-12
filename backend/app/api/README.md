# backend/app/api

**职责：接收外部请求，调用 Service，返回 HTTP 响应。**

这一层现在已经有 FastAPI Router。`main.py` 挂上这些模块：

- `master_data.py`：主数据 Public Read，前缀 `/api/v1`，例如 `GET /api/v1/schools`
- `admin_master_data.py`：主数据 Admin，前缀 `/api/v1/admin`
- `admin_catalog.py`：招生目录 Admin，前缀 `/api/v1/admin`
- `admin_teacher.py`：Teacher Admin，前缀 `/api/v1/admin`，例如 `GET /api/v1/admin/teacher-profiles` 与 `PUT /api/v1/admin/teacher-profiles/{teacher_profile_id}/teach-subjects`

`GET /health` 在 `main.py`，不在这些 router 文件里。没有 Public Teacher 路由。

这一层应该做的事：

- 校验请求参数
- 调用对应的 Service
- 把结果或错误转换成 HTTP 响应

这一层不应该做的事：

- 直接写复杂业务规则
- 直接读写数据库
- 把数据库内部字段原样暴露出去

业务前缀约定（S0-02 起生效）：`/api/v1`。健康检查：`GET /health`。
