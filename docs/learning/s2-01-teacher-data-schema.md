# S2-01：上岸生师资库为什么是这三张表

这篇不是背字段，而是理解 Sprint 2 第一版为什么只建档案、成功录取和可教授科目，以及它们怎样挂到 Sprint 1 的院校主数据上。

设计依据：[`docs/database/s2-01-teacher-data-schema.md`](../database/s2-01-teacher-data-schema.md)、[`docs/decisions/ADR-0002-sprint2-teacher-foundation-model.md`](../decisions/ADR-0002-sprint2-teacher-foundation-model.md)。
Python 描述在 [`backend/app/models/`](../../backend/app/models/)。
真正建表的变更记录是 Alembic revision `695107900fc3`（接在 S1-01 的 `44f5a70a766a` 之后）。

本 Issue **没有 API**。没有管理页、没有登录、没有对外师资接口。

## 1. S2-01 解决什么问题

Sprint 1 已经能说清：哪所学校、哪个学院、哪个专业、哪一年、考什么。

Sprint 2 第一版要能说清：**内部档案里有哪些上岸生老师、他们成功考上了哪里、现在愿意教哪几门科目。**

没有这三张表，后面的 Admin 维护、筛选师资都没有落点。S2-01 只建表结构。写入 API 是以后的 S2-02，须另批。

## 2. 为什么暂时不建 User

当前没有 auth / login / JWT / RBAC。`/api/v1/admin` 只是 URL 命名空间，不是安全边界。

先建登录账户，会把「档案」和「能登录的人」绑死，而登录方案还没批准。第一版只建 `TeacherProfile`。等 auth 明确后，再考虑 `TeacherProfile → User`。

## 3. TeacherProfile 是什么

内部展示用的师资档案头。不是登录账户，不是身份证，不是通讯录。

文件：[`backend/app/models/teacher_profile.py`](../../backend/app/models/teacher_profile.py)。

有的字段：内部展示名 `display_name`（允许重名）、可选简介 `bio`、档案是否启用 `is_active`、可接状态、基础审核状态、时间戳。

没有的字段：真实姓名、性别、年龄、电话、微信、邮箱、照片、身份证、地址。`bio` 只是自由文本介绍，后续 Admin 使用时不得拿它存放联系方式。

## 4. availability_status 和 is_active 有什么区别

两列都在 TeacherProfile 上，职责分开：

| 列 | 问的是 | 取值 |
|---|---|---|
| `is_active` | 这份档案还在不在内部使用 | true / false，默认 true |
| `availability_status` | 这份仍启用的档案，现在能不能接 | `unknown` / `available` / `unavailable`，默认 `unknown` |

`is_active=false`：档案停用。`availability_status=unavailable`：档案仍启用，只是当前不可接。不要用 `paused`。不做排班、日历、可约时段。

## 5. verification_status 表示什么

内部基础审核状态，不是对外认证徽章。

- `unverified`：默认，还没勾
- `verified`：内部已勾选通过
- `rejected`：内部未通过

第一版没有审核队列，所以没有 `pending`。

## 6. 为什么不存认证材料

`/api/v1/admin` 还不是安全边界。成绩单图片、身份证、录取通知书、学信网截图一旦入库，就变成真实个人数据。第一版只留状态字段，不存材料。

## 7. AdmissionRecord 为什么表示成功录取事实

一条记录 = 这个人 **最终上岸** 的一处招生单位身份。

不是报考史，不是失败记录，不是二战过程，不是志愿列表。同一档案可以有多条成功录取（例如跨年）。第一版不要 `is_primary`，不预先指定「对外展示哪一条」。

## 8. 为什么 Catalog 是 optional

历史上岸年份可能还没有补进 Sprint 1 的招生目录。身份仍然要能录入。

所以 `admission_catalog_id` 可空。空的时候，学校 / 学院 / 专业 / 年份 / 学习方式仍然必填。

## 9. School / College / Major 为什么仍然直接保存

录取身份是五元组：`school + college + major + admission_year + study_mode`。

Catalog 是「这一年官方目录怎么配科目」。人上岸的事实，首先挂在稳定的学校 / 学院 / 专业上，而不是必须先有一条当年目录。同校一致性沿用 S1-01 已经存在的组合外键，不靠口头约定。

## 10. Catalog 非空时五元组一致为什么留给 Service

如果填了 Catalog，Service（S2-02）必须检查这条 Catalog 的五元组和录取行完全一致。

第一版 **不用** 六列复合外键把录取焊死在 Catalog 当前身份上。那条链又长又脆。数据库只保证：非空时 Catalog 行必须存在。

测试里有一条「故意挂错 Catalog」：PostgreSQL **允许**。这不是 bug，是分工。

## 11. 为什么 score 直接放 AdmissionRecord

第一版只要可选的结构化总分：初试、复试、综合。不建独立 ExamScore 表，不存单科，不写死四个考试单元。

## 12. 为什么使用 NUMERIC(8, 2)

复试 / 综合分可能有小数（例如 85.50）。INTEGER 会截断合法值。`(8, 2)` 只是存储宽度，**不是满分**。

## 13. 为什么不写死考试满分

不同学校、不同年份、初试和复试量纲不一样。数据库只保证 `NULL` 或 `>= 0`。需要上限时另开决策，不在表上写 500 / 300 / 100。

## 14. AdmissionRecord.is_active 的真实语义

