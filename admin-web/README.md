# admin-web

这里是**内部管理后台**：给项目内部人员用的网页，不是给考研生用的小程序。

第一阶段后台优先于完整小程序，用来做内部数据管理、调研录入，以及后续的人工筛选。原则是：先可用，再美化；页面要有加载中 / 失败 / 空数据状态；前端不复制后端业务逻辑。

## S0-04 当前是什么

当前阶段（S0-04）已建立 Windows 原生可运行的 React + TypeScript + Vite 工程：

- 包管理器：pnpm 12（由 Node.js 自带 Corepack 启用）
- UI 组件库：Ant Design 6
- 单页内部后台壳（无 React Router）
- ESLint + Prettier
- 页面上的 Loading / Error / Empty 是**静态 UI 演示**，不是真实请求

`package.json` 已声明：

- `engines.node`: `>=24 <25`
- `packageManager`: `pnpm@12.4.0`

## 当前没有什么业务能力

- 没有登录 / 认证
- 没有 School / Teacher / Institution 等业务 CRUD
- 没有 React Router
- 没有 API client，不调用后端（包括不调用 `GET /health`）
- 不连接 PostgreSQL
- 没有 CI、Docker、小程序

Ant Design 只提供按钮、布局、提示等 UI 零件。业务规则仍在后端；本阶段后台不复制、不实现业务逻辑。

本仓库的 `admin-web/` **没有** `.env`，也没有需要保密的前端环境变量。

## 前置条件（Windows 原生）

需要：

- Git for Windows
- **Node.js 24 LTS**（`node --version` 应为 `v24.x`）
- 用 Node 自带 **Corepack** 启用 **pnpm 12**

不要求把 Node 装到某个固定盘符。下面是**当前这台开发机**的实际路径，不是项目强制安装路径：

| 项            | 当前开发机实际值     |
| ------------- | -------------------- |
| Node 安装目录 | `E:\DevTools\NodeJS` |
| 实测 Node     | v24.21.0             |
| 实测 npm      | 11.19.0              |
| 实测 Corepack | 0.36.0               |
| 实测 pnpm     | 12.4.0               |

其他开发者按自己的 Node 24 安装位置使用即可。

本次本机安装中遇到过、可参考但**不是强制前提**的两点：

- PowerShell 可能因 ExecutionPolicy 拦截 `npm.ps1`。当前用户可使用 `RemoteSigned`；不要要求所有人改系统级策略。
- `corepack enable` 若要对 Node 安装目录写文件，可能需要管理员 PowerShell。

不要用 `npm install -g pnpm` 绕过 Corepack。

## 进入 admin-web/

```powershell
cd E:\Projects\PostgradTeacherPlatform\admin-web
```

仓库若 clone 在别处，把路径换成实际的 `...\PostgradTeacherPlatform\admin-web`。

确认工具：

```powershell
node --version
pnpm --version
```

应看到 `v24.x` 与 `12.x`。

## 安装依赖

```powershell
pnpm install
```

会按 `pnpm-lock.yaml` 安装到本目录 `node_modules/`。`node_modules/` 只存在于本机，已写入 `.gitignore`，不要提交。

若要校验 lockfile 与 `package.json` 一致、不允许改 lockfile：

```powershell
pnpm install --frozen-lockfile
```

## 开发服务器

```powershell
pnpm dev --host 127.0.0.1 --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173
```

期望：页面能渲染内部管理后台壳，并看到 Loading / Error / Empty 三个静态演示卡片。这是工程验证页，不是正式业务后台。

用完后在运行窗口按 `Ctrl+C` 停止，不要留下占用 5173 的本项目进程。

## 生产构建

```powershell
pnpm build
```

成功后会生成 `dist/`（已 gitignore，不要提交）。Ant Design 体积较大，构建时可能出现 chunk 超过 500kB 的提示；当前阶段视为非阻塞，不要为此引入路由拆包或分析工具。

查看构建结果：

```powershell
pnpm preview --host 127.0.0.1
```

这只是本地查看 `dist/`，不是部署配置。用完后停止 preview 进程。

## 代码检查与格式

```powershell
pnpm lint
pnpm format:check
```

自动按 Prettier 改写（会改工作区文件）：

```powershell
pnpm format
```

期望：`pnpm lint` 无 error；`pnpm format:check` 全部匹配 Prettier。

## Secret 与提交注意

- 不要提交 `node_modules/`、`dist/`、`.env`、密码、Token。
- 本模块当前没有真实 `DATABASE_URL` 或 API Key。
- 后台不连接 backend / PostgreSQL；启动本页面不需要数据库。
