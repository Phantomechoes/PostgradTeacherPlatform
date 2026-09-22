# S1-03B：一个招生目录为什么必须整体保存

这篇不是 API 合同的缩写。它要说明一件事：**招生目录不是几张表各自增删改，而是一次要么全部成功、要么全部撤销的聚合保存。**

当前仍然用 Swagger、`curl` 或测试里的 TestClient 调用。**没有 Admin 网页。** `/api/v1/admin` **没有登录**，只是路径分区，仅用于 localhost 本地开发。

## 1. 03B 解决什么

S1-03A 维护的是稳定主数据，四张彼此相对独立的表：

- School
- College
- Major
- ExamSubject（`school_id` 为空是全国统考，否则是某校自命题）

S1-03B 维护的是 **AdmissionCatalog**：把下面这些放进同一条招生目录。

- 身份：School + College + Major + 年份 + 学习方式（全日制 / 非全日制）
- `directions[]`：研究方向
- `exam_units[]` 里的 `options[]`：初试单元下的可选科目

公开 S1-02 仍然只读。03B 让内部人员能创建、整份保存、显式公开或停用这条目录。

## 2. 什么叫 Aggregate

```text
AdmissionCatalog
├── 基本身份（学校、学院、专业、年份、学习方式、is_active）
├── Directions[]
└── Exam Units
    └── Options[]（指向 ExamSubject）
```

方向和科目选项不是另外两套互不相干的小功能。它们和基本身份一起，才表示「这一年、这个专业、这个学习方式招什么」。

所以保存时必须：

- 一起成功：基本字段、方向、科目选项都变成新的最终样子
- 或一起失败：这次请求里已经发给数据库的修改全部撤销

不能出现「年份已经改了，旧方向却删了一半」。

落库的是三张已有表，没有新表，也没有 migration：

- `admission_catalogs`
- `admission_catalog_directions`
- `admission_catalog_exam_subjects`

## 3. 为什么不是 child row-level REST

没有这些接口：

- `POST /directions`
- `DELETE /directions/{id}`
- 科目选项的单独增删
- Catalog 的 `DELETE`

当前编辑语义是：人在心里（或以后在页面上）改完整份目录，然后按一次保存。`PUT` 的 body 就是保存之后应该剩下的完整集合。

body 里没有的旧方向、旧选项，表示删掉。body 里有的，按新集合重建。这是聚合内部的 SQL `DELETE` + `INSERT`，不是对外的删除 API。

系统也不会自动补一个方向代码 `00`。没写方向，就是没有方向。

## 4. Shell 为什么默认 inactive

```text
POST shell（只交五元组）
        ↓
is_active = false
        ↓
PUT 整份 aggregate（方向 + 科目选项）
        ↓
PATCH status true（显式激活）
        ↓
这时公开 S1-02 才可能看得到
```

如果一 POST 就公开，半成品目录会立刻出现在 S1-02。第一版没有新的 draft / published 枚举。`is_active = false` 同时表示「尚未公开」和「已停用」。它不是第三种正式状态名。

## 5. PUT 为什么是 PUT 而不是 PATCH

03A 的 PATCH 是改一两个字段：没写的字段保持原样。

03B 的 PUT 是提交最终整份目录，顶层必须带上：

- 基本五元组
- `directions`
- `exam_units`

因此 `directions: []` 的意思是：**保存之后一条方向都没有。** 不是「这次没改方向」。`exam_units: []` 同理。

`option_order` 也不要求连号。`1` 和 `3` 可以同时存在。

## 6. Validate Before Delete

错误顺序：

```text
先删掉旧方向和旧选项
        ↓
才发现新科目不存在、跨校、或已停用
```

这时库里的旧子行已经没了。就算后面报错，也多了一次不必要的破坏，回滚负担更重。

当前顺序：

```text
加载 Catalog
        ↓
校验最终的 School / College / Major
        ↓
一次查出全部 ExamSubject，再校验
        ↓
全部合法之后
        ↓
才改基本字段、才删旧子行
```

