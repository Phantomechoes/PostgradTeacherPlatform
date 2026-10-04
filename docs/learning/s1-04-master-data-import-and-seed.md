# S1-04：为什么主数据要有导入器，以及它为什么这么谨慎

这篇不是 CLI 手册的缩写。它要说明一件事：**院校招生主数据不能靠人手一条条点进后台，但也不能让一份 JSON 随便覆盖已经修好的数据。**

Importer 只给 localhost 开发使用。它不是生产摄取管道，也不是爬虫。当前只接受合成 seed。

## 1. 这个模块解决什么

S1-03A / S1-03B / S1-03C 已经能在内部后台维护学校、学院、专业、科目和招生目录。开发、联调、回归测试还需要一份**可重复的合成底稿**，否则每台机器都要重新点一遍。

S1-04 补上这条本地工具链：

- 一份 UTF-8 JSON 描述要有哪些主数据
- 旁边一份 manifest 说明它是合成数据、已批准
- 默认只报告计划，不写库
- 明确 `--apply` 之后，才按现有 Admin 写规则落库

它解决的是「开发环境怎么长出一份干净的主数据」，不是「把全网招生目录灌进生产库」。

## 2. 从哪里触发

没有网页按钮。开发者在 `backend/` 里跑 CLI。

默认 dry-run：

```text
uv run --locked python -m app.importer \
  data/seeds/devseed.json
```

确认计划后再写入：

```text
uv run --locked python -m app.importer \
  data/seeds/devseed.json \
  --apply
```

入口文件是 [`backend/app/importer/__main__.py`](../../backend/app/importer/__main__.py)，真正的参数和事务在 [`cli.py`](../../backend/app/importer/cli.py)。

## 3. 一次导入完整链路

```text
JSON + sidecar manifest
        ↓
validate（结构、业务键、多余字段）
        ↓
preflight（文件内重复、库里是否已有、引用是否成立）
        ↓
dry-run report
        ↓ --apply
Stable Master Data（School / College / Major / ExamSubject）
        ↓
inactive Catalog shell
        ↓
aggregate replace（directions + exam_units）
        ↓
commit
  或
rollback everything
```

dry-run 走到 preflight 就停，打印报告，然后 rollback。`--apply` 才进入写入。写入仍然复用现有 `AdminMasterDataService` 和 `AdminCatalogService`，不走 HTTP，也不另写一套业务规则。

## 4. dry-run 是什么

dry-run 是「假装导入，只说打算做什么」。

它会：

- 读 JSON 和 manifest
- 查数据库，判断每个业务键是 create 还是 skip，或者必须 reject
- 打印 `ImportReport`
- **rollback**，所以 `database_written=false`

它不会：

- insert / update / delete
- 公开 Catalog
- 把失败计划偷偷写成成功

所以默认命令是安全的。看完报告，再决定要不要 `--apply`。

## 5. 为什么业务键不能用数据库 id

PostgreSQL 的 `id` 是这台库自己的自增号。开发机、测试库、以后另一台机器，同一个学校的 `id` 不会一样。

业务上真正认的是：

- 学校：`school_code`
- 学院：某校下的 `college_code`
- 专业：某校下的 `major_code`
- 全国科目：`subject_code`（`scope=national`）
- 学校科目：某校下的 `subject_code`
- 招生目录：学校 + 学院 + 专业 + 年份 + 学习方式

JSON 里写 `school_id=73`，换一台库就指错对象。写 `DEVSEED_S1`，任何环境都能对上同一所合成学校。

这也是为什么导入文件禁止 `id`、`created_at`、`updated_at`、子行 ID。那些是库内部的事，不是业务底稿。

## 6. create / skip / reject

对每个业务键，Importer 只做三件事：

1. **库里没有** → create
2. **库里有，导入字段和现有内容等价** → skip
3. **库里有，内容不同** → reject，整份文件失败

没有第四条「按 JSON 覆盖」。

稳定主数据比较名称、代码、学位类型这些导入字段。Catalog 比较完整的 `directions[]` 和 `exam_units[]`。比较时顺序不敏感，避免 JSON 数组排一下就变成「不同」。

