# 项目状态

最后更新：2026-10-05
当前版本：V0.1 Foundation（未发布业务版本）；工程规范当前为 V0.2
当前 Sprint：Sprint 2 — 上岸生基础师资库
当前主要开发机：macOS Apple Silicon
已验证本地环境：macOS 原生、Windows 原生
CI：Linux / GitHub Actions
GitHub：<https://github.com/Phantomechoes/PostgradTeacherPlatform>

## 正在进行

- **S2-02 Teacher Admin API**：**In Progress（Checkpoint 3B）**
  - Implementation Issue [#45](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/45)
  - Planning Issue [#44](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/44)：**Frozen / CLOSED**
  - API-D1～API-D18 已冻结（含负责人修正后的 API-D7）
  - 当前 checkpoint：Checkpoint 3B — full API integration/regression + transaction boundary + learning
  - Checkpoint 3C（final full QA + PR）须 Owner / Reviewer 验收 3B 后明确批准
  - 无 migration；无 Admin Teacher Web；无 Public Teacher API；无 auth

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

- **S1-03B AdmissionCatalog Admin API**：**Done**
  - Issue #27 已关闭；PR #28 已合并进 `main`（`2ec1cca775a505ddc6eba954e9c6cc7ab5e674bc`）
  - main push CI：run [35689060992](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35689060992)，Backend success，Admin Web success
  - 本机验收：pytest 168 passed；Alembic `44f5a70a766a`；无 migration
  - 交付：2 GET、1 POST inactive shell、1 aggregate PUT、1 status PATCH；聚合事务与显式 activate；无 DELETE、无 row-level child REST；公开 S1-02 合同未改
  - 合同：[`docs/api/s1-03b-admission-catalog-admin-api.md`](./docs/api/s1-03b-admission-catalog-admin-api.md)
  - 学习文档：[`docs/learning/s1-03b-admission-catalog-admin-api.md`](./docs/learning/s1-03b-admission-catalog-admin-api.md)

- **S1-03C Admin Web Master Data UI**：**Done**
  - Issue #31 已关闭；PR #32 已合并进 `main`（`77cd73070e4dd02e439c26b33aebc19b1ed3e56e`）
  - main push CI：run [35740244211](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/35740244211)，Backend success，Admin Web success
  - 交付：React Router 与内部后台布局；原生 fetch API Client；Vite `/api` 开发代理；School / College / Major 维护；全国统考及学校自命题科目维护；Catalog 列表与筛选；inactive shell 创建；完整 aggregate PUT；显式公开与取消公开；错误处理和真实浏览器联调
  - 只新增 `react-router-dom`；无后端改动、无 migration；未引入 auth / RBAC
  - 学习文档：[`docs/learning/s1-03c-admin-web.md`](./docs/learning/s1-03c-admin-web.md)

- **S1-04 Master Data Import & Seed Data**：**Done**
  - Issue #35 已关闭；PR #36 已合并进 `main`（`1c3aee7e9b779226e7bc4afb6ac102107f1af8c3`）
  - main push CI：run [37181033025](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/37181033025)，Backend success，Admin Web success
  - 交付：UTF-8 JSON + sidecar manifest；默认 dry-run；synthetic + approved 显式 `--apply`；business-key import；create / equivalent skip / different reject；Stable Master Data apply；Catalog inactive shell + complete aggregate；never auto publish；whole-file transaction；rollback flushed writes；canonical synthetic development seed；PostgreSQL importer tests；无 migration；无新依赖
  - 合同：[`docs/import/s1-04-import-format.md`](./docs/import/s1-04-import-format.md)
  - 学习文档：[`docs/learning/s1-04-master-data-import-and-seed.md`](./docs/learning/s1-04-master-data-import-and-seed.md)

Sprint 1 — 院校招生主数据：**Done**。S1-01、S1-02、S1-03A、S1-03B、S1-03C、S1-04 均已合入 `main`。Sprint 1 已形成 Schema → Public Read API → Admin Write API → Admin Web → Import / Seed 的完整院校招生主数据闭环。

- **S2-01 Teacher Data Schema**：**Done**
  - Issue #40 已关闭；PR #41 已合并进 `main`（`5508e55dfaf341a7cc8ac5872f5a0c067b130258`）
  - main push CI：run [37205327226](https://github.com/Phantomechoes/PostgradTeacherPlatform/actions/runs/37205327226)，Backend success，Admin Web success
  - Alembic：`695107900fc3`
  - 交付：3 张新业务表 `teacher_profiles` / `admission_records` / `teacher_teach_subjects`；TeacherProfile（`availability_status` / `verification_status`）；AdmissionRecord（成功录取事实、optional AdmissionCatalog 链接、School / College / Major same-school constraints、`NUMERIC(8,2)` 结构化总分、`is_active`）；TeacherTeachSubject（显式可教授科目，不自动生成）；无 ORM `relationship()`；无联系方式 / 认证材料；无 Teacher API / Admin Teacher UI / Public Teacher API
  - 设计：[`docs/database/s2-01-teacher-data-schema.md`](./docs/database/s2-01-teacher-data-schema.md)
  - ADR：[`docs/decisions/ADR-0002-sprint2-teacher-foundation-model.md`](./docs/decisions/ADR-0002-sprint2-teacher-foundation-model.md)
  - 学习文档：[`docs/learning/s2-01-teacher-data-schema.md`](./docs/learning/s2-01-teacher-data-schema.md)

Sprint 2 — 上岸生基础师资库：**In Progress**。S2-01 已完成。S2-02 正在实施 Checkpoint 3B。整个 Sprint 2 尚未 Done。

## Ready（未经批准不得自行进入）

- S2-02 Checkpoint 3C — final full QA + PR；须 Owner / Reviewer 验收 3B 后明确批准
- 不得自行进入 Admin Teacher Web / Public Teacher API / S2-03

## Research Blocked（禁止擅自正式开发）

统一记入 [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)。

## Known Issues

- `pnpm build` 因 Ant Design 体积可能出现 >500kB chunk 提示；当前不阻塞。
- 仍无小程序工程。
- pytest 对 Starlette TestClient / httpx 有 DeprecationWarning（2 条）；当前不阻塞。
- 本地临时查询 / scratch 文件（例如未跟踪的 `.pgsql`）不得误提交。

## 下一里程碑

1. S2-02 Checkpoint 3B 验收（full API integration/regression + transaction boundary + learning）
2. Checkpoint 3C 须 Owner / Reviewer 验收 3B 后明确批准
3. 不得自行进入 Admin Teacher Web / Public Teacher API / S2-03
