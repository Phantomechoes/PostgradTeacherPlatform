# S1-01：院校招生主数据为什么设计成 7 张表

这篇不是背 Schema，而是理解现实业务怎样映射到数据库。

设计依据：[`docs/database/s1-01-master-data-schema.md`](../database/s1-01-master-data-schema.md)、[`docs/decisions/ADR-0001-admission-catalog-domain-model.md`](../decisions/ADR-0001-admission-catalog-domain-model.md)。
Python 描述在 [`backend/app/models/`](../../backend/app/models/)。
真正建表的变更记录是 Alembic revision `44f5a70a766a`。

贯穿例子：

```text
北京交通大学
  → 自动化与智能学院
  → 140500 智能科学与技术
  → 2026 年 · 全日制（full_time）
  → 研究方向 01 / 02
  → 初试科目（按考试单元，有的单元可以选考）
```

## 1. S1-01 解决什么问题

以后要做师资匹配，平台必须先知道：考生面对的是哪所学校、哪个学院、哪个专业、哪一年招生、有没有研究方向、初试考什么。

没有这套主数据，后面的老师档案、匹配、导入都没有稳定的「挂靠点」。S1-01 只建表结构，不做查询 API（那是 S1-02）、不做后台维护页（那是以后的 S1-03）。

## 2. 七个实体

| 实体 | 现实里是什么 | 为什么不能并进别的表 | 和谁关联 |
|---|---|---|---|
| School | 招生单位，如北京交通大学 | 学院、专业、目录都挂在学校下 | 一所学校有多个学院、专业、科目、目录 |
| College | 某校下的院系所 | 学院会改名、可停用；同一专业可在不同学院招生 | 属于 School；被 Catalog 引用 |
| Major | 该校招生专业代码，如 140500 | 专业身份跨年稳定，不按年复制 | 属于 School，**不属于** College |
| AdmissionCatalog | 「某校 + 某院 + 某专业 + 某年 + 学习方式」这一条招生目录 | 年份、科目会变，必须按年留历史 | 指向 School、College、Major |
| AdmissionCatalogDirection | 该目录下公布的研究方向 | 方向是某年目录的子项，不是全校共用一张方向表 | 属于一条 Catalog |
| ExamSubject | 一门考试科目 | 101 是全国统考，895 是某校自命题，不能合成一行 | 统考 `school_id` 为空；自命题属于 School |
| AdmissionCatalogExamSubject | 「这条目录的某个考试单元选了哪门科目」 | 科目可被多年、多目录复用；组合关系必须单独记 | 连接 Catalog 与 ExamSubject |

## 3. 最核心的是 AdmissionCatalog

它代表的不是「一个专业」，而是**某一年、某种学习方式下，这个专业在这个学院怎么招**。

例子里 2026 全日制 140500，是一条 Catalog。如果 2027 专业课从 895 换成别的，应再有一条 2027 的 Catalog，而不是去改 2026 那一行。历史年份靠多条 Catalog 保留。

**Major 不按年复制。** 140500 还是同一个专业身份；变的是「这一年怎么考」。

Python 描述：[`backend/app/models/admission_catalog.py`](../../backend/app/models/admission_catalog.py)。打开后看唯一约束 `uq_admission_catalogs_offering`：同一学校、学院、专业、年份、学习方式只能有一条。

## 4. Major 为什么属于 School，不属于 College

同一专业代码可能在多个学院招生。如果 Major 挂在 College 下，换学院招生就要复制专业，或者改所属学院，历史会对不上。

学院和专业真正绑在一起的地方是 **AdmissionCatalog**：这条目录同时指向一个 College 和一个 Major，并且用组合外键保证它们和 Catalog 是同一所学校。

不要画成 `College → Major` 这种父子关系。

## 5. Direction

研究方向是某条 Catalog 的子项，文件：[`backend/app/models/admission_catalog_direction.py`](../../backend/app/models/admission_catalog_direction.py)。

- 官方没公布方向：**0 行**。不要为了「看起来完整」自己插一行。
- 官方明确「00 不区分研究方向」：才存一行，`direction_code = 00`。

同一条 Catalog 里，方向代码不能重复。

## 6. ExamSubject

文件：[`backend/app/models/exam_subject.py`](../../backend/app/models/exam_subject.py)。

- `school_id` 为空：全国统考，例如 101。全国同一个代码只能有一条。
- `school_id` 非空：该校自命题，例如交大 895。北邮也可以有自己的 895，互不冲突。

**不要以为 `subject_code` 全局唯一。** 只在「全国」或「同一所学校内部」唯一。

## 7. AdmissionCatalogExamSubject

科目可以复用（很多目录都考 101），所以不能把科目字段直接写在 Catalog 上。关联表记录：这条目录、哪个考试单元、选了哪门科目、展示顺序。

`exam_unit` 只能是 1、2、3、4。它不是「政治 / 外语」这种写死的槽位名字，只是第几单元。

**同一个 `exam_unit` 多行 = 或（OR），不是都考。**

例如单元 2：

```text
option_order 1 → 201
option_order 2 → 202
```

意思是：201 **或** 202，不是 201 并且 202。`option_order` 只是显示顺序，不是科目身份。

文件：[`backend/app/models/admission_catalog_exam_subject.py`](../../backend/app/models/admission_catalog_exam_subject.py)。

## 8. 七张表怎么连

