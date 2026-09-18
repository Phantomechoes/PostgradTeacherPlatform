# ADR-0001 AdmissionCatalog domain model

状态：已批准（S1-01 Checkpoint 1）
日期：2026-09-11

## 背景

Sprint 1 需要院校招生主数据。冻结规范写的是 ExamCatalog；真实业务是「按年招生目录」。研究方向与初试科目的归属必须一次定清，避免把方向字段塞进 Catalog。

## 决定

1. **业务名 AdmissionCatalog**，不用 ExamCatalog。表名 `admission_catalogs`。
2. **Major 属于 School，不属于 College**（school-scoped）。同一专业代码可在多学院招生，只通过 Catalog 关联。不做全国复用 Major 表。
3. **AdmissionCatalogDirection 是 Catalog 的子项**。Catalog 上不存 `research_direction_code/name`。
4. **初试科目挂 Catalog**（`admission_catalog_exam_subjects`），Direction 第一版不挂 ExamSubject。
5. **考试单元用 `exam_unit` 1..4**，不用 politics / foreign_language / major_1 / major_2。同一 unit 允许多个备选科目（OR）。
6. **年份在 Catalog.`admission_year`**。School / College / Major 不按年复制。
7. **无研究方向 = 零条 Direction 行**。仅当官方公布「00」时才存 `00`。

## 后果

- 历史年份靠多条 Catalog 保留，科目变化不覆盖旧年。
- 同校一致性用组合外键（无 trigger）。
- 若未来「不同方向不同初试」出现，再演化 Direction-specific 配置，不在 S1-01 预埋。

## 不改

不修改 `docs/product/开发前工程规范_V0.1.md`（冻结基线）。规范中的 ExamCatalog 在实现与文档中映射为 AdmissionCatalog。
