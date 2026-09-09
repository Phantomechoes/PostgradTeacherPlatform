# 项目状态

最后更新：2026-09-09  
当前版本：V0.1 Foundation（未发布业务版本）  
当前 Sprint：Sprint 0 — 工程底座  
主开发环境：Windows 原生  
GitHub：<https://github.com/Phantomechoes/PostgradTeacherPlatform>

## 正在进行

- **Refine AGENTS Operational Rules**（仓库治理，不是业务开发）
  - Issue：[ #3](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/3)
  - 分支：`chore/refine-agents-operational-rules`
  - 状态：文件修改进行中（未 commit / push / PR）
  - 目标：Context Loading Order、Repository State > Conversation Memory、Tool / Skill Routing、Mandatory Stop Conditions
  - 明确不做：不改冻结工程规范、不改 Research Blocked 状态、不进入 S0-02

## 已完成

- **S0-01 Repository Bootstrap**：**Done**
  - Issue #1 已关闭；PR #2 已合并进 `main`（`1bae0e5`）
  - 交付：根目录工程文件、目录骨架、冻结规范纳入仓库、Issue/PR 模板
  - 仍无可运行后端 / 后台 / 小程序

## Ready（S0-01 完成后的下一正式开发任务）

- S0-02 Backend Bootstrap：FastAPI、`GET /health`、pytest、Ruff
- S0-03 Database Bootstrap：PostgreSQL、SQLAlchemy、Alembic、环境配置
- S0-04 Admin Bootstrap：React + TypeScript + Vite + Ant Design
- S0-05 CI：backend test / lint、frontend build

本治理 Issue 完成后，下一正式开发任务仍是 **S0-02 Backend Bootstrap**。未经批准不得自行进入。

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

- 目录骨架和规范已就位，但仍没有可运行程序（无 FastAPI、无数据库、无管理后台工程、无小程序工程）。
- 本机未安装 GitHub CLI（`gh`）。
- 本机未配置持久的 Git `user.name` / `user.email`。

## 下一里程碑

1. 完成本治理 Issue（AGENTS.md 精细化）的 commit / push / PR / 负责人验收。
2. 进入 S0-02 Backend Bootstrap（须单独 Issue 与批准）。

Sprint 0 全部完成后，才开始 Sprint 1（院校—学院—专业—招生目录—考试科目主数据）。