```text
School（北京交通大学）
├─ College（自动化与智能学院）
├─ Major（140500 智能科学与技术）     ← 挂学校，不挂学院
├─ ExamSubject（该校自命题，如 895）
└─ AdmissionCatalog（2026 · full_time）
      ├─ 指向上面的 College
      ├─ 指向上面的 Major
      ├─ Direction（01、02；没有则 0 行）
      └─ CatalogExamSubject
            └─ 指向 ExamSubject（101 统考 或 895 自命题）
```

College 和 Major 的组合发生在 Catalog 上，不是 Major 属于某个 College。

## 9. 外键、唯一、检查在挡什么错

不需要背 SQL。记住三类保护：

**外键（FK）** 防止引用不存在的对象，以及删还被引用的父数据（当前是 `ON DELETE RESTRICT`）。例如目录必须指向真实存在的学校。

**唯一（Unique）** 防止重复身份。例如同一学校不能有两个相同 `major_code`；同一条 Catalog 不能重复同一个方向代码；同一单元不能重复同一科目或同一 `option_order`。

**检查（Check）** 防止明显非法值。例如 `exam_unit` 写成 5、`study_mode` 写成随便一个字符串、`degree_type` 不是学硕/专硕。

**同校组合外键** 专门挡这类错：Catalog 的学校是北京交大，学院却写成北京邮电大学的学院。数据库必须拒绝。打开 [`admission_catalog.py`](../../backend/app/models/admission_catalog.py) 看 `fk_admission_catalogs_college_school` 和 `fk_admission_catalogs_major_school`：学院/专业的 `id` 必须和这条目录的 `school_id` 成对出现。

## 10. is_active

School、College、Major、ExamSubject、AdmissionCatalog 都有 `is_active`。停用不等于从库里抹掉。

历史 Catalog 可能仍引用某学院或某专业。外键是 RESTRICT，硬删会被数据库拦住；即便能删，也会毁掉「2026 当时挂的是哪个学院」这种事实。第一版用停用，让普通读取看不到，数据还在。

Direction 和 CatalogExamSubject **没有** `is_active`：它们是某年目录的子结构，调整时改该年的行。

## 11. Model → Migration → 真实库

```text
backend/app/models/*.py     Python 对表的描述
        ↓
Alembic 文件 44f5a70a766a    结构变更记录
        ↓
alembic upgrade head
        ↓
PostgreSQL 里出现 7 张表
```

只改 Model、不跑 migration，库还是旧的。只在图形界面里手工建表、不留 migration，别人的环境和 CI 会对不上。

在 `backend/` 下：

```text
uv run --locked alembic current
```

期望看到 `44f5a70a766a (head)`。

## 12. VS Code PostgreSQL Explorer

负责人这台 Mac 上，VS Code PostgreSQL Explorer 已经连接成功。打开后应能看到：

- `schools`
- `colleges`
- `majors`
- `admission_catalogs`
- `admission_catalog_directions`
- `exam_subjects`
- `admission_catalog_exam_subjects`
- `alembic_version`

Explorer 适合：**查看、SELECT、理解结构**。
不要用它手工 `CREATE` / `ALTER` / `DROP` 来代替 Alembic。

## 13. 出问题先看哪里

| 症状 | 先看 |
|---|---|
| 表不存在 | `alembic current` 是否 head；migration `44f5a70a766a` 是否执行过 |
| 字段和文档不一致 | 对应 `models/*.py` 与 schema 文档，不要只看 GUI |
| 插入报 unique / check | 是否重复代码、`exam_unit` 越界、学习方式写错 |
| 错校学院/专业 | Catalog 的组合外键；学校 id 是否和学院/专业一致 |
| revision 不是 `44f5a70a766a` | [`backend/migrations/README.md`](../../backend/migrations/README.md) |

## 14. 负责人至少要读懂的关键代码

1. [`backend/app/models/admission_catalog.py`](../../backend/app/models/admission_catalog.py)
   看组合外键和那条唯一约束。能说出「一条目录 = 学校+学院+专业+年份+学习方式」就够。

2. [`backend/app/models/exam_subject.py`](../../backend/app/models/exam_subject.py)
   看 `school_id` 可空，以及两条 partial unique。能说出「101 全国一条、895 按学校各一条」就够。

3. [`backend/app/models/admission_catalog_exam_subject.py`](../../backend/app/models/admission_catalog_exam_subject.py)
   看 `exam_unit` 1..4 和两条 unique。能说出「同单元多科目是备选，不是都考」就够。

4. [`backend/migrations/versions/44f5a70a766a_create_master_data_schema.py`](../../backend/migrations/versions/44f5a70a766a_create_master_data_schema.py)
   看文件名、`revision` / `down_revision`。能说出「真正建表的是这个变更记录，不是改 Python 就自动出现表」就够。不必读完整 SQL。

## 对照规范 8 问

1. **解决什么问题？** 为后续师资匹配提供稳定的院校招生主数据。
2. **从哪里触发？** 当前没有管理页面。结构变化走 Model → Alembic；查看可用 PostgreSQL Explorer 或以后的 API。
3. **请求进入哪个文件？** S1-01 本身不是 HTTP 模块。读数据的 HTTP 入口在 S1-02 的 [`backend/app/api/master_data.py`](../../backend/app/api/master_data.py)。
4. **数据在哪里处理？** 约束在 PostgreSQL；Python Model 描述这些约束。
5. **最后存在哪里？** 上面 7 张表 + `alembic_version`。
6. **返回结果从哪里出来？** S1-01 不返回 JSON。查询结果从 S1-02 API 出来。
7. **出问题先看什么？** 第 13 节。
8. **读哪几段？** Catalog / ExamSubject / CatalogExamSubject 三个 Model，外加 `44f5a70a766a` migration。
