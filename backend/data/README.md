# backend/data

合成开发 seed 与导入样例。这是 localhost development tooling，不是生产摄取管道。

canonical seed：

- [`seeds/devseed.json`](./seeds/devseed.json)
- [`seeds/devseed.manifest.json`](./seeds/devseed.manifest.json)

`seeds/` 只放 `DEVSEED_` 前缀的合成数据。不要放入真实招生目录或 `ZZ_UI_*` 浏览器验收残留。

导入合同：[`../../docs/import/s1-04-import-format.md`](../../docs/import/s1-04-import-format.md)