科目不是在循环里一条条 `get_exam_subject`。Service 先收集并去重 `exam_subject_id`，再调用 `AdminSchoolRepository.get_exam_subjects_by_ids()`，那是一条 `SELECT ... WHERE id IN (...)`。没有科目时不去查。

校验失败时，旧方向和旧选项还在。测试里对仍带停用科目的 active 目录提交非法 PUT，拒绝之后方向 `01`、`02` 都还在。

## 7. 为什么 delete 后需要 flush

同一条目录上，方向代码不能重复（`uq_admission_catalog_directions_code`）。同一单元里，`option_order` 也不能重复。

例子：旧方向已经是 `01`。这次 PUT 的最终集合里仍然有 `01`（名字可能改了）。实现是删掉旧行、再插入新行，不是按 id 更新。

如果旧的 `DELETE` 还停在 Session 里、没有真正发给 PostgreSQL，就立刻 `INSERT` 一个新的 `01`，数据库会在同一次检查里看到两个 `01`，唯一约束冲突。

所以子行替换是：

```text
DELETE 旧 options、旧 directions
        ↓
flush
        ↓
INSERT 新 directions、新 options
        ↓
flush
```

不把 delete 和 insert 放进同一次 flush，也不指望 SQLAlchemy 自己猜执行顺序。

## 8. 为什么基本字段先 flush

五元组（学校、学院、专业、年份、学习方式）有唯一约束 `uq_admission_catalogs_offering`。

实现里，校验通过并改完基本字段之后，**先 flush 这一行**，然后才 `DELETE` 子行。

原因很具体：Repository 的删除用的是 `Session.execute(delete)`。SQLAlchemy 在执行这条 DELETE 之前会 autoflush。如果五元组修改还挂在内存里，冲突会在 DELETE 的 autoflush 里冒出来，变成没有被映射的 `IntegrityError`，而不是稳定的 `duplicate_catalog_offering`。

先 flush，冲突发生在 Service 自己的 `_flush()` 里，已知约束能变成 409。子行也还没开始删。

完整写入顺序是：

```text
1. 加载 Catalog
2. 校验最终 School / College / Major
3. 批量加载并校验 ExamSubject
4. 以上全部成功
5. 修改基本字段
6. flush 基本字段
7. delete 旧 options / directions
8. flush deletes
9. insert 新 directions / options
10. flush inserts
11. Router 返回领域对象
12. get_write_db() commit，然后才发送 HTTP 成功响应
```

任一步抛错，这次请求 rollback，成功响应不会发出去。

## 9. 原子 rollback

测试 `test_final_flush_failure_rolls_back_replaced_aggregate` 用的是真实 HTTP 和真实 PostgreSQL，不是假的内存列表。

原来的 `CATALOG_2027_ID`：

- 2027 / 全日制 / active
- 方向 `01`、`02`
- 科目选项包括 unit 1 的全国科目、unit 2 的两门本校科目、unit 3 的一门已停用科目

然后 PUT 一份本身合法的新聚合：方向改成 `99`，只留 unit 4 的一门全国科目。

Service 对这个 PUT 会 flush 三次。测试让前两次照常执行。第三次先调用真正的 `flush()`，于是 UPDATE、DELETE、INSERT 都已经进入当前 PostgreSQL 事务，然后再抛 `RuntimeError("forced final failure")`。

结果：

- HTTP 是 **500**，不是 200
- 失败点就是这第三次 flush
- rollback 之后：年份、学习方式、方向 `01`/`02`、原来的全部选项都回来了

「SQL 已经发给数据库」不等于「数据已经永久提交」。事务还没 commit 时，rollback 能把这次请求里的步骤一起撤掉。

另一条测试是已知冲突，不是同一件事：把这条 2027 目录改成已经存在的 2026 全日制五元组，得到 **409** `duplicate_catalog_offering`，原目录和子行保持旧值。那是约束映射。上面的 500 才是「破坏性替换已经 flush 之后仍然能整体撤销」。

## 10. flush / commit / rollback

和 03A 同一套分工：

