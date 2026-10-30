# 内容 Schema 与引用契约

契约版本：`P22-CONTENT/0.1.0-isolated`。关联职责：V6 `053`、`082`；主接口 `IC-03`，关联 `IC-06/09/11/22`。内容 Schema 完全独立于 P21 `schema/save/**`。

## 1. 支持的确定输入

本版是明确版本的兼容配置，不宣称可验证任意未来内容文件。`dataset.plan.json` 必须提供恰好 18 个不同文档 key；不可删除有错误的文件来获得 PASS。结构验证前校验固定 SHA-256；新输入必须由内容 owner 交付，P22 审核版本后更新计划/适配器/Schema。原始内容只读。

| owner | 固定版本 | 主数据与镜像数据 |
| --- | --- | --- |
| P03 | P03-CARDS-0.1.0-draft | card_catalog、card_dictionary、character_card_pool |
| P04 | P04-SKELETON-0.1.0-draft | character_skeleton、progression_costs、character_deck_contribution |
| P06 | P06-ENEMY-0.1.0-proposal | enemy_specs、boss_phase_graph、intent_dictionary、asset_requests |
| P07 | P07-STAGES-0.1.0-proposal | stage_graph、stage_content_catalog、stage_rewards、stage_table |
| P09 | P09-POS-MAP/0.1.0-proposal | pos_mapping_rules、category_dictionary、mapping_release_registry、resource_affinity_candidates |

所有 32 个 Schema 由 Draft 2020-12 元 Schema 校验，`$id` 使用本地 `urn:yltt:p22:content:*`。引用解析器只使用已装载的 Schema 注册表，不自动拉取远程 `$ref`。运行时不从样例重新推导 Schema；仓内 Schema 是可审阅、版本化的实体文件。

## 2. 记录字段与语义边界

完整机器约束以各 JSON Schema 为准，下表说明设计与引用职责，不更改上游的数值或玩法决定。

| 类型 | 关键必填字段 | 关联与约束 |
| --- | --- | --- |
| card | card_id、owner_character_id、category、cost、effect_ids、target_rule、trigger_code、zone_after_play、gate、mock_playable | owner_character_id 指向 P03 槽位；effect_ids 指向 effect；费用必须是合规整数，缺失不填 0 |
| effect | effect_id、effect_code、amount、target_side、trigger_code、contract_gate | 状态效果必须绑定 status；非状态效果不得夹带幽灵 status_id |
| character | character_id、display_name、role_code、base_stats、per_level_growth、skill、art、p03_fixture_compatibility、record_status | ATTACK/DEFENSE/HEAL 枚举沿用 P04；兼容 P03 槽位不构成 ID 别名；art 未绑定保持 BLOCKED |
| enemy | enemy_id、tier、max_hp、baseline_attack、initial_state_id、states、asset_registry_id、production_enabled | 行动状态使用敌人作用域；技能和意图必须有定义；正式资源为空产生阻塞 |
| phase | phase_id、rank、initial_state_id、entry_wait_skill_id、asset_request_key、入口行为字段 | 阶段图绑定正确 Boss、HP 与初始状态；rank 唯一；阶段边向前且无环；行动边不可越过权威阶段 |
| stage | stage_id、canonical_stage_id、chapter_id、enemy_refs、reward_ids、unlock_rule、boss_phase_graph_id、production_enabled | Boss 图对应敌人必须在本关；奖励、章节、前置关卡均校验；保留 canonical_stage_id |
| linguistic category | code、formal_category_id、formal_resource_id、quantity、registration_status、resource_role_proposal | 8 个候选分类代码可登记；正式 category/resource 为 null 则列阻塞，不替 P08/P09 设收益数量 |
| asset | asset_id、asset_type、status、path、size_bytes、sha256、source_path、source_sha256、许可/质量回执字段 | 实际路径和源文件均读字节校验；TEST_ONLY/PLACEHOLDER 不等于 APPROVED；声明批准也不能代替 P25/P37/P30 验收 |

局部兼容 Schema 对对象未知字段采取拒绝策略；有意开放的结构以各 Schema 的明确规则为准。TSV 表头、列数和整数/布尔格式严格解析，不静默跳行。JSON 重复键、非有限数、非法 UTF-8 被拒绝。

## 3. ID 注册与命名

本版已实施的 ID 语法为 `^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,159}$`，总长 1–160，区分大小写；同类型/作用域内也拒绝仅大小写不同的冲突。它兼容已收到的 Mock、测试和提案 ID，**不会自动重编号或改成新前缀**。

注册键为 `(kind, scope, id)`。大部分内容使用空 scope，全局同字面 ID 不得跨 kind 重用；敌人行为状态允许在不同敌人 scope 中使用相同局部名称。引用必须声明目标 kind/scope，不能只按字符串猜测。定义和展示镜像分开：JSON 中的定义是注册来源，TSV 镜像是引用与一致性核验，不登记第二次。

