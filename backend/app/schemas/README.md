# backend/app/schemas

**职责：描述 API 的输入和输出长什么样。**

以后这里放 Pydantic Schema。可以把它理解成对外的“表格格式”：

- 请求里允许填哪些字段
- 响应里返回哪些字段
- 哪些字段不能对外暴露（密码、内部状态等）

API 使用 Schema，不直接把数据库 Model 交给前端或小程序。
