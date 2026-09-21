# S1-03A 稳定主数据 Admin API 合同

对应 Issue：[S1-03A](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/23)
状态：implementation complete — PR #24 under review
基线 Schema：S1-01 / Alembic `44f5a70a766a`
公开只读合同：[`s1-02-master-data-read-api.md`](./s1-02-master-data-read-api.md)（**本 Issue 不修改**）

本文冻结稳定主数据的内部维护接口。不含 Catalog / Direction / CatalogExamSubject 写入（S1-03B）。

## 1. 目标

为 School / College / Major / ExamSubject 提供 Admin：

- 读取（含 inactive）
- 创建
- 部分更新（PATCH）
- 停用 / 恢复（status）

不提供 DELETE。不改表结构。

## 2. 安全与范围

`/api/v1/admin` 只是 URL 命名空间，**不是安全边界**。本 Issue **不做 auth**。

第一版仅用于 **localhost 本地开发**。不得把「受信内网」或生产部署写成已批准方案。

## 3. Non-scope

- AdmissionCatalog / Direction / CatalogExamSubject 的任何写接口
- Admin Catalog 聚合保存
- React / Admin Web
- auth / RBAC
- import / S1-04
- hard delete
- Model / migration / DDL
- 公开 S1-02 合同变更（含 `include_inactive`）
- 把 College / Major / ExamSubject 的 `school_id` 改到另一所学校
- National ↔ school-scoped ExamSubject 互转

## 4. 事务

现有 `get_db()` **保持不变**：`SessionLocal()` → yield → close，**不 commit**。S1-02 继续使用。

Admin **写**路由使用新的 `get_write_db()`，并且 `Depends(get_write_db, scope="function")`。

function scope 的含义：path operation 跑完后、**把响应发给客户端之前**，执行 yield 之后的 commit / rollback。客户端看到 201/200 时，事务已经提交成功。

```text
SessionLocal()
  → yield Session
  → path operation（Service / Repository / flush）
  → 成功：commit；异常：rollback
  → close
  → 这时才发送 HTTP 响应
```

不要理解成：先把 201 发给客户端，再在后台 commit。那是 FastAPI yield dependency 默认 `scope="request"` 的行为，Admin 写请求不使用它。

Admin **读**仍用 `get_db()`，不改成 write dependency。

- Repository：query / add / update，必要时 **flush**；**不 commit**
- Write Service：业务校验、调 Repository、把约束错误转成稳定 `code`；**不 commit**
- 所有 create / patch / status 在返回前 flush，使 unique / FK / check 在本次请求内暴露
- 未来 S1-04 import **自己**管理 Session / transaction，直接调同一 Write Service，不 HTTP 调自己

Admin **读**路由继续用 `get_db()`（只读、不 commit）。

## 5. 通用规则

### 5.1 Inactive

| 调用方 | 记录 inactive 时 |
|---|---|
| 公开 S1-02 | 不可见；detail **404** |
| Admin GET detail | **200**，body 含 `is_active: false` |
| Admin GET list | 可通过 `status` 滤出；默认包含 |
| Admin PATCH 字段 / status | **允许**；不得因 inactive 返回 404 |
| 行确实不存在 | **404** |

### 5.2 列表 `status`

`status=all|active|inactive`，默认 **`all`**。非法值 → FastAPI **422**。

`status` 过滤的是**被列出的那类实体自身**的 `is_active`，不是父学校。

### 5.3 Scope 冻结

创建后不可改所属：

- College / Major：`school_id` 只来自创建时的 path，不进入 Update Schema
- ExamSubject：national（`school_id IS NULL`）与 school-scoped 创建后不能互转；Update Schema 不含 `school_id`

### 5.4 父资源与新建 child

`POST /api/v1/admin/schools/{school_id}/colleges`（Major、school-scoped ExamSubject 同理）：

| 父 School | 结果 |
|---|---|
| 不存在 | **404** |
| 存在且 inactive | **422** `parent_inactive` |
| 存在且 active | 允许创建 |

已有 inactive child 仍可 Admin PATCH / 恢复。只禁止在 **inactive 父学校下新建** child。

### 5.5 创建时的 `is_active`

服务端默认 **`is_active=true`**。Create body 不含 `is_active`。停用只走 status 接口。

（Catalog 新建默认为 false 属于 S1-03B，不在本合同。）

### 5.6 分页

仅 **学校列表**分页，对齐 S1-02：

- `page` 默认 1，≥ 1
- `page_size` 默认 20，1–100

学院 / 专业 / 科目列表不分页。

学校列表可选 `q`：对 `school_code` / `name` 的 trim 后子串匹配（与 S1-02 相同语义）。

