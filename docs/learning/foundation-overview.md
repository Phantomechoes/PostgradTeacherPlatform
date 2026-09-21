# 项目工程底座：从 GitHub 到本地运行

这篇不是教你背技术名词，而是让负责人知道现在项目已经搭到什么程度。

S0-01 到 S0-05 合在一起，建立的是**工程底座**，不是五个互相独立的业务模块。所以这里写成一篇，而不是五篇。

## 1. 现在到底已经有什么

### 已经有

- GitHub 工作流：Issue → 分支 → PR → CI → 合进 `main`
- FastAPI 后端（程序入口在 [`backend/app/main.py`](../../backend/app/main.py)）
- 本机 PostgreSQL 18，应用库名 `postgrad_teacher_platform`
- SQLAlchemy：用 Python 描述表、通过 Session 查库
- Alembic：记录并应用数据库结构变化；当前 head 是 `44f5a70a766a`
- pytest 与 Ruff
- GitHub Actions CI（[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)）
- React + TypeScript + Vite + Ant Design 的内部后台壳（[`admin-web/`](../../admin-web/)）
- 7 张院校招生主数据表
- 7 个只读 `GET /api/v1` 接口（会查 PostgreSQL）

### 还没有

- Admin 真正调用 backend
- Admin CRUD（增删改页面）
- 登录 / 鉴权（auth）
- 师资档案（Teacher）
- 种子数据 / 导入
- 微信小程序业务功能
- S1-03 尚未开始

## 2. 两条不同的“流程”

不要把「怎么把代码合进 GitHub」和「程序怎么处理一次请求」混成一张图。

### 工程交付流程（怎么保证 main 稳定）

```text
Issue
  → 开 feature/docs 分支（禁止直接改 main）
  → 改代码 / 文档
  → 本地测试
  → commit
  → Pull Request
  → GitHub Actions CI
  → 负责人验收
  → merge
  → main
```

每一步挡一类错：没有 Issue 就开干、直接改 main、没测就合、CI 红了还硬合。

### 程序运行流程（一次业务请求怎么走）

```text
客户端
  → FastAPI Router
  → Service
  → Repository
  → SQLAlchemy Session
  → PostgreSQL
```

**当前 Admin Web 还没有进入这条业务请求链。** 打开 `http://127.0.0.1:5173` 只是看到静态壳，不会去打 `/api/v1`。

真正走这条链的，是对 FastAPI 的 HTTP 调用（Swagger、`curl`、以后的 Admin）。

## 3. 用真实的 S1-02 看 GitHub 在防什么