| 词 | 谁做 | 含义 |
|---|---|---|
| flush | Service 通过 Repository | 把当前这一步送给 PostgreSQL 检查。事务还没最终生效 |
| commit | `get_write_db()` | 整份 aggregate 一起生效，并且发生在成功响应发出之前 |
| rollback | `get_write_db()` | 这个请求里已经 flush 的步骤一起撤销 |

`AdminCatalogService` 和 `AdminCatalogRepository` 都没有 `commit` / `rollback`，也不自己 `SessionLocal()`。事务主人仍然是写 dependency：

```text
Depends(get_write_db, scope="function")
```

POST、PUT、status 走它。三个 GET 走 `get_db()`，不提交。

## 11. Reference Scope

目录属于学校 S。科目是否能挂上来，规则是：

| ExamSubject.school_id | 含义 | 能否挂到这所学校的目录 |
|---|---|---|
| `NULL` | 全国统考 | 可以 |
| `S` | 这所学校的自命题 | 可以 |
| 其他学校 | 别校自命题 | 不可以，422 `reference_scope_mismatch` |

学院、专业还有「必须和目录同一所学校」的数据库外键。科目没有一条「目录学校 = 科目学校，或科目是全国统考」的外键。只靠 `exam_subject_id` 存在，挡不住把 B 校自命题挂到 A 校目录上。所以这道检查在 Service 里做，不能等数据库。

科目不存在则是 422 `invalid_reference`。

## 12. Active 与 Inactive Reference

| 操作 | 学校 / 学院 / 专业 | 科目 |
|---|---|---|
| POST shell | 必须存在、同校、且 active | 不引用科目 |
| PUT **inactive** 目录 | 必须存在且同校；允许 inactive | 必须存在；全国或同校；允许 inactive |
| PUT **active** 目录 | 最终引用必须存在、同校、且 active | 最终科目必须存在、active、全国或同校 |
| `status=true` | 按目录上**当前**引用重新检查，全部要 active | 同上 |
| `status=false` | 不再额外检查 | **不删除**方向和选项 |

已经是 active，再 PATCH `true`，也不会因为「本来就是 true」就跳过检查。停用只改 `is_active`。

这样 Admin 仍能修订历史，又不会让一份已经公开的目录继续指向停用学校或停用科目。判断标准是 **PUT 之后的最终引用**，不是旧科目。旧的停用科目不会挡住一次合法修复。

## 13. Legacy Data

库里可能已经有 active 目录指向 inactive 科目。03B **不清洗这些行，也不做 migration。**

- Admin GET 原样返回，停用科目仍在，并带 `is_active: false`
- 公开 S1-02 仍按原来的 active-only 规则读，该选项继续被滤掉
- 只有新的 active PUT，或 `status=true`，才强制新规则

所以一条不合法的旧 active 目录没有被卡死。两条路：一次 PUT 换成合法聚合；或者先 `status=false`，按 inactive 规则维护，再激活。

## 14. 为什么 empty aggregate 也能 activate

本阶段没有批准这些规则：

- 必须四个 exam unit
- 必须至少一门科目
- 必须至少一个方向
- `option_order` 必须连续

所以 `directions: []` 且 `exam_units: []`，只要学校、学院、专业存在、同校、且 active，就可以激活。不能把「我们觉得一份目录应该更完整」写成系统规则。

## 15. Admin 和 Public 为什么看到的不一样

同一条 2027 目录，历史上挂着一门停用科目：

- Admin 详情：这门科目仍返回，`subject.is_active` 为 false
- 公开详情：沿用 S1-02，这门选项不出现

Admin 是维护视图，要看见脏数据和停用行。Public 是发布视图，只看见 S1-02 原来允许看见的 active 目录；学校、学院、专业、目录本身有任何一个 inactive，公开详情就是 404，列表里也没有。

03B 使用单独的 `AdminCatalogRepository`。公开的 `AdmissionCatalogRepository._visible_catalogs()` 没有加 `include_inactive`，语义没改。

## 16. S1-04 如何复用

S1-04 导入 **还没有做**。以后如果要做，导入程序不应该 HTTP 调用自己。

