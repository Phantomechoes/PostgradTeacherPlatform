# Changelog

本文件记录项目的可见变化。  
当前处于 V0.1 Foundation（工程底座）阶段，尚未发布面向用户的业务版本。

## [Unreleased]

### Added

- S2-01 上岸生师资数据 Schema（[Issue #40](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/40)），工作分支 `feature/40-teacher-data-schema`：
  - TeacherProfile（内部档案；availability / verification 为 String + CHECK 状态字段）
  - AdmissionRecord（成功录取事实；可选 AdmissionCatalog 链接；`is_active` 为档案有效状态）
  - TeacherTeachSubject（显式可教授科目 N:M；`exam_subject_id` 反查索引）
  - 可选结构化总分 `NUMERIC(8,2)`：`initial_total` / `retest_total` / `final_total`
  - 无联系方式、无认证材料、无 User / auth、无 Public Teacher API
  - Alembic revision `695107900fc3`
  - 设计：[`docs/database/s2-01-teacher-data-schema.md`](./docs/database/s2-01-teacher-data-schema.md)
  - ADR：[`docs/decisions/ADR-0002-sprint2-teacher-foundation-model.md`](./docs/decisions/ADR-0002-sprint2-teacher-foundation-model.md)
  - 学习文档：[`docs/learning/s2-01-teacher-data-schema.md`](./docs/learning/s2-01-teacher-data-schema.md)

- S1-04 主数据导入与合成 seed（[Issue #35](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/35)），工作分支 `feature/35-master-data-import-seed`：
  - UTF-8 JSON + sidecar manifest importer
  - 默认 dry-run；synthetic + approved 才允许显式 `--apply`
  - 稳定主数据 create / skip / reject
  - Catalog inactive shell + 完整 aggregate；不自动公开
  - 整份文件一笔事务
  - 合成 development seed
  - 合同：[`docs/import/s1-04-import-format.md`](./docs/import/s1-04-import-format.md)
  - 学习文档：[`docs/learning/s1-04-master-data-import-and-seed.md`](./docs/learning/s1-04-master-data-import-and-seed.md)

- S1-03C Admin Web 主数据维护界面（[Issue #31](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/31)），工作分支 `feature/31-admin-web-master-data-ui`，Pull Request [#32](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/32)：
  - 院校 / 学院 / 专业 / 全国统考科目 / 自命题科目的 Admin CRUD 与停用恢复
  - 招生目录 inactive shell、整份 PUT 聚合编辑、显式公开 / 取消公开
  - Vite 将 `/api` 代理到 FastAPI；无 auth、无新业务依赖、无 backend / migration 改动
  - 学习文档：[`docs/learning/s1-03c-admin-web.md`](./docs/learning/s1-03c-admin-web.md)

- 跨平台开发基线（[Issue #17](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/17)），已通过 [PR #18](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/18) 合并进 `main`（`af5c8d3`，Done）：
  - 当前主要开发机：macOS Apple Silicon；Windows 原生继续正式支持；CI 仍为 Linux / GitHub Actions
  - 新增当前工程规范 [`docs/product/开发前工程规范_V0.2.md`](./docs/product/开发前工程规范_V0.2.md)；V0.1 保留为历史冻结版本
  - 修正过时的运行说明（backend / admin-web / AGENTS / CONTRIBUTING / README / PROJECT_STATUS）
  - 同步 S1-02 已合入 `main` 的状态
  - push → main CI run [35508339614](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35508339614) Backend / Admin Web success

- S1-02 只读主数据 API（[Issue #15](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/15)），已通过 [PR #16](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/16) 合并进 `main`（`936d11f`，Done）：
  - 7 个 `GET /api/v1` 只读接口；合同见 [`docs/api/s1-02-master-data-read-api.md`](./docs/api/s1-02-master-data-read-api.md)
  - Pydantic read schemas、Repository、薄 Read Service
  - 真实 PostgreSQL 集成测试（事务回滚）
  - 现有 backend CI job 增加 PostgreSQL 18 service → `alembic upgrade head` → pytest
  - `GET /health` 契约不变，仍不查库
  - push → main CI run [35441128414](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35441128414) 两个 job 均 success

- S1-01 主数据 Schema（[Issue #13](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/13)），工作分支 `feature/13-master-data-schema`，已通过 [PR #14](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/14) 合并进 `main`（`a46a09c`，Done）：
  - 7 张表：`schools` / `colleges` / `majors` / `admission_catalogs` / `admission_catalog_directions` / `exam_subjects` / `admission_catalog_exam_subjects`
  - Alembic revision `44f5a70a766a`；无 ORM `relationship()`
  - push → main CI run [35330608773](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35330608773) 两个 job 均 success

- S0-05 CI（[Issue #11](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/11)），工作分支 `feature/11-ci`，已通过 [PR #12](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/12) 合并进 `main`（`0a490aa`，Done）：
  - GitHub Actions：backend `uv sync --locked` / Ruff / pytest；admin-web frozen install / lint / format:check / build
  - `.gitattributes`：工作区文本 LF
  - push → main CI run `34590063714` 两个 job 均 success

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
