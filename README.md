# 考研专业课师资供应平台

仓库名：`PostgradTeacherPlatform`

这是一个面向考研专业课的师资供应平台。当前目标不是马上做出完整小程序，而是先建立一个可以长期维护的 GitHub 工程底座，再按阶段补上后端、数据库、内部管理后台和小程序骨架。

GitHub 是本项目的唯一事实源：代码、Issue、文档和状态都以本仓库为准。

- 仓库地址：<https://github.com/Phantomechoes/PostgradTeacherPlatform>
- 当前任务：S0-02 Backend Bootstrap（[Issue #5](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/5)）
- 当前工作分支：`feature/5-backend-bootstrap`

## 现在做到哪一步

当前阶段：**V0.1 Foundation（工程底座） / Sprint 0**。

Sprint 0 只做工程底座，按顺序分为：

| 编号 | 内容 | 状态 |
|---|---|---|
| S0-01 | 仓库起步：目录、说明文档、协作规范、Issue/PR 模板 | Done |
| S0-02 | 后端骨架：FastAPI、健康检查、测试与代码检查 | 实现完成，待提交 / PR |
| S0-03 | 数据库：PostgreSQL、SQLAlchemy、Alembic | 未开始 |
| S0-04 | 内部管理后台骨架 | 未开始 |
| S0-05 | 持续集成（CI） | 未开始 |

更细的进度见 [`PROJECT_STATUS.md`](./PROJECT_STATUS.md)。

## 现在还没有什么

请先按这个预期来看仓库，避免误以为已经可以运行业务系统：

- 已有最小 FastAPI 应用与 `GET /health`，尚无业务 API
- 还没有数据库和迁移
- 还没有管理后台页面
- 还没有微信小程序工程
- 还没有支付、佣金、自动推荐、学生选师等业务功能

这些不是遗漏，而是按冻结的 V0.1 边界，有意留到后续 Sprint。

## 当前仓库里有什么

Checkpoint 1 建立了根目录说明和协作文件。Checkpoint 2 已建立目录骨架（只有说明文件，没有可运行代码）。

现在可以直接阅读：

| 文件 | 用途 |
|---|---|
| [`README.md`](./README.md) | 项目入口，说明现在到哪一步 |
| [`AGENTS.md`](./AGENTS.md) | 开发 Agent 每次任务必须先读的短规范 |
| [`PROJECT_STATUS.md`](./PROJECT_STATUS.md) | 当前 Sprint、进行中任务和阻塞项 |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | 如何开 Issue、开分支、提 Pull Request |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本变化记录 |
| [`docs/product/开发前工程规范_V0.1.md`](./docs/product/开发前工程规范_V0.1.md) | 完整工程规范（V0.1 冻结基线） |
| [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md) | 调研尚未确认、禁止写死的事项 |
| [`.gitignore`](./.gitignore) | 哪些文件不允许提交到 GitHub |
| [`.editorconfig`](./.editorconfig) | 统一编辑器的缩进和换行 |
| [`.github/ISSUE_TEMPLATE/development_task.md`](./.github/ISSUE_TEMPLATE/development_task.md) | 开发任务 Issue 模板 |
| [`.github/ISSUE_TEMPLATE/bug_report.md`](./.github/ISSUE_TEMPLATE/bug_report.md) | 缺陷报告 Issue 模板 |
| [`.github/pull_request_template.md`](./.github/pull_request_template.md) | Pull Request 审查模板 |

## 当前目录结构（骨架已建立）

以下结构来自已冻结的 V0.1 工程规范。`backend/` 已可运行最小 FastAPI；管理后台和小程序仍只有占位说明：

```text
PostgradTeacherPlatform/
├─ backend/            后端（S0-02 起才放 FastAPI 代码）
├─ admin-web/          内部管理后台（S0-04）
├─ miniprogram/        微信小程序（后续阶段）
├─ docs/               产品、调研、架构、数据库、学习文档
│  └─ product/         工程规范与待决策事项
├─ scripts/            Windows 辅助脚本
├─ .github/            Issue / PR 模板；CI 留给 S0-05
├─ AGENTS.md
├─ README.md
├─ PROJECT_STATUS.md
├─ CONTRIBUTING.md
├─ CHANGELOG.md
├─ .gitignore
└─ .editorconfig
```

不在本任务中新增 `docs/governance/` 或其他治理类目录。

## 当前技术栈（已冻结，尚未落地）

这些选择已经冻结。S0-02 已落地 Python 3.12 + uv + 最小 FastAPI（`GET /health`）。SQLAlchemy、PostgreSQL、管理后台、小程序尚未落地：

- 后端：Python 3.12、FastAPI、SQLAlchemy 2.x、Alembic、Pydantic、PostgreSQL、pytest、Ruff
- 管理后台：React、TypeScript、Vite、Ant Design、pnpm、ESLint、Prettier
- 小程序：微信原生小程序、TypeScript、TDesign Miniprogram
- 主开发环境：Windows 原生

## 在 Windows 上如何开始

1. 用 Git 打开本仓库，开发时不要直接改 `main`。当前工作分支是 `feature/5-backend-bootstrap`。
2. 先读本文件和 [`PROJECT_STATUS.md`](./PROJECT_STATUS.md)。
3. 启动后端、访问 `/health`、跑 pytest / Ruff：见 [`backend/README.md`](./backend/README.md)。
4. 若要提需求或改代码，按 [`CONTRIBUTING.md`](./CONTRIBUTING.md) 先开 GitHub Issue，再开对应分支。
5. 不要把 `.env`、密码、Token 或真实数据库口令提交进仓库。

管理后台和小程序当前仍不能启动。

## 协作原则（摘要）

- 先解释，再修改；一个任务一个分支；`main` 始终保持稳定。
- 原则上：没有 GitHub Issue，不开发。
- 调研尚未确认的业务规则不得写死。被阻塞的事项统一记入 [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)。
- 开发 Agent 必须分检查点推进，未经负责人明确回复“开始 / 继续”，不得修改文件、提交或 push。

完整规则见 [`AGENTS.md`](./AGENTS.md) 与 [`docs/product/开发前工程规范_V0.1.md`](./docs/product/开发前工程规范_V0.1.md)。