### 5.7 Admin 响应字段

Admin 的 read / create / patch / status 响应包含：

- `id`
- 业务字段
- `is_active`

**第一版不暴露 `created_at` / `updated_at`。**

理由：公开 S1-02 已不返回时间戳；Admin 停用/恢复不依赖时间戳；少两个字段可与现有 read schema 风格对齐。需要审计时再加，不作为 03A 产品语义。

## 6. Admin Read

### School

```text
GET /api/v1/admin/schools
    query: status=all|active|inactive（默认 all）
           q?: string
           page, page_size
    200: Page[SchoolAdminRead]

GET /api/v1/admin/schools/{school_id}
    200: SchoolAdminRead
    404: 不存在
    inactive: 200
```

`SchoolAdminRead`：`id`, `school_code`, `name`, `is_active`

### College

```text
GET /api/v1/admin/schools/{school_id}/colleges
    query: status（默认 all）
    父学校不存在: 404
    父学校 inactive: 仍 200，列出该校学院（再按 status 滤学院）
    200: CollegeAdminRead[]

GET /api/v1/admin/colleges/{college_id}
    200: CollegeAdminRead（含 school_id）
    404: 不存在
    inactive: 200
```

`CollegeAdminRead`：`id`, `school_id`, `college_code` (`string | null`), `name`, `is_active`

### Major

```text
GET /api/v1/admin/schools/{school_id}/majors
    query: status（默认 all）
    父学校规则同 College 列表
    200: MajorAdminRead[]

GET /api/v1/admin/majors/{major_id}
    200: MajorAdminRead（含 school_id）
    404: 不存在
    inactive: 200
```

`MajorAdminRead`：`id`, `school_id`, `major_code`, `name`, `degree_type` (`academic` | `professional`), `is_active`

### National ExamSubject

```text
GET /api/v1/admin/exam-subjects/national
    query: status（默认 all）
    200: ExamSubjectAdminRead[]
    只返回 school_id IS NULL 的行
```

**禁止**用「不传 school_id 的通用列表」表示全国统考。

### School-scoped ExamSubject

```text
GET /api/v1/admin/schools/{school_id}/exam-subjects
    query: status（默认 all）
    父学校规则同 College 列表
    200: ExamSubjectAdminRead[]
    只返回该 school_id 的行
```

### ExamSubject detail

```text
GET /api/v1/admin/exam-subjects/{exam_subject_id}
    national 与 school-scoped 共用
    200: ExamSubjectAdminRead
    404: 不存在
    inactive: 200
```

`ExamSubjectAdminRead`：`id`, `school_id` (`int | null`；全国为 `null`), `subject_code`, `name`, `is_active`

## 7. Create

请求与响应均不包含 `id` / `school_id`（path 或服务端赋值）/ `is_active` / 时间戳。成功 **201**，body 为对应 `*AdminRead`。

### School

```text
POST /api/v1/admin/schools
```

```json
{ "school_code": "10004", "name": "北京交通大学" }
```

`school_code`、`name` 必填。

### College

```text
POST /api/v1/admin/schools/{school_id}/colleges
```

```json
{ "college_code": "AUT", "name": "自动化与智能学院" }
```

`name` 必填。`college_code` 可选（可省略或 `null`）。**body 不得含 `school_id`。**

### Major

```text
POST /api/v1/admin/schools/{school_id}/majors
```

```json
{
  "major_code": "140500",
  "name": "智能科学与技术",
  "degree_type": "academic"
}
```

三字段必填。`degree_type` 仅为 `academic` | `professional`。**body 不得含 `school_id`。**

### National ExamSubject

```text
POST /api/v1/admin/exam-subjects/national
```

```json
{ "subject_code": "101", "name": "思想政治理论" }
```

服务端固定 `school_id = NULL`。**body 不得含 `school_id`。**

### School-scoped ExamSubject

```text
POST /api/v1/admin/schools/{school_id}/exam-subjects
```

```json
{ "subject_code": "895", "name": "自动控制理论" }
```

`school_id` 只来自 path。**body 不得含 `school_id`。**

## 8. Patch（部分更新）

成功 **200**，body 为 `*AdminRead`。

空 body `{}` **不允许**：**422** `empty_patch`。至少要有一个将要修改的业务字段。

Write schema（Create / Update / StatusUpdate）配置 `extra="forbid"`。请求里出现 `id`、`school_id`、`is_active`（非 status 接口）、`created_at`、`updated_at` 或其他未知字段 → FastAPI **422** 校验数组。

