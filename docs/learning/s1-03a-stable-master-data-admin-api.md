# S1-03A：一次 Admin 写请求怎样安全地修改 PostgreSQL

这篇不是再抄一遍 API 清单，而是让负责人看懂：**第一次把数据写入 PostgreSQL 时，请求经过哪几层、谁负责提交、失败时为什么不会留下半截修改。**

当前触发方式是 Swagger、`curl` 或测试里的 TestClient。**Admin 网页还不能操作这些接口**（那是 S1-03C）。`/api/v1/admin` **没有登录**，只是路径分区，仅用于 localhost 本地开发。

## 1. S1-03A 解决什么

S1-02 之后，程序只能 **GET** 已启用的学校、学院、专业、科目。运营无法在系统里新建一所学校，也无法停用写错的数据。

S1-03A 给这四类**稳定主数据**补上内部维护能力：

- School
- College
- Major
- ExamSubject（全国统考 / 学校自命题）

可以：创建、部分修改、停用、恢复。
还没有：Catalog 写入、Direction / 考试科目组合、Admin 页面、账号权限、DELETE。

## 2. 一次 POST 完整链路

例子：`POST /api/v1/admin/schools`，body 为学校代码和名称。

```text
Swagger / curl / TestClient
        ↓
Admin Router          backend/app/api/admin_master_data.py
        ↓
get_write_db()        function scope：打开 Session
        ↓
AdminMasterDataService
        ↓
AdminSchoolRepository
        ↓
SQLAlchemy Session
        ↓
INSERT，然后 flush（先问 PostgreSQL 约束）
        ↓
path operation 结束
        ↓
get_write_db() commit（成功）或 rollback（失败）
        ↓
close
        ↓
这时才把 HTTP 响应发给客户端
```

Router 不写 SQL，也不 `commit`。它只认 URL、校验 JSON、调用 Service、把领域错误变成 HTTP。

## 3. GET 和 WRITE 为什么用不同 dependency

| | `get_db()` | `get_write_db()` |
|---|---|---|
| 谁用 | 公开 S1-02 GET，以及 Admin GET | Admin 的 POST / PATCH / status |
| 生命周期 | 打开 Session → 用完 close | function scope：打开 Session → path 函数结束 → commit/rollback → close → **然后才发响应** |
| 会不会提交 | **不会** | **会**，而且必须在告诉客户端成功之前完成 |

读请求没有东西要提交，保持原来的只读生命周期，S1-02 行为不变。
写请求必须有一个明确的事务主人。`flush` 是在事务里提前问数据库约束；`commit` 必须在“告诉客户端成功”之前完成。如果 commit 失败，客户端不能已经拿到 201。

## 4. flush 和 commit 不一样

**flush**：把当前 Session 里还没发出去的改动发给 PostgreSQL，让 unique / 外键 / CHECK 立刻报错。此时事务**还没有最终提交**，还可以 rollback。

**commit**：确认本次事务，改动对后续请求可见。对 Admin 写接口，这一步发生在 HTTP 响应发出去之前（`Depends(..., scope="function")`）。

例子：库里已有 `school_code = 10004`。再 POST 一个同样代码的学校：

1. Service 把新行 `add` 进 Session
2. `flush` → PostgreSQL 发现 `uq_schools_school_code` 冲突
3. Service 把它变成稳定错误 `duplicate_school_code`，而不是把 psycopg 原文丢给前端
4. Router 返回 **409**
5. `get_write_db()` **rollback**，这次插入不留下

如果等到 commit 才发现冲突，错误更晚、更难保证“失败即干净”。

## 5. rollback 是什么

测试里做过这件事：School C 原来的代码是 `ZZ_TEST_S102_C`。PATCH 把它改成已经存在的 `ZZ_TEST_S102_A`。

- flush 触发唯一冲突
- HTTP **409**
- 再 GET School C：代码**仍是** `ZZ_TEST_S102_C`

所以“返回 409”和“数据库没留下半截修改”是两件事。只返回错误但 Session 里还挂着错误值，下次读同一 Session 就会看到脏数据。rollback 把这次请求的改动撤掉。

## 6. 为什么 Repository / Service 不 commit

事务只能有一个主人。现在主人是 `get_write_db()`。

如果 Repository 每改一行就 commit，后面某一步失败就无法整体回滚。S1-03B 的 Catalog 聚合保存（基本信息 + 方向列表 + 科目列表一次提交）正需要这个习惯：多步改动，一次成功或一次失败。

未来 S1-04 导入也不会走 HTTP，而是自己拿 Session、自己管事务，直接调用同一个 Write Service。

## 7. Admin inactive 与 Public inactive

```text
Public S1-02
  inactive → 当它不存在（详情 404，列表看不到）

Admin
  inactive → 仍在
           → GET 200，带 is_active=false
           → 还能改名字
           → 还能 status=true 恢复
```

停用 **不是** 删除。没有 DELETE 接口。历史招生目录以后还可能引用这些学校/专业，所以第一版只改 `is_active`。

