# backend/app

后端的应用程序包。以后几乎所有后端代码都放在这个目录下的子层里。

程序入口是 `main.py`。当前提供 `GET /health`。Windows 启动、测试、Ruff 命令见上级 [`backend/README.md`](../README.md)。

`api/`、`core/`、`models/`、`schemas/`、`services/`、`repositories/` 仍是分层占位，没有业务代码。
