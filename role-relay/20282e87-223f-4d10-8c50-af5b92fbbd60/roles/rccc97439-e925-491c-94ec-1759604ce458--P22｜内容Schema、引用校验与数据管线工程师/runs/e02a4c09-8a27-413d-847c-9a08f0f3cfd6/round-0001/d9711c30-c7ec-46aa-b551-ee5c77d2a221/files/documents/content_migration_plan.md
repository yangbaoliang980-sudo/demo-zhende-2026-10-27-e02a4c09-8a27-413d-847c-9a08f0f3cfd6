# P22 内容版本、默认值与 ID 迁移

## 已完成的范围

本轮真正执行的版本迁移是 **P22-CONTENT-MANIFEST/0.1.0 → /0.2.0**：这两版是本次隔离组件定义的索引元数据版本，并非真实游戏已发行数据版本，也不是 P21 的物理存档 v1/v2。

旧字段 `content_version` 和每个 document 的 path、sha256、format_version、owner 保持不变。新版本只增加 `lifecycle=CANDIDATE`、`production_allowed=false`、`tags=[]`。再次迁移同一 v2 清单无新变化；必填哈希缺失、显式 null 和未知版本会被拒绝。

```bash
python -B tools/content_validation/schema_linter.py migrate-manifest \
  --input tools/content_validation/fixtures/manifest_v1.synthetic.json \
  --output ../P22_metadata_migration
```

输出保留 `original_manifest.json` 原字节、转换后的 `content_manifest.json`、`migration_audit.json` 及完成标记。审计的 `id_rewrites=0`、`source_documents_changed=0`、`save_files_touched=0`。这个合成清单引用的测试文档不作为真实输入存在；此命令仅核验元数据结构并保留声明哈希，`document_bytes_validation=NOT_RUN_METADATA_ONLY_USE_LINT_FOR_DATA_BYTES`。实际 18 份源文件的读取和哈希核验由 lint 完成。

## ID 废弃、迁移和首通身份

`content/manifest/id_migration_map.tsv` 已交付真实 TSV 表头，但没有数据行。原因是上游没有交付已发行内容的旧注册表、批准改名或退役映射。空表是“0 条已知获批迁移”的完整表达，不能用猜测历史填充它。

列：kind、scope、old_id、new_id、canonical_id、status、p13_receipt、p21_receipt、p01_receipt。两端必须已注册且属于同一 kind/scope；旧 ID 保留 DEPRECATED/TOMBSTONE；同源不能指向两个目的地；禁止自环/环；整个别名链保留同一原始 canonical_id。

自动化用例使用 `TEST_STAGE_OLD → TEST_STAGE_MIDDLE → TEST_STAGE_NEW` 合成链，验证 canonical identity 始终为 `TEST_STAGE_OLD`。该链仅在显式 `profile=test` 的库函数测试中可激活，CLI 不提供测试别名提升入口。`PROPOSED` 不生成别名；即便输入写 APPROVED 和三个回执字符串，孤立工具也不能认证外部批准，保持 BLOCKED。独立导入的注册表也必须通过结构、重复及大小写冲突检查。

```bash
python -B tools/content_validation/schema_linter.py id-map --output ../P22_id_map_check
```

`--previous <relative-registry.tsv>` 可检查已发行 ID 丢失、tombstone 重用、canonical 改变及降级。比较只产生报告，绝不修改输入；需要变更时提交 P13/P21/P01，由 P21 处理实际存档转换和回滚语义。P07 的 canonical_stage_id 保留用于原首通身份，P22 不据此重发奖励。

## 后续接收准则

1. 原设计 owner 提交新旧实际文件、版本、需求及 SHA-256。
2. P22 提供版本化 Schema/注册表差异和迁移提案，保留旧 ID。
3. 已发行 ID 删除/重用必须获得 P13/P21/P01 处理；跨接口变更经契约 owner 受理。
4. P32 独立验证数据迁移，P35 审查。正式落位由用户指定的 EXT-INTEGRATOR 执行。

当前步骤 3、4 的正式受理与执行为 BLOCKED/NOT_RUN，没有实际存档重写。
