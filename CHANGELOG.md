# Changelog

本文件记录项目的可见变化。  
当前处于 V0.1 Foundation（工程底座）阶段，尚未发布面向用户的业务版本。

## [Unreleased]

### Added

- S0-04 管理后台起步（[Issue #9](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/9)），工作分支 `feature/9-admin-bootstrap`，已通过 [PR #10](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/10) 合并进 `main`（`1fa1d2e`，Done）：
  - React + TypeScript + Vite，pnpm 12 / Node.js 24
  - Ant Design 6 单页内部后台壳（Loading / Error / Empty 静态演示）
  - ESLint + Prettier
  - Windows 运行说明（`admin-web/README.md`）

- S0-03 数据库起步（[Issue #7](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/7)），工作分支 `feature/7-database-bootstrap`，已通过 [PR #8](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/8) 合并进 `main`（`5440785`，Done）：
  - 本机 PostgreSQL 18.6 开发库 `postgrad_teacher_platform`，应用角色 `postgrad_teacher_platform_app`
  - SQLAlchemy 2.x + psycopg 3、pydantic-settings、`.env.example`
  - Alembic baseline `27d6bd3c881a`（仅 `alembic_version`，无业务表）
  - Windows 数据库 / migration 说明（`backend/README.md`）

- S0-02 后端起步（[Issue #5](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/5)），工作分支 `feature/5-backend-bootstrap`，已通过 [PR #6](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/6) 合并进 `main`（`deba8df`，Done）：
  - Python 3.12 + uv 后端环境（`backend/pyproject.toml`、`backend/uv.lock`、`backend/.python-version`）
  - FastAPI 最小应用（`backend/app/main.py`）
  - `GET /health` 返回 `{"status":"ok"}`
  - Swagger `/docs`
  - pytest（`backend/tests/test_health.py`）
  - Ruff
  - Windows 后端运行说明（`backend/README.md`）

- S0-01 仓库起步（[Issue #1](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/1)），工作分支 `chore/s0-01-repository-bootstrap`：
  - 根目录说明与协作文件：`README.md`、`CONTRIBUTING.md`、`PROJECT_STATUS.md`、`CHANGELOG.md`、`.gitignore`、`.editorconfig`
  - 目录骨架：`backend/`、`admin-web/`、`miniprogram/`、`docs/`、`scripts/`、`.github/`（仅占位说明，无可运行代码）
  - 冻结规范纳入仓库：`AGENTS.md`、`docs/product/开发前工程规范_V0.1.md`、`docs/product/DECISIONS_PENDING.md`
  - GitHub Issue / PR 模板：`.github/ISSUE_TEMPLATE/development_task.md`、`.github/ISSUE_TEMPLATE/bug_report.md`、`.github/pull_request_template.md`
  - S0-01 已通过 [PR #2](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/2) 合并进 `main`（Done）

### Changed

- 精细化根目录 `AGENTS.md` 操作规则（[Issue #3](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/3)）：Context Loading Order、冲突优先级、Tool / Skill Routing、Mandatory Stop Conditions。不改冻结工程规范，不改 Research Blocked 状态。
