# S2-01 师资数据 Schema 设计

对应 Issue：[S2-01](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/40)
状态：Checkpoint 3（Models + migration `695107900fc3` 已落地；等待 PR review）
ADR：[`ADR-0002-sprint2-teacher-foundation-model.md`](../decisions/ADR-0002-sprint2-teacher-foundation-model.md)
Planning：Issue #39，负责人冻结 D1～D9
基线主数据：S1-01 / Alembic `44f5a70a766a`
本 Issue 正式表结构：Alembic `695107900fc3`

Checkpoint 1 验收时负责人冻结 3 条修正（不另开 ADR-0003）：

1. AdmissionRecord **必须**有 `is_active`（默认 true；不是 hard delete；Unique 覆盖 active / inactive，不做 partial unique）
2. TeacherTeachSubject **必须**有 `exam_subject_id` 单列 index（Unique 左前缀只覆盖 Teacher → subjects）
3. TeacherProfile 三个低基数状态列 **不建** standalone index

本文是第一版设计。正式表结构以 Alembic `695107900fc3` 为准。

Sprint 1 已核实（models + migration `44f5a70a766a`，不是 Planning 报告假设）：

- `colleges` / `majors` 已有 `UNIQUE (id, school_id)`
- `admission_catalogs` 已用组合 FK `(college_id, school_id)`、`(major_id, school_id)` + `school_id` FK
- `college_id` / `major_id` **没有**额外单列 FK
- 状态列是 `String` + `CHECK`，项目中没有 PostgreSQL ENUM
- 全部业务表 `id` 为 `BIGINT Identity`
- 全部业务表使用 `TimestampMixin`
- 无 ORM `relationship()`

## 1. 设计目标

为内部管理提供最小上岸生师资档案：

- 可录入、可停用档案
- 可标记可接状态与基础审核状态
- 可记录一条或多条成功录取
- 可显式挂可教授科目
- 可与 Sprint 1 School / College / Major / AdmissionCatalog / ExamSubject 关联

## 2. Non-scope

不做：

- User / auth / login / JWT / RBAC
- 独立 ExamScore / Availability / Verification / TeacherContact 表
- 联系方式列（phone / mobile / wechat / qq / email / contact_note / address）
- 认证材料、身份证、成绩单图片、录取通知书、学信网、OCR
- Public Teacher API
- API / Admin Web / 小程序（本 Issue 后续 Checkpoint 也不做 API）
- 推荐、支付、Match / Demand / Order / Candidate
- 排班、日历、可约时段、试听、SLA、接单量
- `is_primary`
- 完整考试历史、失败报考、二战过程、志愿历史

不修改 `docs/product/DECISIONS_PENDING.md`。

## 3. 关系图

```text
schools 1──* colleges
schools 1──* majors
schools 1──* exam_subjects          -- 全国统考 school_id IS NULL
schools 1──* admission_catalogs

teacher_profiles 1──* admission_records
teacher_profiles *──* exam_subjects
                 via teacher_teach_subjects

admission_records
  ├─ school_id                       required FK → schools.id
  ├─ (college_id, school_id)         composite FK → colleges(id, school_id)
  ├─ (major_id, school_id)           composite FK → majors(id, school_id)
  ├─ admission_year / study_mode
  └─ admission_catalog_id            optional FK → admission_catalogs.id
```

没有 User。没有独立分数表。没有独立可接 / 审核 / 联系方式表。

## 4. TeacherProfile → `teacher_profiles`

内部展示用的师资档案头。不是登录账户。未来 auth 明确后再考虑 `TeacherProfile → User`。

| 列 | 类型意图 | nullable | default | 说明 |
|---|---|---|---|---|
| id | BIGINT identity | NO | | PK |
| display_name | VARCHAR(255) | NO | | 内部展示名，**不得 Unique，不得 Index Unique** |
| bio | TEXT | YES | | 可选内部简介。不得用它绕过 D6 保存联系方式或敏感认证材料（DB 无法可靠 CHECK；属后续 Admin Service / 使用规范） |
| is_active | BOOLEAN | NO | true | 档案是否启用 |
| availability_status | VARCHAR(32) | NO | `unknown` | 见第 5 节 |
| verification_status | VARCHAR(32) | NO | `unverified` | 见第 6 节 |
| created_at | TIMESTAMPTZ | NO | now() | TimestampMixin |
| updated_at | TIMESTAMPTZ | NO | now() | TimestampMixin |

