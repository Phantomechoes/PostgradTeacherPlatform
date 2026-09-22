# admin-web

这里是**内部管理后台**：给项目内部人员用的网页，不是给考研生用的小程序。

第一阶段后台优先于完整小程序，用来做内部数据管理、调研录入，以及后续的人工筛选。原则是：先可用，再美化；页面要有加载中 / 失败 / 空数据状态；前端不复制后端业务逻辑。

## 当前是什么

可在 **macOS 原生** 与 **Windows 原生** 上运行的 React + TypeScript + Vite 内部管理后台（CI 在 Linux 上跑）：

- 包管理器：pnpm 12.4（由 Node.js 自带 Corepack 启用）
- UI：Ant Design 6
- 路由：react-router-dom
- 用原生 `fetch` 调用 `/api/v1/admin`（Vite 把 `/api` 代理到 `http://127.0.0.1:8000`）
- 可维护：School / College / Major / ExamSubject / AdmissionCatalog
- ESLint + Prettier
- GitHub Actions：frozen install / lint / format:check / build

`package.json` 已声明：

- `engines.node`: `>=24 <25`
- `packageManager`: `pnpm@12.4.0`

## 当前没有什么业务能力

- 没有登录 / 认证（`/api/v1/admin` 不是安全边界，只用于 localhost）
- 没有 Teacher / Institution、支付、小程序
- 没有 Catalog 的 child REST，没有硬删除
- 不直接连接 PostgreSQL；改数据必须同时启动 backend

业务规则仍在后端。前端只组请求、展示结果和错误。

本仓库的 `admin-web/` **没有** `.env`，也没有需要保密的前端环境变量。

## 前置条件（通用）

需要：

- Git
- **Node.js 24 LTS**（`node --version` 应为 `v24.x`）
- 用 Node 自带 **Corepack** 启用 **pnpm 12.4**

不要用 `npm install -g pnpm` 绕过 Corepack。不要求把 Node 装到某个固定路径。

## macOS

Homebrew 可用于安装 Node 24，但不是强制。

```text
node --version
pnpm --version
```

应看到 `v24.x` 与 `12.4.x`。不要把 `/Users/<username>/` 写进项目要求。

## Windows

Windows 原生仍然正式支持。使用 Git for Windows 与 PowerShell 即可，不要求 WSL。

下面是**某台已验收 Windows 开发机**的路径，**不是强制路径**：

| 项            | 该机示例值                   |
| ------------- | ---------------------------- |
| Node 安装目录 | `E:\DevTools\NodeJS`（示例） |
| 实测 Node     | v24.21.0                     |
| 实测 npm      | 11.19.0                      |
| 实测 Corepack | 0.36.0                       |
| 实测 pnpm     | 12.4.0                       |

Windows 本机安装中遇到过、可参考但**不是强制前提**的两点：

- PowerShell 可能因 ExecutionPolicy 拦截 `npm.ps1`。当前用户可使用 `RemoteSigned`；不要要求所有人改系统级策略。
- `corepack enable` 若要对 Node 安装目录写文件，可能需要管理员 PowerShell。

## 进入 admin-web/

```text
cd <repo>/admin-web
```

仓库若 clone 在别处，把路径换成实际的 `PostgradTeacherPlatform/admin-web`。

确认工具：

```text
node --version
pnpm --version
```

## 核心命令（跨平台）

安装依赖（校验 lockfile，不允许改 lockfile）：

```text
pnpm install --frozen-lockfile
```

`node_modules/` 只存在于本机，已写入 `.gitignore`，不要提交。

开发服务器：

```text
pnpm dev --host 127.0.0.1 --port 5173
```

浏览器打开 `http://127.0.0.1:5173`。需要同时启动 backend（`127.0.0.1:8000`），页面才会加载真实主数据。若本机设置了 `HTTP_PROXY`，访问 `127.0.0.1` 时请排除代理，否则 Vite 可能返回 502。用完后按 `Ctrl+C` 停止，不要留下占用 5173 的本项目进程。

生产构建：

```text
pnpm build
```

成功后会生成 `dist/`（已 gitignore，不要提交）。Ant Design 体积较大，构建时可能出现 chunk 超过 500kB 的提示；当前阶段视为非阻塞。

查看构建结果：

```text
pnpm preview --host 127.0.0.1
```

这只是本地查看 `dist/`，不是部署配置。

代码检查：

```text
pnpm lint
pnpm format:check
```

自动按 Prettier 改写（会改工作区文件）：

```text
pnpm format
```

期望：`pnpm lint` 无 error；`pnpm format:check` 全部匹配 Prettier。

## Secret 与提交注意

- 不要提交 `node_modules/`、`dist/`、`.env`、密码、Token。
- 本模块当前没有真实 `DATABASE_URL` 或 API Key。
- 后台通过 `/api` 调用 localhost backend；不把数据库口令写进前端。
