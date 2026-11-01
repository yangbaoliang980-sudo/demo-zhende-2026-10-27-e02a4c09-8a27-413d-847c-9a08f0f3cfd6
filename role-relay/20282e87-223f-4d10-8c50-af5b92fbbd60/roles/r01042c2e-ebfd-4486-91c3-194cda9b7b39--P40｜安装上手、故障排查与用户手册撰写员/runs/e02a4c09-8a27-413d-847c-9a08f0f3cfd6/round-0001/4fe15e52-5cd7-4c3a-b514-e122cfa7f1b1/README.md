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

---

## 本次归档的原始文件

- [P40_delivery_receipt.json](files/data/P40_delivery_receipt.json)
- [fb3074ae-1-delivery_manifest.json](files/data/fb3074ae-1-delivery_manifest.json)
- [user_install_guide.txt](files/documents/user_install_guide.txt)
- [anki_addon_guide.txt](files/documents/anki_addon_guide.txt)
- [recovery_guide.txt](files/documents/recovery_guide.txt)
- [known_limits.txt](files/documents/known_limits.txt)
- [ZeninTCG - Fan made - Tamers Chibi Sticker Pack.jpg](files/images/ZeninTCG%20-%20Fan%20made%20-%20Tamers%20Chibi%20Sticker%20Pack.jpg)
- [InnoFusion 3.0 _ The Clan Wars - 30-Hour India's Premier Software + Hardware Hackathon.jpg](files/images/InnoFusion%203.0%20_%20The%20Clan%20Wars%20-%2030-Hour%20India's%20Premier%20Software%20%2B%20Hardware%20Hackathon.jpg)
- [エレメンタルストーリー公式攻略Wiki _ マッシュエンペラー.jpg](files/images/%E3%82%A8%E3%83%AC%E3%83%A1%E3%83%B3%E3%82%BF%E3%83%AB%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AA%E3%83%BC%E5%85%AC%E5%BC%8F%E6%94%BB%E7%95%A5Wiki%20_%20%E3%83%9E%E3%83%83%E3%82%B7%E3%83%A5%E3%82%A8%E3%83%B3%E3%83%9A%E3%83%A9%E3%83%BC.jpg)
- [Glowing arrow creating a neon light speed trail.jpg](files/images/Glowing%20arrow%20creating%20a%20neon%20light%20speed%20trail.jpg)
- [50 Hit Impact VFX.jpg](files/images/50%20Hit%20Impact%20VFX.jpg)
- [VFX Area of Effect.jpg](files/images/VFX%20Area%20of%20Effect.jpg)
- [Unity Game VFX - Light Skill Collection - EricWang(Unity VFX Artist) - BOOTH.jpg](files/images/Unity%20Game%20VFX%20-%20Light%20Skill%20Collection%20-%20EricWang(Unity%20VFX%20Artist)%20-%20BOOTH.jpg)
- [Download Twinkling Starburst Emblem PNG 05252024 PNG _ Wallpapers.com.jpg](files/images/Download%20Twinkling%20Starburst%20Emblem%20PNG%2005252024%20PNG%20_%20Wallpapers.com.jpg)
- [Purple Shard Cascade.jpg](files/images/Purple%20Shard%20Cascade.jpg)
- [千棘海刺 - 洛克王国_手游WIKI_BWIKI_哔哩哔哩.jpg](files/images/%E5%8D%83%E6%A3%98%E6%B5%B7%E5%88%BA%20-%20%E6%B4%9B%E5%85%8B%E7%8E%8B%E5%9B%BD_%E6%89%8B%E6%B8%B8WIKI_BWIKI_%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9.jpg)
- [P27_silhouette_review_board.png](files/images/P27_silhouette_review_board.png)
- [P27_card_layout_studies.png](files/images/P27_card_layout_studies.png)
- [relay-materials-1-e69105fc1b.zip](files/archives/relay-materials-1-e69105fc1b.zip)
- [relay-materials-2-ca6ada3652.zip](files/archives/relay-materials-2-ca6ada3652.zip)
- [relay-materials-3-166c0973a2.zip](files/archives/relay-materials-3-166c0973a2.zip)
- [relay-materials-4-1c81a8a0fa.zip](files/archives/relay-materials-4-1c81a8a0fa.zip)