状态列使用 **String + CHECK**，与 Sprint 1 `degree_type` / `study_mode` 一致。不引入 PostgreSQL ENUM。

`display_name` 只是内部展示。同名允许。禁止用姓名去重。

禁止列：`real_name`、`gender`、`age`、`phone`、`mobile`、`wechat`、`qq`、`email`、`contact_note`、身份证、`photo`、`address`、`political_status`。

### Index

第一版 **不建** `is_active` / `availability_status` / `verification_status` 单列 index。它们是低基数状态，当前 Teacher 数据量和查询计划尚未形成。S2-02 若真实列表查询证明需要，再按 WHERE / ORDER BY / 组合过滤决定单列、composite 或 partial index。

不为 `display_name` 建 unique index。

### Check

- `ck_teacher_profiles_availability`：`availability_status IN ('unknown', 'available', 'unavailable')`
- `ck_teacher_profiles_verification`：`verification_status IN ('unverified', 'verified', 'rejected')`

### 删除 / 停用

soft disable：`is_active = false`。第一版不提供 hard DELETE。仍被 `admission_records` / `teacher_teach_subjects` 引用时，ON DELETE RESTRICT 也会挡住误删。

## 5. Availability

字段，不是表。放在 `teacher_profiles.availability_status`。

| 值 | 含义 |
|---|---|
| `unknown` | 默认。尚未标明能否接 |
| `available` | 当前可接 |
| `unavailable` | 当前不可接 |

不要 `paused`。档案是否启用由 `is_active` 负责。两列职责分开：

- `is_active=false`：档案停用，不参与后续内部选用
- `availability_status=unavailable`：档案仍启用，当前不可接

不做排班、日历、可约时段、试听时间、SLA、接单量。

## 6. Verification

字段，不是表。放在 `teacher_profiles.verification_status`。

| 值 | 含义 |
|---|---|
| `unverified` | 默认。内部尚未勾选基础审核 |
| `verified` | 内部已勾选基础审核通过 |
| `rejected` | 内部基础审核未通过 |

第一版不用 `pending`（没有审核队列工作流）。

Verification 只表示内部基础审核状态。禁止保存认证材料、身份证、成绩单图片、录取通知书、学信网截图、联系方式证明。

## 7. AdmissionRecord → `admission_records`

一条成功录取事实。不是报考史、不是志愿史、不是目录副本。

同一 `TeacherProfile` 允许多条成功录取。第一版 **不要** `is_primary`。第一版 **必须**有 `is_active`（第 8 节）。

| 列 | 类型意图 | nullable | default | 说明 |
|---|---|---|---|---|
| id | BIGINT identity | NO | | PK |
| teacher_profile_id | BIGINT | NO | | FK → teacher_profiles.id |
| school_id | BIGINT | NO | | FK → schools.id |
| college_id | BIGINT | NO | | 与 school_id 组成组合 FK → colleges(id, school_id) |
| major_id | BIGINT | NO | | 与 school_id 组成组合 FK → majors(id, school_id) |
| admission_year | SMALLINT | NO | | `>= 2000`，无人为上限 |
| study_mode | VARCHAR(32) | NO | | `full_time` / `part_time` |
| admission_catalog_id | BIGINT | YES | | FK → admission_catalogs.id；可空 |
| initial_total | NUMERIC(8, 2) | YES | | 初试总分 |
| retest_total | NUMERIC(8, 2) | YES | | 复试分 |
| final_total | NUMERIC(8, 2) | YES | | 总成绩 / 综合分 |
| is_active | BOOLEAN | NO | true | 内部档案有效状态；见第 8 节 |
| created_at | TIMESTAMPTZ | NO | now() | |
| updated_at | TIMESTAMPTZ | NO | now() | |

`college_id` / `major_id` **没有**额外单列 FK。同校一致性沿用 S1-01 已存在的 `uq_colleges_id_school_id` / `uq_majors_id_school_id`。

不存单科、不写死四个考试单元、不存成绩单图片 / OCR / 身份证 / 录取通知书 / 学信网材料。

### Unique

```text
uq_admission_records_teacher_offering
  UNIQUE (teacher_profile_id, school_id, college_id, major_id, admission_year, study_mode)
```

业务语义：同一师资、同一招生单位五元组，只记一条成功录取。`is_active` **不加入** Unique。停用后仍占据同一业务 identity。未来需要同一五元组时：恢复 / 修改已有行，而不是再 INSERT 第二条。不做 partial unique。

允许：

