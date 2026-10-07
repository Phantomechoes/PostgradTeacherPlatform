# S2-03：Teacher Admin Web 怎样维护上岸生师资库

这篇给项目负责人看。它不重复接口清单，也不把前端文件名排成目录。合同仍在 [`docs/api/s2-02-teacher-admin-api.md`](../api/s2-02-teacher-admin-api.md)。这里要看清一件事：管理员在网页上点的按钮，怎样变成 S2-02 已经冻结的 Admin HTTP，再落到已有的三张师资表。几条容易看反的规则，不能在网页上改成更「简单」的做法。

`http://127.0.0.1:5173` 只给本机内部人员用。页面标题写着 Local Admin · No Auth。`/api/v1/admin` 仍然只是路径分区，不是登录边界。

## 1. S2-03 解决什么

三层各留下一件事：

| 阶段 | 留下什么 | 没有留下什么 |
|---|---|---|
| S2-01 | `TeacherProfile`、`AdmissionRecord`、`TeacherTeachSubject` 三张表 | 没有 HTTP |
| S2-02 | 内部 Admin API：创建档案、改三个状态、登记录取、整份替换可教授科目 | 没有管理页面 |
| S2-03 | React Admin Web，把上面的 API 接到 `/teachers` | 没有新表、没有 migration、没有新的后端合同 |

S2-02 完成后、S2-03 之前，内部维护师资需要通过 Swagger 或 `curl` 调用 Admin API。S2-03 让内部管理员在网页上完成同一件事。

这仍然不是公开师资接口。没有 `/api/v1/teacher-profiles`，也没有给考研生看的师资页。电话、微信、邮箱也不在这个页面上。

## 2. 从哪里进入

左侧菜单「师资」。

```text
/teachers
  列表、搜索、筛选、分页
  「新增师资」只提交名称，以及选填的简介

点某一行的名称
  → /teachers/{id}

/teachers/{id}
  编辑档案
  档案启用 / 停用
  可授课状态
  核验状态
  录取记录
  可教授科目
```

创建成功后进入该老师的详情。服务端给三个状态的默认值：档案启用、可授课「未知」、核验「未核验」。网页创建时不发送这三列。

同一后台里，院校、全国统考科目、招生目录仍走原来的页面。师资页不改那些主数据的规则。

## 3. 一次 Teacher 请求怎样走

浏览器不连接 PostgreSQL。所有师资请求都经过同一条路：

```text
浏览器  http://127.0.0.1:5173
        ↓
TeachersPage 或 TeacherDetailPage
        ↓
admin-web/src/api/teacher.ts    组路径和 JSON
        ↓
admin-web/src/api/client.ts     fetch，只懂 HTTP / JSON / ApiError
        ↓
Vite 把 /api 转到 http://127.0.0.1:8000
        ↓
S2-02 FastAPI Admin Router
        ↓
Service 校验，Repository 查询或 flush
        ↓
PostgreSQL
        ↓
JSON
        ↓
页面用这次响应更新自己的 state
```

业务对错仍在 S2-02 Service。网页负责组请求、展示错误、在失败时留下未保存的编辑。

编辑档案是这条路的一个例子：

```text
详情页「编辑档案」
    ↓
TeacherProfileEditModal
    只把真正变化的 display_name / bio 放进 PATCH
    简介被清空时，bio 写成 null
    没有任何变化时，不发请求
    ↓
updateTeacherProfile()
    PATCH /api/v1/admin/teacher-profiles/{id}
    ↓
响应是 TeacherAdminSummary
    它没有录取列表，也没有可教授科目
    ↓
mergeTeacherSummary()
    用摘要覆盖档案头
    原样保留已经加载的 admission_records 和 teach_subjects
```

所以改一个名字，不会把详情页上的录取和科目清掉。若没有修改却发出 `PATCH {}`，服务端会拒绝。网页在发出之前就停住。

## 4. 三个 Teacher 状态为什么不能联动

档案头上有三列，问的是三件不同的事：

