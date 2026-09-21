# S1-02：一次主数据 GET 请求怎样从 HTTP 走到 PostgreSQL

数据库在 S1-01 之后已经能被后端 Python 代码查询。缺的是给前端和外部调用方的**稳定应用合同**：固定的 HTTP 入口、参数规则、JSON 形状、404 / 422 等错误语义，以及「普通读取只看启用中的数据」。

S1-02 把「能查库」变成 7 个只读 GET API。合同见 [`docs/api/s1-02-master-data-read-api.md`](../api/s1-02-master-data-read-api.md)。没有写接口、没有登录。

核心例子：

```text
GET /api/v1/admission-catalogs/{catalog_id}
```

## 1. S1-02 解决什么问题

没有这层 API 时，只有写 Python、直接拿 SQLAlchemy Session 的人能读表。浏览器、以后的 Admin、Swagger 调用方没有约定好的路径和返回字段。

S1-02 的价值不是「第一次让程序能碰到 PostgreSQL」——FastAPI 在 S0-03 之后就已经能连库。价值是：**把读取规则收成可测试、可文档化的 HTTP 合同。**

## 2. 当前 7 个 GET

| 路径 | 人话 |
|---|---|
| `GET /api/v1/schools` | 按页列出启用中的学校，可按代码或名称搜 |
| `GET /api/v1/schools/{school_id}` | 看一所启用中的学校 |
| `GET /api/v1/schools/{school_id}/colleges` | 列出该校启用中的学院 |
| `GET /api/v1/schools/{school_id}/majors` | 列出该校启用中的专业（主数据，不是某年招生名单） |
| `GET /api/v1/schools/{school_id}/admission-years` | 该校实际出现过的、读 API 可见的招生年份 |
| `GET /api/v1/admission-catalogs` | 按学校筛选招生目录列表（必须带 `school_id`） |
| `GET /api/v1/admission-catalogs/{catalog_id}` | 一条目录的详情：学校/学院/专业、方向、初试科目组合 |

没有 `GET /exam-subjects`，也没有全局 `GET /colleges`。学院和专业都挂在学校路径下。

## 3. 一次请求完整流程

以目录详情为例：

```text
Browser / curl / Swagger
        ↓
FastAPI Router          backend/app/api/master_data.py
        ↓
MasterDataReadService   backend/app/services/master_data.py
        ↓
AdmissionCatalogRepository
                        backend/app/repositories/master_data.py
        ↓
SQLAlchemy Session      来自 get_db()
        ↓
PostgreSQL
        ↑
Repository 行数据
        ↑
Service 组装（方向列表、按单元分组的科目）
        ↑
Pydantic Schema         AdmissionCatalogDetail
        ↑
JSON
```

| 层 | 为什么存在 |
|---|---|
| Router | 认 URL 和参数，把 HTTP 和业务代码隔开 |
| Service | 判断「算不算找到」、把多块查询结果拼成对外结构 |
| Repository | 只负责按 Session 查库，不管 HTTP |
| Schema | 规定 JSON 有哪些字段，避免把数据库整行端出去 |
| Session | 这一次请求共用一个数据库工作上下文 |

## 4. Router

文件：[`backend/app/api/master_data.py`](../../backend/app/api/master_data.py)。

打开 `get_catalog_detail()`。它声明路径、`response_model=AdmissionCatalogDetail`、用 `_or_404` 把「找不到」变成 HTTP 404，然后调用 Service。

Router **不写 SQL**。参数不合法（缺必填 query、类型不对）由 FastAPI 变成 422，往往到不了 Service。

## 5. Service

文件：[`backend/app/services/master_data.py`](../../backend/app/services/master_data.py)。

`get_catalog_detail()` 做三件事：向 Repository 要目录主信息；要方向；要考试科目选项；然后拼成 `AdmissionCatalogDetail`。目录主信息找不到就抛 `MasterDataNotFoundError`，由 Router 转 404。

学校详情、学院列表等会先 `_require_active_school`：停用或根本没有的学校，按不存在处理。

### `_group_exam_units()`

数据库里科目是平铺的行。API 要按考试单元分组。不要去背函数源码，看这个概念转换：

Repository 查回来（示意）：

```text
unit=1  option=1  101 思想政治理论
unit=2  option=1  201 英语一
unit=2  option=2  202 英语二
```

Service 组装成 JSON 里的结构（示意）：

```text
exam_units:
  - exam_unit: 1
    options: [101]
  - exam_unit: 2
    options: [201, 202]    ← 仍是 OR，不是两门都考
```

所以：**表里的行结构**和 **API 的 JSON 结构**可以不同。拼装发生在 Service，不发生在 SQL 里。

## 6. Repository

文件：[`backend/app/repositories/master_data.py`](../../backend/app/repositories/master_data.py)。

这里才出现 `select` / `join` / `where` / `order_by`。Repository 构造时接收已有 `Session`，自己不 `SessionLocal()`。

打开 `_visible_catalogs()`：一条目录要在普通读取里出现，Catalog、School、College、Major **四个都得是 active**。任一停用，详情就是 404。

`get_catalog()` 用这个可见条件取主信息（一次查出目录 + 学校 + 学院 + 专业）。
`list_directions()` 按方向代码排序取子行。
`list_exam_options()` 再取科目链接，并且 **丢掉 inactive 的 ExamSubject**。

## 7. Schema

文件：[`backend/app/schemas/master_data.py`](../../backend/app/schemas/master_data.py)。

打开 `AdmissionCatalogDetail`。这是 API 对外合同，不是数据库表的镜子。