- 同一人多年（`admission_year` 不同）
- 同一年不同专业（`major_id` 不同）
- 同一年同专业不同学院（`college_id` 已进入 Unique；College 区分培养单位）
- 同一年同学硕/专硕对应不同 Major 行（Major 已按 `degree_type` 分列）
- 同一年全日制与非全日制（`study_mode` 不同）

禁止：

- 用 `display_name` 去重
- 第一版加入 `is_primary`

不会错误禁止的情况：同一人同一年同专业、但学院不同。College 已在 Unique 中。

同一六元组的第二条成功录取：第一版视为同一录取事实，由 Unique 拒绝。若日后出现必须并存的第二条（例如专项计划与普通计划且五元组完全相同），停止并另开决策，**不预埋** `plan_type` / `admission_channel`。

### Index

Unique 左前缀覆盖按师资列出录取。另建：

- `ix_admission_records_school_year`（school_id, admission_year）
- `ix_admission_records_college_id`
- `ix_admission_records_major_id`
- `ix_admission_records_admission_catalog_id`（可空 FK 查询）

不另建 `ix_admission_records_teacher_profile_id`（已被 Unique 左前缀覆盖）。`is_active` 暂不建单列 index。

### Check

- `ck_admission_records_study_mode`：`study_mode IN ('full_time', 'part_time')`
- `ck_admission_records_year`：`admission_year >= 2000`
- `ck_admission_records_initial_total_nonnegative`：`initial_total IS NULL OR initial_total >= 0`
- `ck_admission_records_retest_total_nonnegative`：`retest_total IS NULL OR retest_total >= 0`
- `ck_admission_records_final_total_nonnegative`：`final_total IS NULL OR final_total >= 0`

不设满分上限。不写死 500 / 300 / 百分制。若业务日后需要上限：停止并报告，不自造行业常量。

## 8. AdmissionRecord.is_active

Checkpoint 1 原方案没有 `is_active`。负责人验收后冻结：第一版必须加入。

语义：

- `is_active=true`：这条成功录取记录当前作为 TeacherProfile 档案的一部分有效
- `is_active=false`：因人工纠错 / 归档，不再作为当前档案有效

它 **不** 表示「历史录取事实后来不存在」。它只是内部档案有效状态。

原因：当前项目原则是不提供 hard delete。没有 `is_active` 时，管理员误录一条完全不该存在的 AdmissionRecord 后，没有干净的作废方式。

不要 `is_primary`。Unique 仍覆盖 active / inactive。S2-02 再实现恢复 / 修改已有行；本 Checkpoint 不实现 API。

## 9. AdmissionCatalog 可选

`admission_catalog_id` nullable。允许录入 Catalog 尚未补齐的历史年份上岸生。

写入规则（Service，S2-02 实现；本文只标明边界）：

- `admission_catalog_id IS NULL`：只要求 School / College / Major 存在且同校；允许该年尚无 Catalog
- 非空：加载该 Catalog，其 `school_id / college_id / major_id / admission_year / study_mode` 必须与本行完全一致，否则拒绝

第一版 **不用** Catalog 五元组复合 FK。理由见第 10 节。

ON DELETE RESTRICT：仍被录取引用的 School / College / Major / Catalog 不得删。

## 10. AdmissionRecord FK：方案比较

必须基于 Sprint 1 **真实** schema，而不是 Planning 报告里的口头「组合 FK」。已读取 `backend/app/models/admission_catalog.py` 与 `44f5a70a766a`：Catalog 确实使用组合 FK。

### 10.1 school / college / major 同校

| 方案 | 做法 |
|---|---|
| A | 普通单列 FK `college_id → colleges.id`、`major_id → majors.id`，同校一致性交给 Service |
| B | 与 S1-01 Catalog 相同：`school_id` FK + `(college_id, school_id)` / `(major_id, school_id)` 组合 FK。支撑物已经存在：`uq_colleges_id_school_id`、`uq_majors_id_school_id` |

**推荐 B。**

同校是结构化事实，S1-01 已经用清晰、无 trigger 的组合 FK 表达。AdmissionRecord 复用同一支撑 Unique，不新增脆弱链，也不需要为录取再发明一套 school 校验。`college_id` / `major_id` 仍然没有单列 FK。

### 10.2 admission_catalog_id 与五元组一致

| 方案 | 做法 |
|---|---|
| A | nullable 单列 FK `admission_catalog_id → admission_catalogs.id`；非空时 Service 校验五元组完全一致 |
| B | 六列复合 FK `(admission_catalog_id, school_id, college_id, major_id, admission_year, study_mode) → admission_catalogs(...)`，并给 Catalog 增加 `UNIQUE (id, 五元组)` |

