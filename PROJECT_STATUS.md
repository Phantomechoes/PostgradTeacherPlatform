# 项目状态

最后更新：2026-09-09  
当前版本：V0.1 Foundation（未发布业务版本）  
当前 Sprint：Sprint 0 — 工程底座  
主开发环境：Windows 原生  
GitHub：<https://github.com/Phantomechoes/PostgradTeacherPlatform>

## 正在进行

- **S0-01 Repository Bootstrap**
  - Issue：[ #1](https://github.com/Phantomechoes/PostgradTeacherPlatform/issues/1)
  - 分支：`chore/s0-01-repository-bootstrap`
  - 状态：**S0-01 四个检查点实施完成，等待 commit / push / PR / merge 验收**
  - 说明：本地文件修改已按四个检查点做完，但尚未提交、尚未推送、尚未创建 PR、尚未合并 `main`。按工程规范，此时 **S0-01 还不算 Done**。

## 已完成

- GitHub 仓库已建立，`main` 上有初始提交（仅含一行标题的 `README.md`）。
- 已从 `main` 拉出工作分支 `chore/s0-01-repository-bootstrap`。
- 已建立 S0-01 对应 Issue #1。
- 四个检查点的文件实施（未提交）：根目录工程文件、目录骨架、冻结规范复制、Issue/PR 模板。

## Ready（当前未开始，S0-01 完成后才进入）

- S0-02 Backend Bootstrap：FastAPI、`GET /health`、pytest、Ruff
- S0-03 Database Bootstrap：PostgreSQL、SQLAlchemy、Alembic、环境配置
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

- 目录骨架和规范已就位，但仍没有可运行程序（无 FastAPI、无数据库、无管理后台工程、无小程序工程）。
- 本机未安装 GitHub CLI（`gh`）；创建 PR 需通过浏览器或后续约定方式处理。
- S0-01 尚未 commit / push / 创建 PR / 合并。未经负责人批准，不提交、不推送、不合并。

## 下一里程碑

1. 负责人批准后：`git add` → commit → push 当前 chore 分支 → 创建 PR → 人工 Review → merge `main`。
2. PR 合并进 `main` 且验收通过后，S0-01 才算 Done。
3. 然后才进入 S0-02 Backend Bootstrap。

Sprint 0 全部完成后，才开始 Sprint 1（院校—学院—专业—招生目录—考试科目主数据）。
