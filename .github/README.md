# .github

这里**不是业务代码目录**。它是 GitHub 平台自己会读取的配置区。

GitHub 看到这个目录后，才会知道：

- 开 Issue 时用哪套模板（`ISSUE_TEMPLATE/`）
- 开 Pull Request 时用哪套模板（`pull_request_template.md`）
- 代码推送后自动跑哪些检查（`workflows/`，真正的 CI 留给 **S0-05**）

不要把后端、后台或小程序的功能代码放在这里。
