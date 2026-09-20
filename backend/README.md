# backend

这里是**后端**：运行在服务器上的程序，负责接收请求、执行业务规则、读写数据库。

可以把它理解成仓库里的“柜台后厨”。管理后台和小程序都是窗口；真正算规则、存数据的工作在这里完成。

## 当前状态

S1-02 已合入 `main`。当前 backend 具备：

- Python 3.12 + uv + FastAPI
- SQLAlchemy 2.x + Alembic + PostgreSQL 18
- 7 张主数据业务表；Alembic head：`44f5a70a766a`
- 7 个只读 `GET /api/v1` 接口
- 分层：`Router → Service → Repository → Model → PostgreSQL`
- `GET /health` 仍返回 `{"status":"ok"}`，**不查库**
- 自动化测试（当前基线 88 passed，数量会随测试增长）
- CI：Ubuntu + PostgreSQL 18 + Ruff + Alembic + pytest

约定的分层：

```text
API / Router  →  Service  →  Repository  →  Model  →  PostgreSQL
```

## 跨平台说明

当前主要开发机是 macOS。正式支持 **macOS 原生** 与 **Windows 原生**。CI 使用 Linux。

下面先写平台无关命令。macOS / Windows 只在安装 PostgreSQL、复制 `.env` 等必须分平台的步骤上分开。

不要把 `E:\`、`/Users/<username>/`、`/opt/homebrew` 当成项目强制路径。

## 前置条件（通用）

本机需要：

- Git
- [uv](https://docs.astral.sh/uv/)（本仓库用 uv 管理 Python 与依赖）
- PostgreSQL 18.x（本机安装，不用 Docker）

不要求：

- 把 Python 加进系统 PATH
- 卸载或改动 Anaconda（若已有，不要用它跑本项目）

本目录 `.python-version` 固定为 **3.12**。所有命令通过 `uv run --locked ...` 走本目录 `.venv` 里的 Python 3.12。

若本机还没有 Python 3.12：

```text
uv python install 3.12
```

## 进入 backend/

仓库 clone 在哪里，就把路径换成实际的 `PostgradTeacherPlatform/backend`。后面命令都在这个目录执行：

```text
cd <repo>/backend
```

## 安装 / 同步依赖

```text
uv sync --locked
uv run --locked python --version
```

应显示 `Python 3.12.x`。`.venv/` 只存在于本机，已写入 `.gitignore`，不要提交。

## PostgreSQL

数据库名：`postgrad_teacher_platform`。
应用角色：`postgrad_teacher_platform_app`（FastAPI / SQLAlchemy / Alembic 日常连接，是本库 owner）。
`postgres` 超级用户只用于安装后的初始化 / 管理（建库、建角色），**不要**写进应用的 `DATABASE_URL`。

本机开发库建议 `listen_addresses = localhost`。

### macOS

当前已验收的一台机器：Apple Silicon、PostgreSQL 18、Homebrew。Homebrew 是推荐安装方式，**不是**业务代码依赖。

检查：

```text
brew --version
psql --version
brew services list
pg_isready -h 127.0.0.1 -p 5432
```

如需启动 PostgreSQL 18：

```text
brew services start postgresql@18
```

不要把 `/opt/homebrew` 或 `/Users/<username>/` 写进项目要求。

### Windows

Windows 原生仍然正式支持。使用 Git for Windows 与 PowerShell 即可，不要求 WSL。

下面是**某台已验收 Windows 开发机**的路径，**不是强制路径**。其他开发者按自己的安装位置替换，不要照抄 `E:\postgresql18`。

| 项 | 该机示例值 |
|---|---|
| 版本 | PostgreSQL 18.6 |
| Installation Directory | `E:\postgresql18`（示例） |
| Data Directory | `E:\postgresql18\data`（示例） |
| psql | `E:\postgresql18\bin\psql.exe`（示例） |
| Windows Service | `postgresql-x64-18` |
| Port | `5432` |

检查服务：

```powershell
Get-Service postgresql-x64-18
```

期望：`Status` 为 `Running`。

```powershell
& "E:\postgresql18\bin\pg_isready.exe" -h 127.0.0.1 -p 5432
& "E:\postgresql18\bin\psql.exe" --version
```

`Get-NetTCPConnection -LocalPort 5432` 应只看到 loopback（例如 `127.0.0.1`、`::1`），不应再出现 `0.0.0.0:5432` 或 `[::]:5432`。这是本机安全配置，不是业务代码。

## `.env.example` → `.env`

仓库只提交占位文件 `backend/.env.example`，用户是应用角色，占位密码为 `CHANGE_ME`：

```text
DATABASE_URL=postgresql+psycopg://postgrad_teacher_platform_app:CHANGE_ME@localhost:5432/postgrad_teacher_platform
```

每个开发者在本机复制一份真实配置（不要提交）：

```text
cp .env.example .env
```

Windows PowerShell 也可以：

```powershell
Copy-Item .env.example .env
```

然后只在 `backend/.env` 里把 `CHANGE_ME` 换成应用角色的真实密码。不要把真实密码或完整真实 `DATABASE_URL` 写进 README、Issue、PR、日志或测试。

- 真实 `.env` 已被根目录 `.gitignore` 忽略，禁止 `git add`。
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
- `Base` 是 Model 的声明式基类。S1-01 已有 7 张主数据 Model。
- **禁止** `Base.metadata.create_all()`。建表只走 Alembic。

`GET /health` **不走**这条链路，也不 import 数据库模块。

## Alembic 迁移

历史 empty baseline：`27d6bd3c881a`（只创建 `alembic_version`）。
当前 head：`44f5a70a766a`（7 张主数据表）。

在 `backend/` 下：

```text
uv run --locked alembic current
uv run --locked alembic heads
uv run --locked alembic history
uv run --locked alembic upgrade head
```

期望：`current` 与 `heads` 都是 `44f5a70a766a`。已经是 head 时，再执行 `upgrade head` 是安全的。

约定流程：

```text
修改 Model → 生成 migration → 人工阅读 → 执行 → 测试
```

可能丢数据的迁移必须再次请负责人确认。

## 启动 FastAPI

```text
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

