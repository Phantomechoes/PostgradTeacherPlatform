# backend

这里是**后端**：运行在服务器上的程序，负责接收请求、执行业务规则、读写数据库。

可以把它理解成仓库里的“柜台后厨”。管理后台和小程序都是窗口；真正算规则、存数据的工作以后都在这里完成。

当前阶段（S0-02）已用 uv 初始化 Python 3.12 工程，并提供最小 FastAPI 应用与 `GET /health`。

约定的分层（请求从上到下，业务分层尚未实现）：

```text
API / Router  →  Service  →  Repository  →  Model  →  PostgreSQL
```

## 前置条件（Windows 原生）

本机需要：

- Git for Windows
- [uv](https://docs.astral.sh/uv/)（本仓库用 uv 管理 Python 与依赖）

不要求：

- 把 Python 加进系统 PATH
- 卸载或改动 Anaconda
- 安装 PostgreSQL（那是 S0-03）

系统里如果已有 Anaconda Python 3.10，可以保留。本项目**不要**用它。所有命令都通过 `uv run` 走本目录 `.venv` 里的 Python 3.12。

## Python 版本

本目录 `.python-version` 固定为 **3.12**。

实际使用的解释器必须是 uv 管理的 CPython 3.12，而不是 PATH 上的 `python`。

## uv 的作用

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

会创建或更新 `.venv/`，并安装运行依赖（FastAPI、Uvicorn）和开发依赖（pytest、httpx、Ruff）。

确认解释器：

```powershell
uv run python --version
```

应显示 `Python 3.12.x`。

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

浏览器或 PowerShell：

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing
```

期望：

- HTTP 200
- 正文：`{"status":"ok"}`

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

当前应收集并通过 `tests/test_health.py` 中的健康检查测试。

## 运行 Ruff

```powershell
uv run ruff check .
```

期望输出：`All checks passed!`

## 当前 S0-02 明确没有什么

- 没有 PostgreSQL、SQLAlchemy、Alembic、数据库连接
- 没有用户系统、登录认证
- 没有学校 / 老师等业务 API
- 没有 `/api/v1` 业务路由，也没有 Service / Repository 实现
- 没有 React 管理后台、微信小程序、Docker、CI

`app/api/`、`core/`、`models/`、`schemas/`、`services/`、`repositories/` 仍是分层占位目录。

## 常见注意事项

- 始终在 `backend/` 下使用 `uv run`，不要依赖全局 `python`。
- 不要把 `.venv/`、`.env`、密码或数据库口令提交进 Git。
- 本阶段没有 `.env`。环境变量从 S0-03 才需要。
- 健康检查直接写在 `app/main.py`，尚未拆业务分层。
- pytest 可能出现来自 Starlette / httpx 的 DeprecationWarning；当前不阻止 S0-02。不要为此改业务代码或擅自加依赖。
