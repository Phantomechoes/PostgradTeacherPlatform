# AGENTS.md — Grok 开发行为规范 V0.1

你正在参与“考研专业课师资供应平台”项目。

## 最高优先级

1. GitHub 是唯一事实源。
2. main 必须始终稳定，禁止直接开发。
3. 一个 Issue 对应一个主要 feature/fix/docs 分支。
4. **先解释，再修改。**
5. 未经项目负责人明确回复“开始/继续/按方案做”，不得修改文件、安装依赖、提交、push 或执行数据库变更。
6. 默认将任务拆成 2～5 个检查点，每个检查点结束后停止并汇报，等待“继续”。
7. 调研尚未确认的业务规则不得写死。
8. 不得自行进入下一 Sprint。
9. 不得自行合并 PR。
10. 不得隐藏测试失败、命令失败或风险。

## 每次任务开始

先声明：“我现在只检查，不修改文件。”

检查：
- `git status`
- `git branch --show-current`
- `git log -5 --oneline`
- `git remote -v`
- `git fetch`

阅读：
- `AGENTS.md`
- `PROJECT_STATUS.md`
- 当前 Issue
- 与任务直接相关的代码/文档

若发现未知未提交修改，立即停止。

## 修改前必须输出

【本次任务】  
【为什么现在做】  
【现有程序结构】  
【计划修改的文件】  
【程序执行流程】  
【本次明确不做】  
【风险】  
【验收方式】  
【检查点划分】

等待项目负责人批准。

## 修改中

- 只修改当前 Issue 必需文件；
- 不做顺手重构；
- 不更换核心技术栈；
- 不升级核心依赖大版本；
- 不引入无必要依赖；
- 不执行不可逆操作；
- 不删除未知文件；
- 不覆盖他人工作；
- 每个检查点结束必须汇报并停止。

## 修改完成必须提供

【完成内容】  
【验收条件】  
【修改文件】  
【完整程序流程】  
【数据库变化】  
【API 变化】  
【Windows 运行方式】  
【手动验收】  
【自动测试真实结果】  
【负责人需要理解的 3 个概念】  
【已知限制】  
【下一 Issue 建议】

不得自动继续。

## Git 禁止项

未经明确批准禁止：直接改 main、force push、reset --hard、改写历史、删除分支、合并 PR、覆盖未知修改。

## 数据库

任何 Schema 修改必须遵循：

`Model → Alembic migration → 人工阅读 migration → 执行 → 测试`

可能丢数据的 migration 必须再次请求明确确认。

## 敏感信息

不得提交 `.env`、密码、Token、真实数据库口令、身份证、未授权成绩单、未授权访谈录音/截图、公司内部敏感资料。日志不得打印敏感信息。

## 当前业务边界

未经解锁禁止正式开发：支付、佣金结算、自动推荐、完整机构端、完整考研生端、学生选师、试听、换师、SLA 正式规则、合同/发票、IM、自动抓取个人联系方式。

统一进入：`docs/product/DECISIONS_PENDING.md`。

## 当前技术栈

后端：Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic + Pydantic + PostgreSQL + pytest + Ruff  
后台：React + TypeScript + Vite + Ant Design + pnpm + ESLint + Prettier  
小程序：微信原生小程序 + TypeScript + TDesign Miniprogram  
主开发环境：Windows 原生。
