# backend

这里是**后端**：运行在服务器上的程序，负责接收请求、执行业务规则、读写数据库。

可以把它理解成仓库里的“柜台后厨”。管理后台和小程序都是窗口；真正算规则、存数据的工作以后都在这里完成。

当前阶段（S0-03）已在 S0-02 的 FastAPI / `GET /health` 之上，补上 Windows 原生 PostgreSQL、SQLAlchemy、Alembic 与 `.env` 配置。**还没有业务表、业务 API。**

约定的分层（请求从上到下，业务分层尚未实现）：

```text
API / Router  →  Service  →  Repository  →  Model  →  PostgreSQL
```

## 前置条件（Windows 原生）

本机需要：

- Git for Windows
- [uv](https://docs.astral.sh/uv/)（本仓库用 uv 管理 Python 与依赖）
- PostgreSQL 18.x（官方 EDB Interactive Installer，不用 Docker）

不要求：

- 把 Python 加进系统 PATH
- 卸载或改动 Anaconda

系统里如果已有 Anaconda Python 3.10，可以保留。本项目**不要**用它。所有命令都通过 `uv run` 走本目录 `.venv` 里的 Python 3.12。

## Python 3.12 / uv

本目录 `.python-version` 固定为 **3.12**。实际解释器必须是 uv 管理的 CPython 3.12，而不是 PATH 上的 `python`。

uv 同时做三件事：

1. 按 `.python-version` 选用 Python 3.12
2. 按 `pyproject.toml` / `uv.lock` 安装依赖到本目录 `.venv/`
3. 用 `uv run ...` 在该环境里执行命令

`.venv/` 只存在于本机，已写入 `.gitignore`，不要提交。

若本机还没有 Python 3.12，可先执行（不改 PATH）：

```powershell
uv python install 3.12
```

## 进入 backend/

在 PowerShell 中进入本目录。本仓库当前路径示例：

```powershell
cd E:\Projects\PostgradTeacherPlatform\backend
```

若仓库 clone 在其他位置，把路径换成实际的 `...\PostgradTeacherPlatform\backend`。后面所有命令都在这个目录执行。

## 安装 / 同步依赖

```powershell
uv sync
```

会创建或更新 `.venv/`，并安装运行依赖（FastAPI、Uvicorn、SQLAlchemy 2.x、psycopg、Alembic、pydantic-settings）和开发依赖（pytest、httpx、Ruff）。

确认解释器：

```powershell
uv run python --version
```

应显示 `Python 3.12.x`。

## PostgreSQL（当前开发机实际环境）

下面是**当前这台开发机**已经验收过的路径，不是平台强制路径。其他开发者若把 PostgreSQL 装在别的盘或目录，按自己的实际路径替换，不要照抄 `E:\postgresql18`。

| 项 | 当前开发机实际值 |
|---|---|
| 版本 | PostgreSQL 18.6 |
| Installation Directory | `E:\postgresql18` |
| Data Directory | `E:\postgresql18\data` |
| psql | `E:\postgresql18\bin\psql.exe` |
| Windows Service | `postgresql-x64-18` |
| Port | `5432` |
| `listen_addresses` | `localhost`（本机开发库只绑 loopback） |
| 数据库名 | `postgrad_teacher_platform` |
| 应用角色 | `postgrad_teacher_platform_app` |

### postgres 超级用户 vs 应用角色

| 角色 | 用途 |
|---|---|
| `postgres` | 只用于安装后的初始化 / 管理（建库、建角色）。**不要**写进应用的 `DATABASE_URL`。 |
| `postgrad_teacher_platform_app` | FastAPI / SQLAlchemy / Alembic 日常连接账户。是本库的 owner。 |

### 检查服务

```powershell
Get-Service postgresql-x64-18
```

期望：`Status` 为 `Running`。

### 检查端口是否接受连接

把 `psql` / `pg_isready` 换成你本机的实际路径：

```powershell
& "E:\postgresql18\bin\pg_isready.exe" -h 127.0.0.1 -p 5432
& "E:\postgresql18\bin\psql.exe" --version
```

期望：`pg_isready` 显示接受连接；`psql` 版本为 18.x。

本机开发库已收紧为只监听 localhost：

```text
PostgreSQL local development database
listen_addresses = localhost
```

`Get-NetTCPConnection -LocalPort 5432` 应只看到 loopback（例如 `127.0.0.1`、`::1`），不应再出现 `0.0.0.0:5432` 或 `[::]:5432`。其他开发者若自行安装 PostgreSQL，也建议把 `listen_addresses` 设为 `localhost`，这不是业务代码，而是本机安全配置。

不要把真实数据库密码写进命令历史以外的仓库文件。需要手工连库时，在本机终端输入密码即可。

## `.env.example` → `.env`

仓库只提交占位文件：

```text
backend/.env.example
```

内容只有占位密码 `CHANGE_ME`，用户是应用角色，不是 `postgres`：

```text
DATABASE_URL=postgresql+psycopg://postgrad_teacher_platform_app:CHANGE_ME@localhost:5432/postgrad_teacher_platform
```

每个开发者在本机复制一份真实配置（不要提交）：

```powershell
Copy-Item .env.example .env
```

然后只在 `backend/.env` 里把 `CHANGE_ME` 换成应用角色的真实密码。

- 真实 `.env` 已被根目录 `.gitignore` 忽略，禁止 `git add`。
- 不要把真实 `DATABASE_URL` 写进 README、Issue、PR、日志或测试。
- 如果密码包含 URL 保留字符（`@ : / ? # %` 等），需要做 URL encoding（例如 `@` → `%40`），由本机负责人处理。

## SQLAlchemy：config / Engine / Session

连接链路：

```text
backend/.env
  → pydantic-settings（app/core/config.py）
  → settings.database_url
  → SQLAlchemy Engine（app/core/database.py）
  → psycopg 3
  → PostgreSQL
  → SessionLocal / Session
```

- `config.py` 只负责读配置；`DATABASE_URL` 使用 `SecretStr`，避免无意打印。
- `database.py` 在 import 时创建 Engine 对象，**不会**在 import 时执行 SQL。第一次真正用连接时才连库。
- `SessionLocal` 是 Session 工厂；`get_db()` 按请求产出并关闭 Session。
- `Base` 是以后 Model 的声明式基类。当前没有任何业务 Model。
- **禁止** `Base.metadata.create_all()`。建表只走 Alembic。

`GET /health` **不走**这条链路，也不 import 数据库模块。

## Alembic 迁移

迁移脚本在 `migrations/`。当前只有空的 baseline：`27d6bd3c881a`（`empty baseline`）。它只让库里出现 `alembic_version`，不创建业务表。

在 `backend/` 下：

```powershell
uv run alembic current
uv run alembic heads
uv run alembic history
uv run alembic upgrade head
```

期望：

- `current` 与 `heads` 都是 `27d6bd3c881a`
- `history` 为 `<base> -> 27d6bd3c881a (head), empty baseline`
- 已经是 head 时，再执行 `upgrade head` 是安全的（不会重复建表）

约定流程：

```text
修改 Model → 生成 migration → 人工阅读 → 执行 → 测试
```

可能丢数据的迁移必须再次请负责人确认。

## 启动 FastAPI

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

看到类似下面的日志表示已启动：

```text
Uvicorn running on http://127.0.0.1:8000
```

不要用系统里的 `python -m uvicorn`，以免走到 Anaconda。

若 8000 已被占用：不要杀掉未知进程，换一个空闲本地端口，或先查清占用者。

## 访问 GET /health

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing
```

期望：

- HTTP 200
- 正文：`{"status":"ok"}`

`/health` 不检查数据库是否可连。

## 访问 /docs

浏览器打开：

```text
http://127.0.0.1:8000/docs
```

这是 FastAPI 自动生成的 Swagger 页面，应返回 HTTP 200。

用完后在运行 uvicorn 的窗口按 `Ctrl+C` 停止。不要留下占用 8000 的本项目进程。

## 运行 pytest

```powershell
uv run pytest
```

当前应收集并通过 `tests/test_health.py` 中的健康检查测试。可能出现来自 Starlette / httpx 的 DeprecationWarning；当前不阻止验收。不要为此改业务代码或擅自加依赖。

## 运行 Ruff

```powershell
uv run ruff check .
```

期望输出：`All checks passed!`

## 当前 S0-03 明确没有什么

- 没有 School / Teacher / User / Institution / Candidate 业务 Model
- 没有业务表（库中目前只有 `alembic_version`）
- 没有业务 CRUD、没有 `/api/v1` 业务路由
- 没有把 `/health` 绑到数据库，也没有 `/ready`
- 没有 React 管理后台、微信小程序、Docker、CI

`app/api/`、`models/`、`schemas/`、`services/`、`repositories/` 仍是分层占位。`app/core/` 已有配置与数据库连接，没有业务规则。

## Secret 安全注意事项

- 只把真实密码放在本机 `backend/.env`。
- 仓库只提交 `backend/.env.example`（占位 `CHANGE_ME`）。
- 不要提交 `.venv/`、`.env`、密码、Token、真实数据库口令。
- `alembic.ini` 里的 `sqlalchemy.url` 也是占位值；运行时由 `migrations/env.py` 从 `.env` 读取。
- 不要在日志、测试或文档中打印 `DATABASE_URL`。
- 应用连接不要使用 `postgres` 超级用户。
