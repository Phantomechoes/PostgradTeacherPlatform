# backend/app/repositories

**职责：数据库读写。**

这里已经有 Repository。Service 存取数据时走这一层，而不是在业务规则里直接拼 SQL。

当前包括 `master_data.py`、`admin_master_data.py`、`admin_catalog.py` 和 `admin_teacher.py`（`AdminTeacherRepository`）。它们负责查询和写入。业务规则由 Service 决定。Repository 不 `commit`，也不管理请求生命周期。

可以把它理解成“仓库管理员”：只负责按要求取出或放回数据，不决定业务该怎么走。