`content_id_registry.tsv` 列为：`kind,scope,id,canonical_id,lifecycle,owner,source_path,pointer,source_sha256,production_allowed`。排序固定为 kind → scope → id；原始 ID 保留。当前 137 个定义全部 CANDIDATE。asset_request 是资源需求身份，不能代替 asset。

生命周期：CANDIDATE → RELEASED → DEPRECATED/TOMBSTONE。该图仅描述状态意义，当前工具不执行发布提升。已发行 ID 删除、重用或 canonical_id 改动必须报 P13/P21/P01；旧 tombstone 必须保留。未交付的正式 ID 不生成虚构记录。

## 4. 引用、环与镜像一致性

| 关系 | 处理 |
| --- | --- |
| 关卡前置、解锁 | 必须无环、目标存在；重复边/同节点问题按固定结构约束检查 |
| Boss 阶段转换 | 必须无环、rank 向前、端点存在并归属正确 Boss |
| 敌人行动循环 | 允许正常轮转；所有目标必须存在且不能直接跨阶段 |
| 角色卡池与 P04 兼容槽位 | 检查目标及字段一致性，不合并双方角色身份 |
| ID 迁移链 | 禁止自环、环、跨 kind/scope、未知端点、多目的地、canonical 改变 |
| JSON/TSV 镜像 | 校验费用、角色关联、阶段/敌人/奖励等关键字段，避免两份视图偏离 |

空正式资产、正式资源和正式类别不是已解析引用，单列为 BLOCKED。非空但找不到定义的 ID 是 ERROR，导致退出 2。故“0 悬空引用”只覆盖本轮明确的 403 条非空内容引用，不表示正式内容已齐全。

P09 的 NINJAL/Anki 文档 source_id 依据其原始来源回执分类为外部文档，未提供固定正文哈希则 BLOCKED；不把文档 source_id 误当游戏内容 ID。未知来源或不匹配的源数据哈希仍拒绝。

## 5. 版本、默认值和资源路径

Schema `default` 是注解，不会填入缺失值。只有明确的 `migrate-manifest` 路径会给本岗清单添加 CANDIDATE、production_allowed=false、tags=[]；不会填血量、费用、奖励或角色数值，也不会处理 P21 物理存档。未知版本直接拒绝。

资源路径必须为包根内相对 POSIX 路径：拒绝绝对路径、盘符、反斜杠、路径逃逸、符号链接，以及解析后越出指定根的文件。文件大小和 SHA-256 均校验。占位素材在隔离样例中可被识别，但正式门禁保持 BLOCKED。当前没有 P30 目录契约和正式素材，`resource_manifest.json` 如实记录 0。

## 6. CLI、错误及输出

`schema_linter.py --root <package-root> <command>`：`--root` 位于子命令之前。默认 root 为完整包目录。

| 子命令 | 输入 / 输出 | 退出码 |
| --- | --- | --- |
| lint | 固定计划 → 注册表、引用、缺失绑定、清单、日志 | 0=候选静态通过；2=错误；3=缺运行前提 |
| preflight / lint --profile production | 同样校验并保留生产门禁 | 本版条件不齐备时 3 |
| negative-samples | 五个真实错误文件 → 逐案拒绝证据 | 0=错误按预期被拒绝，不是错误数据通过 |
| assets --catalog REL | P30 候选目录 → 字节/路径检查报告 | 0=结构与字节通过；2=失败；正式门禁单列 |
| id-map [--previous REL] | 注册表与迁移表 → 别名/退役检查 | 0=表结构/一致性通过；2=失败；proposal 不激活 |
| migrate-manifest --input REL --output DIR | 旧元数据清单 → 原字节副本、新清单、审计 | 0=明确元数据迁移完成；2=版本/字段错误 |

错误包含 code、severity、file、JSON Pointer、owner；TSV 错误还提供含表头的实际行号。报告按稳定键排序且不包含时间和绝对输出路径；输入集合、Schema 集合、辅助输入、计划和校验器源码均有独立 SHA-256 指纹。每个报告目录的 `report_complete.json` 最后写入并绑定所有输出哈希；中断的部分目录没有完成标记，不可作为通过证据。已有目录或包内目录拒绝写入。

## 7. 参考

JSON Schema Draft 2020-12：https://json-schema.org/draft/2020-12/  
默认值注解：https://json-schema.org/understanding-json-schema/reference/annotations  
本地引用注册：https://python-jsonschema.readthedocs.io/en/stable/referencing/

这些公开文档用于 Schema 技术语义说明；项目授权、玩法与来源仍以包内固定上游工件为准。
