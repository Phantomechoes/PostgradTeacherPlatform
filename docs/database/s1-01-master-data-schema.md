# S1-01 主数据 Schema 设计

对应 Issue：[S1-01](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/13)
状态：Done
PR：[ #14](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/14)
merge commit：`a46a09cd2c636eb2197e6ee01281a940069398bf`
基线：Alembic `27d6bd3c881a` → `44f5a70a766a`

## 1. 设计目标

为内部管理与后续师资匹配提供第一版**院校招生主数据**：

- 招生单位、学院、学校范围内的招生专业
- **按年**招生目录
- 目录下的研究方向
- 目录级初试科目组合（含同一考试单元的备选科目）

正式业务名：**AdmissionCatalog**（不用 ExamCatalog）。

## 2. Non-scope

S1-01 不做：Teacher / User / Institution / Candidate；推荐、选师、支付、佣金；API / Admin CRUD；导入与爬虫；NationalMajor；复试科目；导师；Direction 级科目；source metadata；全局 ResearchDirection 表。

不修改冻结规范 `docs/product/开发前工程规范_V0.1.md`。

## 3. 最终 ER

```text
schools 1──* colleges
schools 1──* majors
schools 1──* exam_subjects          -- 仅自命题；全国统考 school_id IS NULL
schools 1──* admission_catalogs

colleges 1──* admission_catalogs
majors   1──* admission_catalogs

admission_catalogs 1──* admission_catalog_directions
admission_catalogs 1──* admission_catalog_exam_subjects *──1 exam_subjects
```

语义示例（北京交通大学 / 自动化与智能学院 / 140500）：

```text
School: 北京交通大学
└─ College: 自动化与智能学院
└─ Major: 140500 智能科学与技术（属于学校，不属于学院）
   └─ 2026 AdmissionCatalog（全日制）
      ├─ exam units 1..4（含同一 unit 的备选科目）
      └─ directions
         ├─ 01 智能系统与工程
         └─ 02 人工智能应用
   └─ 2027 AdmissionCatalog
      ├─ 当年 exam units
      └─ 当年 directions
```

01 / 02 **共享**该 Catalog 的初试科目，不各自挂科目。

## 4. School

招生单位。内部 `id`；`school_code` 为业务代码。

| 列 | 类型意图 | nullable | 说明 |
|---|---|---|---|
| id | BIGINT identity | NO | PK |
| school_code | VARCHAR | NO | 招生单位代码 |
| name | VARCHAR | NO | 当前名称 |
| is_active | BOOLEAN | NO | 默认 true |
| created_at | TIMESTAMPTZ | NO | |
| updated_at | TIMESTAMPTZ | NO | |

不加：省市、官网、source。

## 5. College

某校下的院系所。`college_code` **可空**（来源经常没有院代码）。

| 列 | nullable | 说明 |
|---|---|---|
| id | NO | PK |
| school_id | NO | FK → schools.id |
| college_code | YES | 校内院系代码 |
| name | NO | 不全局唯一 |
| is_active | NO | 默认 true |
| created_at / updated_at | NO | |

## 6. Major

**属于 School，不属于 College。** 同一 `major_code` 可在多个学院招生，通过 Catalog 关联。

**不做**全国复用的单一 Major 行；若以后要国标学科树，另建 NationalMajor。

| 列 | nullable | 说明 |
|---|---|---|
| id | NO | PK |
| school_id | NO | FK → schools.id |
| major_code | NO | 该校招生专业代码，**非**全局唯一 |
| name | NO | |
| degree_type | NO | `academic` / `professional` |
| is_active | NO | 默认 true |
| created_at / updated_at | NO | |

`degree_type` 放在 Major：学硕/专硕是该校该专业代码的身份，不是某一年才出现的属性。同年既招学硕又招专硕 = 两个 Major、两条 Catalog。

## 7. AdmissionCatalog

核心**年度**实体：学校 + 学院 + 专业 + 年份 + 学习方式。

| 列 | nullable | 说明 |
|---|---|---|
| id | NO | PK |
| school_id | NO | FK → schools.id（与 college/major 同校，见第 16 节） |
| college_id | NO | 与 school_id 组成组合 FK → colleges(id, school_id) |
| major_id | NO | 与 school_id 组成组合 FK → majors(id, school_id) |
| admission_year | NO | 如 2026 |
| study_mode | NO | `full_time` / `part_time` |
| is_active | NO | 默认 true；该年条目作废时用 |
| created_at / updated_at | NO | |

**禁止**在 Catalog 上存 `research_direction_code` / `research_direction_name`。

第一版不加：拟招生人数、复试线、导师、复试科目、备注长文本、source。

2026 考 895、2027 换专业课：两条 Catalog，科目关系只改 2027。不覆盖 2026，不复制 Major。

## 8. AdmissionCatalogDirection

某 Catalog 下公布的研究方向。

| 列 | nullable | 说明 |
|---|---|---|
| id | NO | PK |
| admission_catalog_id | NO | FK → admission_catalogs.id |
| direction_code | NO | 有行则必须有代码 |
| direction_name | NO | |
| created_at / updated_at | NO | |

**不加 `is_active`：** Catalog 已是年度快照；停招/调整用新年 Catalog 或删/改该年 direction 行（实施时避免 hard delete 被引用的父实体）。

### 无研究方向时

**统一规则：没有 Direction 行。**

- 官方未公布方向 → 0 行。不要自动插「00」。
- 官方明确公布「00 不区分研究方向」→ **存一行**，`direction_code = '00'`，名称为官方名称。

禁止同一语义有时为空、有时为 00。`direction_code` 有行则 NOT NULL，避免空字符串。

## 9. ExamSubject

| 列 | nullable | 说明 |
|---|---|---|
| id | NO | PK |
| school_id | YES | NULL = 全国统考；非空 = 该校自命题 |
| subject_code | NO | **非**全局唯一 |
| name | NO | |
| is_active | NO | 默认 true |
| created_at / updated_at | NO | |

例：`101` + `school_id NULL`；`895` + 交大 `school_id`。

## 10. AdmissionCatalogExamSubject

Catalog 的初试单元与科目。科目挂 Catalog，**不挂 Direction**。

| 列 | nullable | 说明 |
|---|---|---|
| id | NO | PK |
| admission_catalog_id | NO | FK |
| exam_subject_id | NO | FK |
| exam_unit | NO | 1..4，**不是**政治/外语语义 slot |
| option_order | NO | 同单元备选展示序，从 1 起；**不是**科目身份 |
| created_at / updated_at | NO | |

同一 `exam_unit` 多行 = **OR** 备选（如 unit 2：201 / 202 / 203）。

第一版不预埋 Direction-specific 科目。若未来官方出现「同 Catalog 不同方向不同初试」，再单开演化。

## 11. 约束汇总

### PK

全部 `id`（BIGINT identity）。业务 code 不当 PK。

### FK

- colleges.school_id → schools.id
- majors.school_id → schools.id
- exam_subjects.school_id → schools.id（可空）
- admission_catalogs.school_id → schools.id
- admission_catalogs `(college_id, school_id)` → colleges `(id, school_id)`
- admission_catalogs `(major_id, school_id)` → majors `(id, school_id)`
- admission_catalog_directions.admission_catalog_id → admission_catalogs.id
- admission_catalog_exam_subjects.admission_catalog_id → admission_catalogs.id
- admission_catalog_exam_subjects.exam_subject_id → exam_subjects.id

`college_id` / `major_id` **没有**额外单列 FK。同校一致性只靠组合 FK + `school_id` FK（第 16 节）。

建议 `ON DELETE RESTRICT`（历史 Catalog 仍引用时不得删学校/专业）。

### Unique

| 表 | Unique |
|---|---|
| schools | `school_code` |
| colleges | **partial** `(school_id, college_code) WHERE college_code IS NOT NULL` |
| majors | `(school_id, major_code)` |
| admission_catalogs | `(school_id, college_id, major_id, admission_year, study_mode)` |
| admission_catalog_directions | `(admission_catalog_id, direction_code)` |
| exam_subjects | 两条 **partial unique index**（第 14 节） |
| admission_catalog_exam_subjects | `(admission_catalog_id, exam_unit, exam_subject_id)` |
| admission_catalog_exam_subjects | `(admission_catalog_id, exam_unit, option_order)`（option_order NOT NULL） |

为组合 FK 另加：`colleges (id, school_id)` UNIQUE、`majors (id, school_id)` UNIQUE（与 PK(id) 兼容）。

### Index（非 unique）

与 migration `44f5a70a766a` 一致：

- `ix_colleges_school_id`
- `ix_exam_subjects_school_id`
- `ix_admission_catalogs_college_id`
- `ix_admission_catalogs_major_id`
- `ix_admission_catalogs_year`
- `ix_admission_catalogs_school_year`（school_id, admission_year）
- `ix_admission_catalog_exam_subjects_exam_subject_id`

不建：`ix_majors_school_id`、`ix_admission_catalog_directions_admission_catalog_id`、`ix_admission_catalog_exam_subjects_admission_catalog_id`（已被 UNIQUE 左前缀覆盖）。

### Check

- `majors.degree_type IN ('academic', 'professional')`
- `admission_catalogs.study_mode IN ('full_time', 'part_time')`
- `admission_catalogs.admission_year >= 2000`（第一版不设置人为年份上限）
- `admission_catalog_exam_subjects.exam_unit BETWEEN 1 AND 4`
- `admission_catalog_exam_subjects.option_order >= 1`
- `is_active` 列默认 true（类型 BOOLEAN）

## 12. AdmissionCatalog 年份模型

School / College / Major 相对稳定。Catalog 带 `admission_year`。
同一专业 2026、2027 = 两条 Catalog。科目变化只动对应年的 `admission_catalog_exam_subjects`。Major 不按年复制。

## 13. Direction 模型

见第 8 节。无方向 = 0 行；官方 00 = 一行 `00`。不加 is_active。

## 14. ExamSubject：national vs school-scoped

两条 partial unique index（实现放 Checkpoint 2/3）：

```sql
CREATE UNIQUE INDEX uq_exam_subjects_national_code
  ON exam_subjects (subject_code)
  WHERE school_id IS NULL;

CREATE UNIQUE INDEX uq_exam_subjects_school_code
  ON exam_subjects (school_id, subject_code)
  WHERE school_id IS NOT NULL;
```

全国 101 只能一条；交大 895 与北邮 895 可并存。

## 15. exam_unit / alternatives

不用 politics / foreign_language / major_1 / major_2。
`exam_unit` 1..4。同 unit 多 `exam_subject_id` 为备选。
`option_order` NOT NULL，故 `(catalog, unit, option_order)` 可 UNIQUE，无 NULL 歧义。

## 16. College / Major 同校一致性

Catalog 同时有 `school_id`、`college_id`、`major_id`，必须：

- `colleges.school_id = admission_catalogs.school_id`
- `majors.school_id = admission_catalogs.school_id`

**最终采用：only composite FK + `school_id` FK。** 不是候选方案。

- `UNIQUE (id, school_id)` on colleges、majors
- Catalog FK `(college_id, school_id) → colleges(id, school_id)`
- Catalog FK `(major_id, school_id) → majors(id, school_id)`
- Catalog FK `school_id → schools.id`

`college_id` / `major_id` **没有**额外单列 FK。禁止 trigger。

## 17. 历史数据策略

年度历史靠多条 Catalog（不同 `admission_year`）。
稳定实体用 `is_active`。
不要 `valid_from/to`、`deleted_at`、SCD2、history 表。
不要 hard delete 仍被历史 Catalog 引用的 School/College/Major/Subject。

## 18. Migration 后 Workbench 验证清单

Workbench **只读验证**，禁止在其中 CREATE/ALTER/DROP 替代 Alembic。

1. `SELECT version_num FROM alembic_version;` 为新 revision（不是只有 baseline）。
2. public 表恰好为：`alembic_version` + 下述 7 张业务表。
3. 列名/nullable 与本文一致。
4. FK 含同校组合 FK。
5. Unique / partial unique / check 存在。
6. 插入错校 college 应失败；重复 national 101 应失败；同 catalog 同 unit 同 subject 应失败。
7. `GET /health` 仍不连库。

表名（**统一 plural snake_case**；项目尚无业务表约定，S1-01 起冻结此约定）：

- `schools`
- `colleges`
- `majors`
- `admission_catalogs`
- `admission_catalog_directions`
- `exam_subjects`
- `admission_catalog_exam_subjects`

## 19. Future evolution

- Direction 级不同初试科目
- 研究方向全局主数据 / 跨年稳定 id
- NationalMajor 学科树
- source / source_url
- 学院改名历史快照
- 拟招生人数、复试
- CI 增加 PostgreSQL service（须另批）

## 20. AdmissionCatalog 唯一性假设

采用：

`UNIQUE (school_id, college_id, major_id, admission_year, study_mode)`

**假设：** 方向已拆到子表后，同一学校+学院+专业+年份+学习方式只需一条 Catalog。现有公开研招结构与交大 140500 示例支持此假设。若日后发现必须拆成两条 Catalog（且不是方向、也不是学习方式差异），再单开 Issue，**不加** `catalog_variant` / `version` 预埋列。
