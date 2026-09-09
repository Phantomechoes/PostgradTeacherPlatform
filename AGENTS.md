# AGENTS.md — Grok 开发行为规范 V0.1

你正在参与“考研专业课师资供应平台”项目。

本文件是每次任务前的**操作卡片 + 红线**，不是完整工程手册。  
详细制度见 [`docs/product/开发前工程规范_V0.1.md`](./docs/product/开发前工程规范_V0.1.md)。  
待决策事项见 [`docs/product/DECISIONS_PENDING.md`](./docs/product/DECISIONS_PENDING.md)。

## 最高优先级

1. GitHub 是唯一事实源。
2. **Repository State > Conversation Memory**：旧聊天不能覆盖当前真实仓库状态。
3. main 必须始终稳定，禁止直接开发。
4. 一个 Issue 对应一个主要 feature/fix/docs/chore 分支。
5. **先解释，再修改。**
6. 未经项目负责人明确回复“开始/继续/按方案做”，不得修改文件、安装依赖、提交、push 或执行数据库变更。
7. 默认将任务拆成 2～5 个检查点，每个检查点结束后停止并汇报，等待“继续”。
8. 调研尚未确认的业务规则不得写死。
9. 不得自行进入下一 Sprint。
10. 不得自行合并 PR。
11. 不得隐藏测试失败、命令失败或风险。
12. 不得 silent scope expansion：发现新的独立问题，新建 Issue，不顺手扩大当前任务。

## 每次任务开始：Required Context Loading Order

先声明：“我现在只检查，不修改文件。”

按此顺序确认（不得只凭旧聊天直接改代码）：

1. `AGENTS.md`（本文件）
2. `PROJECT_STATUS.md`
3. Git：`git status`、`git branch --show-current`、`git log -5 --oneline`、`git remote -v`、`git fetch`
4. 当前 GitHub Issue
5. 与任务直接相关的 docs
6. 若涉及产品规则：`docs/product/DECISIONS_PENDING.md`
7. 若涉及已有模块：对应 README / docs / tests / 实现代码

聊天上下文与当前仓库冲突时，以当前仓库为准。  
仓库文档自身冲突时：**停止并报告负责人**，不得猜测哪个版本正确。

## 冲突时以谁为准

信息冲突时优先级：

1. 当前实际 Git / GitHub 状态
2. 当前仓库中的冻结规范 / ADR / `PROJECT_STATUS.md`
3. 当前 Issue 已确认范围
4. 当前任务中负责人最新明确指令
5. 历史聊天上下文 / Agent 记忆

若 1～4 之间互相冲突：停止询问，不得自行决定。

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

## Tool / Skill Routing

不得虚构、写死当前环境里不存在的 Skill 名称。

若环境提供与任务匹配的 Skill / Tool：

1. 先发现当前**实际可用**能力；
2. 阅读其说明；
3. 确认适用于当前任务；
4. 再按其要求执行。

没有对应能力时：按本仓库规范 + 普通工具执行。

按任务类型路由（细节以工程规范为准，此处只指路）：

### Git / GitHub

涉及 Issue、Branch、Commit、Push、PR、Merge、GitHub Actions / CI 时：优先使用 Git / GitHub 对应能力。  
本地以实际 `git` 状态为准；远端以 GitHub 实际状态为准。  
Merge、删除远端分支、force push 等高影响操作必须额外批准。

### Python Backend

涉及 Python、uv、FastAPI、Pydantic、pytest、Ruff、Python 依赖时：先检查 `backend/` 现有配置与工程规范。  
不得绕过项目依赖管理擅自全局装包。新增核心依赖前必须说明：为什么需要、现有依赖够不够、对项目有何影响。

### Database

涉及 PostgreSQL、SQLAlchemy、Alembic、Model、Schema、Migration 时：先检查当前 Model、migration 状态、数据影响、兼容性。  
流程：`Model → Alembic migration → 人工阅读 → 执行 → 测试`。  
删除表/列、不可逆 migration、数据清洗必须额外确认。

### Frontend / Admin / Mini-program

涉及 React、TypeScript、Vite、Ant Design、微信小程序、TDesign 时：先确认该模块已进入允许开发的 Sprint。  
**不得因为目录已经存在就擅自初始化框架。**

### Documentation

涉及产品边界、架构、数据库、API、重大技术决定、模块完成时：判断是否同步  
`docs/product/`、`docs/architecture/`、`docs/database/`、`docs/api/`、`docs/decisions/`、`docs/learning/`。

### Research-Blocked Logic

任务触及 `docs/product/DECISIONS_PENDING.md` 中仍为 Research Blocked 的事项时：

- 正式业务实现必须停止。
- 允许：技术可行性调研、数据模型候选、接口草案、明确标注“非正式规则”的 Mock / Prototype、提出待决策方案。
- 不允许：自行选一个方案写入正式业务逻辑，或把假设包装成已确认需求。

## Mandatory Stop Conditions

出现以下任意情况必须停止，向负责人报告。停后只解释问题、影响和可选方案，**不得为了把任务做完而自行选择高风险路径。**

- 当前 branch 与任务预期不一致
- 在 main 上准备进行开发修改
- 工作区存在来源不明的未提交修改
- 当前 Issue 与实际修改范围不一致，或需要扩大 Issue Scope
- 发现未知文件准备被覆盖或删除
- 需要 force push、reset --hard、改写历史、删除分支
- 需要破坏性数据库 migration 或删除数据
- 发现真实密码 / Token / `.env` / 敏感信息
- 任务触及 Research Blocked 业务逻辑（正式实现）
- 测试失败且无法确认原因，或需要跳过 / 伪造测试
- 需要新增未经批准的核心依赖，或改变冻结技术栈 / 冻结工程规范
- 当前仓库文档互相冲突
- 远端状态与本地预期不一致
- 无法明确判断某项操作是否会影响 main 或用户数据

未经明确批准同样禁止：直接改 main、合并 PR、覆盖未知修改。

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