`true`：这条成功录取当前作为档案的一部分有效。

`false`：因人工纠错或归档，不再作为当前档案有效。

它 **不** 表示「历史上岸后来没发生过」。项目不提供 hard delete。误录一条不该存在的录取后，用 `is_active=false` 作废。Unique 仍然占着同一五元组：以后要同一身份，是恢复 / 修改已有行，不是再插第二条。不要 `is_primary`。

## 15. TeacherTeachSubject 为什么必须显式录入

这是管理员勾选的「现在能教哪门科目」标签。禁止根据 Catalog 或录取自动生成。

## 16. 「考过某科目」和「能教某科目」为什么不是一回事

当年初试考了 895，不等于现在愿意或适合教 895。也可能能教自己没考过的全国统考科目。两件事必须分开存。这是师资标签，不是推荐算法。

## 17. 为什么需要 exam_subject_id 反向索引

Unique `(teacher_profile_id, exam_subject_id)` 的左前缀是老师，适合「这个老师教哪些科目」。

内部筛师经常是「这门科目有哪些老师」。左前缀帮不上，所以另建 `ix_teacher_teach_subjects_exam_subject_id`。不要再给 `teacher_profile_id` 建单列 index。

## 18. DB constraint 与未来 Service validation 的分工

**数据库现在就挡：** 同校学院/专业、录取 Unique、可教授科目 Unique、状态 / 年份 / 学习方式 CHECK、分数不为负、外键存在、禁止 hard delete 仍被引用的父行。

**S2-02 Service 再挡：** Catalog 五元组一致、inactive 父实体能不能建录取、禁止自动生成可教授科目、拒绝联系方式字段。

## 19. 为什么仍然不用 ORM relationship()

延续 Sprint 1：表上写清外键，查询写在 Repository。第一版不引入 `relationship()`。关联怎么查，等有 API 时再显式写 SQL。

## 20. 三张表怎么连

```text
TeacherProfile
  ├─ 1:N AdmissionRecord
  │      ├─ School
  │      ├─ College          （与 school_id 组合 FK，必须同校）
  │      ├─ Major            （与 school_id 组合 FK，必须同校）
  │      └─ AdmissionCatalog? （optional；非空只保证行存在）
  │
  └─ N:M ExamSubject
         via TeacherTeachSubject
```

```text
teacher_profiles
admission_records
teacher_teach_subjects
```

加上 Sprint 1 原有 7 张，业务表共 10 张。没有 `users`、没有联系方式表、没有独立分数 / 可接 / 审核表。

## 21. Model → Migration → 真实库

```text
backend/app/models/teacher_*.py / admission_record.py
        ↓
Alembic 文件 695107900fc3
        ↓
alembic upgrade head
        ↓
PostgreSQL 里多 3 张表
```

在 `backend/` 下：

```text
uv run --locked alembic current
```

期望看到 `695107900fc3 (head)`。

CI 会在空的 PostgreSQL 上从 baseline 一路 `upgrade head`，不依赖本机已有 teacher 行。

## 22. 出问题先看哪里

| 症状 | 先看 |
|---|---|
| 3 张师资表不存在 | `alembic current` 是否 `695107900fc3` |
| 插入非法 availability / verification | TeacherProfile 的 CHECK |
| 跨校学院或专业 | AdmissionRecord 组合 FK |
| 同一人同一五元组插第二条 | `uq_admission_records_teacher_offering`（含已停用行） |
| Catalog 填了但和学校对不上，库却收下了 | 这是设计：交给 S2-02 Service |
| 出现电话 / 微信列 | 立即停止；第一版禁止联系方式 |

## 23. 负责人至少要读懂的关键代码

1. [`backend/app/models/teacher_profile.py`](../../backend/app/models/teacher_profile.py)
   看状态 CHECK 和默认值。能说出「档案启用」和「能不能接」是两列就够。

2. [`backend/app/models/admission_record.py`](../../backend/app/models/admission_record.py)
   看组合外键、Unique、可空 Catalog、`is_active`。能说出「成功录取挂学校学院专业，目录可选」就够。

3. [`backend/app/models/teacher_teach_subject.py`](../../backend/app/models/teacher_teach_subject.py)
   看 Unique 和 `exam_subject_id` 的 index。能说出「能教什么必须手勾，不是从考试科目抄来」就够。

4. [`backend/migrations/versions/695107900fc3_create_teacher_data_schema.py`](../../backend/migrations/versions/695107900fc3_create_teacher_data_schema.py)
   看 `revision` / `down_revision`。能说出「只新增 3 张表，没有改 Sprint 1 那 7 张」就够。

## 对照规范 8 问

1. **解决什么问题？** 为内部管理提供最小上岸生师资档案、成功录取和可教授科目。
2. **从哪里触发？** 当前没有管理页面。结构变化走 Model → Alembic。
3. **请求进入哪个文件？** S2-01 本身不是 HTTP 模块。还没有 Teacher API。
4. **数据在哪里处理？** 约束在 PostgreSQL；Python Model 描述这些约束。
5. **最后存在哪里？** `teacher_profiles`、`admission_records`、`teacher_teach_subjects`。
6. **返回结果从哪里出来？** S2-01 不返回 JSON。
7. **出问题先看什么？** 第 22 节。
8. **读哪几段？** 三个 Model，外加 `695107900fc3` migration。

当前没有：User、auth、联系方式、Public Teacher API、推荐、支付、交易、认证材料。
