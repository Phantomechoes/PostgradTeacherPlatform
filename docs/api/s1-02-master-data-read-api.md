# S1-02 只读主数据 API 合同

对应 Issue：[S1-02](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/15)
状态：implementation complete, awaiting PR review / merge
基线 Schema：S1-01 / Alembic `44f5a70a766a`
基线 commit：`a46a09cd2c636eb2197e6ee01281a940069398bf`

本文冻结本 Issue 的只读查询合同。实现已完成，等待 PR 审查。

## 1. 目标

在已落地的 7 张主数据表上提供只读查询：

- Repository（接收 `Session`）
- 薄 Read Service
- Pydantic read schemas
- `GET /api/v1` 接口
- 真实 PostgreSQL 集成测试
- 现有 backend CI job 最小增加 PostgreSQL service

`GET /health` 契约不变，仍不查库，仍不挂 `/api/v1`。

## 2. Non-scope

不做：

- `GET /exam-subjects`、`GET /directions`
- 全局 `GET /colleges`、全局 `GET /majors`
- `POST` / `PUT` / `PATCH` / `DELETE`
- Admin CRUD、Teacher、Institution、Candidate、Payment、Recommendation
- seed / import、爬虫、auth
- ORM `relationship()`
- `AsyncSession` / asyncpg / 第二套 engine
- 新业务 migration / DDL / Model 变更
- `include_inactive` 查询参数

不修改冻结规范 `docs/product/开发前工程规范_V0.1.md`。