**推荐 A（Service）。**

六列复合 FK 在 `catalog_id IS NULL` 时因 MATCH SIMPLE 本就不会检查，表面上能表达「有 Catalog 才焊死」。但它：

- 为可选引用制造长复合链
- 需要给 Catalog 再加一层 `UNIQUE (id, 五元组)` 只为支撑 FK
- Catalog 身份日后若出现维护入口，焊死会变脆

负责人冻结：第一版优先 Service validation。本设计遵循该冻结。

## 11. 分数类型

只允许三列：`initial_total` / `retest_total` / `final_total`。均可空。

| 候选 | 结论 |
|---|---|
| INTEGER | 不采用。复试 / 综合分可能有小数（如 85.5），INTEGER 会截断合法值 |
| NUMERIC(8, 2) | **采用。**(8, 2) 只是存储宽度，不是满分 |

CHECK 只保证 `NULL OR >= 0`。

不硬编码满分 500 / 300 / 百分制。需要上限时停止并报告。

不存单科、图片、OCR。

## 12. TeacherTeachSubject → `teacher_teach_subjects`

显式记录：某 TeacherProfile 愿意 / 能教授哪个 ExamSubject。

这是人工师资标签，不是推荐算法，也不是「当年考过什么」。

| 列 | 类型意图 | nullable | 说明 |
|---|---|---|---|
| id | BIGINT identity | NO | PK |
| teacher_profile_id | BIGINT | NO | FK → teacher_profiles.id |
| exam_subject_id | BIGINT | NO | FK → exam_subjects.id |
| created_at | TIMESTAMPTZ | NO | 何时打上标签 |
| updated_at | TIMESTAMPTZ | NO | 与 Sprint 1 关联表 TimestampMixin 一致 |

### Unique

`uq_teacher_teach_subjects_teacher_subject`：`(teacher_profile_id, exam_subject_id)`

一个 Teacher 可关联多个 ExamSubject。一个 ExamSubject 可关联多个 Teacher。

### FK

- `fk_teacher_teach_subjects_teacher_id` → `teacher_profiles.id` ON DELETE RESTRICT
- `fk_teacher_teach_subjects_exam_subject_id` → `exam_subjects.id` ON DELETE RESTRICT

直接 FK `exam_subjects.id`。ExamSubject 自己已经表达 national（`school_id IS NULL`）或 school-scoped。

第一版 **不要** 复制 `school_id` / `subject_code` / `subject_scope` 到关联表。按学校筛选时 Repository join 现有 `exam_subjects`。避免双份事实源。

### Index

- Unique 左前缀覆盖按师资列出科目
- `ix_teacher_teach_subjects_exam_subject_id`：按科目反查师资

### timestamps / is_active

**要 timestamps。** 与 S1-01 `admission_catalog_exam_subjects` / `admission_catalog_directions` 一致，记录何时打上标签。第一版关联行没有其它可变载荷，`updated_at` 仍保留 mixin，不为未来 PATCH 预埋业务列。

**不要 is_active。** 关联行本身表示「有这个标签」。去掉标签 = 删除该行（S2-02 再决定是单行删除还是整份替换集合）。不要把标签做成可停用实体。

不要：`level`、`score`、`priority`、`price`、`experience_years`、`automatic_match_weight`、`proficiency`。

不得根据 AdmissionRecord 自动生成。不得根据 AdmissionCatalog 自动生成。只能管理员显式录入。

## 13. 约束与索引汇总

### PK

全部 `id`（BIGINT identity）。

### FK（建议名，ON DELETE RESTRICT）

| 名称 | 列 | 引用 |
|---|---|---|
| `fk_admission_records_teacher_id` | `teacher_profile_id` | `teacher_profiles.id` |
| `fk_admission_records_school_id` | `school_id` | `schools.id` |
| `fk_admission_records_college_school` | `(college_id, school_id)` | `colleges(id, school_id)` |
| `fk_admission_records_major_school` | `(major_id, school_id)` | `majors(id, school_id)` |
| `fk_admission_records_catalog_id` | `admission_catalog_id` | `admission_catalogs.id`（可空） |
| `fk_teacher_teach_subjects_teacher_id` | `teacher_profile_id` | `teacher_profiles.id` |
| `fk_teacher_teach_subjects_exam_subject_id` | `exam_subject_id` | `exam_subjects.id` |