| 列 | 网页上的名字 | 问的是 |
|---|---|---|
| `is_active` | 档案状态 | 这份档案还用不用 |
| `availability_status` | 可授课状态 | 现在接不接新教学：未知 / 可授课 / 不可授课 |
| `verification_status` | 核验状态 | 基础审核到了哪一步：未核验 / 已核验 / 已拒绝 |

它们不能互相改写。四个容易看反的例子：

- 档案已停用，核验状态仍可以是「已核验」。
- 可授课是「可授课」，不表示档案一定启用。
- 核验被拒绝，不会自动停用档案。
- 停用档案，不会自动改成「不可授课」。

详情页因此分三次调用，每次只带自己那一列：

- `PATCH .../teacher-profiles/{id}/status`，body 只有 `is_active`
- `PATCH .../teacher-profiles/{id}/availability`，body 只有 `availability_status`
- `PATCH .../teacher-profiles/{id}/verification`，body 只有 `verification_status`

停用老师之后，可授课和核验仍可单独修改。恢复档案也只把 `is_active` 改回真，不动另外两列。

## 5. Teacher List 为什么有两套「学校」

`/teachers` 的筛选里有两个学校选择器。它们不是同一件事。

录取条件发给列表接口，用来找**同一条仍然有效的录取**：

- `school_id`
- `college_id`
- `major_id`
- `admission_year`
- `study_mode`

学院和专业都挂在这所录取院校下面，选了院校后两者一起可选。这些条件必须落在同一条 `is_active = true` 的 `AdmissionRecord` 上。老师有两条录取时，不能用 A 的学校配 B 的专业拼出一次命中。这个判断在 S2-02，网页只是把字段交给列表接口。

可教授科目是另一条线，只发：

- `exam_subject_id`

它匹配 `TeacherTeachSubject`，不匹配录取。

`subjectSchoolId` 只出现在网页自己的地址栏里，名字是 `subject_school_id`。它的唯一用途是调用 `listSchoolSubjects()`，把那所学校的自命题填进「选择科目」。[`teacher.ts`](../../admin-web/src/api/teacher.ts) 的列表函数故意不接收它，也不会把它写成 `school_id`。

例子：老师的成功录取在 A 大学，但他可以教授 B 大学的自命题 901。

```text
录取院校选 A     → 列表请求里的 school_id 是 A
科目院校选 B     → 只用来加载 B 的自命题
再选中 901       → 列表请求里只有 exam_subject_id
```

这时请求里没有 `subject_school_id`。`school_id` 也不会变成 B。

## 6. AdmissionRecord 为什么不是普通 CRUD

录取记录的是「这个人已经成功考上了这条招生」。它不是意向，也不是在读状态。

网页没有删除录取的按钮，S2-02 也没有 DELETE。停用只发：

```text
PATCH /api/v1/admin/admission-records/{id}/status
{ "is_active": false }
```

停用后有两个不同的可见范围：

- 打开 `/teachers/{id}`，这条已停用的录取还在详情里。
- `/teachers` 用学校、学院、专业、年份、学习方式筛选时，只匹配仍然有效的录取。作废记录不会把老师算进结果。

学校、学院、专业在**新建**或**主动换成另一条**时，必须当前启用。已经写在录取上的引用，后来被停用，详情仍显示它，并带上「已停用」。编辑框会把这条当前引用留在选项里，而且不能把它当成一条新的启用项去重选。

只改成绩时，网页比较旧行和表单，**不重新发送**没变的 `school_id`、`college_id`、`major_id`。否则一次合法的改分，会被服务端看成「又选择了已经停用的学校」。历史记录就无法维护。

## 7. Catalog 为什么看五元组，而不是公开状态

录取可以挂一条招生目录。对得上，指这五项相同：

学校、学院、专业、年份、学习方式。

目录后来取消公开，不表示这五项变了。网页按这五项查询目录时使用 `status=all`，所以未公开目录会出现在选项里，标签是「未公开」。管理员可以选它。

