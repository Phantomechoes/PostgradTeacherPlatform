# .github

这里**不是业务代码目录**。它是 GitHub 平台自己会读取的配置区。

GitHub 看到这个目录后，才会知道：

- 开 Issue 时用哪套模板（`ISSUE_TEMPLATE/`）
- 开 Pull Request 时用哪套模板（`pull_request_template.md`）
- 代码推送后自动跑哪些检查（`workflows/`）

S0-05 CI 已存在（`.github/workflows/ci.yml`）：

- Backend：Ubuntu、PostgreSQL 18、`uv sync --locked`、Ruff、Alembic、pytest
- Admin Web：Ubuntu、Node 24、Corepack / pnpm、frozen install、lint、format:check、build

CI 使用 Linux，不表示开发者必须使用 Linux。本机开发支持 macOS 与 Windows。本任务不修改 `ci.yml` 的运行策略。

不要把后端、后台或小程序的功能代码放在这里。