ORM Model 里有 `is_active`、`created_at`、`updated_at`。当前只读 API **故意不返回这些字段**。调用方不能靠 JSON 判断停用，因为停用数据根本不会作为「找到了」返回。

## 8. Session 从哪里来

[`backend/app/core/database.py`](../../backend/app/core/database.py) 的 `get_db()` 按请求提供 Session。Router 用 FastAPI 的依赖注入拿到它，再交给 Read Service / Repository。

不要写成「Repository 自己开连接」。当前约定是：**一个请求一个 Session，查库的人接收它，不创建它。**

`GET /health` 不走 `get_db`。

## 9. 404、200 空列表、422

| 例子 | HTTP | 含义 |
|---|---|---|
| `GET /api/v1/schools/999999` | 404 | 路径上的那所学校不存在，或已停用。当成「没有这个资源」。 |
| `GET /api/v1/admission-catalogs?school_id=999999` | 200，`items` 为空 | 这是列表过滤。学校不对或没有匹配目录，返回空页，不是 404。 |
| `GET /api/v1/admission-catalogs`（不带 `school_id`） | 422 | 缺了合同规定的必填参数，请求本身不合法。 |

记住：路径上的资源没有 → 404；筛完没有行 → 200 空列表；参数非法 → 422。

## 10. 目录详情为什么是三次查询

当前实现里，`get_catalog_detail` 对应三次 Repository 调用：

1. Catalog + School + College + Major
2. Directions
3. Exam options + ExamSubject

没有使用 ORM `relationship()`（S1-01 / S1-02 都明确不做这个）。负责人可以把它理解为：**三个来源分开读取，再由 Service 组装。** 调试时也可以按这三块分别查：主信息没了、方向空了、还是科目少了。

从当前结构可以理解为：方向和科目不会在一条大 join 里缠在一起。不要把它说成「当年就是为了避免某种 join 问题」——冻结文档没有把那句话写成历史动机。

## 11. 测试在保护什么

不需要读完全部用例。当前 backend 基线大约 88 个测试，数量以后会变。

- [`backend/tests/test_master_data_api.py`](../../backend/tests/test_master_data_api.py)：用 FastAPI 的 TestClient，在 **Python 进程内部模拟 HTTP 请求**经过应用。保护路由、参数校验、状态码、JSON 合同。它**不需要**真正启动 8000 端口，也不是通过真实网络去访问服务器。不要把它理解成 `curl` 打本机服务。
- [`backend/tests/test_master_data_repository_integration.py`](../../backend/tests/test_master_data_repository_integration.py)：连**真实 PostgreSQL**。保护「可见目录」过滤、排序、inactive 科目不出现等查询行为。

另外还有 Service / Schema 的单测。CI 里会 `alembic upgrade head` 再 `pytest`，所以迁移和查询是绑在一起守的。

## 12. 实际手动验证

跨平台核心步骤（在 `backend/` 下）：

```text
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

然后打开 `http://127.0.0.1:8000/docs`，用 Swagger 点 7 个 GET。

健康检查（不查库）：

```text
curl -sS http://127.0.0.1:8000/health
```

学校列表：

```text
curl -sS "http://127.0.0.1:8000/api/v1/schools?page=1&page_size=20"
```

库里还没有业务种子数据时，列表可以是空的 200，这是正常的。不要用写接口往库里塞数据——本模块没有写接口。

## 13. 出问题先看哪里

| 症状 | 先看 |
|---|---|
| 422 | Router 的 Query/Path；是否缺 `school_id`、enum 写错 |
| 404 | Service 的 NotFound；该行或关联学校/学院/专业是否 inactive |
| 列表空、但你觉得库里有 | Repository 的 active 过滤；是否走了公开只读而不是直接查表 |
| 科目少了 | `list_exam_options` 是否滤掉了停用科目 |
| 科目顺序不对 | Repository 的 `order_by`，以及 `_group_exam_units` 是否按 unit 切开 |
| 500 / 连库失败 | `database.py`、`.env`、PostgreSQL 是否在 5432 监听 |
| health 200 但 API 500 | health 本来就不查库，要查 API 那条链路 |

## 14. 负责人至少要读懂的关键代码

1. [`get_catalog_detail`](../../backend/app/api/master_data.py)（Router）
   看懂：路径、response_model、404 转换、没有 SQL。

2. [`MasterDataReadService.get_catalog_detail`](../../backend/app/services/master_data.py) 和 `_group_exam_units`
   看懂：三次 Repository 调用；平铺科目变成按单元分组。

3. [`_visible_catalogs`](../../backend/app/repositories/master_data.py)、`get_catalog`、`list_exam_options`
   看懂：四个 active 条件；科目还要科目本身 active。

4. [`AdmissionCatalogDetail`](../../backend/app/schemas/master_data.py)
   看懂：JSON 有 school/college/major/directions/exam_units，没有 `is_active`。

## 对照规范 8 问

1. **解决什么问题？** 把主数据读取收成稳定的只读 HTTP 合同。
2. **从哪里触发？** 当前是开发者用 Swagger / `curl` / 测试。Admin 尚未调用。
3. **请求进入哪个文件？** [`backend/app/api/master_data.py`](../../backend/app/api/master_data.py)，由 [`main.py`](../../backend/app/main.py) 挂载。
4. **数据在哪里处理？** 查询在 Repository；组装和 404 语义在 Service。
5. **最后存在哪里？** 仍在 S1-01 的 7 张表；本模块不写库。
6. **返回结果从哪里出来？** Pydantic Schema → FastAPI JSON。
7. **出问题先看什么？** 第 13 节。
8. **读哪几段？** Router 的 `get_catalog_detail`、Service 组装、Repository 的 `_visible_catalogs`。