“字段 optional”只表示**可以不传**，不表示显式 `null` 合法。数据库 NOT NULL 的字段（`school_code`、`name`、`major_code`、`degree_type`、`subject_code` 等）PATCH 显式 `null` → FastAPI **422**。唯一例外：`College.college_code` 可为 null，`{"college_code": null}` 表示清空学院代码，不是 empty patch。

Update Schema **不含**：`id`, `school_id`, `is_active`, `created_at`, `updated_at`。

提供的字段必须通过原有格式校验（非空字符串、`degree_type` enum 等）。

```text
PATCH /api/v1/admin/schools/{school_id}
    body: { "school_code"?: string, "name"?: string }

PATCH /api/v1/admin/colleges/{college_id}
    body: { "college_code"?: string | null, "name"?: string }

PATCH /api/v1/admin/majors/{major_id}
    body: { "major_code"?: string, "name"?: string, "degree_type"?: "academic"|"professional" }

PATCH /api/v1/admin/exam-subjects/{exam_subject_id}
    body: { "subject_code"?: string, "name"?: string }
```

ExamSubject PATCH **不得**改变 national / school-scoped。不存在 → 404；inactive → 仍可 PATCH。

## 9. Status

```text
PATCH /api/v1/admin/schools/{school_id}/status
PATCH /api/v1/admin/colleges/{college_id}/status
PATCH /api/v1/admin/majors/{major_id}/status
PATCH /api/v1/admin/exam-subjects/{exam_subject_id}/status
```

```json
{ "is_active": true }
```

或 `{ "is_active": false }`。`is_active` 必填，必须是 boolean。

- 不存在 → 404
- 已是目标状态 → 200，幂等
- inactive 记录可以 PATCH `is_active: true` 恢复
- 成功 200，body 为 `*AdminRead`

**没有 DELETE 路由。**

停用学校 **不级联**停用学院/专业/科目。公开 S1-02 仍会因学校 inactive 而把该校详情当成 404；Admin 子资源仍按自身 `is_active` 管理。

## 10. 错误响应

### 10.1 FastAPI / Pydantic 校验（缺字段、类型、enum、`status` 非法等）

HTTP **422**，保持 FastAPI 默认：

```json
{ "detail": [ { "loc": ["body", "name"], "msg": "...", "type": "..." } ] }
```

### 10.2 应用错误（稳定 `code`）

HTTP 4xx，body：

```json
{
  "detail": {
    "code": "duplicate_school_code",
    "message": "school_code already exists"
  }
}
```

- `code`：**稳定**，客户端与测试按它断言
- `message`：人类可读，可调整措辞，不作为契约主键
- 不得返回 psycopg 原文、constraint SQL、连接串/密码

| 情况 | HTTP | code |
|---|---|---|
| path 资源不存在 | 404 | `not_found` |
| 创建 child 时 path 上的学校不存在 | 404 | `not_found` |
| 创建 child 时学校存在但 inactive | 422 | `parent_inactive` |
| `school_code` 重复 | 409 | `duplicate_school_code` |
| 同校下非空 `college_code` 重复 | 409 | `duplicate_college_code` |
| 同校 `major_code` 重复 | 409 | `duplicate_major_code` |
| 全国 `subject_code` 重复 | 409 | `duplicate_national_subject_code` |
| 同校 `subject_code` 重复 | 409 | `duplicate_school_subject_code` |
| CHECK（如非法 `degree_type` 已由 Pydantic 拦住；其它 DB check） | 422 | `check_violation` |
| PATCH `{}` 或未包含任何字段 | 422 | `empty_patch` |

不同学校的相同 school-scoped `subject_code` **不是**冲突。
两个 `college_code` 均为 `null` 的学院可以共存于同一学校（与 S1-01 部分唯一索引一致）。

Admin **不**对 inactive 目标使用 404。

## 11. 与 S1-02 的关系

公开 7 个 GET **不变**：active-only、不暴露 `is_active`、无 `GET /exam-subjects`。

Admin 停用某校后：

- `GET /api/v1/schools/{id}` → 404
- `GET /api/v1/admin/schools/{id}` → 200 且 `is_active: false`

本 Issue 测试必须包含这条回归。

## 12. 数据库

**无 migration。** 使用现有 7 张表中的 `schools` / `colleges` / `majors` / `exam_subjects`。不改 Model 约束。

## 13. Checkpoint

1. Issue + branch + 本合同（本文件）
2. `get_write_db` + write schemas + AdminSchoolRepository + Write Service + 单测
3. Admin router + PostgreSQL 集成 + 冲突/事务/inactive + S1-02 回归
4. 实现与本合同对齐后的文档收口 + PR