## 7. 为什么不默认 update

Admin Web 是给人改数据的。运营可能已经把学校名称改对，或把某条目录的科目选项手工修好。

如果导入默认 update，下一次跑 seed 会把人工修正冲掉。第一版宁可：

- 一模一样 → 跳过，当作已经到位
- 不一样 → 停下来让人看，不要擅自覆盖

以后如果要「按来源更新」，必须另开决策。当前没有这条路径。

## 8. 整份文件一笔事务

一份 JSON 里的学校、学院、专业、科目、招生目录，是同一份底稿。不允许出现：

- 学校写进去了
- 学院写进去了
- Catalog 做到一半失败
- 库里留下半截 seed

所以 **整个 import document 共用一个 Session、一笔事务**。不是每个 Catalog 一笔，也不是 Stable 先提交再单独提交 Catalog。

## 9. flush 和 commit 的区别

**flush**：把当前 Session 里还没发出去的改动发给 PostgreSQL，让唯一约束、外键立刻报错。事务仍未完成，还可以撤回。

**commit**：确认这整笔事务。之后其他连接能看见这些行。

Importer 写入时，Service / Repository 只 `add` + `flush`。真正的 `commit` 只发生在 CLI 看到整份报告 `ok` 之后。

## 10. rollback 为什么能撤回已经 flush 的行

flush 过的 INSERT 已经到了 PostgreSQL，但还在**未提交的事务**里。

rollback 告诉数据库：这次事务作废。已经 flush 的 School、已经建好的 inactive Catalog shell、已经插入的方向和科目选项，全部消失。

测试里故意在 Stable flush 之后、或 Catalog children flush 之后注入失败，再检查表计数回到导入前。这就是「失败即干净」的证据。

CLI 失败时打印 `APPLY REJECTED` / `ROLLED BACK`，然后退出码非 0。

## 11. Catalog shell 为什么先 inactive

招生目录一旦 `is_active=true`，公开 S1-02 就可能看见它。导入程序没有人眼检查，不能替运营决定「这份目录可以对外」。

03B 已经规定：先 POST 一个只有五元组的 inactive shell，再 PUT 整份 aggregate，再由管理员显式公开。Importer 走同一条路，并且到 PUT 为止。

它 **never auto publish**，也 **不调用 `set_status(true)`**。导入成功后，Admin Web 仍显示未公开；公开详情 404。

## 12. aggregate replace 是什么

招生目录不是「再 POST 一个方向、再 POST 一个科目」。03B 的保存语义是：提交之后，方向集合和考试单元集合必须正好等于这次给的数组。

Importer 对新 Catalog 的做法：

1. `create_shell`：五元组，`is_active=false`
2. `replace_aggregate`：把 `directions[]` 和 `exam_units[]` 整份写进去

这是完整替换，不是往空壳上补几行。空数组也合法：表示这份目录没有方向、没有考试单元。

对**已经存在**的 Catalog，Importer 不会自动再 PUT 一次。等价就 skip，不等价就整份拒绝。

## 13. 为什么 existing equal 只 skip

skip 的意思是：库里已经有一份内容相同的记录，导入不必再写。

对 Catalog 尤其重要：

- skip **不会**再调用 `replace_aggregate`
- skip **不会**改 `is_active`
- 已公开的等价目录保持公开
- 未公开的等价目录保持未公开
- 子行 ID 保持原样

如果每次等价导入都 PUT 一遍，children 会被删掉重建，ID 会变，也更容易误伤人工维护。

## 14. inactive 引用规则

稳定主数据：

- 在 inactive School 下面新建 College / Major / 学校科目 → `parent_inactive`，整份拒绝
- 已存在的 inactive 学校，字段仍等价 → skip，不恢复启用

Catalog：

- 新建 Catalog 时，School / College / Major 必须存在且 active，否则按现有 03B 规则拒绝
- 新建的 Catalog 本身是 inactive，所以可以引用 inactive ExamSubject
- 已存在且等价的 active Catalog，即使后来有科目被停用，仍然 skip，不重写、不改 status

这些规则来自现有 Admin Service，不是 Importer 另编的。

## 15. seed 与真实数据的区别

canonical seed 在：

