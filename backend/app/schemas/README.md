# backend/app/schemas

**职责：描述 API 的输入和输出长什么样。**

这里已经有 Pydantic Schema，包括主数据读模型（`master_data.py`）、主数据 Admin（`admin_master_data.py`）、招生目录 Admin（`admin_catalog.py`）和 Teacher Admin（`admin_teacher.py`）。Teacher Admin Schema 只服务 `/api/v1/admin`，不表示已经有 Public Teacher API。没有 StudentDemand、Institution、Candidate 或 Match Schema。

Schema 是对外的“表格格式”：

- 请求里允许填哪些字段
- 响应里返回哪些字段
- 哪些字段不能对外暴露（密码、内部状态等）

API 使用 Schema，不直接把数据库 Model 交给前端或小程序。
