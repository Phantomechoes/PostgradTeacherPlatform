# 项目状态

最后更新：2026-09-19
当前版本：V0.1 Foundation（未发布业务版本）
当前 Sprint：Sprint 1 — 院校招生主数据
主开发环境：Windows 原生
GitHub：<https://github.com/Phantomechoes/PostgradTeacherPlatform>

## 正在进行

- **S1-02 Read-only Master Data API**
  - Issue：[ #15](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/15)
  - 分支：`feature/15-master-data-read-api`
  - 状态：In Progress / implementation complete, awaiting PR review / merge
  - 目标：只读 Repository、薄 Read Service、Pydantic read schemas、`GET /api/v1` 查询接口、PostgreSQL 集成测试、backend CI PostgreSQL service
  - 明确不做：写接口、Admin CRUD、Teacher / Institution / Candidate、支付、推荐、seed/import、爬虫、auth、`relationship()`、AsyncSession、新业务 migration、`include_inactive`

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

Sprint 1 **尚未 Done**。Schema 已合入 `main`；只读 API 实现完成，等待 PR 审查。

## Ready（S1-02 之后，未经批准不得自行进入）

- S1-03 内部后台主数据维护（Admin master data CRUD）
- S1-04 导入 / 种子数据
- Sprint 2 上岸生基础师资库

## Research Blocked（禁止擅自正式开发）

统一记入 [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)。

## Known Issues

- `pnpm build` 因 Ant Design 体积可能出现 >500kB chunk 提示；当前不阻塞。
- 仍无小程序工程。
- pytest 对 Starlette TestClient / httpx 有 DeprecationWarning（2 条）；当前不阻塞。
- 本机未安装 GitHub CLI（`gh`）。
- 仓库根目录可能出现 VS Code PostgreSQL Workbench 的未跟踪 `.pgsql` 查询文件，不要提交。

## 下一里程碑

1. 完成 S1-02 只读主数据 API 的 PR 审查与合并（尚未 merge）。
2. 再进入 S1-03 Admin CRUD（须单独 Issue 与批准）。