| 步骤 | 本项目实例 | 挡住什么 |
|---|---|---|
| Issue | [#15](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/15) | 没有范围就写代码 |
| 分支 | `feature/15-master-data-read-api` | 直接在 `main` 上开发 |
| PR | [#16](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/16) | 没人审查、说不清做了什么 |
| CI | PR 上的 Backend / Admin Web | 本机能跑、别人或 GitHub 跑不起来 |
| merge | `936d11f` | 未批准就进稳定主干 |
| main CI | push 后再跑一遍 | merge 后主干仍然可测 |

## 4. Backend 是什么

[`backend/app/main.py`](../../backend/app/main.py) 是 FastAPI 程序入口：创建 `app`，挂上主数据路由，并提供健康检查。

打开后重点看三件事：

1. `app = FastAPI(...)`：这就是 Web 服务本身。
2. `app.include_router(master_data_router)`：7 个只读 API 从这里接进来。
3. `GET /health`：返回 `{"status":"ok"}`。

**`GET /health` 故意不访问数据库。** 它只回答「进程还活着吗」。数据库挂了，health 仍可能是 200。主数据 GET 则会真实查 PostgreSQL。

本地启动（必须先进入 `backend/`）：

```text
cd <repo>/backend
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/docs` 可以看到 Swagger。

## 5. PostgreSQL、SQLAlchemy Model、Alembic

不要把这三样当成一件事。

| 名字 | 一句话 |
|---|---|
| PostgreSQL | 真正存数据的仓库。表、行、约束都在这里。 |
| SQLAlchemy Model | Python 世界里对「表长什么样」的描述，文件在 [`backend/app/models/`](../../backend/app/models/)。 |
| Alembic migration | 「结构应该从版本 A 变成 B」的变更记录，文件在 [`backend/migrations/versions/`](../../backend/migrations/versions/)。 |

```text
改 Model
  → 生成 / 编写 Alembic migration
  → 人工阅读
  → alembic upgrade head
  → PostgreSQL 里的真实表变化
```

**改了 Model，数据库不会自动变。** 必须有对应 migration，并且执行过 `alembic upgrade head`。

当前 head：`44f5a70a766a`（7 张主数据表）。更早的 `27d6bd3c881a` 只是空 baseline，当时还没有业务表。

## 6. engine / SessionLocal / get_db

文件：[`backend/app/core/database.py`](../../backend/app/core/database.py)。
连接字符串来自本机 `backend/.env`。该文件不提交 Git。配置说明见 [`backend/README.md`](../../backend/README.md)。真实密码不得进入文档。读取配置的代码在 [`backend/app/core/config.py`](../../backend/app/core/config.py)。

打开 `database.py` 后，看懂这三样就够了：

| 名字 | 大致干什么 |
|---|---|
| `engine` | 应用访问 PostgreSQL 的入口配置（用 `.env` 里的 `DATABASE_URL` 建出来）。 |
| `Session` | 一次数据库工作上下文。业务查询、写入都通过它进行。 |
| `SessionLocal` | 用来**创建** Session 的工厂。它本身不是某一次请求的 Session。 |
| `get_db()` | 每次 FastAPI 请求通过 `SessionLocal()` 创建一个 Session，交给这次请求使用，最后关闭。Router 不自己连库，Repository 也不自己调用 `SessionLocal()`。 |

不需要懂连接池内部实现。记住：**业务查询走 Session；health 不走这条链路。**

## 7. Admin Web 是什么

[`admin-web/`](../../admin-web/) 是给内部人员用的网页，不是考研生小程序。技术是 React + Vite + Ant Design。

当前 [`admin-web/src/App.tsx`](../../admin-web/src/App.tsx) 自己写着：S0-04 工程骨架，尚未接入业务数据。页面上的 Loading / Error / Empty 是**静态演示**，不是真实请求失败。

`http://127.0.0.1:5173` 能打开，只说明 Vite 开发服务器活着。**不等于后台已经能管理数据库。**

## 8. 当前运行关系图

三个进程可以同时开着，但关系不一样：

```text
Browser
  ↓
Admin Web (5173)
  ✕ 当前尚未接 Backend

FastAPI (8000)
  ↓
SQLAlchemy Session
  ↓
PostgreSQL (5432)

GET /health
  → FastAPI
  → 直接返回 {"status":"ok"}
  → 不查 PostgreSQL

GET /api/v1/...
  → FastAPI
  → Service / Repository
  → 真实读取 PostgreSQL
```

| 进程 | 默认端口 | 当前是否连别人 |
|---|---|---|
| PostgreSQL | 5432 | 被 FastAPI 连接 |
| FastAPI | 8000 | 已连 PostgreSQL；尚未被 Admin 调用 |
| Vite Admin | 5173 | 独立页面，不打 backend |

## 9. CI 是第二层保障

文件：[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)。

对 `main` 的 Pull Request，以及 push 到 `main`，都会跑。本机能跑，只证明你这台机器这套 `.env` / 依赖能过；CI 是在 GitHub 的 Ubuntu 上再用锁文件重跑一遍。

**Backend job：** 起 PostgreSQL 18 测试库 → `uv sync --locked` → Ruff → `alembic upgrade head` → pytest。

**Admin job：** Node 24 + Corepack → `pnpm install --frozen-lockfile` → lint → format:check → build。

打开 `ci.yml` 后看懂：`on:` 什么时候触发；backend 的 `services.postgres` 和后面几步命令；admin 的 lint / build。不必背 YAML 语法。

## 10. 出问题优先看哪里

| 症状 | 第一处 |
|---|---|
| FastAPI 起不来 | 是否在 `backend/` 下执行；[`backend/README.md`](../../backend/README.md)；`main.py` |
| 提示连不上数据库 | PostgreSQL 是否在跑；本机 `backend/.env` 的应用角色（不是 `postgres` 超级用户）；`database.py` / `config.py`；配置说明见 [`backend/README.md`](../../backend/README.md) |
| 表结构对不上 | `uv run --locked alembic current` 是否为 `44f5a70a766a`；[`backend/migrations/README.md`](../../backend/migrations/README.md) |
| pytest 红 | 必须在 `backend/` 下：`uv run --locked pytest`；看失败的那个 `backend/tests/` 文件 |
| Admin 页面空白 / 构建失败 | [`admin-web/README.md`](../../admin-web/README.md)；`pnpm lint` / `pnpm build` |
| GitHub CI 红 | Actions 里看是 Backend 还是 Admin Web；不要只在本机再点一次「能打开」就当过了 |

## 11. 负责人至少要读懂的关键代码

1. [`backend/app/main.py`](../../backend/app/main.py)
   看 `FastAPI`、`include_router`、`health`。能说出「入口在这、health 不查库、业务 API 是另挂的路由」就够。

2. [`backend/app/core/database.py`](../../backend/app/core/database.py)
   看 `engine`、`SessionLocal`、`get_db`。能说出「SessionLocal 是工厂，get_db 每次请求用它创建一个 Session，用完关闭」就够。

3. [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
   看两个 job 各自跑什么。能说出「PR 会在 Linux 上自动跑 Ruff / 迁移 / pytest 和前端 lint/build」就够。

## 对照规范 8 问

1. **解决什么问题？** 让项目能在 GitHub 上协作、在本机跑 backend 和 Admin 壳、用 CI 守 `main`。
2. **从哪里触发？** 开发：Issue / PR。运行：本机终端启动进程；浏览器打开 8000 或 5173。
3. **请求进入哪个文件？** 业务 HTTP 进入 `main.py` 再进路由。Admin 页面进入 `admin-web/src/main.tsx` → `App.tsx`，当前不再往下打 API。
4. **数据在哪里处理？** 主数据读取在 Service / Repository；health 不处理数据。
5. **最后存在哪里？** 业务数据在 PostgreSQL；Git 历史在 GitHub。
6. **返回结果从哪里出来？** health 和 GET API 从 FastAPI 返回 JSON；Admin 目前只渲染静态组件。
7. **出问题先看什么？** 上一节的表。
8. **读哪 3 段？** `main.py`、`database.py`、`ci.yml`。