看到类似下面的日志表示已启动：

```text
Uvicorn running on http://127.0.0.1:8000
```

不要用系统里的 `python -m uvicorn`，以免走到 Anaconda 或其他 PATH 上的 Python。

若 8000 已被占用：不要杀掉未知进程，换一个空闲本地端口，或先查清占用者。

## 访问 GET /health

```text
curl -sS http://127.0.0.1:8000/health
```

Windows PowerShell 等价示例：

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing
```

期望：HTTP 200，正文 `{"status":"ok"}`。`/health` 不检查数据库是否可连。

只读主数据 API 合同见 [`docs/api/s1-02-master-data-read-api.md`](../docs/api/s1-02-master-data-read-api.md)。

## 访问 /docs

浏览器打开：

```text
http://127.0.0.1:8000/docs
```

这是 FastAPI 自动生成的 Swagger 页面，应返回 HTTP 200，并包含 `/health` 与 7 个 `GET /api/v1` 只读接口。

用完后在运行 uvicorn 的窗口按 `Ctrl+C` 停止。不要留下占用 8000 的本项目进程。

## 运行 pytest

```text
uv run --locked pytest
```

当前基线 88 passed（含 health、metadata、schemas、service、repository、PostgreSQL integration、API）。数量会随测试增长。可能出现来自 Starlette / httpx 的 DeprecationWarning；当前不阻止验收。

## 运行 Ruff

```text
uv run --locked ruff check .
```

期望输出：`All checks passed!`

## 当前明确没有什么

- 没有写接口、没有 Admin CRUD、没有 auth
- 没有 Teacher / User / Institution / Candidate
- 没有把 `/health` 绑到数据库，也没有 `/ready`
- 没有微信小程序、Docker
- 管理后台在 `admin-web/`，本目录不包含 React

## Secret 安全注意事项

- 只把真实密码放在本机 `backend/.env`。
- 仓库只提交 `backend/.env.example`（占位 `CHANGE_ME`）。
- 不要提交 `.venv/`、`.env`、密码、Token、真实数据库口令。
- `alembic.ini` 里的 `sqlalchemy.url` 也是占位值；运行时由 `migrations/env.py` 从 `.env` 读取。
- 不要在日志、测试或文档中打印 `DATABASE_URL`。
- 应用连接不要使用 `postgres` 超级用户。