`college_id` / `major_id` 没有单列 FK。

### Unique

| 名称 | 列 |
|---|---|
| `uq_admission_records_teacher_offering` | `(teacher_profile_id, school_id, college_id, major_id, admission_year, study_mode)` |
| `uq_teacher_teach_subjects_teacher_subject` | `(teacher_profile_id, exam_subject_id)` |

`teacher_profiles.display_name` 不是 Unique。

### Check

| 名称 | 表达式 |
|---|---|
| `ck_teacher_profiles_availability` | `availability_status IN ('unknown', 'available', 'unavailable')` |
| `ck_teacher_profiles_verification` | `verification_status IN ('unverified', 'verified', 'rejected')` |
| `ck_admission_records_study_mode` | `study_mode IN ('full_time', 'part_time')` |
| `ck_admission_records_year` | `admission_year >= 2000` |
| `ck_admission_records_initial_total_nonnegative` | `initial_total IS NULL OR initial_total >= 0` |
| `ck_admission_records_retest_total_nonnegative` | `retest_total IS NULL OR retest_total >= 0` |
| `ck_admission_records_final_total_nonnegative` | `final_total IS NULL OR final_total >= 0` |

### Index（非 unique）

TeacherProfile 三个状态列第一版 **无** standalone index。

- `ix_admission_records_school_year`（school_id, admission_year）
- `ix_admission_records_college_id`
- `ix_admission_records_major_id`
- `ix_admission_records_admission_catalog_id`
- `ix_teacher_teach_subjects_exam_subject_id`

不建：`ix_teacher_profiles_is_active`、`ix_teacher_profiles_availability_status`、`ix_teacher_profiles_verification_status`、`ix_admission_records_teacher_profile_id`、`ix_teacher_teach_subjects_teacher_profile_id`、`ix_admission_records_is_active`。

## 14. 删除 / 停用语义

| 对象 | 第一版 |
|---|---|
| TeacherProfile | `is_active=false`；无 hard DELETE |
| AdmissionRecord | `is_active=false` 表示不再作为当前档案有效；无 hard DELETE；Unique 仍占据该五元组 |
| TeacherTeachSubject | 无 `is_active`；去掉标签 = 删关联行（S2-02） |
| 被引用的 School / College / Major / Catalog / ExamSubject / TeacherProfile | ON DELETE RESTRICT |

不要 `deleted_at`、SCD2、history 表。

## 15. DB constraint vs Service validation

**数据库保证：**

- PK / 常规 FK / 同校组合 FK
- 录取 Unique
- 可教授科目 Unique
- study_mode / year / 状态 CHECK
- 分数 `NULL OR >= 0`
- ON DELETE RESTRICT

**Service 保证（S2-02，本文只标明边界）：**

- 非空 `admission_catalog_id` 与五元组完全一致
- 是否允许在 inactive School / College / Major 下建录取（建议拒绝，对齐 03A `parent_inactive`，实现时确认）
- 不根据录取或目录自动写 TeacherTeachSubject
- 不接受联系方式或材料字段
- 是否允许挂 inactive ExamSubject 为可教授科目（建议允许保留历史标签、新建时是否拒绝留给 S2-02）

## 16. ORM

延续 Sprint 1：显式 FK + Repository 查询。第一版 **不引入 `relationship()`**。若有人认为必须引入：停止并报告，不在 Checkpoint 2 自行加入。

## 17. Public / Admin

本 Schema 只服务后续 Admin API。

不新增 Public Teacher 路由。TeacherProfile / AdmissionRecord / TeacherTeachSubject 均不得通过 Public API 暴露。

`GET /health` 与 S1-02 Public 合同不变。

`/api/v1/admin` 仍不是安全边界。这是第一版不存联系方式的原因之一。

## 18. 表名

plural snake_case，与 S1-01 冻结约定一致：

- `teacher_profiles`
- `admission_records`
- `teacher_teach_subjects`

没有：`users`、`exam_scores`、`teacher_availabilities`、`teacher_verifications`、`teacher_contacts`。

## 19. 落地与范围

Alembic revision `695107900fc3` 只 CREATE 三张新表及其 FK / Unique / Check / Index。不 ALTER Sprint 1 原 7 张表。

Catalog 五元组一致仍不是 DB constraint，属于 S2-02 Service validation。metadata / constraint tests 注明：DB deliberately does not enforce Catalog five-tuple equality。

本 Issue 不做：API、Service、Repository、Admin Web、Public Teacher API、auth、联系方式、真实个人数据。
