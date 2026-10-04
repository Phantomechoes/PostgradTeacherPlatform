# ADR-0002 Sprint 2 teacher foundation model

状态：Accepted
日期：2026-10-04
依据：Sprint 2 Planning Issue #39；负责人冻结 D1～D9；S2-01 Issue #40
详细字段：[`docs/database/s2-01-teacher-data-schema.md`](../database/s2-01-teacher-data-schema.md)

## 背景

Sprint 1 已提供院校招生主数据。Sprint 2 要建立上岸生基础师资库。当前没有 auth，`/api/v1/admin` 不是安全边界。机构交易、选师、支付、推荐仍为 Research Blocked。

需要一次定清：第一版有哪些表、哪些只是状态字段、如何挂到 Sprint 1 主数据。

## 决定（D1～D9，负责人冻结）

1. **TeacherProfile-only，不建 User。**（D1 = B）不实现 auth / login / JWT / RBAC。未来 auth 明确后再考虑 `TeacherProfile → User`。
2. **AdmissionCatalog 可选。**（D2 = B）录取身份是 `school + college + major + admission_year + study_mode`。`admission_catalog_id` 可空。非空时由 Service 校验与五元组完全一致。
3. **不建独立 ExamScore 表。**（D3 = A）可选结构化总分放在 AdmissionRecord：`initial_total` / `retest_total` / `final_total`。可空，`>= 0`。不写死四个考试单元，不存单科，不存成绩单图片 / OCR / 身份证 / 录取通知书 / 学信网材料。
4. **Availability 是 TeacherProfile 字段。**（D4 = A）冻结：`unknown` / `available` / `unavailable`。默认 `unknown`。不要 `paused`。不做排班、日历、可约时段、试听、SLA、接单量。
5. **Verification 是 TeacherProfile 字段。**（D5 = A）冻结：`unverified` / `verified` / `rejected`。默认 `unverified`。第一版不用 `pending`。只表示内部基础审核状态，不存认证材料。
6. **不保存联系方式。**（D6 = A）禁止 phone / mobile / wechat / qq / email / contact_note / address。
7. **显式 TeacherTeachSubject。**（D7 = B）TeacherProfile N:M ExamSubject。业务 Unique `(teacher_profile_id, exam_subject_id)`。禁止根据 AdmissionCatalog 或历史考试科目自动生成。这是人工师资标签，不是推荐算法。**D7 与 Planning 中 Grok 原推荐（第一版不做关联表）不同，以负责人选择为准。**
8. **Admin only。**（D8 = A）不新增 Public Teacher API。TeacherProfile / AdmissionRecord / TeacherTeachSubject 不得经 Public API 暴露。
9. **只记录成功上岸 / 最终录取。**（D9 = A）不建考试历史、失败报考、志愿史。同一 TeacherProfile 允许多条 AdmissionRecord。第一版不要 `is_primary`。

## Checkpoint 1 设计选择

这些是冻结之后的落地选择。Checkpoint 1 验收时负责人修正了第 3、6 条中的索引 / `is_active` 细节（见下一节）。不另开 ADR-0003。

1. **状态列：String + CHECK。** 与 Sprint 1 `degree_type` / `study_mode` 一致。不引入 PostgreSQL ENUM。
2. **分数：NUMERIC(8, 2)，可空，CHECK `>= 0`。** 不用 INTEGER（复试 / 综合分可能有小数）。`(8, 2)` 是存储宽度，不是满分。不写死 500 / 300 / 百分制。
3. **AdmissionRecord 要 `is_active`。** 默认 true。表示这条成功录取当前是否作为档案有效；不表示历史事实后来不存在。项目不提供 hard delete，误录用 `is_active=false` 作废。Unique 覆盖 active / inactive，不做 partial unique。不要 `is_primary`。
4. **school / college / major：组合 FK（方案 B）。** 已读取 S1-01 真实 schema：`colleges` / `majors` 已有 `UNIQUE (id, school_id)`，Catalog 已用组合 FK。AdmissionRecord 复用同一支撑，不靠 Service 保证同校。
5. **Catalog 五元组一致：Service（方案 A）。** 不用六列复合 FK。`admission_catalog_id` 保持 nullable 单列 FK + RESTRICT。
6. **TeacherTeachSubject：要 timestamps，不要 `is_active`。** 与 S1-01 关联表 TimestampMixin 一致。去掉标签 = 删行。不复制 `school_id` / `subject_code` / scope。必须有 `exam_subject_id` 单列 index。
7. **录取 Unique：** `(teacher_profile_id, school_id, college_id, major_id, admission_year, study_mode)`。College 已区分培养单位。不用姓名去重。`is_active` 不加入 Unique。
8. **不引入 ORM `relationship()`。**
9. **TeacherProfile 三个状态列第一版不建 standalone index。** 低基数；等 S2-02 真实查询再决定。

## Checkpoint 1 验收修正

负责人 2026-10-04 冻结，仍记在本 ADR（Accepted）：

- 修正 A：AdmissionRecord 加 `is_active`
- 修正 B：TeacherTeachSubject 加 `ix_teacher_teach_subjects_exam_subject_id`
- 修正 C：TeacherProfile 不建 `is_active` / `availability_status` / `verification_status` 单列 index

## 后果

- 第一版三张业务表：`teacher_profiles`、`admission_records`、`teacher_teach_subjects`。
- 历史上岸生可以在尚未补 Catalog 时录入。
- 可教授科目必须管理员显式勾选。
- Research Blocked 商业事项不因本 ADR 解除。不修改 `docs/product/DECISIONS_PENDING.md`。

## 不改

不修改冻结规范 V0.2 正文。不引入 ORM `relationship()`。不把 `/api/v1/admin` 写成安全边界。不解除 Research Blocked。
