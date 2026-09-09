# Changelog

本文件记录项目的可见变化。  
当前处于 V0.1 Foundation（工程底座）阶段，尚未发布面向用户的业务版本。

## [Unreleased]

### Added

- S0-01 仓库起步（[Issue #1](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/1)），工作分支 `chore/s0-01-repository-bootstrap`：
  - 根目录说明与协作文件：`README.md`、`CONTRIBUTING.md`、`PROJECT_STATUS.md`、`CHANGELOG.md`、`.gitignore`、`.editorconfig`
  - 目录骨架：`backend/`、`admin-web/`、`miniprogram/`、`docs/`、`scripts/`、`.github/`（仅占位说明，无可运行代码）
  - 冻结规范纳入仓库：`AGENTS.md`、`docs/product/开发前工程规范_V0.1.md`、`docs/product/DECISIONS_PENDING.md`
  - GitHub Issue / PR 模板：`.github/ISSUE_TEMPLATE/development_task.md`、`.github/ISSUE_TEMPLATE/bug_report.md`、`.github/pull_request_template.md`
  - S0-01 已通过 [PR #2](https://github.com/Phantomechoes/PostgradTeacherPlatform/pull/2) 合并进 `main`（Done）

### Changed

- 精细化根目录 `AGENTS.md` 操作规则（[Issue #3](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/3)）：Context Loading Order、冲突优先级、Tool / Skill Routing、Mandatory Stop Conditions。不改冻结工程规范，不改 Research Blocked 状态。
