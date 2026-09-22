# S1-03C：内部管理后台怎样接到真实 Admin API

这篇不是页面清单。它要说明一件事：**管理员在网页上点的按钮，怎样变成 03A / 03B 已经冻结的 Admin HTTP，而不会在前端再发明一套业务规则。**

`http://127.0.0.1:5173` 只给内部人员用。`/api/v1/admin` **仍然没有登录**，只是路径分区，仅用于 localhost 本地开发。

## 1. 03C 解决什么

03A 能维护学校、学院、专业、科目。03B 能创建未公开的招生目录壳，再一次 PUT 整份目录，再显式公开。在 03C 之前，这些只能用 Swagger 或 `curl` 做。

03C 补上内部网页：

- 院校列表和详情（学院 / 专业 / 自命题科目三个 Tab）
- 全国统考科目
- 招生目录列表
- 招生目录整份编辑器

停用不是删除。公开和取消公开也不是删除。前端不提供 Catalog 的 child REST，也不调用公开 S1-02 去改 Admin 数据。

## 2. 从哪里触发

浏览器打开 `http://127.0.0.1:5173`（Vite 开发服务器）。

```text
左侧菜单「院校」
  → /schools
  → 查看
  → /schools/{id}?tab=colleges|majors|subjects

左侧菜单「全国统考科目」
  → /exam-subjects/national

左侧菜单「招生目录」
  → /catalogs  （必须先选学校）
  → 新增招生目录
  → /catalogs/{id}
  → 保存整份目录 / 公开 / 取消公开
```

页面上的 Loading / 失败 Alert / 空表，来自真实请求，不是 S0-04 那三张静态演示卡。

## 3. 一次保存怎么走

例子：在编辑器里点「保存整份目录」。

```text
浏览器  http://127.0.0.1:5173/catalogs/31
        ↓
CatalogEditorPage 组好完整 PUT body
  五元组 + directions[] + exam_units[]
        ↓
catalog.ts  replaceCatalogAggregate()
        ↓
client.ts   PUT JSON
        ↓
Vite 把 /api 转到 http://127.0.0.1:8000
        ↓
FastAPI     /api/v1/admin/admission-catalogs/{id}
        ↓
03B Write Service  先校验，再整份替换
        ↓
PostgreSQL  三张表同一事务
        ↓
HTTP 200    CatalogAdminDetail
        ↓
编辑器用服务端详情刷新页面和原始快照
```

失败时 Modal / 表单还在，当前编辑内容不会被清空。成功时才用服务端结果覆盖草稿。

创建目录走另一条路：`POST` 只交五元组，服务端强制 `is_active=false`，然后立刻进入编辑器。前端不会在 POST 之后自动公开。

## 4. 前端为什么不自己「发布」

保存和公开是两件事：

| 按钮 | 请求 | 含义 |
|---|---|---|
| 保存整份目录 | `PUT` 完整聚合 | 把当前编辑写成数据库里的最终样子 |
| 公开 | `PATCH .../status { is_active: true }` | 这时公开 S1-02 才可能看见 |
| 取消公开 | `PATCH .../status { is_active: false }` | 方向和科目选项还在 |

如果表单有未保存修改，不能拿库里的旧版本悄悄公开。页面会先拦住，让人保存或放弃修改。

`directions: []` 和 `exam_units: []` 都是合法最终集合。前端不要求四个考试单元、至少一门科目、至少一个方向。

同一考试单元里多个科目是 **OR**。`option_order` 不要求连号。PUT body **没有** Direction / 选项的数据库行 id。

## 5. 科目选择器从哪来

编辑器里能选的科目只有：

```text
全国统考科目（school_id 为空）
  +
当前学校的自命题科目
```

Admin 默认把 inactive 也加载进来，并标「已停用」。历史目录里已经引用的停用科目必须还能看见，不能在打开编辑器时被前端删掉。

正常 UI 不会列出外校自命题。跨校科目由后端返回 `reference_scope_mismatch`。后端仍是最终权威。

## 6. 数据落在哪

前端不直接碰数据库。写请求进了 03A / 03B 之后，仍落在这几张已有表：

- `schools` / `colleges` / `majors` / `exam_subjects`
- `admission_catalogs`
- `admission_catalog_directions`
- `admission_catalog_exam_subjects`

没有新表，没有 migration，没有 DELETE REST。

## 7. 出问题先看哪里

| 现象 | 先看 |
|---|---|
| 页面空白或 5173 打不开 | Vite 是否在 `admin-web/` 里启动；本机 `HTTP_PROXY` 会不会把 `127.0.0.1` 转到错误代理 |
| 列表一直转圈 / Alert「服务器错误」 | FastAPI 是否在 8000；Vite 只代理 `/api` |
| 院校代码重复出现在表单上 | `formErrors.ts` 的 `duplicate_*` 映射 |
| 保存目录后公开接口仍 404 | 目录是不是还没点「公开」；School / College / Major 是不是 inactive |
| 公开被 422 | 引用是否停用，或科目是否跨校 |
| 取消公开后方向不见了 | 不应发生；status=false 不删 children。看是否误点了「保存整份目录」且确认清空集合 |

## 8. 负责人至少读这 3 处

1. [`admin-web/src/api/client.ts`](../../admin-web/src/api/client.ts)  
   所有页面共用的 fetch。它只懂 HTTP / JSON / `ApiError`，不懂学校或目录。

2. [`admin-web/src/api/catalog.ts`](../../admin-web/src/api/catalog.ts)  
   五个 Catalog 接口：列表、详情、POST shell、PUT 整份、PATCH status。没有 child REST。

3. [`admin-web/src/pages/CatalogEditorPage.tsx`](../../admin-web/src/pages/CatalogEditorPage.tsx) 里保存和公开两段  
   `PUT` 提交完整聚合；有未保存修改时不能直接公开；取消公开不删子行。

稳定主数据的 URL 和字段在 [`admin-web/src/api/masterData.ts`](../../admin-web/src/api/masterData.ts)。合同仍以 [`docs/api/s1-03a-stable-master-data-admin-api.md`](../api/s1-03a-stable-master-data-admin-api.md) 和 [`docs/api/s1-03b-admission-catalog-admin-api.md`](../api/s1-03b-admission-catalog-admin-api.md) 为准。

## 对照规范 8 问

1. **解决什么问题？** 让内部人员用网页维护稳定主数据和招生目录，而不再只靠 Swagger。
2. **从哪里触发？** 浏览器 `127.0.0.1:5173` 的菜单和按钮。
3. **请求进入哪个文件？** 页面 → `masterData.ts` 或 `catalog.ts` → `client.ts` → Vite `/api` 代理 → FastAPI Admin 路由。
4. **数据在哪里处理？** 业务规则仍在 backend Write Service。前端只组 JSON、展示错误、保留未保存编辑。
5. **最后存在哪张表？** 上面第 6 节的 7 张已有表。
6. **返回结果从哪里出来？** Admin JSON。公开 S1-02 只有目录被显式公开、且四级都 active 时才看得到。
7. **出问题先看什么？** 第 7 节的表。
8. **读哪 3 段？** `client.ts`、`catalog.ts`、Catalog 编辑器的保存 / 公开。
