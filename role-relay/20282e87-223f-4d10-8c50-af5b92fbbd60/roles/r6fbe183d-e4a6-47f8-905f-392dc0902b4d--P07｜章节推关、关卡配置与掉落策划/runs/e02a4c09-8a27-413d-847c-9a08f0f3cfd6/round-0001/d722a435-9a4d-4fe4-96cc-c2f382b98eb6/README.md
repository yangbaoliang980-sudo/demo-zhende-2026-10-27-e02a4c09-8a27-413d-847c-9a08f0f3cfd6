# P07｜章节推关、关卡配置与掉落交付

**已完成 P07 的独立候选配置、章节节点图、首通与重试规则，以及作者静态验证。当前状态：LOCAL_CONFIG_DELIVERED / FORMAL_INTEGRATION_BLOCKED。**

任务 ID：P07-S07-STAGES-001
内容版本：P07-STAGES-0.1.0-proposal

本次交付包含 **2 个关卡节点、4 个奖励包、8 条奖励组成记录、67 条固定输入与期望用例、57 项已执行的校验器作者测试**。这些成果可以交给下游复核和消费；**真实关卡运行、领奖事务、Anki 联动及独立验收仍未执行。**

## 一、完整交付文件

**完整包：[P07_Stage_Delivery_V0.1.zip](https://chatgpt.com/library?file_id=libfile_2d4cd8ee786c81918587e7546bc2878f&account_id=personal)**

包内共 **67 个文件**，大小 **1,214,430 字节**。已完成 ZIP CRC 检查，并重新解压执行来源核验、配置静态检查、校验器测试和文件哈希校验，结果均符合预期。完整原始命令、输出和退出码见 [P07_delivery_receipt.json](https://chatgpt.com/library?file_id=libfile_9f96b44f91b08191840537bf5d8e7386&account_id=personal)。

ZIP 的 SHA-256：

纯文本

`cd494cd3f6a29d1fc8cdd5abe3459a9ce3795bfdd4b42681586768d671eae9f6`

阅读入口：[README(1).md](https://chatgpt.com/library?file_id=libfile_e10f79db3ebc8191aa82eb45ce27f985&account_id=personal)，完整包内的入口名称为 README.md。

四项强制成果均已生成实体文件：

| 文件 | 包内完整相对路径 | 实际大小 | 已交付内容 |
| --- | --- | --- | --- |
| [stage_graph.json](https://chatgpt.com/library?file_id=libfile_dab97ac3af708191bcc0f5151da716d2&account_id=personal) | content/stages/stage_graph.json | 12,644 字节 | 两关路线、敌人引用、解锁、重试、奖励分域和撤回语义 |
| [stage_rewards.tsv](https://chatgpt.com/library?file_id=libfile_b697746e46088191be89deab7af8d53f&account_id=personal) | content/stages/stage_rewards.tsv | 2,597 字节 | 首通与重复奖励分表记录、资源类型、领取对象和预算来源 |
| [first_clear_policy.md](https://chatgpt.com/library?file_id=libfile_448e18aadf4c8191828a4e481de0c4d0&account_id=personal) | design/stages/first_clear_policy.md | 10,814 字节 | 首通键、领取条件、原子提交要求、中断恢复和胜利撤回规则 |
| [stage_retry_cases.json](https://chatgpt.com/library?file_id=libfile_796fdcdd83408191b70a4d3cd65edd70&account_id=personal) | content/stages/stage_retry_cases.json | 170,850 字节 | 67 条固定输入、操作序列与期望投影，逐条保留 NOT_RUN |

逐件路径、实际大小、完整 SHA-256、格式／版本、源输入哈希、接收岗位和修改白名单，已记录在 [delivery_manifest.sha256(1).tsv](https://chatgpt.com/library?file_id=libfile_ecfd6e17cec08191a1b6eddeac9cf761&account_id=personal)。包内清单覆盖其余 **66 个文件**，清单自身及 ZIP 的哈希由外层交付回执固定。

另外提供关卡表和奖励表的可编辑阅读副本：

[stage_tables.xlsx](https://chatgpt.com/library?file_id=libfile_6d2b158c4e14819191547ab4f2dc1ce6&account_id=personal)

## 二、首章候选已经配置

本版遵循 V6 的 **S07 两关路线**，配置为普通关 → BOSS 关。精英保留未启用入口说明，没有新增第三关或第二章。

| 顺序 | 关卡 ID | 敌人引用 | 解锁条件 | 首通共享代币 | 首通每名入场角色 XP | 重复掉落 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MOCK_P07_STAGE_001 | MOCK_P06_ENEMY_001 游离字屑 | 合法三人快照、固定内容及授权入场记录 | 3 | 4 | 停用，0 |
| 2 | MOCK_P07_STAGE_002 | MOCK_P06_ENEMY_003 失序校勘者 | 普通关有效通关且原子提交完成 | 12 | 18 | 停用，0 |

**表中的金额沿用 P05 未批准测试预算。** 重复掉落尚无 P05 预算和 P08 边界回执，所以本版明确停用；这不代表已经决定正式游戏长期没有重复收益。

章节图已提供可编辑 [chapter_nodes.svg](https://chatgpt.com/library?file_id=libfile_a88d31c6a2c8819197f17ee01419cb18&account_id=personal)，包内同时包含 Mermaid 源文件。

本次处理了一个会影响路线可达性的成长条件：**普通首通的 3 代币、每人 4 XP，不足以达到 P04 的 LV2 条件，因此 BOSS 入口没有强制要求 LV2。**

若两关使用同一组三人完成首通，合计为 **15 个共享代币、每人 22 累计 XP**。按 P04 测试成本，三人各升一次 LV2 共需 12 代币，剩余 3；累计 XP22 尚未达到 LV3 所需的 25。该结果是配置算术，**不代表已验证三人能够击败 BOSS**。数值来源和成长边界均写入首通规则及源输入回执。

BOSS 直接引用 P06 的三阶段图，没有覆盖敌人 HP、攻击、阈值或 AI。P05 原先无阶段 BOSS 的回合结果不能直接用于本关。

## 三、首通、重复与撤回规则已经落入配置

以下均为本版候选配置对下游实现的要求，正式运行合同仍待接收。

### 1. 首通不依赖 battle_id

永久首通逻辑键为：

纯文本

`["STAGE_FIRST_CLEAR", player_save_scope_id, canonical_stage_id]`

同一玩家存档作用域、同一 stage，即使换了 battle_id、内容版本或奖励版本，也不能再次取得首通奖励。

重复奖励使用独立作用域：

纯文本

`["STAGE_REPEAT_CLEAR",
 player_save_scope_id,
 canonical_stage_id,
 battle_id,
 terminal_revision]`

同时要求维护同一 battle 的结果守卫：**更高终局修订号只能进入修订／撤回对账，不能被解释为新的一局并再次发奖。**

### 2. 领取与解锁要求同一原子提交

配置要求由 P18 判断资格、P17 校验资源与角色增量、P21 完成原子提交。进度、首通标记、代币、XP、终局回执与解锁不能分别提前发布。

结果页按钮只确认或重查已提交回执。事务结果未知时，先查权威回执，不允许直接开始新一局来绕开未完成结算。

### 3. 重试、恢复与主动退出有明确区别

- **失败后重试：**创建新的 battle_id，重新校验入场条件。
- **恢复同一场战斗：**保留原 battle_id 和固定内容版本。
- **主动退出未结束战斗：**先由权威关闭为 ABORTED，拒绝该旧 attempt 的迟到 WIN。
- **WIN 后崩溃或响应丢失：**使用原结果身份恢复／对账，不重复发奖。
- **已首通后再次失败：**不抹掉原有有效首通记录。

### 4. 撤回胜利不重新开放首通

发奖前撤回，取消待处理 WIN，保留失效修订记录，不发奖励、不解锁后续。

发奖后撤回，候选规则要求保留已领取标记，进入待审状态；依赖它的新入口和后续新奖励先隔离。**不自动制造负钱包、不自动降级，也不删除首通键让玩家重新领取。** 具体权益处置仍需 P18/P17/P21 与 P01 的版本化决策。

### 5. Anki 与关卡奖励保持独立来源

关卡不能伪造学习事件；Anki Undo 不直接清空关卡首通，也不能充当战斗撤回。

入口／重试零费用以及零复习可进入，只用于隔离测试夹具。正式零学习日权益仍受 DEC-003 和 P08/P01 门禁约束。上述规则完整记录在已交付的首通政策文件中。

## 四、上游材料已实际核验，并补齐了 P06 文件缺口

本次实际打开并核验了 **8 个唯一 ZIP**：

| 核验对象 | 清单项核验结果 |
| --- | --- |
| 原上传附件 | 35/35 |
| 内嵌 relay 包 | 34/34 |
| P01 完整包 | 15/15 |
| P02 完整包 | 14/14 |
| P03 完整包 | 16/16 |
| P04 完整包 | 19/19 |
| P05 完整包 | 19/19 |
| P06 完整包 | 42/42 |

合计核验 **194 条逐层清单项**，各 ZIP CRC 通过。这里包含不同封装层对相同文件的重复核验，不是声称读取了 194 个不同源文件。

有两点交接差异已记录：

- 独立的 P01 决策 TSV、P04 成长 TSV 存在仅有表头的副本；本次采用完整内层 ZIP 中的实际内容。
- P06 完整成果 ZIP 不在上传的 35 个原附件中，也不在给定固定提交的文件树中。本次已从正文指定的精确成果链接取得真实 ZIP，其 **168,593 字节**及 SHA-256 与交接声明一致，随后核验了其中的敌人配置和 42 项文件清单。

V6 原文也已按固定提交读取，本地 SHA-256 与 Git blob 校验匹配。全部来源版本、原始路径和哈希见 [source_input_receipt.json](https://chatgpt.com/library?file_id=libfile_98c67056b6848191a64fea635be9c59e&account_id=personal)。

完整包保留了 **16 份实际消费的只读源快照，以及原始交接 ZIP 和补齐的 P06 ZIP**，下游可以离线复核来源。

## 五、实际验证结果与边界

| 验证层级 | 当前结果 | 证据含义 |
| --- | --- | --- |
| 原始 ZIP、清单及源快照绑定 | **PASS** | 字节、大小、哈希及来源绑定匹配 |
| P07 候选配置静态检查 | **PASS** | 两关图可达、无环、终点明确；候选 ID 引用和奖励预算一致 |
| P07 校验器作者测试 | **PASS，57/57** | 检查错误配置能够被拒绝 |
| 章节图与表格作者目视检查 | **PASS** | 中文、数值和图示可读 |
| 重新解压与交付哈希核验 | **PASS** | 完整包可复算 |
| 正式前置检查 | **BLOCKED** | 实际退出码为 3，缺少正式合同、路径、政策和环境 |
| 独立设计审核／P35 SPEC Gate | **NOT_RUN** | 没有独立回执 |
| P18 真实关卡单元、IC-11/13 契约运行 | **NOT_RUN** | 没有真实实现接入证据 |
| P21 持久化、并发与故障注入 | **NOT_RUN** | 没有执行真实事务 |
| P32 独测、P33 人工、P35 独审 | **NOT_RUN** | 作者没有代签 |
| 游戏目标机、真实 Anki E2E | **NOT_RUN** | 没有运行证据 |
| 正式工程写入及跨模块集成 | **BLOCKED** | 路径授权及整合条件未齐 |

**67 条关卡用例仍是期望数据，真实关卡／奖励执行数为 0。** 其中包括：

- P07-ST-026/027：同 stage、不同 battle 的首通防重复。
- P07-ST-031：两个终局争用首通权的两种交错顺序。
- P07-ST-037/039：提交前崩溃、提交后响应丢失。
- P07-ST-044—048：胜利撤回、已消费收益及依赖关卡隔离。
- P07-ST-065/066：存档迁移与旧备份缺失幂等历史。

完整执行回执保留原始 stdout、stderr、退出码及哈希；静态通过没有被写成真实事务幂等通过。

解压后，在包根可直接复算：

Bash

`python design/stages/verification/verify_input_archives.py
python design/stages/verification/validate_stage_content.py
python -m unittest discover -s design/stages/verification -p 'test_*.py' -v
python design/stages/verification/verify_manifest.py`

正式前置探针：

Bash

`python design/stages/verification/validate_stage_content.py --formal`

本版本最后一条应输出 BLOCKED 并退出 **3**。

## 六、下游接收与尚未解除的阻塞

| 责任方 | 仍需补齐的具体证据 |
| --- | --- |
| P13 | actual_path_mapping.json、真实工程固定提交、写入白名单、正式内部 DTO 版本与哈希 |
| P22 | 正式内容 ID 注册表、stage/reward Schema、必要的别名迁移 |
| P08 | 固定版本的 Anki 与关卡奖励边界／PolicyRecord |
| P01 | 本 S07 配置版本的范围接收、前置阶段状态及权益裁决 |
| P05 | 基于 P06 三阶段 BOSS 的节奏与奖励预算、重复掉落预算 |
| P06 | 普通敌样本从 S03 用于 S07 的接收确认 |
| P34 | 目标游戏引擎、OS、Anki 版本及测试环境指纹 |
| P18 | 实际关卡实现固定提交、P14 结果与 P17/P21 事务合同及运行证据 |
| P32／P33／P35 | 各自独立测试、人工旅程和门禁回执 |

交付文件已经按 **P05、P06、P18、P20、P22、P32** 的消费需要整理，包内 downstream_handoff.json 固定了接收文件及哈希，接收状态均为 **PREPARED_NOT_ACKNOWLEDGED**。

下一位可以从完整包的 README.md 直接进入配置、规则、用例、源证据和复算命令。正式工程路径仍等待 P13 映射；跨模块合并仍交由用户指定的 **EXT-INTEGRATOR**。

---

## 本次归档的原始文件

- [requirements_baseline_v6.txt](files/documents/requirements_baseline_v6.txt)
- [decisions_pending.tsv](files/data/decisions_pending.tsv)
- [task_register.tsv](files/data/task_register.tsv)
- [handoff_receipts.tsv](files/data/handoff_receipts.tsv)
- [gate_issues.tsv](files/data/gate_issues.tsv)
- [P01_S00_V6_完整交接包.zip](files/archives/P01_S00_V6_%E5%AE%8C%E6%95%B4%E4%BA%A4%E6%8E%A5%E5%8C%85.zip)
- [battle_state_machine.md](files/documents/battle_state_machine.md)
- [effect_priority.tsv](files/data/effect_priority.tsv)
- [terminal_phase_truth_table.tsv](files/data/terminal_phase_truth_table.tsv)
- [battle_replay_fixtures.json](files/data/battle_replay_fixtures.json)
- [interface_rfc_and_blockers.md](files/documents/interface_rfc_and_blockers.md)
- [P02_DELIVERY_README.md](files/documents/P02_DELIVERY_README.md)
- [P02_S01_战斗状态机与确定性结算规则_V0.1_完整交付包.zip](files/archives/P02_S01_%E6%88%98%E6%96%97%E7%8A%B6%E6%80%81%E6%9C%BA%E4%B8%8E%E7%A1%AE%E5%AE%9A%E6%80%A7%E7%BB%93%E7%AE%97%E8%A7%84%E5%88%99_V0.1_%E5%AE%8C%E6%95%B4%E4%BA%A4%E4%BB%98%E5%8C%85.zip)
- [9c42e18d-card_choice_cases.tsv](files/data/9c42e18d-card_choice_cases.tsv)
- [9c42e18d-1-card_choice_cases.tsv](files/data/9c42e18d-1-card_choice_cases.tsv)
- [card_catalog.json](files/data/card_catalog.json)
- [card_choice_cases.tsv](files/data/card_choice_cases.tsv)
- [interface_rfc_blockers.md](files/documents/interface_rfc_blockers.md)
- [manifest.sha256.tsv](files/data/manifest.sha256.tsv)
- [P03_static_validation.log](files/other/P03_static_validation.log)
- [card_effect_examples.json](files/data/card_effect_examples.json)
- [P03_S01_S02_卡牌牌组与专属技能_V0.1_完整交付包.zip](files/archives/P03_S01_S02_%E5%8D%A1%E7%89%8C%E7%89%8C%E7%BB%84%E4%B8%8E%E4%B8%93%E5%B1%9E%E6%8A%80%E8%83%BD_V0.1_%E5%AE%8C%E6%95%B4%E4%BA%A4%E4%BB%98%E5%8C%85.zip)
- [party_deck_rules.md](files/documents/party_deck_rules.md)
- [P04_character_skeleton.json](files/data/P04_character_skeleton.json)
- [P04_party_constraints.md](files/documents/P04_party_constraints.md)
- [P04_progression_costs.tsv](files/data/P04_progression_costs.tsv)
- [P04_character_deck_contribution.tsv](files/data/P04_character_deck_contribution.tsv)
- [P04_S02_Character_Progression_Delivery_V0.1.zip](files/archives/P04_S02_Character_Progression_Delivery_V0.1.zip)
- [balance_parameters.tsv](files/data/balance_parameters.tsv)
- [fixed_seed_simulation.py](files/code/fixed_seed_simulation.py)
- [simulation_results.csv](files/data/simulation_results.csv)
- [reward_abuse_cases.md](files/documents/reward_abuse_cases.md)
- [balance_report.md](files/documents/balance_report.md)
- [P05_S01_Balance_Delivery_V0.1.zip](files/archives/P05_S01_Balance_Delivery_V0.1.zip)
- [relay-materials-1-3559b922b7.zip](files/archives/relay-materials-1-3559b922b7.zip)
- [relay-materials-1-1b174d40f0.zip](files/archives/relay-materials-1-1b174d40f0.zip)

