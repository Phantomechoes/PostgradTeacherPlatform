# S1-04 导入 JSON 合同

对应 Issue：[S1-04](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/35)

本文冻结第一版导入文件与 sidecar manifest。这是 **localhost 开发工具合同**，不是生产摄取管道。不含真实招生数据。

第一版交付：

- UTF-8 JSON 数据文件 + sidecar manifest
- 默认 dry-run
- 显式 `--apply` 才写入
- 合成且 `verification_status=approved` 才允许 apply
- School / College / Major / ExamSubject apply
- Catalog inactive shell + 完整 aggregate replace
- create / equivalent skip / different reject
- 整份文件一笔事务
- 合成 development seed

明确不交付：CSV、Excel、网页抓取、真实招生目录、默认 update、来源元数据表、migration、automatic publish、部分事务、Admin Web 导入按钮、Public 写 API。

## 1. 原则

- `schema_version` 必须是 `1`
- 引用只用业务键，不用数据库 `id`
- 文件是 UTF-8 JSON
- 不接受 `id` / `is_active` / `created_at` / `updated_at` / 子行 ID
- College 批量导入：`college_code` 必填且非空
- Catalog 的 `directions` / `exam_units` 允许空数组
- 不自动生成 `direction_code=00`
- 不要求四个考试单元
- CLI 默认 dry-run，不写数据库
- `--apply` 整份文件一笔事务：Stable Master Data + Catalog + children
- Catalog：五元组不存在则创建 inactive shell，再走现有 Admin Catalog aggregate PUT；不自动公开
- Catalog 已存在且 aggregate 等价 → skip（不改 active/inactive）；不等价 → 整份拒绝，不覆盖
- Importer 不会覆盖 Admin Web 中人工修正过的数据

## 2. Data document

```json
{
  "schema_version": 1,
  "schools": [],
  "colleges": [],
  "majors": [],
  "exam_subjects": [],
  "catalogs": []
}
```

`schema_version` 必须为 `1`。多余字段拒绝。

### schools

业务键：`school_code`。

```json
{ "school_code": "DEVSEED_S1", "name": "DEVSEED University" }
```

### colleges

业务键：`school_code` + `college_code`。`college_code` 必填、非空。Admin Web 允许某学院 `college_code` 为 null；批量导入不允许。

```json
{
  "school_code": "DEVSEED_S1",
  "college_code": "DEVSEED_CS",
  "name": "DEVSEED College"
}
```

### majors

业务键：`school_code` + `major_code`。

```json
{
  "school_code": "DEVSEED_S1",
  "major_code": "DEVSEED_081200",
  "name": "DEVSEED Major",
  "degree_type": "academic"
}
```

`degree_type`：`academic` | `professional`。

### exam_subjects

两种 scope：`national` 与 `school`。

全国统考科目业务键：`scope=national` + `subject_code`。不得带 `school_code`。

```json
{
  "scope": "national",
  "subject_code": "DEVSEED_101",
  "name": "DEVSEED Politics"
}
```

学校自命题业务键：`scope=school` + `school_code` + `subject_code`。必须带 `school_code`。

```json
{
  "scope": "school",
  "school_code": "DEVSEED_S1",
  "subject_code": "DEVSEED_801",
  "name": "DEVSEED School Subject"
}
```

### catalogs

身份是五元组业务键，不是 `catalog_id`：

- `school_code`
- `college_code`
- `major_code`
- `admission_year`
- `study_mode`

```json
{
  "school_code": "DEVSEED_S1",
  "college_code": "DEVSEED_CS",
  "major_code": "DEVSEED_081200",
  "admission_year": 2026,
  "study_mode": "full_time",
  "directions": [
    { "direction_code": "01", "direction_name": "DEVSEED Direction" }
  ],
  "exam_units": [
    {
      "exam_unit": 1,
      "options": [
        {
          "option_order": 1,
          "subject_scope": "national",
          "subject_code": "DEVSEED_101"
        },
        {
          "option_order": 3,
          "subject_scope": "school",
          "school_code": "DEVSEED_S1",
          "subject_code": "DEVSEED_801"
        }
      ]
    }
  ]
}
```

`study_mode`：`full_time` | `part_time`。`admission_year >= 2000`。`exam_unit` 为 1–4。`option_order >= 1`，无需连续。同一单元多个 option 表示 OR。

每个 option：

- `subject_scope`：`national` | `school`
- `subject_code`
- 学校自命题 option 必须带 `school_code`

`directions: []` 与 `exam_units: []` 合法。空集合表示这份目录没有方向、没有考试单元，不是缺字段。

### 拒绝的字段

数据文件和 Catalog 子对象都不得包含：

- 数据库主键 / 自增 `id`
- `catalog_id`、`school_id`、`college_id`、`major_id`、`exam_subject_id`
- `is_active`
- `created_at` / `updated_at`
- Direction / exam option 的子行 ID

## 3. Manifest sidecar

数据文件 `name.json` 对应 `name.manifest.json`。

```json
{
  "schema_version": 1,
  "dataset_id": "devseed-v1",
  "data_kind": "development_seed",
  "source_type": "synthetic",
  "source_description": "Minimal synthetic seed for local development.",
  "publisher": "PostgradTeacherPlatform",
  "retrieved_at": "2026-09-22",
  "verification_status": "approved"
}
```

第一版：

