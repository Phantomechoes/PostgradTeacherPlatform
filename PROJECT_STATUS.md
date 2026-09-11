# 项目状态

最后更新：2026-09-11
当前版本：V0.1 Foundation（未发布业务版本）  
当前 Sprint：Sprint 0 — 工程底座  
主开发环境：Windows 原生  
GitHub：<https://github.com/Phantomechoes/PostgradTeacherPlatform>

## 正在进行

- **S0-03 Database Bootstrap**
  - Issue：[ #7](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/7)
  - 分支：`feature/7-database-bootstrap`
  - 状态：implementation complete，awaiting Git submission / PR review（尚未 merge，因此不是 Done）
  - 目标：PostgreSQL 18.x、SQLAlchemy 2.x、Alembic、pydantic-settings、`.env.example`、Windows 数据库说明
  - 本机开发库：`listen_addresses = localhost`（不对外网卡监听）
  - 明确不做：业务表 / CRUD、登录、推荐、支付、React、小程序、Docker、CI、Research Blocked 逻辑

## 已完成

- **S0-01 Repository Bootstrap**：**Done**
  - Issue #1 已关闭；PR #2 已合并进 `main`（`1bae0e5`）
  - 交付：根目录工程文件、目录骨架、冻结规范纳入仓库、Issue/PR 模板

- **Refine AGENTS Operational Rules**：**Done**
  - Issue #3 已关闭；PR #4 已合并进 `main`（`03ce647`）
  - 交付：Context Loading Order、Repository State > Conversation Memory、Tool / Skill Routing、Mandatory Stop Conditions
  - 未改冻结工程规范，未改 Research Blocked 状态

- **S0-02 Backend Bootstrap**：**Done**
  - Issue #5 已关闭；PR #6 已合并进 `main`（`deba8df`）
  - 交付：Python 3.12 + uv、FastAPI、`GET /health`、pytest、Ruff、Windows 后端运行说明

## Ready（S0-03 之后，未经批准不得自行进入）

- S0-04 Admin Bootstrap：React + TypeScript + Vite + Ant Design
- S0-05 CI：backend test / lint、frontend build

## Research Blocked（禁止擅自正式开发）

统一记入 [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)：

- 在线支付
- 推荐费 / 抽成 / 佣金结算
- 自动推荐算法
- 完整机构端
- 完整考研生端
- 学生自主选师
- 试听规则、换师规则、SLA 正式规则
- 合同 / 发票、平台代收代付
- 站内 IM
- 复杂风控评分
- 自动爬取或反查个人联系方式

## Known Issues

- S0-03 实现已完成，但尚未 commit / push / PR / merge，因此还不能标 Done。
- 仍无管理后台工程、小程序工程。
- pytest 对 Starlette TestClient / httpx 有 DeprecationWarning（2 条）；当前不阻塞。
- 本机未安装 GitHub CLI（`gh`）。

## 下一里程碑

1. 将 S0-03 提交、push、开 PR；merge 进 `main` 后才把 S0-03 标为 Done。
2. 进入 S0-04 Admin Bootstrap（须单独 Issue 与批准）。

Sprint 0 全部完成后，才开始 Sprint 1（院校—学院—专业—招生目录—考试科目主数据）。
