# docs/learning

**给项目负责人看的学习说明。**

每个业务模块完成后，必须在这里解释清楚，而不是只交代码。至少回答：

1. 这个模块解决什么问题？
2. 用户或管理员从哪里触发？
3. 请求进入哪个文件？
4. 数据在哪里处理？
5. 最后存在哪张表？
6. 返回结果从哪里出来？
7. 出问题优先看哪些文件？
8. 负责人至少应该能读懂哪 3 段关键代码？

禁止只复制源码或堆术语。

## 当前学习路线

按这个顺序读。每一篇解决一类问题，不要跳着从 API 开始。

1. [`foundation-overview.md`](./foundation-overview.md)
   先看工程底座：GitHub 怎么合代码、backend / 数据库 / 后台 / CI 各自干什么。不先搞清楚这些，后面的表和 API 会对不上号。

2. [`s1-01-master-data-schema.md`](./s1-01-master-data-schema.md)
   再看 7 张主数据表：现实里的学校、学院、专业、招生年份，为什么要拆成这些表，而不是一张大表。

3. [`s1-02-master-data-read-api.md`](./s1-02-master-data-read-api.md)
   最后看一次真实 GET 请求：从浏览器 / Swagger 走进 FastAPI，经过 Service、Repository，读到 PostgreSQL，再变成 JSON。

## 后续规则

以后业务模块达到 Done 之前，必须补对应的 learning 文档。代码合进 `main` 不等于负责人已经能看懂。

例如：S1-03（内部后台主数据维护）完成时，必须新增 Admin CRUD 对应的 learning，不能再只剩模板。