## 3. 最终 endpoints

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/schools` | 分页学校列表 |
| GET | `/api/v1/schools/{school_id}` | 学校详情 |
| GET | `/api/v1/schools/{school_id}/colleges` | 该校学院列表（不分页） |
| GET | `/api/v1/schools/{school_id}/majors` | 该校专业主数据列表（不分页） |
| GET | `/api/v1/schools/{school_id}/admission-years` | 该校实际存在的招生年份 |
| GET | `/api/v1/admission-catalogs` | 招生目录列表（**必须** `school_id`） |
| GET | `/api/v1/admission-catalogs/{catalog_id}` | 招生目录详情 |

以上 7 个 endpoint 必须出现在 OpenAPI。

## 4. 通用规则

### 4.1 Active-only

所有业务读取**固定**只返回 `is_active=true` 的行。

- 不提供 `include_inactive`
- 第一版 read response **不暴露** `is_active`
- path 上的学校 / catalog 若 inactive，按「不存在」处理（404）
- catalog 列表额外要求关联的 School、College、Major 均为 active
- catalog 详情：所属 School / College / Major 任一 inactive → 404
- exam option 指向 inactive `ExamSubject` → 不返回该 option

Admin / 鉴权阶段以后再做停用数据读取。

### 4.2 错误

| 情况 | HTTP |
|---|---|
| path 资源不存在，或 inactive | 404 |
| query / path 类型或 enum 非法（含缺必填 query） | FastAPI 422 |
| 列表过滤结果为空 | 200 + 空 `items`（不是 404） |

本 Issue 无鉴权，不返回 401 / 403。

### 4.3 分页

仅用于：

- `GET /api/v1/schools`
- `GET /api/v1/admission-catalogs`

| 参数 | 类型 | 默认 | 约束 |
|---|---|---|---|
| `page` | int | 1 | min 1 |
| `page_size` | int | 20 | min 1，max 100 |

响应：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

`page` / `page_size` 回显请求值。`colleges` / `majors` / `admission-years` 不分页。

### 4.4 Session

继续同步 SQLAlchemy `Session`，复用 `get_db()`。

不要：`AsyncSession`、asyncpg、第二套 engine。Repository 不自己 `SessionLocal()`。

## 5. Endpoints

### 5.1 `GET /api/v1/schools`

Query：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `q` | `str \| None` | 否 | 匹配 `school_code` 或 `name` |
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20 |

固定：`School.is_active = true`。

`q`：简单 PostgreSQL `ILIKE '%q%'`，条件为

`(school_code ILIKE :q OR name ILIKE :q)`。

不要全文搜索。省略 `q` 则不做文本过滤。

稳定排序：`school_code ASC, id ASC`。

响应：`Page[SchoolSummary]`。

### 5.2 `GET /api/v1/schools/{school_id}`

只返回 active School。

不存在或 inactive → 404。

响应：`SchoolSummary`。

### 5.3 `GET /api/v1/schools/{school_id}/colleges`

学校不存在 / inactive → 404。

只返回该校 active colleges。不分页。

稳定排序：`college_code ASC NULLS LAST, name ASC, id ASC`。

响应：`list[CollegeSummary]`。

### 5.4 `GET /api/v1/schools/{school_id}/majors`

学校不存在 / inactive → 404。

只返回该校 active majors。不分页。

这是 **Major 主数据**，不是某学院某年招生专业。

稳定排序：`major_code ASC, id ASC`。

响应：`list[MajorSummary]`。

### 5.5 `GET /api/v1/schools/{school_id}/admission-years`

用途：学校 → 年份 → 招生目录 的选择流程。

学校不存在 / inactive → 404。

只从该校 **active** `AdmissionCatalog` 提取 distinct `admission_year`。
年份来自 active Catalog，且关联 College/Major 也必须 active，确保年份至少对应一条读取 API 可见 Catalog。

排序：年份 DESC。

响应：`AdmissionYearsRead`

```json
{
  "items": [2027, 2026, 2025]
}
```

学校存在但没有 active Catalog：

```json
{
  "items": []
}
```

HTTP 200。不要 404。

### 5.6 `GET /api/v1/admission-catalogs`

Query：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `school_id` | int | **是** | 缺省或类型非法 → 422 |
| `admission_year` | int | 否 | |
| `college_id` | int | 否 | |
| `major_id` | int | 否 | |
| `study_mode` | `full_time` \| `part_time` | 否 | 非法值 → 422 |
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20 |

固定过滤：

- `AdmissionCatalog.is_active = true`
- 关联 `School.is_active = true`
- 关联 `College.is_active = true`
- 关联 `Major.is_active = true`

这是 list / filter endpoint：

- `school_id` 不存在或 inactive → **200 + 空分页**（不是 404）
- `college_id` / `major_id` 与该校不匹配 → **200 + 空分页**

稳定排序：`admission_year DESC, college_id ASC, major_id ASC, id ASC`。

响应：`Page[AdmissionCatalogSummary]`。

Summary 含：`id`、`admission_year`、`study_mode`、`school`、`college`、`major`。

### 5.7 `GET /api/v1/admission-catalogs/{catalog_id}`

404 当：

- catalog 不存在
- catalog inactive
- 所属 School / College / Major 任一 inactive

响应：`AdmissionCatalogDetail`，含：

- `id`、`admission_year`、`study_mode`
- `school`、`college`、`major`
- `directions`
- `exam_units`

无研究方向：`directions = []`。**不自动生成 `00`。**

官方已公布「00 不区分研究方向」时，库中会有一行 `direction_code = "00"`，按普通方向返回。

同 `exam_unit` 多 `options` = **OR** 备选。

只包含 active `ExamSubject`。`CatalogExamSubject` 指向 inactive subject 时，不返回该 option。若某 `exam_unit` 过滤后没有任何 active option，省略该 unit。

`directions` 排序：`direction_code ASC, id ASC`。

`options` 排序：`exam_unit ASC, option_order ASC, link.id ASC`；`exam_units` 按 `exam_unit ASC`。

## 6. Pydantic read schemas（第一版）

不要为每个表制造 Create / Update Schema。不要把 ORM Model 直接当 response。

### `SchoolSummary`

```json
{
  "id": 1,
  "school_code": "...",
  "name": "..."
}
```

### `CollegeSummary`

```json
{
  "id": 1,
  "college_code": "...",
  "name": "..."
}
```

`college_code` 可为 `null`。嵌套在 Catalog 响应中时，学校身份由并列的 `school` 提供。

### `MajorSummary`

```json
{
  "id": 1,
  "major_code": "...",
  "name": "...",
  "degree_type": "academic"
}
```

`degree_type`：`academic` | `professional`。

### `ExamSubjectSummary`

```json
{
  "id": 1,
  "subject_code": "101",
  "name": "...",
  "school_id": null
}
```

`school_id = null` 表示全国统考科目。

### `DirectionRead`

```json
{
  "id": 1,
  "direction_code": "01",
  "direction_name": "..."
}
```

### `ExamSubjectOptionRead`

```json
{
  "option_order": 1,
  "subject": {
    "id": 1,
    "subject_code": "201",
    "name": "...",
    "school_id": null
  }
}
```

### `ExamUnitRead`

```json
{
  "exam_unit": 1,
  "options": []
}
```

### `AdmissionCatalogSummary`

```json
{
  "id": 1,
  "admission_year": 2026,
  "study_mode": "full_time",
  "school": {},
  "college": {},
  "major": {}
}
```

`school` / `college` / `major` 分别为 `SchoolSummary` / `CollegeSummary` / `MajorSummary`。

`study_mode`：`full_time` | `part_time`。

### `AdmissionCatalogDetail`

在 Summary 字段之上增加：

```json
{
  "directions": [],
  "exam_units": [
    {
      "exam_unit": 1,
      "options": [
        {
          "option_order": 1,
          "subject": {
            "id": 1,
            "subject_code": "101",
            "name": "...",
            "school_id": null
          }
        }
      ]
    }
  ]
}
```

### `Page[T]`

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### `AdmissionYearsRead`

```json
{
  "items": [2027, 2026]
}
```

## 7. Repository

两个 Repository，接收 `Session`。不知道 HTTP，不构造 Pydantic response，不自己开 Session。

### `SchoolRepository`

- `get_active_by_id`
- `list_schools`
- `list_colleges`
- `list_majors`
- `list_admission_years`

### `AdmissionCatalogRepository`

- `list_catalogs`
- `get_catalog`
- `list_directions`
- `list_exam_options`

## 8. Service / Router

薄 Service，负责：

- 404 用例判断
- Catalog detail 组装
- `exam_unit` 分组
- Repository 调用编排

Router 只负责：

- HTTP
- query / path validation
- `Depends(get_db)`
- 调 Service
- 返回 Pydantic response

## 9. ORM / 查询策略

S1-02 **不增加** `relationship()`。

Catalog detail 使用三次明确查询，避免 `directions × subjects` join explosion：

1. Catalog + School + College + Major
2. Directions
3. `CatalogExamSubject` + `ExamSubject`

不要一条大 join 同时拉 Directions 与 Subjects。

## 10. 测试合同（后续 Checkpoint）

- repository / API 集成测试使用**真实 PostgreSQL**
- SQLite **不作为** repository / API 集成测试数据库
- Checkpoint 2 允许纯 unit tests（不连库）覆盖组装 / 404 判断
- `GET /health` 测试继续不导入 database、不查库

## 11. CI 合同

修改现有 `.github/workflows/ci.yml` 的 backend job，最小增加：

1. PostgreSQL service
2. 测试用 `DATABASE_URL`（临时测试账号，不要真实 secret）
3. `alembic upgrade head`
4. `pytest`

不要新建第二个 CI workflow。

## 12. Checkpoint 规划

| Checkpoint | 内容 |
|---|---|
| 1 | Issue + branch + status + API contract（本文） |
| 2 | Pydantic schemas + Repository + thin Service + 纯 unit tests |
| 3 | Router + PostgreSQL integration tests + backend CI PostgreSQL service |
| 4 | docs / final QA / commit / push / PR |

Checkpoint 1–4 实现已完成，等待 PR 审查。