它自己持有 Session、自己 commit / rollback，然后调用同一个 `AdminCatalogService`。Service 只依赖两个 Repository，不依赖 FastAPI。这就是现在不让 Service commit 的原因：HTTP 和导入可以共用规则，但不能共用同一个事务主人。

## 17. 排错地图

| 现象 | 先看 |
|---|---|
| POST shell 422，detail 是数组 | Schema：多了 `is_active`、方向、选项，或五元组不合法 |
| POST / PUT 422 `invalid_reference` | Service：学校、学院、专业或科目不存在 |
| PUT 422 `inactive_reference` | 目录将保持或变为 active，但最终引用里有停用行 |
| PUT 422 `reference_scope_mismatch` | 学院、专业或科目不属于这所学校 |
| PUT 409 `duplicate_catalog_offering` | 五元组撞了另一条目录；应在删子行之前被映射 |
| PUT 成功后旧方向或旧选项没了 | 正常，如果它们不在这次 body 里。先核对 body 是不是最终集合 |
| 500 之后数据没恢复 | `get_write_db()` 是否 rollback；写路由是不是 `scope="function"` |
| Admin 看得到、Public 看不到 | 多半是目录或上级 inactive；公开还会滤掉停用科目。这通常不是 03B 写坏了 |
| activate 失败 | 按当前库里的学校、学院、专业和科目重跑 active 规则，不是看 body |

未知的 `IntegrityError`、`RuntimeError` 或数据库故障会原样抛出，变成服务器错误，不会被伪装成业务 422。响应里也不放 psycopg 原文、SQL、`DATABASE_URL` 或密码。

## 18. 负责人关键代码

1. [`backend/app/api/admin_catalog.py`](../../backend/app/api/admin_catalog.py)
   看五个路由、读用 `get_db`、写用 `get_write_db(scope="function")`、`_call` 怎样映射错误。这里没有 SQL。

2. [`backend/app/services/admin_catalog.py`](../../backend/app/services/admin_catalog.py)
   看 `replace_aggregate` 和 `_replace_children`：先校验，再 flush 基本字段，再删、flush、插、flush。能说出「规则和步骤在这，commit 不在这」就够。

3. [`backend/app/repositories/admin_catalog.py`](../../backend/app/repositories/admin_catalog.py)
   看 Admin 列表含 inactive、删除子行、`flush`。它和公开 Repository 是两个类。

4. [`backend/app/schemas/admin_catalog.py`](../../backend/app/schemas/admin_catalog.py)
   看 shell 只收五元组，PUT 必须带两个集合，重复方向 / 单元 / 选项在这里就被拒绝。

5. [`backend/app/core/database.py`](../../backend/app/core/database.py)
   看 `get_write_db`：yield 之后 commit，异常则 rollback，最后 close。成功响应在这之后才发出。

科目的批量查询在 [`admin_master_data.py` 的 Repository](../../backend/app/repositories/admin_master_data.py) 的 `get_exam_subjects_by_ids`，不是一套新的学校仓库。

## 19. 对照规范 8 问

1. **解决什么问题？** 让内部能整份维护招生目录，同时不改公开 S1-02 的可见性。
2. **从哪里触发？** 现在是 Swagger、curl 或测试，不是 Admin 页面。
3. **请求进入哪个文件？** [`admin_catalog.py`](../../backend/app/api/admin_catalog.py)，由 [`main.py`](../../backend/app/main.py) 挂到 `/api/v1/admin`。
4. **数据在哪里处理？** 校验和替换顺序在 Service，SQL 在 Admin Catalog Repository，事务在 `get_write_db`。
5. **最后存在哪里？** `admission_catalogs`、`admission_catalog_directions`、`admission_catalog_exam_subjects`。
6. **返回结果从哪里出来？** `CatalogAdminDetail` / `CatalogAdminSummary`，由 FastAPI 写成 JSON。
7. **出问题先看什么？** 第 17 节。先分清是校验失败、唯一冲突，还是请求级 rollback。
8. **读哪几段？** Router 的写 dependency、`replace_aggregate`、`get_write_db`。
