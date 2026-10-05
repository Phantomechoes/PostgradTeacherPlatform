# S2-02 Teacher Admin API 合同

对应 Issue：[S2-02](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/45)
Planning 冻结：[Issue #44](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/44)（CLOSED / COMPLETED）
状态：Checkpoint 1 — 合同与 Pydantic schemas（尚未实现 Router / Service / Repository）
基线 Schema：S2-01 / Alembic `695107900fc3`
ADR：[`ADR-0002-sprint2-teacher-foundation-model.md`](../decisions/ADR-0002-sprint2-teacher-foundation-model.md)
稳定主数据 Admin：[`s1-03a-stable-master-data-admin-api.md`](./s1-03a-stable-master-data-admin-api.md)
招生目录 Admin：[`s1-03b-admission-catalog-admin-api.md`](./s1-03b-admission-catalog-admin-api.md)
公开只读合同：[`s1-02-master-data-read-api.md`](./s1-02-master-data-read-api.md)（**本 Issue 不修改**）

#44 已冻结 API-D1～API-D18。本实现无权重新设计这些决策。

**API-D7 已由负责人修正，与原 Grok Planning 推荐不同。以 #44 最终冻结版本为准。**

本文冻结 Teacher Admin API。不含 Admin Teacher Web、Public Teacher API、auth、migration。

## 1. 目标

为内部管理员维护：

- TeacherProfile 档案头
- 三个正交状态：`is_active` / `availability_status` / `verification_status`
- 成功录取 AdmissionRecord
- 显式可教授科目 TeacherTeachSubject

资源模型（API-D1 = C）：

```text
TeacherProfile                  主资源
  ├─ AdmissionRecord            独立子资源（自有 id 与 is_active）
  └─ TeacherTeachSubject        无载荷标签集合（整集合 PUT）
```

## 2. 安全与范围

全部 Teacher API 仅位于 `/api/v1/admin`。

`/api/v1/admin` 只是 URL 命名空间，**不是安全边界**。本 Issue **不做 auth** / login / JWT / RBAC。

第一版仅用于 **localhost 本地开发**。

## 3. Non-scope

- Admin Teacher Web
- Public Teacher API（不得新增 `/api/v1/teacher...`）
- auth / login / JWT / RBAC
- User
- ExamScore 独立表
- 联系方式：phone / mobile / wechat / qq / email / address / contact_note
- Verification material、身份证、录取通知书、成绩单、OCR
- matching / recommendation / payment / institution workflow / IM
- hard DELETE REST
- TeachSubject row-level POST/DELETE REST
- 独立 `GET /admission-records/{id}`（API-D18 = A）
- 自动从 Admission / Catalog 推导 TeacherTeachSubject
- Model / migration / DDL
- 公开 S1-02 合同变更
- completeness rule（API-D13 = A）

## 4. 事务

读：现有 `get_db()`（yield + close，**不 commit**）。

写：现有 `get_write_db()`，且 `Depends(get_write_db, scope="function")`。

```text
SessionLocal()
  → yield Session
  → path operation（Service 校验 / 变更 / flush）
  → 成功：commit；异常：rollback
  → close
  → 这时才发送 HTTP 响应
```

- Repository：query / add / delete-for-replace / flush；**不 commit / rollback**
- Service：业务校验、组装 Read schema、把已知约束映射为稳定 `code`；**不 commit / rollback**
- 客户端看到 201/200 时，事务已经提交成功

TeachSubject PUT 必须：

1. 验证全部 requested subject 存在
2. 完成 API-D7 `added_ids` 判断
3. 完成 API-D12 inactive subject 判断
4. 再 delete old
5. 再 insert new
6. flush
7. `get_write_db` commit

任意错误整请求 rollback。不得出现：旧标签已删、新标签校验失败的半状态。

Checkpoint 1 不实现 Service / Repository；上述规则在 Checkpoint 2 落地。

## 5. Endpoints

全部位于 `/api/v1/admin`。

| method | path | purpose |
|---|---|---|
| GET | `/teacher-profiles` | 分页列表 + 筛选 |
| GET | `/teacher-profiles/{teacher_profile_id}` | 详情（含全部录取与科目） |
| POST | `/teacher-profiles` | 创建档案头 |
| PATCH | `/teacher-profiles/{teacher_profile_id}` | 改 `display_name` / `bio` |
| PATCH | `/teacher-profiles/{teacher_profile_id}/status` | 改 `is_active` |
| PATCH | `/teacher-profiles/{teacher_profile_id}/availability` | 改 `availability_status` |
| PATCH | `/teacher-profiles/{teacher_profile_id}/verification` | 改 `verification_status` |
| POST | `/teacher-profiles/{teacher_profile_id}/admission-records` | 新增一条成功录取 |
| PATCH | `/admission-records/{admission_record_id}` | 纠错录取字段 |
| PATCH | `/admission-records/{admission_record_id}/status` | 作废 / 恢复该录取 |
| PUT | `/teacher-profiles/{teacher_profile_id}/teach-subjects` | 整集合替换可教授科目 |

明确没有：

- DELETE Teacher
- DELETE AdmissionRecord
- TeachSubject row-level POST/DELETE REST
- 独立 `GET /admission-records/{id}`
- Public Teacher API

Write schema：`extra="forbid"`。未知字段 → FastAPI 默认 422 数组。

## 6. TeacherProfile create

```text
POST /api/v1/admin/teacher-profiles
```

```json
{
  "display_name": "ZZ_S202_T1",
  "bio": null
}
```

| 字段 | 规则 |
|---|---|
| `display_name` | 必填；非空；不允许 null；不允许 blank |
| `bio` | 可省略或 `null`；非 null 时不得为空字符串 / blank |

服务端固定（API-D2 = A）：

- `is_active = true`
- `availability_status = "unknown"`
- `verification_status = "unverified"`

Create schema **不得接受**：`is_active`、`availability_status`、`verification_status`、`id`、timestamps、User、任何联系方式。

成功 **201**，body 为 `TeacherAdminDetail`（`admission_records: []`，`teach_subjects: []`）。

Teacher 不存在的 path 调用 → 404 `not_found`。inactive Teacher 的 GET detail → **200**。

## 7. TeacherProfile PATCH

```text
PATCH /api/v1/admin/teacher-profiles/{teacher_profile_id}
```

只允许 `display_name` / `bio`（API-D3）。

| 字段 | omitted | explicit null | `""` / blank |
|---|---|---|---|
| `display_name` | 保持 | 422 | 422 |
| `bio` | 保持 | 清空为 SQL NULL | 422 |

`{}` → 未来 Service 422 `empty_patch`。

Schema 必须让 `model_dump(exclude_unset=True)` 区分 omitted 与 explicit null。不得把 omitted 当成 explicit null。

普通 PATCH 不得接受 `is_active` / `availability_status` / `verification_status`。

不存在 → 404。inactive 目标仍可 PATCH 档案头（200）。

## 8. 三个状态（正交）

三者保持正交（API-D3 / API-D13）。

- 停用 Teacher **不**自动修改 availability
- `rejected` **不**自动 inactive
- `unverified` 允许 `is_active=true`
- verification 可在 `unverified` / `verified` / `rejected` 之间任意显式切换
- 不增加 `pending` / `approved_by` / `reviewed_at`
- 无 completeness：激活不要求 verified、录取或科目

### StatusUpdate

复用现有 `StatusUpdate`：

```json
{ "is_active": true }
```

`is_active` 必填 boolean。已是目标状态 → 200 幂等。

```text
PATCH /api/v1/admin/teacher-profiles/{teacher_profile_id}/status
```

### AvailabilityUpdate

```text
PATCH /api/v1/admin/teacher-profiles/{teacher_profile_id}/availability
```

```json
{ "availability_status": "available" }
```

仅 `unknown` / `available` / `unavailable`。字段必填。非法 literal → FastAPI 422 数组。`extra="forbid"`。

### VerificationUpdate

```text
PATCH /api/v1/admin/teacher-profiles/{teacher_profile_id}/verification
```

```json
{ "verification_status": "verified" }
```

仅 `unverified` / `verified` / `rejected`。`pending` 非法。字段必填。`extra="forbid"`。

## 9. Teacher list

```text
GET /api/v1/admin/teacher-profiles
```

| query | 规则 |
|---|---|
| `status` | `all` \| `active` \| `inactive`，默认 **`all`**（API-D17） |
| `availability?` | `unknown` \| `available` \| `unavailable` |
| `verification?` | `unverified` \| `verified` \| `rejected` |
| `q?` | trim 后子串；**只搜 `display_name`**；不搜 bio；无联系方式列 |
| `school_id?` | `> 0` |
| `college_id?` | `> 0` |
| `major_id?` | `> 0` |
| `admission_year?` | `>= 2000` |
| `study_mode?` | `full_time` \| `part_time` |
| `exam_subject_id?` | `> 0`；当前 TeacherTeachSubject EXISTS |
| `page` | 默认 1，`>= 1` |
| `page_size` | 默认 20，1–100 |

非法 query → FastAPI 默认 422 数组。

响应：`Page[TeacherAdminSummary]`。

排序（确定性，不新增 index）：

```text
display_name ASC, id ASC
```

`total`：以 `teacher_profiles` 为 COUNT 主体。禁止 JOIN 后再 count 导致重复 Teacher。

### 9.1 Admission filters：same-row + active-only

`school_id` / `college_id` / `major_id` / `admission_year` / `study_mode` 必须落在 **同一条** AdmissionRecord，且只匹配 `AdmissionRecord.is_active = true`（API-D5 = A）。

禁止多个独立 JOIN / 多个独立 EXISTS 造成交叉命中：

```text
Admission 1: School A / Major Y
Admission 2: School B / Major X
filter: school_id=A AND major_id=X
→ 不得命中该 Teacher
```

未来 Repository 必须是 **同一个** Admission EXISTS predicate。

`exam_subject_id` 使用当前 `teacher_teach_subjects` 的 EXISTS，不从 Admission / Catalog 推导。

## 10. Teacher read schemas

第一版 **不暴露** `created_at` / `updated_at`（API-D15 = A）。不包含 contact / sensitive material。

### TeacherAdminSummary

- `id`
- `display_name`
- `bio`（`string | null`）
- `is_active`
- `availability_status`
- `verification_status`

列表不展开全部录取。

### TeacherAdminDetail

Summary 字段 +：

- `admission_records`：全部录取，含 inactive（API-D6 = B）
- `teach_subjects`：`ExamSubjectAdminRead[]`

inactive Teacher：GET detail **200**，不得当 404。

Admission 排序：

```text
is_active DESC, admission_year DESC, id ASC
```

Teach subjects 读取排序：`exam_subject_id ASC`。输入顺序无业务语义。

嵌套主数据（API-D14 = B）复用现有：

- `SchoolAdminRead`
- `CollegeAdminRead`
- `MajorAdminRead`
- `ExamSubjectAdminRead`

不得复制一套 read model。历史 inactive master / inactive ExamSubject **仍返回**，其 `is_active=false` 必须可见。GET **不得**过滤它们。

## 11. AdmissionRecord create

```text
POST /api/v1/admin/teacher-profiles/{teacher_profile_id}/admission-records
```

`teacher_profile_id` 只来自 path，body 不得含该字段。`is_active` 由 Service 固定 `true`。

Create 允许：

- `school_id` / `college_id` / `major_id`：必填，`> 0`
- `admission_year`：必填，`>= 2000`
- `study_mode`：`full_time` \| `part_time`
- `admission_catalog_id`：可省略或 `null`；非 null 时 `> 0`
- `initial_total` / `retest_total` / `final_total`：可省略或 `null`；非 null 必须 `>= 0`；Decimal 语义；不写死 500 / 300 / 100

不得接受：`teacher_profile_id`、`is_active`、`id`、timestamps。

成功 **201**，body 为 `AdmissionRecordAdminRead`。

### 11.1 Service 规则（Checkpoint 2 实现）

| 情况 | HTTP | code |
|---|---|---|
| Teacher 不存在 | 404 | `not_found` |
| Teacher inactive | 422 | `parent_inactive` |
| School / College / Major 不存在 | 422 | `invalid_reference` |
| 引用存在但 inactive（create / 更换 refs） | 422 | `inactive_reference` |
| College 或 Major 与 `school_id` 不同校 | 422 | `reference_scope_mismatch` |
| 录取 Unique | 409 | `duplicate_admission` |

create / 更换 refs 时 School / College / Major 必须存在、同校、**active**（API-D8 = C）。

Service 必须显式加载 School / College / Major 并校验同校，不要等组合 FK 再变成泛化 `invalid_reference`。

## 12. optional AdmissionCatalog

`admission_catalog_id = null`：合法。只校验 School / College / Major。

非 null：Service 加载 Catalog，其五元组必须与 AdmissionRecord **effective target state** 完全一致：

- `school_id`
- `college_id`
- `major_id`
- `admission_year`
- `study_mode`

| 情况 | HTTP | code |
|---|---|---|
| Catalog 不存在 | 422 | `invalid_reference` |
| Catalog 存在但五元组不同 | 422 | `catalog_identity_mismatch` |

Catalog **不要求** `is_active=true`（API-D9 = A）。Admission 表达历史成功录取事实，不绑定 Catalog 当前公开状态。

## 13. AdmissionRecord PATCH

```text
PATCH /api/v1/admin/admission-records/{admission_record_id}
```

允许：`school_id` `college_id` `major_id` `admission_year` `study_mode` `admission_catalog_id` `initial_total` `retest_total` `final_total`

不得接受：`teacher_profile_id`、`is_active`、`id`、timestamps。

| 字段 | omitted | explicit null |
|---|---|---|
| 三个 totals | 保持 | 清空该分数 |
| `admission_catalog_id` | 保持 | 解除 Catalog 链接 |
| 五元组必填列 | 保持 | 422 |

`{}` → 未来 Service 422 `empty_patch`。

Schema 必须支持 `model_dump(exclude_unset=True)` 区分 omitted 与 explicit null。

### 13.1 effective target state

Service 必须：

1. `exclude_unset`
2. 将 PATCH 提供字段覆盖到旧 AdmissionRecord
3. 得到完整 effective target state
4. 对完整 state 做 same-school、reference、Catalog five-tuple、Unique 校验

不得只校验本次单独出现的字段。例如只改 `major_id`，仍必须与旧 school / college / year / study_mode / Catalog 一起校验。

改 refs 时，**新** School / College / Major 必须存在、同校、active。PATCH **未修改 refs** 时，可以继续维护引用后来 inactive 的历史录取（API-D8）。

Unique 撞到另一行（含 inactive 占用）→ 409 `duplicate_admission`。

不存在的 Admission → 404 `not_found`。Teacher inactive **不**把已有 Admission 变成 404。

## 14. AdmissionRecordAdminRead

用于 Teacher detail nested response，以及 Admission PATCH / status 返回值。

- `id`
- `teacher_profile_id`
- `school` → `SchoolAdminRead`
- `college` → `CollegeAdminRead`
- `major` → `MajorAdminRead`
- `admission_year`
- `study_mode`
- `admission_catalog_id`（`int | null`）
- `initial_total` / `retest_total` / `final_total`（Decimal \| null）
- `is_active`

不返回 timestamps。

历史 master 即使 inactive 也可以出现，其 `is_active=false` 必须可见。

HTTP JSON 中分数表现为 **JSON number 或 null**，不是字符串型业务合同。Pydantic 若默认把 Decimal 序列化成 string，schema 层用最小方式保证 JSON number。数据库仍为 `NUMERIC(8, 2)`，不得改成 float 存储。

## 15. Admission status

```text
PATCH /api/v1/admin/admission-records/{admission_record_id}/status
```

```json
{ "is_active": true }
```

复用 `StatusUpdate`。不存在 → 404。

- deactivate（`false`）：允许；Unique 仍占该五元组
- reactivate（`true`）：重新校验引用存在、College / Major 同校、Catalog 非空时五元组一致
- **不要求** School / College / Major / Catalog 当前 active（API-D10 = A）
- 不增加「必须有 Catalog / 必须有成绩」等 completeness
- 不复制 Catalog publish/activate 规则

无 hard DELETE。误录入用 `is_active=false`。

## 16. TeachSubjectsPut

```text
PUT /api/v1/admin/teacher-profiles/{teacher_profile_id}/teach-subjects
```

```json
{
  "exam_subject_ids": [10, 11, 12]
}
```

| 规则 | 值 |
|---|---|
| 字段 | required，必须是 list |
| `null` | 422 |
| `[]` | 合法，清空全部标签 |
| 每个 id | `> 0` |
| payload 内重复 id | Schema 层 422 |
| 输入顺序 | 无业务语义；不要用 set 改变 JSON contract |
| 读取顺序 | `exam_subject_id ASC` |
| Teacher 不存在 | 404 `not_found` |

`extra="forbid"`。成功 200，body 为该 Teacher 的 `teach_subjects`（`ExamSubjectAdminRead[]`）或 `TeacherAdminDetail`；Checkpoint 2 实现时与 GET detail 的科目部分一致。推荐返回 `TeacherAdminDetail` 以便客户端一次拿到当前集合。

全国统考（`school_id IS NULL`）与任意学校自命题都允许作为教学标签。不根据 Teacher Admission school 限制 TeachSubject scope。

不得根据 Admission / Catalog 自动生成。

## 17. API-D7（负责人修正版）

**与原 Grok Planning 推荐 A 不同，以本冻结为准。**

TeacherTeachSubject 没有 `is_active`，编辑入口只有整集合 PUT。inactive Teacher 完全禁止 PUT 会导致无法删除误录标签。

### AdmissionRecord（inactive Teacher）

- POST 新 AdmissionRecord → **禁止**，422 `parent_inactive`
- PATCH 已有 AdmissionRecord → **允许**
- PATCH 已有 AdmissionRecord `/status` → **允许**（含 deactivate / reactivate）
- 已有 Admission 不因 Teacher inactive 变成 404

inactive Teacher 仍允许 PATCH 档案头与三个状态 endpoint（否则无法恢复）。

### TeacherTeachSubject（inactive Teacher）

允许对**已有集合**保留 / 删除 / 清空。
**禁止**新增任何原集合中不存在的 `exam_subject_id`。

Service 必须比较：

```text
existing_ids = 当前 TeacherTeachSubject 集合
requested_ids = PUT payload 集合
added_ids = requested_ids - existing_ids
```

Teacher inactive 时：

- `added_ids` 非空 → 422 `parent_inactive`
- `added_ids` 为空 → 允许继续 replace

| existing | PUT | 结果 |
|---|---|---|
| `[10,11,12]` | `[10,11]` | 允许 |
| `[10,11,12]` | `[]` | 允许 |
| `[10,11,12]` | `[10,11,12]` | 允许 |
| `[10,11,12]` | `[10,11,13]` | 拒绝 `parent_inactive` |

`PUT [10,12]`（existing `[10,11]`）：12 是新增 → 整请求失败并 rollback，11 不得被删除。

不得要求管理员为了删除错误标签而先 reactivate Teacher。

先前已从集合删除的 subject，对当前集合属于 `added_id`：inactive Teacher 不得通过 PUT 重新加入。

## 18. API-D12 inactive ExamSubject

TeachSubject PUT：

1. 所有 requested id 必须存在，否则 422 `invalid_reference`
2. **新加入** 的 subject 必须 active，否则 422 `inactive_reference`
3. 已经挂在 Teacher 上、后来 inactive 的 subject 可以继续保留
4. payload 未出现的旧 subject 删除
5. 与 D7 同时生效：Teacher inactive 时先检查 `added_ids`；即使新 subject 本身 active，只要是新增关系 → 422 `parent_inactive`

## 19. 错误合同

Pydantic 缺字段 / 类型 / enum / extra forbidden / duplicate subject ids / 非正 id / 非法 null：FastAPI 默认 422 数组。

应用错误：

```json
{
  "detail": {
    "code": "duplicate_admission",
    "message": "..."
  }
}
```

`code` 稳定。`message` 可读，不作为契约主键。

| 情况 | HTTP | code |
|---|---|---|
| path Teacher / Admission 不存在 | 404 | `not_found` |
| Admission Unique | 409 | `duplicate_admission` |
| TeachSubject Unique race fallback | 409 | `duplicate_teach_subject` |
| inactive Teacher 禁止的新增录取或新增科目 | 422 | `parent_inactive` |
| 引用行不存在 | 422 | `invalid_reference` |
| 新建或更换引用时目标 inactive | 422 | `inactive_reference` |
| College / Major 与 school 不同校 | 422 | `reference_scope_mismatch` |
| Catalog 存在但五元组不一致 | 422 | `catalog_identity_mismatch` |
| 已知 CHECK | 422 | `check_violation` |
| PATCH `{}` | 422 | `empty_patch` |
| 未知 IntegrityError | 不包装 | 服务器故障路径 |

不得泄露 psycopg 原文、SQL、`DATABASE_URL`、credentials。

Admin 对 inactive **目标资源**返回 200，不因 Teacher / Admission inactive 给 404。

## 20. 错误体系（API-D16）

复用 `MasterDataWriteError` 及已有：

- `NotFoundError`
- `ParentInactiveError`
- `ConflictError`
- `InvalidReferenceError`
- `InactiveReferenceError`
- `ScopeMismatchError`
- `CheckViolationError`
- `EmptyPatchError`

Teacher-specific IntegrityError / constraint mapping 放在 Teacher Service/module。

**不得**把下列约束塞进 S1-03A master-data mapping：

- `uq_admission_records_teacher_offering`
- `uq_teacher_teach_subjects_teacher_subject`
- Teacher-specific FK / CHECK

`catalog_identity_mismatch` 可用继承 `MasterDataWriteError` 的最小错误类型实现。不得重构 S1-03。

Checkpoint 1 只冻结合同，不写 Service exception 实现。

已知约束（Checkpoint 2 映射）：

- `uq_admission_records_teacher_offering` → 409 `duplicate_admission`
- `uq_teacher_teach_subjects_teacher_subject` → 409 `duplicate_teach_subject`
- 已知 Teacher / Admission FK → 422 `invalid_reference`
- 已知 Teacher / Admission CHECK → 422 `check_violation`

## 21. 无 migration

本 Issue **绝对不允许 migration**。Alembic head 保持 `695107900fc3`。

不得改 Model、加列、加 index、改 FK / Unique / CHECK。

现有三张表足以支撑本合同。若发现不能支撑：停止并报告 blocker，不得顺手 migration。

## 22. 测试矩阵（含 D7 修正）

合成数据 only：`ZZ_` / `TEST_` / `SYNTHETIC_`。禁止真实姓名、联系方式、真实成绩单。

Checkpoint 1：schema tests。

Checkpoint 2/3 必须覆盖：

- Teacher create 默认状态；禁止 create 时 verified
- PATCH display_name/bio；empty_patch；bio null 清空
- 三个状态 endpoint 正交
- list：status / availability / verification / q / pagination / total
- same-row admission filter
- inactive admission 不参与列表筛师，但出现在 detail
- exam_subject EXISTS，无重复 total
- Admission create：Catalog null / 匹配 / mismatch / 跨校 / inactive master / inactive Teacher
- Admission PATCH effective state；explicit null
- Admission status；reactivate 允许 inactive master
- TeachSubject PUT：`[]`、重复、缺科目、新 inactive subject、保留已有 inactive subject、原子 rollback
- Public API regression；无 Teacher public 路径
- alembic current 仍为 `695107900fc3`

D7 修正（必须）：

1. existing `[10,11]` → PUT `[10]`：成功
2. existing `[10,11]` → PUT `[]`：成功
3. existing `[10,11]` → PUT `[10,11]`：成功 / 幂等
4. existing `[10,11]` → PUT `[10,11,12]`（12 active）：422 `parent_inactive`
5. existing `[10,11]` → PUT `[10,12]`：整请求失败并 rollback，11 不得被删除
6. existing 中 subject 11 后来 inactive，PUT `[10,11]`：允许保留
7. inactive Teacher 不得通过 PUT 重新加入已删除的 subject

## 23. Checkpoint

1. Issue + branch + 本合同 + Pydantic schemas + schema tests + `PROJECT_STATUS` In Progress（本文件）
2. Repository + Service + PostgreSQL tests（须 Checkpoint 1 验收后批准）
3. Router + API 回归 + learning + 最终 QA / PR（须 Checkpoint 2 验收后批准）