未公开只表示公开读接口还看不见这条目录。它不表示这条成功录取无效，也不要求先把目录公开才能保存录取。

五项对不上时，S2-02 返回 `catalog_identity_mismatch`。网页展示这句话，不自己再发明一套「怎样算同一条目录」。

## 8. 分数为什么区分 omitted 和 null

初试总分、复试总分、最终总分在 JSON 里只有两种值：数字，或 `null`。没有空字符串。

PATCH 的规则是：

| 这次 JSON | 含义 |
|---|---|
| 不写这个字段 | 保持原来的分数 |
| 写成数字 | 改成这个数字 |
| 写成 `null` | 清空 |

所以管理员把原来的 80 清空时，请求必须是：

```json
{ "initial_total": null }
```

漏掉这个字段，80 还在。写成 `""`，请求在进入业务规则之前就会因形状不合法而失败。

新建录取时没有「原值」。分数空着就不放进创建 body，而不是为了清空去发 `null`。

## 9. TeachSubject 为什么必须 whole-set PUT

可教授科目没有单独的启用开关，也没有「加一条」「删一条」的接口。唯一写入口是整份替换：

```text
PUT /api/v1/admin/teacher-profiles/{id}/teach-subjects
{ "exam_subject_ids": [ ... ] }
```

这个数组就是保存之后的完整集合。少一个 id，就是拿掉那门课。空数组就是清空。多一个 id，就是新增。

编辑器把两份名单分开：

```text
打开「编辑科目」
    baseline = 详情里已经挂着的 teach_subjects
    draft    = 管理员正在改的本地名单，一开始等于 baseline

点保存
    draft 和 baseline 相同 → 不发 PUT
    不同 → 发送 draft 的完整 id 列表

成功
    只用响应里的 teach_subjects 替换页面上的科目

失败
    页面上原来的集合不动，编辑器里的 draft 还在
```

因此不能做成两个按钮分别 POST 和 DELETE。那样一次失败会留下一半。整份替换时，S2-02 也是先做完全部检查，通过之后才删旧关系、插入新关系。

保存请求还在进行时，已有科目的复选框会锁住，避免一次迟到的点击改掉已经提交的那份 draft。

## 10. D7：inactive Teacher 为什么还能删科目

档案停用之后，不能给这个老师**新增**可教授科目，也不能新增录取。已经挂着的科目不是新建，所以可以留下、拿掉或全部清空。

例如当前集合是 `[10, 11]`，老师已经停用：

| 请求 | 结果 |
|---|---|
| `PUT [10]` | 允许。只是拿掉 11 |
| `PUT []` | 允许。清空 |
| `PUT [10, 11]` | 允许。集合没增加 |
| `PUT [10, 11, 12]` | 拒绝，`parent_inactive`。数据库仍是 `[10, 11]` |

若网页把「老师已停用」做成「整个 PUT 都不能点」，管理员就无法清掉不该再展示的旧科目。

网页在已经知道老师停用、并且 draft 里出现新 id 时，会先提示并拦住请求。这只覆盖页面自己已经看见的状态。若 draft 组好之后，档案在别处被停用，仍由 S2-02 返回 `parent_inactive`，并且不改已保存的集合。

## 11. D12：inactive ExamSubject 为什么还能出现在 Teacher 上

科目自己的 `is_active` 和老师的档案状态是两件事。

一门课挂到老师身上时是启用的，后来可以被停用。详情必须继续显示这门已停用的课。管理员可以保留它，也可以从集合里拿掉。

拿掉之后不能再加回来。因为「加回来」是新增，而新增的科目必须当前启用。

编辑器因此用两个来源，不能合成一份「只查启用科目」的名单：

| 区域 | 数据从哪来 | 停用科目在不在 |
|---|---|---|
| 当前已有关系 | 老师详情里的 `teach_subjects` | 在。后来停用的也显示 |
| 可新增科目 | 全国统考和学校自命题的 **active** 查询 | 不在 |