- `source_type` 只接受 `synthetic`
- `--apply` 还要求 `verification_status=approved`
- manifest **不写入数据库**
- 不增加来源元数据 Model / 表 / migration
- 真实招生来源只是未来扩展，本 Issue 不实施

公开网页可以访问，不等于可以批量抓取或商业转载。本工具当前禁止导入真实招生数据。

## 4. CLI：dry-run 与 apply

在 `backend/` 下执行。

默认 dry-run，**不写数据库**：

```text
uv run --locked python -m app.importer \
  data/seeds/devseed.json
```

等价于：校验 JSON + manifest → preflight → 打印计划 → rollback。横幅：

```text
DRY RUN
NO DATABASE WRITES
```

真实写入必须显式加上 `--apply`：

```text
uv run --locked python -m app.importer \
  data/seeds/devseed.json \
  --apply
```

第一版 apply gate：

- `source_type=synthetic`
- `verification_status=approved`

真实招生数据：当前禁止 apply。

成功且有 create：`APPLY COMPLETE` / `DATABASE WRITTEN`（`database_written=true`，`committed=true`）。
成功但全量 skip（或合法空 document）：`APPLY COMPLETE` / `NO DATABASE CHANGES`（`database_written=false`，`committed=true`）。
失败横幅：`APPLY REJECTED` / `ROLLED BACK`（`database_written=false`，`committed=false`）。

这是 localhost 开发工具，不是生产 ingestion pipeline。

## 5. 冲突策略

对每个业务键：

| 库里的状态 | 导入内容 | 结果 |
|---|---|---|
| 不存在 | 合法 | **create** |
| 已存在，业务内容等价 | 相同字段 | **skip** |
| 已存在，业务内容不同 | 名称、学位类型、方向、科目选项等不同 | **reject**（`conflict_existing`） |

没有 **update**。

特别强调：

- Importer 不会覆盖 Admin Web 中人工修正的数据
- 已存在且 inactive、字段仍等价：`skip`，**不恢复 active**
- Catalog 已存在且已公开、aggregate 仍等价：`skip`，不改 status，不重写 children

## 6. Catalog 语义

新 Catalog：

```text
create inactive shell
        ↓
complete aggregate replace
        ↓
保持 inactive
```

Importer：

- 只调用 `AdminCatalogService.create_shell` 与 `replace_aggregate`
- **never auto publish**
- **不得调用** `set_status(true)`

已有 Catalog：

- equivalent → skip（不 PUT 覆盖，不改 status）
- different → reject（整份文件失败）

这不是自动 PUT 覆盖。

`directions=[]`、`exam_units=[]` 合法。空 aggregate 由自动化测试覆盖，canonical seed 不必再放第二份空 Catalog。

一个 `exam_unit` 多个 option 表示 OR。`option_order` 无需连续，例如 `1` 与 `3` 可以同时存在。

## 7. 事务

整个 import document **一个 transaction**。

Stable Master Data + Catalog + children 全部成功才 commit。任何失败整份 rollback。

不是每个 Catalog 一笔事务。也不是 Stable 提交后再单独提交 Catalog。

失败后：已经 flush 过的 School / Catalog shell / children 都会撤回，开发库看不到半截导入。

## 8. Dry-run 报告语义

- 业务键不存在 → planned create
- 业务键存在且导入字段等价 → skip（即使现有行 inactive）
- 业务键存在但内容不同 → `conflict_existing`
- 不计划 update，不恢复 inactive，不公开 Catalog
- dry-run 结束时 rollback，`database_written=false`

Catalog 五元组相同则比较完整 `directions` 与 `exam_units`。不等价则 reject，不计划 PUT 覆盖。

## 9. Apply 语义

- 成功才 commit；任意一步失败 rollback 整份文件
- 稳定主数据：不存在 → create（默认 active）；字段等价 → skip；不等价 → 整份拒绝，不 update
- 已存在 inactive 且字段等价 → skip，保持 inactive
- inactive School 下新建 College / Major / 学校科目 → `parent_inactive`，整份拒绝
- Catalog 身份是五元组
- Catalog 不存在 → 创建 `is_active=false` 的 shell，再调用现有 aggregate PUT，保持 inactive
- Catalog 已存在且 aggregate 完全等价 → skip，不改 active/inactive，不重复写 children
- Catalog 已存在但 aggregate 不等价 → 整份拒绝，零写入，不自动 update
- 不调用 set status，不自动公开
- 引用解析走业务键，并遵守现有 `invalid_reference` / `inactive_reference` / `reference_scope_mismatch`

新建 Catalog 引用 inactive ExamSubject：允许（shell 保持 inactive）。新建 Catalog 引用 inactive School / College / Major：拒绝。

## 10. Canonical synthetic seed

仓库只保留一套 canonical 开发 seed：

- [`backend/data/seeds/devseed.json`](../../backend/data/seeds/devseed.json)
- [`backend/data/seeds/devseed.manifest.json`](../../backend/data/seeds/devseed.manifest.json)

内容全部使用 `DEVSEED_` 前缀。不含真实学校、真实招生目录、`ZZ_UI_*`、Checkpoint 临时 ID、数据库自增 id。

## 11. 当前限制

- 无 CSV / Excel
- 无网页抓取
- 无真实招生数据 apply
- 无默认 update
- 无来源元数据表
- 无 Admin Web 导入按钮
- 无 Public 写 API
- 新 Catalog 导入后仍须管理员在 Admin Web 显式公开
