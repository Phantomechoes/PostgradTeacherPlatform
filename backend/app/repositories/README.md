# backend/app/repositories

**职责：数据库读写。**

以后这里放 Repository。Service 需要存取数据时，通过这一层去查、增、改，而不是在业务规则里直接拼 SQL。

可以把它理解成“仓库管理员”：只负责按要求取出或放回数据，不决定业务该怎么走。
