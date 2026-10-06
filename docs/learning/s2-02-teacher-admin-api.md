# S2-02：内部怎样维护一份师资档案

这篇不是把接口清单再抄一遍。合同在 [`docs/api/s2-02-teacher-admin-api.md`](../api/s2-02-teacher-admin-api.md)。这里解释请求为什么分成四层、一次写入谁负责提交，以及几条容易看反的业务规则。

当前没有管理页面，也没有登录。调用方是 Swagger、`curl` 或测试里的 TestClient。路径都在 `/api/v1/admin` 下面。

## 1. 为什么分成 Schema、Repository、Service、Router

S2-01 只建了三张表。S2-02 让内部人员能创建档案、改状态、登记成功录取、替换可教授科目。这四层各管一件事：

| 层 | 文件 | 负责什么 | 不负责什么 |
|---|---|---|---|
| Schema | `backend/app/schemas/admin_teacher.py` | JSON 长什么样、哪些字段必填、分数怎样变成数字 | 不访问数据库 |
| Repository | `backend/app/repositories/admin_teacher.py` | 查询和写入 PostgreSQL | 不决定业务对错，不 commit |
| Service | `backend/app/services/admin_teacher.py` | 校验、组装返回对象、把已知约束变成稳定 `code` | 不认识 HTTP，不 commit |
| Router | `backend/app/api/admin_teacher.py` | 解析路径、查询参数和 body，调用 Service，把业务错误变成 HTTP | 不自己查表，不算业务规则 |

先把形状定下来，再写查询，再写规则，最后才接到 HTTP。某一层的测试失败时，就知道该看哪一层，而不是整条链路一起猜。

## 2. `/api/v1/admin` 不是安全边界

这个前缀只表示「内部维护」，不是「已经登录的管理员」。

当前没有 auth、JWT、RBAC。任何人只要能访问这台开发服务，就能调用这些接口。所以它只用于本机开发。不要把电话、微信、邮箱写进 `bio`，表里也没有这些列。

公开读接口仍是 `/api/v1` 下的院校主数据。没有 `/api/v1/teacher-profiles`，也没有公开师资详情。

## 3. 读和写的事务边界

GET 使用 `get_db()`：打开 Session，用完关闭，不提交。

POST、PATCH、PUT 使用 `get_write_db(scope="function")`：

```text
打开 Session
    ↓
Router 调用 Service
    ↓
Service 校验，Repository flush（先问数据库约束）
    ↓
路径函数返回
    ↓
get_write_db commit；失败则 rollback
    ↓
这时才把 HTTP 响应发给客户端
```

`scope="function"` 的意义是：提交发生在响应发出去之前。如果提交阶段失败，客户端不能先拿到 201 或 200。

Repository 和 Service 里没有 `commit`，也没有 `rollback`。事务主人是 `get_write_db`。Service 里的 `flush` 只是在当前事务中提前把 SQL 送到 PostgreSQL，事务仍然可以整笔撤销。

## 4. 三个状态互不带动

`TeacherProfile` 上有三列，问的是三件不同的事：

| 列 | 问的是 | 例子 |
|---|---|---|
| `is_active` | 这份档案还用不用 | 停用后不再作为可维护的新录取对象 |
| `availability_status` | 现在接不接新教学 | `unknown` / `available` / `unavailable` |
| `verification_status` | 基础审核到了哪一步 | `unverified` / `verified` / `rejected` |

停用档案不会自动改成「不接教学」。审核拒绝也不会自动停用档案。三个 PATCH 各自只改自己那一列。

## 5. AdmissionRecord 是独立的成功录取事实

录取不是档案头上的几个字段，而是子记录：哪所学校、哪个学院、哪个专业、哪一年、全日制还是非全日制，以及可选的初试、复试、总分。

它记录的是「这个人已经成功考上了这条招生」，不是意向，也不是在读状态。

- 详情返回这个老师的全部录取，包括已经作废的（`is_active = false`）。
- 列表按学校、学院、专业、年份、学习方式筛选时，只看仍然有效的录取。

所以：一条录取作废后，用学校去筛列表，这个老师不会因为这条作废记录被算进去；打开详情，这条作废记录还在。

## 6. 筛选必须落在同一条录取上

错误理解：老师有两条录取，A 是学校甲，B 是专业乙，于是「学校甲 + 专业乙」能找到这个老师。

正确规则：所有条件必须同时满足同一条 `AdmissionRecord`。实现是一条相关子查询（correlated `EXISTS`），里面同时要求：

- `teacher_profile_id` 等于当前老师
- `is_active` 为真
- 本次请求里带上的学校、学院、专业、年份、学习方式

A 只满足学校，B 只满足专业。两条拼起来不算命中。