科目所属院校只影响第二块名单。换一所学校去查找自命题，不会改掉第一块里已经勾着的科目。

## 12. Admission School 为什么不等于 TeachSubject School

录取院校约束的是这条成功录取属于哪所学校、学院、专业。它不限制这个老师能教哪些学校的自命题。

老师可以录取在 A 大学，同时教授 B 大学的自命题。两套学校选择器必须分开：

- 列表和录取表单里的院校，写入或筛选 `AdmissionRecord`。
- 科目编辑器里的「科目所属院校」，只调用 `listSchoolSubjects()`，用来列出那所学校当前启用的自命题。

第二个选择器不修改录取，也不把 B 写进老师的 `school_id`。师资档案上本来就没有「所属院校」这一列。

## 13. 前端失败时为什么不能先改 persisted state

详情页上有三类写操作。它们成功之后，各自只替换自己那一块，并且都按「当前 state」来合并，而不是用一个旧副本盖掉别人刚写完的结果。

| 操作 | 响应里有什么 | 页面怎样更新 |
|---|---|---|
| 档案头、三个状态 | `TeacherAdminSummary` | 盖住档案头；保留已加载的录取和科目 |
| 录取创建、修改、停用 | 一条 `AdmissionRecord` | 只替换 `admission_records` 里的对应行 |
| 可教授科目 | 整份老师详情 | 只替换 `teach_subjects` |

整份替换科目失败时，页面不能先把表上的现有科目删掉再等响应。422 或网络失败之后，管理员看到的必须仍是数据库里那一份。编辑器里没保存的 draft 可以留着，便于改完再提交。

## 14. 数据最后存在哪里

网页不连接数据库。写请求进了 S2-02 之后，仍落在 S2-01 的三张表：

- `teacher_profiles`
- `admission_records`
- `teacher_teach_subjects`

学校、学院、专业、招生目录、考试科目仍在 Sprint 1 已有的表里：

- `schools`
- `colleges`
- `majors`
- `admission_catalogs`
- `exam_subjects`

S2-03 没有新表，没有 migration，也没有改后端合同。Alembic head 仍是 S2-01 的 `695107900fc3`。

## 15. 错误从哪里出来

[`client.ts`](../../admin-web/src/api/client.ts) 只做三件事：发出 HTTP、解析 JSON、变成 `ApiError`。业务码放在 `code`。FastAPI 的形状校验是一个数组，放在 `validationErrors`。它不知道「师资停用」和「院校停用」该怎样对管理员说。

[`teacherFormErrors.ts`](../../admin-web/src/features/teacher/teacherFormErrors.ts) 只服务师资页，把这些码变成中文：

| code | 网页上的意思 |
|---|---|
| `duplicate_admission` | 已存在相同录取信息 |
| `parent_inactive` | 当前师资已停用，不能新增录取或新增可教授科目 |
| `inactive_reference` | 新选择的引用已停用 |
| `reference_scope_mismatch` | 学院或专业不属于当前院校 |
| `catalog_identity_mismatch` | 招生目录和录取的五元组不一致 |

主数据页面仍用自己的错误映射。那里的 `parent_inactive` 仍是「院校已停用，无法新增下级数据。」师资页没有改那句文案。同一个后端错误码，在两个页面上说的是两种父记录。

## 16. 出问题先看哪里

