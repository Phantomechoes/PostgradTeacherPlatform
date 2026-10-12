# backend/app/services

**职责：业务规则。**

这里已经有 Service。API 收到请求后，允不允许、怎么处理、结果是什么，由这一层决定。Router 不直接写这些规则，Repository 不代替这一层做审批。

当前包括：

- `MasterDataReadService`（`master_data.py`）
- `AdminMasterDataService`（`admin_master_data.py`）
- `AdminCatalogService`（`admin_catalog.py`）
- `AdminTeacherService`（`admin_teacher.py`）

Teacher Admin 已实现档案、三个正交状态、录取和整集合可教授科目。三个状态互不带动：不要求已核验、已有录取或已有可教授科目才能保持 active。这不是选师、支付或自动推荐。

Service 不自行 `commit` / `rollback`。写事务由 `get_write_db` 在请求结束时提交或回滚。

调研尚未确认的规则（支付、佣金、选师、SLA 等）不得在这里写死。