- [`backend/data/seeds/devseed.json`](../../backend/data/seeds/devseed.json)
- [`backend/data/seeds/devseed.manifest.json`](../../backend/data/seeds/devseed.manifest.json)

它演示：

- 1 所学校、1 个学院、1 个专业
- 1 门全国科目、1 门学校自命题
- 1 份未公开 Catalog：有方向、有考试单元、有一个 OR 示例（同一单元两个 option，`option_order` 不必连续）

所有业务键使用 `DEVSEED_` 前缀。它不是某所真实大学的招生目录，也不能拿去当生产数据。

真实招生数据当前禁止 `--apply`。网页能打开，不等于可以批量抓取或商业转载。

## 16. manifest 的作用

sidecar 文件告诉工具：这份 JSON 从哪来、是不是合成、是否允许写入。

第一版只接受：

- `source_type=synthetic`
- `verification_status=approved`

manifest **不入库**。没有来源表，没有 migration。以后如果要记录真实来源，必须另开 Issue。

缺 manifest、JSON 不合法、来源不是 synthetic approved，`--apply` 直接拒绝。

## 17. 如何读 ImportReport

CLI 先打印横幅，再打印 JSON 报告。

重点字段：

- `mode`：`dry-run` 或 `apply`
- `planned.items[]`：每个业务键的 `create` / `skip`
- `planned.create_count` / `skip_count`
- `created`：按类型统计这次计划新建多少
- `skipped.catalog`：被跳过的 Catalog 数
- `errors[]`：`path` + `code` + `message`
- `database_written` / `committed`

常见错误码：

- `invalid_schema` / `invalid_json` / `missing_manifest`
- `duplicate_in_document`
- `conflict_existing`
- `unknown_reference` / `invalid_reference`
- `inactive_reference` / `parent_inactive`
- `reference_scope_mismatch`
- `apply_source_not_allowed`

dry-run 成功时 `database_written` 仍为 false。apply 被拒绝时也是 false，并且已经 rollback。

## 18. 数据最后在哪

没有新表。写入的仍是 S1-01 那七张表：

- `schools` / `colleges` / `majors` / `exam_subjects`
- `admission_catalogs`
- `admission_catalog_directions`
- `admission_catalog_exam_subjects`

Stable create 默认 `is_active=true`。Catalog create 默认 `is_active=false`。

## 19. 出问题先看哪些文件

| 现象 | 先看 |
|---|---|
| 命令一运行就写库 | 是不是加了 `--apply`。默认必须是 dry-run |
| schema 报错 | [`schemas.py`](../../backend/app/importer/schemas.py) 与 JSON 合同 |
| 重复键 | [`duplicates.py`](../../backend/app/importer/duplicates.py) |
| 计划是 skip / reject | [`preflight.py`](../../backend/app/importer/preflight.py) |
| apply 后 Catalog 仍未公开 | 正常。不会调用 `set_status` |
| apply 失败但库里有半截 | 不该发生。看 [`cli.py`](../../backend/app/importer/cli.py) 的 rollback 与测试 |
| 想覆盖已有名称 | 第一版做不到，这是冲突策略，不是 bug |

## 20. 负责人至少读懂这 3 段

1. [`backend/app/importer/cli.py`](../../backend/app/importer/cli.py)
   默认 dry-run；`--apply` 成功才 `commit`，失败 `rollback`。

2. [`backend/app/importer/apply.py`](../../backend/app/importer/apply.py)
   稳定主数据走 `AdminMasterDataService.create_*`；Catalog 走 `create_shell` + `replace_aggregate`；skip 的行不写。

3. [`backend/app/importer/preflight.py`](../../backend/app/importer/preflight.py)
   用业务键查库，决定 create / skip / reject。这里没有 UPDATE。

## 21. 当前限制和下一步

当前没有：

- CSV / Excel
- 网页抓取
- 真实招生目录 apply
- 默认 update
- 来源元数据表
- Admin Web 导入按钮
- Public 写 API
- 自动公开

下一步不是 Sprint 2。本功能 PR 合并并通过 main CI 之后，再单独做 status sync。真实数据导入仍须负责人另开决策。