| 现象 | 先看 |
|---|---|
| 列表、搜索、两套学校筛选不对 | [`TeachersPage.tsx`](../../admin-web/src/pages/TeachersPage.tsx)、[`TeacherFilters.tsx`](../../admin-web/src/features/teacher/TeacherFilters.tsx)、[`teacher.ts`](../../admin-web/src/api/teacher.ts) |
| 改名、清空简介，或三个状态互相带动 | [`TeacherDetailPage.tsx`](../../admin-web/src/pages/TeacherDetailPage.tsx)、[`TeacherStatusControls.tsx`](../../admin-web/src/features/teacher/TeacherStatusControls.tsx)、[`mergeTeacherSummary.ts`](../../admin-web/src/features/teacher/mergeTeacherSummary.ts) |
| 录取新建、改分、历史停用引用 | [`AdmissionRecordModal.tsx`](../../admin-web/src/features/teacher/AdmissionRecordModal.tsx)、[`AdmissionRecordsPanel.tsx`](../../admin-web/src/features/teacher/AdmissionRecordsPanel.tsx)、[`admissionRecordHelpers.ts`](../../admin-web/src/features/teacher/admissionRecordHelpers.ts) |
| 科目整份保存、D7、D12 | [`TeachSubjectsEditor.tsx`](../../admin-web/src/features/teacher/TeachSubjectsEditor.tsx)、[`TeachSubjectsPanel.tsx`](../../admin-web/src/features/teacher/TeachSubjectsPanel.tsx)、[`teachSubjectHelpers.ts`](../../admin-web/src/features/teacher/teachSubjectHelpers.ts) |
| HTTP 状态、JSON、校验数组 | [`teacher.ts`](../../admin-web/src/api/teacher.ts)、[`client.ts`](../../admin-web/src/api/client.ts) |
| 规则本身是否允许 | [`docs/api/s2-02-teacher-admin-api.md`](../api/s2-02-teacher-admin-api.md) |

页面一直转圈或提示服务器错误时，先确认 FastAPI 在 `127.0.0.1:8000`，以及本机代理没有把 `127.0.0.1` 转走。Vite 只代理 `/api`。

## 17. 负责人至少读懂哪 3 个关键阅读点

1. [`admin-web/src/api/teacher.ts`](../../admin-web/src/api/teacher.ts)
   网页最终调用哪些 S2-02 路径。列表不发送 `subject_school_id`。三个状态是三个 PATCH。科目只有一次 whole-set PUT。

2. [`admin-web/src/pages/TeacherDetailPage.tsx`](../../admin-web/src/pages/TeacherDetailPage.tsx)
   档案头、录取、可教授科目怎样先后写进同一个详情。成功时各换各的一块，失败时不先改页面上已经保存的名单。

3. 两处最容易看反的前端规则：
   [`admissionRecordHelpers.ts`](../../admin-web/src/features/teacher/admissionRecordHelpers.ts) 的 `buildAdmissionPatch`：没变的学校、学院、专业为什么必须省略，清空分数为什么必须是 `null`。
   [`TeachSubjectsEditor.tsx`](../../admin-web/src/features/teacher/TeachSubjectsEditor.tsx)：已有科目为什么不能和「只查启用科目」的候选名单合成一份；老师停用后为什么仍可以保存一份更小的集合。

## 对照规范 8 问

1. **解决什么问题？** 让内部管理员用网页维护师资档案、三个状态、成功录取和可教授科目，而不再只靠 Swagger 或 curl。
2. **从哪里触发？** 浏览器 `127.0.0.1:5173` 的「师资」菜单，`/teachers` 和 `/teachers/{id}`。
3. **请求进入哪个文件？** 页面 → [`teacher.ts`](../../admin-web/src/api/teacher.ts) → [`client.ts`](../../admin-web/src/api/client.ts) → Vite `/api` 代理 → S2-02 FastAPI Admin Router。
4. **数据在哪里处理？** 业务规则仍在 S2-02 Service。网页组 JSON、展示错误、失败时保留未保存编辑。
5. **最后存在哪张表？** `teacher_profiles`、`admission_records`、`teacher_teach_subjects`。学校、学院、专业、目录、科目仍在 Sprint 1 已有表。
6. **返回结果从哪里出来？** S2-02 Admin JSON。档案头返回摘要，科目整份替换返回详情。没有公开师资 JSON。
7. **出问题优先看什么？** 第 16 节的表。规则争议以 S2-02 合同为准。
8. **负责人至少读哪 3 个位置？** `teacher.ts`、`TeacherDetailPage.tsx`，以及 `buildAdmissionPatch` 和 `TeachSubjectsEditor`。
