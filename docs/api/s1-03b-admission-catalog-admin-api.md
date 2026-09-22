# S1-03B 招生目录 Admin API 合同

对应 Issue：[S1-03B](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/27)
状态：Implemented in S1-03B (Issue #27, PR #28)
基线 Schema：S1-01 / Alembic `44f5a70a766a`
公开只读合同：[`s1-02-master-data-read-api.md`](./s1-02-master-data-read-api.md)（**本 Issue 不修改**）
稳定主数据 Admin：[`s1-03a-stable-master-data-admin-api.md`](./s1-03a-stable-master-data-admin-api.md)（已合入，本 Issue 不修改其稳定实体写接口）

本文冻结 AdmissionCatalog 的内部维护接口。不含 Admin Web（S1-03C）。

## 1. 目标

为招生目录提供 Admin：

- 读取（含 inactive）
- 创建 **inactive shell**（身份五元组）
- **PUT 完整聚合替换**：基本字段 + `directions[]` + `exam_units[]`
- 显式 `PATCH .../status` 后才对公开 S1-02 可见

不提供 DELETE REST。不提供 Direction / CatalogExamSubject 的 row-level REST。不新增 draft enum / 新列。

## 2. 安全与范围

`/api/v1/admin` 只是 URL 命名空间，**不是安全边界**。本 Issue **不做 auth**。第一版仅用于 **localhost 本地开发**。

## 3. Non-scope

- School / College / Major / ExamSubject 写入（S1-03A）
- React / Admin Web
- auth / RBAC
- import / S1-04 实现
- row-level `POST/PATCH/DELETE .../directions` 或 `.../exam-subject-options`
- Catalog DELETE REST
- Model / migration / DDL
- 公开 S1-02 合同变更
- 新增 `draft` / `published` 字段
- 「必须四个 exam_unit」「必须至少一个 option」等未批准的完整度规则
- 自动生成 `direction_code=00`
- 清洗已有 Catalog 数据，或为新写入规则做 migration

## 4. 事务

读：现有 `get_db()`（yield + close，**不 commit**）。

写：现有 `get_write_db()`，且 `Depends(get_write_db, scope="function")`。

```text
SessionLocal()
  → yield Session
  → path operation（validate / replace / flush）
  → 成功 commit；异常 rollback
  → close
  → 这时才发送 HTTP 响应
```

- Repository：query / add / delete-children-for-replace / flush；**不 commit**
- Write Service：业务校验、聚合替换、已知约束 → 稳定 `code`；**不 commit**
- S1-04 import **自己**管理 Session / transaction，直接调同一 Write Service，不 HTTP 调自己

## 5. 数据模型事实

### 5.1 AdmissionCatalog

唯一五元组：`school_id` + `college_id` + `major_id` + `admission_year` + `study_mode`

- constraint：`uq_admission_catalogs_offering`
- `study_mode`：`full_time` | `part_time`（`ck_admission_catalogs_study_mode`）
- `admission_year`：`>= 2000`（`ck_admission_catalogs_year`）
- College 必须与 Catalog 同校：`fk_admission_catalogs_college_school`
- Major 必须与 Catalog 同校：`fk_admission_catalogs_major_school`
- School FK：`fk_admission_catalogs_school_id`

### 5.2 Direction

- 唯一：`catalog_id` + `direction_code`（`uq_admission_catalog_directions_code`）
- 无方向：`directions = []`（0 行）
- 官方明确「00 不区分研究方向」才保存 `direction_code = "00"`
- **禁止**系统自动生成 00

### 5.3 CatalogExamSubject

- `exam_unit`：1..4（`ck_catalog_exam_unit`）
- `option_order`：`>= 1`（`ck_catalog_exam_option_order`）
- 同 Catalog + exam_unit 下同一 `exam_subject_id` 不重复：`uq_catalog_exam_unit_subject`
- 同 Catalog + exam_unit 下 `option_order` 不重复：`uq_catalog_exam_unit_option_order`
- 同一 exam_unit 多个 option = **OR**，不是都考
- 当前数据库 **没有** Catalog ↔ ExamSubject 的 same-school composite FK；跨校科目必须由 Service 显式拒绝

## 6. Child 身份（value collection）

Direction 与 CatalogExamSubject 在 Admin **聚合合同**中视为集合值，不是独立 REST 资源。

- PUT **不得**接受 child row `id`
- 集合替换后数据库 child id **可能重新生成**
- 前端不得依赖 Direction id / link id 做 row-level CRUD
- Admin response **不暴露** CatalogExamSubject link id；Direction **也不暴露** row id
- 业务身份：`direction_code`；科目选项：`exam_unit` + `option_order` + `exam_subject_id`
- 公开 S1-02 response **不改**

内部实现可以对旧 child 做 SQL `DELETE` 再插入。这 **不等于** 提供 `DELETE /api/...`。

## 7. Admin Read

### 7.1 列表

```text
GET /api/v1/admin/admission-catalogs
```

| query | 规则 |
|---|---|
| `school_id` | **必须**，`> 0` |
| `status` | `all` \| `active` \| `inactive`，默认 `all` |
| `admission_year?` | 可选 |
| `college_id?` | 可选 |
| `major_id?` | 可选 |
| `study_mode?` | `full_time` \| `part_time` |
| `page` | 默认 1，`>= 1` |
| `page_size` | 默认 20，1–100 |

- Admin **包含** inactive Catalog；**不要**复用公开 `_visible_catalogs()`（那要求 Catalog/School/College/Major 全 active）
- `school_id` 对应学校 **不存在**： **200** 空 Page（与 S1-02 列表过滤一致，不是 404）
- 学校 **inactive**：仍允许 Admin 查询该校 Catalog
- 非法 query → FastAPI 默认 422 数组

响应：`Page[CatalogAdminSummary]`

### 7.2 详情

```text
GET /api/v1/admin/admission-catalogs/{catalog_id}
```

- 不存在 → **404** `not_found`
- inactive → **200**，含 `is_active: false`
- 必须返回：catalog 基本字段、`school` / `college` / `major`（AdminRead，含各自 `is_active`）、`directions`、`exam_units`
- **不得**过滤 inactive ExamSubject。option 指向停用科目时仍返回，且 subject 带 `is_active: false`

## 8. POST shell

```text
POST /api/v1/admin/admission-catalogs
```

```json
{
  "school_id": 1,
  "college_id": 2,
  "major_id": 3,
  "admission_year": 2026,
  "study_mode": "full_time"
}
```

- Write schema `extra="forbid"`；不得含 `id` / `is_active` / `directions` / `exam_units` / 时间戳
- 服务端强制 `is_active = false`
- 成功 **201**，body 为 `CatalogAdminDetail`（`directions: []`，`exam_units: []`，`is_active: false`）

### 8.1 引用校验（全部在 body，不是 path）

创建 Catalog 是在已有稳定主数据下新增业务 child。body 引用不得伪装成 path 404。

| 情况 | HTTP | code |
|---|---|---|
| School / College / Major 行不存在 | 422 | `invalid_reference` |
| 引用存在但 inactive | 422 | `inactive_reference` |
| College 或 Major 的 `school_id` ≠ body.`school_id` | 422 | `reference_scope_mismatch` |
| 五元组与已有 Catalog 冲突 | 409 | `duplicate_catalog_offering` |

Pydantic：`admission_year >= 2000`，`study_mode` enum。非法值优先 FastAPI 422 数组。

## 9. PUT aggregate

```text
PUT /api/v1/admin/admission-catalogs/{catalog_id}
```

这是 **完整替换**，不是 PATCH。缺少任一顶层字段 → 422。`extra="forbid"`。

```json
{
  "school_id": 1,
  "college_id": 2,
  "major_id": 3,
  "admission_year": 2026,
  "study_mode": "full_time",
  "directions": [
    { "direction_code": "01", "direction_name": "控制科学与工程" }
  ],
  "exam_units": [
    {
      "exam_unit": 1,
      "options": [
        { "option_order": 1, "exam_subject_id": 10 }
      ]
    },
    {
      "exam_unit": 2,
      "options": [
        { "option_order": 1, "exam_subject_id": 11 },
        { "option_order": 2, "exam_subject_id": 12 }
      ]
    }
  ]
}
```

不得包含：`id`、`is_active`、child row id、时间戳。

允许修改五元组字段。最终必须：College/Major 与 `school_id` 同校，否则 422 `reference_scope_mismatch`。五元组撞到**另一条** Catalog → 409 `duplicate_catalog_offering`。

Catalog path 不存在 → 404 `not_found`。inactive Catalog **允许 PUT**（不是 404）。

`directions` 与 `exam_units` **必须出现**，可为 `[]`，不得为 `null`。

## 10. Directions payload

```json
{ "direction_code": "01", "direction_name": "..." }
```

- `direction_code`：1..32 字符
- `direction_name`：1..255 字符
- 同一 payload 内 `direction_code` 不得重复 → 422（Pydantic/应用校验，不必等 DB）
- 不自动排序生成业务含义；保存后读取按 `direction_code` ASC
- 不自动插入 `00`

## 11. Exam units / options payload

```json
{
  "exam_unit": 1,
  "options": [
    { "option_order": 1, "exam_subject_id": 123 }
  ]
}
```

第一版允许 `exam_units: []`。不要求四个 unit、不要求至少一个 option、不要求 1/2/3/4 齐全。

若某个 `exam_unit` **出现在 payload 中**：其 `options` **不得为空**。

- `exam_unit`：1..4；同一 payload 内不得重复
- `exam_subject_id`：`> 0`
- `option_order`：`>= 1`；**不要求连续**（`1, 3` 合法）
- 同一 unit 内 `option_order` 不得重复；`exam_subject_id` 不得重复
- 同一 unit 多 option = OR

## 12. ExamSubject 范围（Service 显式）

Catalog 的 `school_id = S`。合法科目仅：

| 科目 | 是否允许 |
|---|---|
| `school_id IS NULL`（全国统考） | 允许 |
| `school_id = S`（该校自命题） | 允许 |
| `school_id` 为其他学校 | **422** `reference_scope_mismatch` |
| 科目行不存在 | **422** `invalid_reference` |

## 13. 引用的 active 语义

| 操作 | School / College / Major | ExamSubject |
|---|---|---|
| POST shell | 必须存在且 **active**，且同校 | 不引用科目 |
| PUT **inactive** Catalog | 必须存在且同校；**允许 inactive**（修历史） | 必须存在；national 或同校；**允许 inactive** |
| PUT **active** Catalog | 必须存在、同校、**全部 active** | 必须存在、national 或同校、**全部 active** |
| `PATCH status true` | 必须存在、同校、**全部 active** | 必须存在、national 或同校、**全部 active** |
| `PATCH status false` | 不额外校验引用 | 不删除 children |

这样避免：active Catalog 经 PUT 后，公开 S1-02 因 parent inactive 或科目被滤掉而「悄悄少 option」。

引用 inactive（在禁止场景）→ 422 `inactive_reference`。

### 13.1 已有数据 vs 新写入规则

库里可能已有 **active** Catalog，其引用在新规则下不合法（例如 option 指向 inactive ExamSubject，或 College 已停用）。S1-03B **不主动清洗**这些行，也 **不做 migration**。

| 动作 | 规则 |
|---|---|
| GET Admin（含 inactive / 历史脏数据） | 原样返回，不过滤 inactive subject |
| PUT **inactive** Catalog | 允许继续维护 inactive 引用（存在且同校即可） |
| PUT **active** Catalog / `PATCH status=true` | **必须**满足第 13 节新写入规则，否则 422 |
| 当前 active Catalog 不满足新规则 | 两条路，二选一：一次 PUT 把聚合修成合法数据；或先 `status=false`，再按 inactive PUT 维护，修好后再 activate |

GET 不会因为历史数据不合法而失败。只有 **新的写入/激活** 才强制新规则。

## 14. 集合替换（内部 DELETE，不是 REST DELETE）

PUT 的 `directions[]` 与 `exam_units/options[]` 是**完整集合**。

- payload 中没有的旧 child 行 → 删除
- payload 中有的 → 按新集合重建
- 这是聚合内部的 SQL DELETE + INSERT，**没有任何** `DELETE /api/v1/admin/...`

实现时（Checkpoint 2）应注意顺序：先删旧 children 并 flush，再插新 children 并 flush，避免同一 flush 里新旧相同 `direction_code` 或 `exam_unit+option_order` 的临时 unique 冲突。

## 15. 原子事务

PUT 必须同一 Session、同一请求事务：

```text
load Catalog
  → validate refs
  → update Catalog 基本字段
  → replace directions
  → replace exam options
  → flush
  → 全部成功 → get_write_db commit → HTTP
  → 任一步失败 → rollback（基本字段与 children 全部恢复）
```

禁止：基本信息已改、children 失败的半完成状态。

## 16. Status

```text
PATCH /api/v1/admin/admission-catalogs/{catalog_id}/status
```

```json
{ "is_active": true }
```

或 `{ "is_active": false }`。`extra="forbid"`。不存在 → 404。

- `false`：总是允许，幂等，**不删除** children
- `true`：Catalog 必须存在；School/College/Major 全部 active 且同校；所有引用 ExamSubject 存在、active、national 或同校。否则 422 `inactive_reference` 或 `reference_scope_mismatch`

**不**在激活时新增「exam_units 非空」或「必须四门」规则。shell 默认 inactive，只有显式 `status=true` 才是发布动作。

若该 Catalog **当前已是 active** 但引用不满足第 13 节：`status=true` 仍按新规则校验（幂等成功仅当已经合法）；不合法则 422。修复方式见 13.1，不清洗旧库。

## 17. 公开可见性

| 状态 | 公开 `GET /api/v1/admission-catalogs` | 公开详情 |
|---|---|---|
| POST shell（inactive） | 看不到 | 404 |
| PUT 后仍 inactive | 看不到 | 404 |
| `status=true` 成功 | 按现有 S1-02 active-only 规则可见 | 200（若四级都 active） |

不修改 S1-02。

## 18. 错误合同

应用错误：

```json
{ "detail": { "code": "duplicate_catalog_offering", "message": "..." } }
```

`code` 稳定。Pydantic 校验保持 FastAPI 默认 422 数组。

| 情况 | HTTP | code |
|---|---|---|
| Catalog path 不存在 | 404 | `not_found` |
| body 引用的 School/College/Major/ExamSubject 不存在 | 422 | `invalid_reference` |
| 引用存在但 inactive（POST / active PUT / activate） | 422 | `inactive_reference` |
| College/Major/Subject 与 Catalog 不同校 | 422 | `reference_scope_mismatch` |
| 五元组冲突 | 409 | `duplicate_catalog_offering` |
| payload 内 direction_code / exam_unit / option_order / exam_subject_id 重复 | 422 | Pydantic 或应用校验（非 DB） |
| PUT `{}` 或缺顶层字段 | 422 | FastAPI 校验 |
| 未知 IntegrityError | 不得包装成已知业务错误 | 服务器故障路径 |

不得返回 psycopg 原文、SQL、`DATABASE_URL`、密码。

### 已知 DB 约束映射

| constraint | 映射 |
|---|---|
| `uq_admission_catalogs_offering` | 409 `duplicate_catalog_offering` |
| `fk_admission_catalogs_school_id` | 422 `invalid_reference` 或 `reference_scope_mismatch`（以实现时能区分的为准；优先 Service 先校验） |
| `fk_admission_catalogs_college_school` | 同上 |
| `fk_admission_catalogs_major_school` | 同上 |
| `fk_admission_catalog_exam_subjects_subject_id` | 422 `invalid_reference` |
| `uq_admission_catalog_directions_code` | fallback：应用校验未拦住时的 duplicate direction |
| `uq_catalog_exam_unit_subject` | fallback：同 unit 重复科目 |
| `uq_catalog_exam_unit_option_order` | fallback：同 unit 重复 option_order |
| `ck_admission_catalogs_study_mode` | 正常应被 Pydantic 拦住 |
| `ck_admission_catalogs_year` | 正常应被 Pydantic 拦住 |
| `ck_catalog_exam_unit` | 正常应被 Pydantic 拦住 |
| `ck_catalog_exam_option_order` | 正常应被 Pydantic 拦住 |

未知 constraint：**原样异常**。

## 19. Admin Read vs Public Read

**不要**给 S1-02 的 `AdmissionCatalogRepository` 加 `include_inactive`。03B 实现应新增独立 Admin Catalog Repository。公开 `_visible_catalogs()` 语义不变。

## 20. Response 形状

第一版 **不暴露** `created_at` / `updated_at`（与 03A 一致）。

### CatalogAdminSummary

```json
{
  "id": 1,
  "admission_year": 2026,
  "study_mode": "full_time",
  "is_active": false,
  "school": {
    "id": 1,
    "school_code": "10004",
    "name": "北京交通大学",
    "is_active": true
  },
  "college": {
    "id": 2,
    "school_id": 1,
    "college_code": "AUT",
    "name": "自动化与智能学院",
    "is_active": true
  },
  "major": {
    "id": 3,
    "school_id": 1,
    "major_code": "140500",
    "name": "智能科学与技术",
    "degree_type": "academic",
    "is_active": true
  }
}
```

嵌套使用 03A 的 `SchoolAdminRead` / `CollegeAdminRead` / `MajorAdminRead`。

### CatalogAdminDetail

Summary + `directions` + `exam_units`：

```json
{
  "id": 1,
  "admission_year": 2026,
  "study_mode": "full_time",
  "is_active": false,
  "school": { "id": 1, "school_code": "10004", "name": "北京交通大学", "is_active": true },
  "college": { "id": 2, "school_id": 1, "college_code": "AUT", "name": "自动化与智能学院", "is_active": true },
  "major": { "id": 3, "school_id": 1, "major_code": "140500", "name": "智能科学与技术", "degree_type": "academic", "is_active": true },
  "directions": [
    { "direction_code": "01", "direction_name": "控制科学与工程" }
  ],
  "exam_units": [
    {
      "exam_unit": 2,
      "options": [
        {
          "option_order": 1,
          "subject": {
            "id": 11,
            "school_id": null,
            "subject_code": "201",
            "name": "英语一",
            "is_active": true
          }
        },
        {
          "option_order": 2,
          "subject": {
            "id": 99,
            "school_id": 1,
            "subject_code": "895",
            "name": "自命题",
            "is_active": false
          }
        }
      ]
    }
  ]
}
```

`exam_units` 按 `exam_unit` ASC；options 按 `option_order` ASC。不返回空的 exam_unit 分组（库中没有该 unit 的行就不出现该组）。

## 21. S1-04 复用

未来 aggregate Write Service 必须可被 Admin HTTP 与 S1-04 importer 共同调用。Importer 自己管理 transaction，不 HTTP 调自己。

## 22. Research Blocked

`DECISIONS_PENDING.md` 中的机构模式、选师、费用、试听、换师、支付、推荐、完整机构端、完整考研生端、IM 等与内部 Catalog 主数据维护无关。

**S1-03B = NOT Research Blocked。** 不得把上述事项写进 03B 业务规则。

## 23. Checkpoints

1. branch + PROJECT_STATUS + 本合同（本文件）
2. Admin Catalog schemas + repository + aggregate service + lower-layer tests
3. Router + PostgreSQL API 集成 + 原子 rollback + S1-02 / S1-03A 回归
4. learning + final QA + commit + push + PR
