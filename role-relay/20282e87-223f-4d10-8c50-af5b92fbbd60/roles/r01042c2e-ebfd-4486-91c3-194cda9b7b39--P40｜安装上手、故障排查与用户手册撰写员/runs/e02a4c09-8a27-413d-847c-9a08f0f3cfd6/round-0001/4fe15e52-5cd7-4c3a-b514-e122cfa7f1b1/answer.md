## P40｜安装上手、故障排查与用户手册交付

目前已从实际附件核实两项关键限制：

- P13 路径映射：`actual_game_repository`、`actual_game_commit` 和正式工程路径均未确定，`production_write_authorized=false`。
- P21 存档模块：现有版本为 `0.1.0-isolated`，其说明明确表示 Windows 尚未通过验证，当前存档恢复能力不能直接作为正式游戏的用户操作说明。

因此，本次交付需要把“已交付的独立模块”和“用户可安装的完整游戏”严格区分。不能将隔离测试程序、UI 示例或设计素材描述为已经可安装、可联动 Anki 的正式版本。

## 本次实际成果

P40 独立文档交付包已生成

17 个 ZIP 内文件 · 30,175 字节 · 已完成解压及逐文件完整性校验

完整交付 ZIP

文件校验 PASS

下载 P40_UserDocs_V0.1.zip

下载 P40_delivery_receipt.json

下载 delivery_manifest.json

四份要求的独立手册均已生成，可以单独下载：

Windows 安装与卸载手册

安装前置条件、SHA-256 校验、版本绑定、首次启动与卸载门禁。

user_install_guide.txt

Anki 插件与同步说明

插件启停、四评分、Undo、ACK 状态、断线重试与隔离规则。

anki_addon_guide.txt

存档备份和灾难恢复手册

提交结果未知、备份校验、冻结恢复、迁移、回滚及数据保全。

recovery_guide.txt

已知限制与不支持功能

模块完成范围、版本兼容性、隐私边界及尚未实现的用户功能。

known_limits.txt

另外，ZIP 中包含 38 条错误与状态索引、24 条待 P33 复走的操作步骤、10 项阻塞登记、来源证据记录、版本绑定表和校验脚本。

## 验证结果

| 验证项目 | 实际结果 |
| --- | --- |
| ZIP CRC | PASS |
| ZIP 成员与独立文件字节一致 | 17/17 PASS |
| 文档清单完整性 | 16/16 PASS |
| 全新解压后校验 | PASS |
| Windows RC 安装 | NOT_RUN |
| 真实 Anki 复习及奖励 | NOT_RUN |
| 生产版备份与恢复 | NOT_RUN |
| P33 人工复走 | NOT_RUN |
| P35 独立放行 | NOT_RUN |

ZIP SHA-256：bbcd4bea52805bb1bc1ff2dc9c1ca93299d69e954b12f22f0d08b0a377cf0da9

最终交接状态：`ISOLATED_DOCUMENTATION_PREPARED_RC_BLOCKED`。

P40 已交付可审阅、可核验、可归档的文档实体，但尚不能宣布 S08 正式用户手册通过验收。下一步应由 P36 提供固定 RC，P10 提供正式可安装插件，P33 在同一版本逐项复走，最后由 P35 独立审查。

本次没有覆盖其他岗位文件、没有擅自整合源码，也没有修改 GitHub 仓库。成果文件可由接力台直接下载归档。