# 项目状态

最后更新：2026-09-22
当前版本：V0.1 Foundation（未发布业务版本）；工程规范当前为 V0.2
当前 Sprint：Sprint 1 — 院校招生主数据
当前主要开发机：macOS Apple Silicon
已验证本地环境：macOS 原生、Windows 原生
CI：Linux / GitHub Actions
GitHub：<https://github.com/Phantomechoes/PostgradTeacherPlatform>

## 正在进行

- **S1-03B AdmissionCatalog Admin API**：**In Progress**
  - Issue：[ #27](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/27)
  - 分支：`feature/27-admission-catalog-admin-api`
  - 范围：Admin Catalog 读（含 inactive）；创建 inactive shell；PUT 聚合保存（基本字段 + directions[] + exam_units[]）；显式 activate
  - 明确不做：Admin Web、auth、migration、row-level child REST、S1-03C
  - 合同：[`docs/api/s1-03b-admission-catalog-admin-api.md`](./docs/api/s1-03b-admission-catalog-admin-api.md)
  - 学习文档：[`docs/learning/s1-03b-admission-catalog-admin-api.md`](./docs/learning/s1-03b-admission-catalog-admin-api.md)

## 已完成

- **S0-01 Repository Bootstrap**：**Done**
  - Issue #1 已关闭；PR #2 已合并进 `main`（`1bae0e5`）

- **Refine AGENTS Operational Rules**：**Done**
  - Issue #3 已关闭；PR #4 已合并进 `main`（`03ce647`）

- **S0-02 Backend Bootstrap**：**Done**
  - Issue #5 已关闭；PR #6 已合并进 `main`（`deba8df`）

- **S0-03 Database Bootstrap**：**Done**
  - Issue #7 已关闭；PR #8 已合并进 `main`（`5440785`）

- **S0-04 Admin Web Bootstrap**：**Done**
  - Issue #9 已关闭；PR #10 已合并进 `main`（`1fa1d2e`）

- **S0-05 CI**：**Done**
  - Issue #11 已关闭；PR #12 已合并进 `main`（`0a490aa`）
  - push → main CI：run `34590063714`，Backend success，Admin Web success
  - 交付：`.github/workflows/ci.yml`、`.gitattributes`（LF）

Sprint 0 工程底座：**Done**。

- **S1-01 Master Data Schema**：**Done**
  - Issue #13 已关闭
  - PR #14 已合并进 `main`（`a46a09cd2c636eb2197e6ee01281a940069398bf`）
  - main push CI：run [35330608773](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35330608773)，Backend success，Admin Web success
  - 当前 DB revision：`44f5a70a766a`
  - 交付：7 张主数据表（School / College / Major / AdmissionCatalog / AdmissionCatalogDirection / ExamSubject / AdmissionCatalogExamSubject）；无 ORM `relationship()`

- **S1-02 Read-only Master Data API**：**Done**
  - Issue #15 已关闭
  - PR #16 已合并进 `main`（`936d11f3797a0b692d7f4d47103526954af9febb`）
  - main push CI：run [35441128414](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35441128414)，Backend success，Admin Web success
  - 本机验收：Ruff passed；pytest 88 passed（含 PostgreSQL 集成测试）
  - 交付：7 个 `GET /api/v1` 只读接口；Repository / 薄 Read Service / Pydantic read schemas；backend CI PostgreSQL 18 service

- **Mac Development Environment**：**Accepted**
  - macOS 26.2 / Apple Silicon arm64
  - Python 3.12.14、uv、PostgreSQL 18.6、Node 24、pnpm 12.4
  - backend 与 admin-web 本地 QA 已通过

- **[Governance] Adopt cross-platform development baseline**：**Done**
  - Issue #17 已关闭
  - PR #18 已合并进 `main`（`af5c8d389d1e320ce16b3713cd0eb60210df1d59`）
  - main push CI：run [35508339614](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35508339614)，Backend success，Admin Web success
  - 交付：工程规范 V0.2；当前主要开发机 macOS；macOS / Windows 正式支持本地开发；CI 为 Linux

- **S1-03A Stable Master Data Admin API**：**Done**
  - Issue #23 已关闭
  - PR #24 已合并进 `main`（`9d4b7f113c1fbeebe17aa21752d1c479e20fd488`）
  - main push CI：run [35679480362](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35679480362)，Backend success，Admin Web success
  - 交付：School / College / Major / ExamSubject 的 Admin 读（含 inactive）与 create / patch / status；`get_write_db()`（`scope="function"`）；无 DELETE、无 Catalog 写入、无 migration、无 auth
  - 合同：[`docs/api/s1-03a-stable-master-data-admin-api.md`](./docs/api/s1-03a-stable-master-data-admin-api.md)
  - 学习文档：[`docs/learning/s1-03a-stable-master-data-admin-api.md`](./docs/learning/s1-03a-stable-master-data-admin-api.md)

Sprint 1 **尚未 Done**。S1-03A 已合入 `main`；S1-03B 进行中；Admin Web 尚未开始。

## Ready（未经批准不得自行进入）

- S1-03C Admin Web Master Data UI（依赖 S1-03B）
- S1-04 导入 / 种子数据
- Sprint 2 上岸生基础师资库

## Research Blocked（禁止擅自正式开发）

统一记入 [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)。

## Known Issues

- `pnpm build` 因 Ant Design 体积可能出现 >500kB chunk 提示；当前不阻塞。
- 仍无小程序工程。
- pytest 对 Starlette TestClient / httpx 有 DeprecationWarning（2 条）；当前不阻塞。
- 本地临时查询 / scratch 文件（例如未跟踪的 `.pgsql`）不得误提交。

## 下一里程碑

1. 完成 S1-03B（Issue #27）后再进入 S1-03C
2. 完成内部后台主数据维护后再进入 S1-04