停用一所学校 **不会** 批量改它下面学院、专业的 `is_active`。公开接口之所以看不到，是因为读的时候要求学校本身是 active。学校恢复后，原来仍是 active 的下级会对公开接口重新可见。

## 8. Parent inactive

父学校 inactive 时：

| 操作 | 结果 |
|---|---|
| GET 该校已有学院 / 专业 / 自命题 | **200**，Admin 还要管这些下级 |
| PATCH 已有下级、把下级恢复 | **允许** |
| 再 **新建** 学院 / 专业 / 自命题 | **422** `parent_inactive` |

父学校根本不存在：新建下级 **404**。

## 9. National / School ExamSubject

- 全国统考：`POST /api/v1/admin/exam-subjects/national`，服务端固定 `school_id = NULL`（如 101）
- 学校自命题：`POST /api/v1/admin/schools/{school_id}/exam-subjects`，`school_id` 只来自路径（如某校 895）

创建后不能互转。PATCH 不能带 `school_id`；硬传会因为 write schema `extra="forbid"` 变成 422。

## 10. Error mapping

| 情况 | HTTP | 怎么理解 |
|---|---|---|
| 这条记录根本没有 | 404 | `not_found` |
| 代码重复 | 409 | `duplicate_*` |
| 父学校停用还要新建下级 | 422 | `parent_inactive` |
| PATCH `{}` | 422 | `empty_patch` |
| JSON 缺字段、类型错、显式 null、多传字段 | 422 | **Pydantic 默认数组**，结构与上面的 `{code, message}` 不同 |

业务 422 的 body 是：

```json
{ "detail": { "code": "parent_inactive", "message": "..." } }
```

Pydantic 422 的 body 是 `detail` 数组。测试和前端要按两种形状处理，不要混成一种。

未知的数据库错误不会被假装成 409/422，避免把真正的故障藏起来。

## 11. 测试事务为什么不污染开发库

自动化测试里有一层**外层事务**：整个测试用例在一个未最终提交的数据库事务里。请求里的 `commit()` 在 SQLAlchemy 里只提交内部 SAVEPOINT，让同一测试的下一次 GET 能看到刚才写入的行。测试结束时外层 **rollback**，`ZZ_TEST_...` 不会留在开发库。

可以把它理解成：测试演练了正式的 commit/rollback 逻辑，但用一层外套把真实库保护起来。

## 12. 当前还没有什么

- Admin Web 还没接这些 API
- 没有登录 / 权限
- 没有 Catalog / 方向 / 初试科目组合的写入
- 没有 DELETE
- 没有种子导入（S1-04）

## 13. 排错地图

| 现象 | 先看 |
|---|---|
| POST 422，detail 是数组 | Schema：缺字段、null、extra 字段 |
| POST 422，`code=parent_inactive` 或 `empty_patch` | Service 业务规则；Router 映射 |
| 409 duplicate_* | 代码冲突；Repository flush；不要去翻 psycopg 原文 |
| Admin GET 看得到，Public 404 | 正常：该行 `is_active=false` |
| 写完立刻 GET 没有 | 是否误用了 `get_db` 而不是 `get_write_db` |
| 测试数据进了开发库 | `conftest.py` 外层事务 / `get_write_db` override |

## 14. 负责人关键代码

1. [`backend/app/core/database.py`](../../backend/app/core/database.py)
   看 `get_db` 和 `get_write_db`。能说出「读不提交、写成功才提交、失败回滚」就够。

2. [`backend/app/api/admin_master_data.py`](../../backend/app/api/admin_master_data.py)
   看路由前缀、`national` 写在 `{id}` 前面、`_call` 如何把领域错误变成 HTTP。不要在这里找 SQL。

3. [`backend/app/services/admin_master_data.py`](../../backend/app/services/admin_master_data.py)
   看 `create_*`、inactive 父学校、`_flush` 把已知约束变成 `ConflictError`。能说出「业务规则在这，HTTP 不在这」就够。

4. [`backend/app/repositories/admin_master_data.py`](../../backend/app/repositories/admin_master_data.py)
   看 get/list（含 inactive）和 `flush`。能说出「SQL 在这，不 commit」就够。

## 15. 对照规范 8 问

1. **解决什么问题？** 让内部能维护稳定主数据，而不改公开只读合同。
2. **从哪里触发？** 现在是 Swagger / curl / 测试，不是 Admin 页面。
3. **请求进入哪个文件？** [`admin_master_data.py`](../../backend/app/api/admin_master_data.py)，由 [`main.py`](../../backend/app/main.py) 挂载。
4. **数据在哪里处理？** 规则在 Service，SQL 在 Repository，事务在 `get_write_db`。
5. **最后存在哪里？** 仍是 `schools` / `colleges` / `majors` / `exam_subjects`。
6. **返回结果从哪里出来？** AdminRead Schema → FastAPI JSON。
7. **出问题先看什么？** 第 13 节。
8. **读哪几段？** `get_write_db`、Router `_call`、Service `_flush`。