## 7. 修改录取时先合成完整目标

PATCH 可以只带一个字段。Service 不是只检查这个字段，而是：

```text
数据库里的旧行
    + 本次 JSON 里真正出现的字段（exclude_unset）
    = 改完之后的完整目标
    → 按这个目标做校验
    → 通过后才写入
    → flush
```

没出现在 JSON 里的字段保持旧值。JSON 里明确写出 `null` 的字段，是要把可空列清空。例如同时传 `initial_total: null` 和 `admission_catalog_id: null`，会取消分数并断开招生目录，而不是忽略这两个键。

因此：只改分数时，即使学校后来被停用，仍然允许，因为学校没有变。只改年份时，如果还挂着旧年份的招生目录，整次请求失败，年份也不会被改掉。

## 8. 招生目录要对上五元组，不看它是否启用

录取可以挂一条 `AdmissionCatalog`。对得上，指这五项相同：

学校、学院、专业、年份、学习方式。

目录后来被停用，不表示这五项变了。恢复一条录取时，要求这五项仍然对得上，也要求学校、学院、专业还在；不要求它们当前是启用状态，也不要求目录当前是启用状态。

## 9. 停用的老师可以减科目，不能加科目

`TeacherTeachSubject` 没有自己的启用开关。修改方式是整份替换：请求里的科目列表就是新的完整集合。

停用老师时：

```text
added_ids = 请求中的科目 - 当前已经挂着的科目
```

`added_ids` 为空：允许。所以可以删掉一个、全部清空，或原样再提交一次。

`added_ids` 非空：拒绝，错误码 `parent_inactive`。失败时旧集合保持不变，不会先删后加留下一半。

## 10. 后来停用的科目可以留，新的停用科目不能加

科目自己的 `is_active` 是另一件事。

- 已经挂在这个老师身上的科目，后来被停用：这次替换里可以继续留下，也可以拿掉。
- 当前集合里没有、而科目本身已停用：不能新增，错误码 `inactive_reference`。

## 11. 先确认科目存在，再判断能不能新增

替换科目的顺序是：

1. 老师必须存在
2. 读出当前已挂科目
3. 按请求里的 id 批量加载科目
4. 有 id 不存在 → `invalid_reference`
5. 算出 `added_ids`
6. 老师已停用且有新增 → `parent_inactive`
7. 新增的科目已停用 → `inactive_reference`
8. 以上都通过，才删除旧关系并插入新关系

这里曾经写反过。停用老师再提交一个不存在的新科目时，旧实现先报 `parent_inactive`。测试要求先报「这个科目不存在」。修复后，存在性检查在停用父记录检查之前。这个顺序同时锁在 Service 测试和 HTTP 测试里。

## 12. 测试各证明什么

| 测试 | 证明 |
|---|---|
| Schema | JSON 形状、空字符串、显式 null、分数在 JSON 里是数字 |
| Repository | 同一条录取上的筛选、停用录取不参与筛选、PostgreSQL 约束 |
| Service | 业务规则、错误码、删除已 flush 后整笔回滚、约束名如何映射 |
| HTTP | 路径和查询参数有没有接错、错误码有没有变成正确的 HTTP 状态、跨请求还能读到、提交失败时不会先返回成功 |

HTTP 测试不把 Service 的每一种排列再做一遍。它只锁那些穿过 Router 之后仍可能变形的行为。

## 13. 明确不在本篇范围内

- Admin Web 页面
- 公开师资 API
- 登录和权限
- 电话、微信、邮箱等联系方式
- DELETE 老师或录取
- 单条添加或删除科目的接口
- 单独按录取 id 做 GET

这些都没有批准，本文不设计它们。

## 14. 出问题先看哪里

1. 返回了 422 但 `detail` 是数组：多半是路径、查询参数或 JSON 形状不合法，请求还没进 Service。
2. `detail.code` 是 `not_found`、`parent_inactive`、`invalid_reference`、`catalog_identity_mismatch`、`duplicate_admission`：看 Service 里对应校验，以及 Router 的状态码表有没有漏。
3. 客户端先收到了成功，但数据其实没留下：看 `get_write_db(scope="function")` 是否仍在响应前提交。

建议读这三段：

- Router 怎样把 `MasterDataWriteError` 变成 HTTP：[`backend/app/api/admin_teacher.py`](../../backend/app/api/admin_teacher.py)
- 录取修改如何合成完整目标：[`backend/app/services/admin_teacher.py`](../../backend/app/services/admin_teacher.py) 的 `update_admission`
- 列表筛选为什么必须同一行：[`backend/app/repositories/admin_teacher.py`](../../backend/app/repositories/admin_teacher.py) 的 `_apply_admission_exists`
