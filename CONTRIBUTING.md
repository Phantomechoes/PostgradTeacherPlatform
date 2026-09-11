# 如何参与本项目

本文说明人和开发 Agent 应如何向本仓库贡献改动。  
完整工程规范：[`docs/product/开发前工程规范_V0.1.md`](./docs/product/开发前工程规范_V0.1.md)。  
给 Agent 的短规范：[`AGENTS.md`](./AGENTS.md)。  
调研尚未确认的事项：[`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)。

当前对应任务：[Issue #7 — S0-03 Database Bootstrap](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/7)。

## 必须遵守的原则

1. GitHub 是唯一事实源。
2. 不要直接在 `main` 上开发。`main` 必须始终可理解、可回滚。
3. 原则上：**没有 GitHub Issue，不开发。**
4. 一个 Issue 对应一个主要分支、一个可验收目标。
5. 先解释，再修改。未经项目负责人明确回复“开始 / 继续 / 按方案做”，不得改文件、安装依赖、提交、push 或执行数据库变更。
6. 调研尚未确认的业务规则不得写死。
7. 不要把 `.env`、密码、Token、真实数据库口令或未授权敏感资料提交进仓库。

## 开始一个任务前

先做只读检查，不要改文件：

```text
git status
git branch --show-current
git log -5 --oneline
git remote -v
```

确认：

- 当前不在 `main` 上开发；
- 工作区没有来源不明的未提交修改；
- 即将修改的内容属于当前 Issue。

若发现未知未提交修改：**立即停止，不得覆盖。**

## Issue

新工作先开 GitHub Issue。开发任务使用 [`.github/ISSUE_TEMPLATE/development_task.md`](./.github/ISSUE_TEMPLATE/development_task.md)；真实缺陷使用 [`.github/ISSUE_TEMPLATE/bug_report.md`](./.github/ISSUE_TEMPLATE/bug_report.md)。Issue 至少写清：

- 背景
- 当前阶段依据（为什么现在可以做，是否受调研阻塞）
- 目标
- 明确不做的事
- 验收条件
- 影响范围：backend / admin-web / miniprogram / database / docs / ci
- 负责人验收后应理解的 3 件事

当前被调研阻塞、禁止擅自正式开发的内容包括：支付、佣金结算、自动推荐、完整机构端、完整考研生端、学生选师、试听、换师、SLA 正式规则、合同/发票、IM、自动抓取个人联系方式。  
这些事项统一记入 [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)。

## 分支

只保留长期稳定主分支：`main`。

功能分支命名：

```text
feature/<issue-id>-<short-name>
fix/<issue-id>-<short-name>
docs/<issue-id>-<short-name>
chore/<issue-id>-<short-name>
```

示例：

```text
chore/s0-01-repository-bootstrap
feature/21-school-model
fix/34-school-search
docs/40-interview-v1
```

发现新的独立问题，应新建 Issue 和新分支，不要在当前 PR 里顺手扩大范围。

## 提交说明

采用简化 Conventional Commits：

```text
feat: ...
fix: ...
docs: ...
test: ...
refactor: ...
chore: ...
ci: ...
```

禁止无意义信息，例如 `update`、`change`、`fix stuff`。

未经项目负责人明确批准，禁止：

- 直接提交 `main`
- `git push --force`
- `git reset --hard`
- 改写历史
- 删除未知分支
- 覆盖他人工作
- 由开发 Agent 自行合并 Pull Request

## Pull Request

每个 PR 必须对应一个 Issue。开 PR 时使用 [`.github/pull_request_template.md`](./.github/pull_request_template.md)。PR 至少写清：

- 对应 Issue
- 做了什么，为什么这么做
- 本次明确没有做什么
- 修改了哪些文件
- 数据库 / API 有没有变化
- 如何在 Windows 上手工验收
- 自动测试的真实命令和结果（没有测试时如实写“本阶段无自动测试”）
- 项目负责人需要理解的 3 个概念
- 风险与已知限制

代码完成不等于任务完成。还需要文档、解释、负责人验收，以及批准后的合并。

## Windows 开发注意

- 主开发环境是 Windows 原生，不把 WSL 或容器当成当前前提。
- 文本文件使用 UTF-8；换行与缩进以 [`.editorconfig`](./.editorconfig) 为准。
- 本地密钥只放在 `.env`，仓库只提交 `.env.example`。真实数据库口令不得进入 Git / Issue / PR。
- 后端使用 uv 管理的 Python 3.12；不要使用 Anaconda 或系统 Python 作为本项目解释器。
- FastAPI / SQLAlchemy / Alembic 使用应用角色 `postgrad_teacher_platform_app`，不要使用 `postgres` 超级用户作为日常 `DATABASE_URL`。

## 当前阶段不要做的事

Sprint 0 尚未完成前，不要开始：

- FastAPI 业务接口（S0-02 只有 `/health`；业务 API 留给后续 Sprint）
- 业务数据库表（S0-03 只有 Alembic baseline / `alembic_version`）
- 管理后台页面（属于 S0-04）
- CI 工作流（属于 S0-05）
- 被调研阻塞的业务功能
