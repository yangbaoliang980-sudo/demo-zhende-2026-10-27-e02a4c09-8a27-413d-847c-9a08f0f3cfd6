# P17｜角色、编队、属性与共享钱包运行库交付

**P17 的可执行隔离运行库、测试、接口说明和完整交接包已完成。最终 123 项作者测试全部通过，最终 ZIP 已在新解压目录复跑通过。**

任务编号：`P17-S05-S06-S07-META-001`
交付版本：`P17-META/0.1.0-isolated`
当前状态：**ISOLATED_RUNTIME_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED**

正式工程接入仍受 **P13 路径授权、P21 真实事务实现及跨域接口接收** 阻塞；P32 独测、P33 人工验收、P35 独审，以及 Windows、引擎、真实 Anki 和整游戏 E2E 均为 **NOT_RUN**。

## 一、完整成果下载

| 文件 | 实际大小 | 内容 |
| --- | --- | --- |
| **P17_CharacterPartyWallet_V0.1.zip** | **2,129,280 字节** | 206 个实体文件，包含完整源码、测试、上游原件、执行证据、接口说明及交接资料 |
| **delivery_receipt.json** | **78,172 字节** | ZIP 与 16 个独立导出的实际大小、SHA-256、包内路径，以及新解压目录的完整复跑记录 |

ZIP 的 SHA-256：

纯文本

`339c492a8f4f3963d0391e78eccb1d261a9b289bb12dc43349a22b581148daa4`

已实际完成：

- ZIP CRC 检查。
- **206 个包内文件**与生成目录逐字节比对。
- **16 个独立导出文件**与 ZIP 内对应文件的同名、同字节比对。
- 新解压目录的完整运行验证。

清单记录其余 **205 个文件**；清单自身和 ZIP 由包外回执绑定，避免循环哈希。回执中的 exports、`archive` 数值均由工具对实际文件计算。

### 主要文件单独下载

| 文件 | 用途 |
| --- | --- |
| README.md | 阅读入口、能力范围、运行命令与验收边界 |
| P17_API.md | 角色、编队、钱包、候选事务、错误码及重新载入 API |
| integration_handoff.md | 下一位接收、接线和正式集成要求 |
| wallet_delta_contract.json | P13 原 WalletDeltaCandidate 定义的独立 Schema 投影 |
| wallet_concurrency_tests.py | 并发消费、预留、兑现、撤销及重复请求测试 |
| source_input_receipt.json | 上游来源、固定提交、实际文件哈希及缺失输入 |
|  | 逐文件路径、大小、SHA、版本、源输入哈希、接收人和修改白名单 |
| verification_status.json | 作者测试、契约检查、真机、E2E、独立验收的分层状态 |
| blockers.json | 11 项正式接入缺项、责任方与解除条件 |
| interface_rfcs.json | 6 项附带 base SHA 的版本化接口提案 |
| defect_log.json | 本轮实际发现的 4 个缺陷、修复与回归证据 |
| lifecycle_execution.json | 完整生命周期的请求、候选、来源、模拟提交和最终状态 |
| demo_summary.json | 实际执行示例的简要结果 |

核心源码可单独查看：

- service.py：不可变候选生成、提交前重验及公共读取 API。
- rules.py：`runtime/meta/wallet/rules.py`，共享钱包与来源分摊规则。
- projection.py：编队校验、完整战斗导出及原 P13 DTO 投影。

**运行时请使用完整 ZIP，保留源码目录、P13 原依赖及上游测试输入。**

## 二、本轮实际实现

### 1. 角色获取、编队与成长

已实现角色获取、拥有权校验、累计经验授予、逐级升级、技能成长和三人上阵快照。

成长计算复用 P04 原始配置：

- 升级必须满足累计 XP 门槛，单次只能提升一级。
- 训练代币按原配置扣除，**XP 不扣减，也不自动触发升级**。
- 技能提升校验角色等级、当前 rank 和资源余额。
- 技能 rank 只改变养成数据，不自行放大 P03 卡牌的伤害、治疗或护盾。
- 战斗编队必须恰好三名已定义、已拥有且互不重复的角色，保留槽位顺序。
- 没有加入“攻击、防御、治疗必须各一名”的限制，也没有把总角色数量写死为三名。

派生属性使用 P04 的整数公式，完整保留 **HP、攻击、防御、支援**。P05 的 15 条逐级属性投影已用于实际回归对照。

### 2. 装备装卸与属性复算

装备机制已在明确标注的合成测试配置下实现，覆盖：

- 装备实例获取与归属。
- 装备槽位、角色等级及职业条件。
- 装上、卸下和整组替换。
- 同一实例不能同时装备给两个角色。
- 非法替换失败时，原装备和属性保持不变。
- 重新载入后按内容配置复算属性。

**默认配置仍关闭装备功能。** P04 原件中的 DEC-009 尚未批准，本包的测试装备及加成没有被当作正式内容、价格或平衡参数。

### 3. 共享钱包与权益防重

钱包按来源逐笔保存资源，区分：

- 可用资源。
- 已预留资源。
- 已消费资源。
- 已撤销资源。

每个来源批次均验证数量守恒；消费和预留保留明确分摊记录。预留后的资源不能再次用于升级，释放会按原来源返还，兑现必须匹配原用途和成本。

权益去重与请求幂等分别处理：

| 情况 | 实际行为 |
| --- | --- |
| 同 request_id、同完整请求 | 返回重复 no-op，不再次扣款或授予 |
| 同 request_id、不同参数 | 拒绝 ID 碰撞 |
| 同一权益换 request_id 或投递引用 | 仍不能重复兑现 |
| 同一权益改变金额或政策 | 拒绝权益内容碰撞 |
| 首通奖励换一场 battle_id | 不能借此重新领取；首通键不包含 battle_id |
| 重复关卡奖励 | 另外绑定具体战斗凭证，分别去重 |
| 可用资源不足，包括部分资源不足 | 整个操作无候选，不能部分扣费 |

### 4. 学习奖励与撤销边界

本包能够对**外部 P11 解析出的授权输入**计算学习资源授予候选，资格判定仍归 P11。默认外部证据端口关闭，调用者不能通过自报 trusted=true 或任意金额绕过它。

在隔离测试中，完整未消费的学习来源可以生成撤销候选。出现已消费或已预留时，返回：

纯文本

`BLOCKED / E_RECONCILIATION_REQUIRED`

此时没有部分扣款候选，不生成负余额，也不拿其他来源的资源补偿缺口。已消费 Undo、未来抵扣、负债、豁免及恢复授予，继续等待 P08/P01 政策与 P11 接口处理。

### 5. 原子事务候选与只读战斗数据

角色变化、钱包变化、来源分摊、预留记录和请求指纹进入同一个不可变候选。提交前可以重新计算，并校验：

- 领域 revision 与钱包 revision。
- 请求指纹与内容哈希。
- profile、store instance 和 continuity。
- 外部证据绑定。
- 完整候选后态是否逐字节一致。

**P21 未绑定时，提交入口明确拒绝，不发生“先扣资源后补存档”。**

编队同时提供完整的 P17 导出和兼容原 P13 形状的投影。原 P13 EntityStats 缺少支援、技能、装备及 P03 关联字段，这些信息保留在完整导出中，并已提交 RFC 提案。

## 三、实际执行示例

已运行 P04 原生命周期夹具：

**空状态 → 获取三个角色 → 授予 15 代币 → 授予 XP → 设置编队 → 升级 → 重新解码 → 重试原请求。**

最终结果：

| 角色测试 ID | 等级 | 累计 XP | HP | 攻击 | 防御 | 支援 |
| --- | --- | --- | --- | --- | --- | --- |
| MOCK_P04_CHAR_001 | 2 | 10 | 108 | 21 | 6 | 4 |
| MOCK_P04_CHAR_002 | 3 | 25 | 168 | 10 | 23 | 6 |
| MOCK_P04_CHAR_003 | 1 | 10 | 108 | 7 | 7 | 17 |

钱包余额：

纯文本

`15 − 4 − 4 − 6 = 1`

实际生成 **11 个内存模型提交**，最终领域 revision 为 **11**、钱包 revision 为 **4**。重新载入后重试原请求返回 DUPLICATE_NO_OP。

完整输入、候选、模型回执和结果均保存在上方的生命周期执行文件中。所有模型回执均标明 **durable=false**，没有将其写成 P21 持久化通过。

## 四、实际验证结果

下列检查存在包含和重叠关系，不能相加为额外测试总数。

| 验证层级 | 本轮结果 | 证明范围 |
| --- | --- | --- |
| 作者设计复核 | COMPLETED_AUTHOR_REVIEW | 所有权、纯候选边界、来源和声明范围 |
| 最终作者测试 | **123 PASS，0 FAIL，0 error，0 skip** | 最终 ZIP 新解压目录复跑一致 |
| 并发测试 | **8 项通过，包含在 123 项内** | 重复请求、余额竞争、预留、兑现／释放、撤销／消费竞争 |
| 原 P13 校验器 | **17 条 DTO 通过** | Party、Wallet、WalletDelta、AtomicCommitProposal |
| 缺跨域契约的提交投影 | **7 次按预期阻止** | 没有把缺 P11/P18 对应候选的请求包装成正式成功提交 |
| P04 原生命周期 | **完整结果匹配** | 角色、XP、升级费用、余额和属性 |
| P05 属性投影 | **15 行对照通过** | 三个测试角色 Lv1～Lv5 |
| 跨进程确定性 | **PASS** | 三个不同 PYTHONHASHSEED 的独立 Python 进程摘要一致 |
| 另一个 Python 进程重新载入 | **PASS，作者测试范围** | stdin 提供字节后的数值一致性；未验证真实游戏存档重启 |
| 输入原件复核 | **PASS** | 5 个上传 ZIP、5069 个展开成员及包内 93 份只读原件 |
| 正式前置检查 | **BLOCKED，exit 3** | 真实路径、事务、政策、内容及环境仍缺项 |
| P32／P33／P35 | **NOT_RUN** | 未代签独测、人工或独审 |
| Windows、引擎、真实 Anki、整游戏 E2E | **NOT_RUN** | 未执行 |

边界检查实际发现并修复了 **4 个 P17 缺陷**：模块直接导入的循环依赖、长账号 ID 导致 DTO 超长，以及两处畸形数据触发 Python 异常的问题。失败时源码、原始失败日志、针对性回归和最终全量通过记录均已保留；P32 复测和 P35 关单仍为 NOT_RUN。

## 五、正式接入仍需解除的阻塞

| 阻塞 | 责任方与下一步 |
| --- | --- |
| 四条 P17 正式路径仍为 null／write_allowed=false | **P13**：出具实际工程路径、固定提交与授权白名单 |
| P21 真实存储 API 和物理事务实现未收到 | **P21**：实现原子提交、持久去重、权威查询和备份连续性 |
| P11 原 WalletPort 与本包模型尚无批准的无损转换 | **P11／P13／P21**：保留原 source_after 全量语义，处理接口适配 |
| 真实首通、掉落、关卡消费凭证及联合事务未接入 | **P18／P13／P21**：提供终局、预算、资格和成本的解析接口 |
| 编队 DTO 缺少完整属性、技能和装备消费合同 | **P13／P15／P14**：处理版本化字段及消费口径 |
| 四键、已消费 Undo、无学习日、装备与正式内容仍待批准 | **P01／P08／P04／P05／P22**：提供明确版本和批准证据 |
| 目标工程、环境及独立验收缺失 | **P13／P34／P32／P33／P35**：执行各自范围内的验证 |

另已记录完整快照的容量限制：当前沿用 P13 的消息和数组技术界限，不能通过删除历史去重凭证来腾空间。长期记录分段与迁移需由 P13/P21 承接。

**6 项 RFC 均为 PREPARED_NOT_SUBMITTED。** 已准备 **13 个接收方、64 条带实际文件哈希的交接记录**，状态为 PREPARED_NOT_ACKNOWLEDGED，保存在包内 downstream_receipts.json。

## 六、下一位直接复现

完整解压后进入 P17_CharacterPartyWallet_V0.1，使用 Python 3.12：

Bash

`python -B tools/verify_delivery.py
python -B tools/author_tests.py
python -B tools/check_contracts.py
python -B -m character_party_runtime
python -B tools/replay_demo.py
python -B tools/check_determinism.py
python -B tools/preflight.py`

本次最终 ZIP 新目录实跑中，**前六条退出码均为 0，最后一条为 3／BLOCKED**；命令、退出码、标准输出及错误输出已完整写入包外交付回执。

下一位可以直接接收本包进行接口受理或独立复测。正式路径授权由 P13 处理，物理事务由 P21 处理，跨模块最终合并继续交给用户指定的 **EXT-INTEGRATOR**。

---

## 本次归档的原始文件

- [builder.py](files/code/builder.py)
- [06c45882-1-input_immutability_check.json](files/data/06c45882-1-input_immutability_check.json)
- [b75d7867-1-demo_summary.json](files/data/b75d7867-1-demo_summary.json)
- [3fc42b47-1-defect_log.json](files/data/3fc42b47-1-defect_log.json)
- [f6fdd7c0-1-path_mapping_request.json](files/data/f6fdd7c0-1-path_mapping_request.json)
- [b829da11-1-contract_acceptance.json](files/data/b829da11-1-contract_acceptance.json)
- [relay-materials-1-c617d116d7.zip](files/archives/relay-materials-1-c617d116d7.zip)
- [relay-materials-2-d3f598c365.zip](files/archives/relay-materials-2-d3f598c365.zip)
- [relay-materials-3-02e8113369.zip](files/archives/relay-materials-3-02e8113369.zip)
- [relay-materials-4-dc22516766.zip](files/archives/relay-materials-4-dc22516766.zip)
- [P15_DeckRuntime_V0.1.zip](files/archives/P15_DeckRuntime_V0.1.zip)
- [P15_API.md](files/documents/P15_API.md)
- [invalid_play_cases.json](files/data/invalid_play_cases.json)
- [deck_patch_schema.json](files/data/deck_patch_schema.json)
- [deck.py](files/code/deck.py)
- [commands.py](files/code/commands.py)
- [deck_determinism_tests.py](files/code/deck_determinism_tests.py)
- [card_legality_table.tsv](files/data/card_legality_table.tsv)
- [example_requests.json](files/data/example_requests.json)
- [content.py](files/code/content.py)
- [P16_EnemyAI_V0.1.zip](files/archives/P16_EnemyAI_V0.1.zip)
- [47cc0e19-1-downstream_receipts.json](files/data/47cc0e19-1-downstream_receipts.json)
- [P16_API.md](files/documents/P16_API.md)
- [enemy_intent_schema.json](files/data/enemy_intent_schema.json)
- [5998045e-1-delivery_manifest.sha256.tsv](files/data/5998045e-1-delivery_manifest.sha256.tsv)
- [phases.py](files/code/phases.py)
- [types.py](files/code/types.py)
- [3568e96b-1-p14_adapter.py](files/code/3568e96b-1-p14_adapter.py)
- [p06_projection_results.json](files/data/p06_projection_results.json)
- [input_immutability_check.json](files/data/input_immutability_check.json)
- [boss_transition_cases.tsv](files/data/boss_transition_cases.tsv)
- [91352728-1-planner.py](files/code/91352728-1-planner.py)
- [demo_summary.json](files/data/demo_summary.json)
- [delivery_receipt.json](files/data/delivery_receipt.json)
- [README.md](files/documents/README.md)
- [integration_handoff.md](files/documents/integration_handoff.md)
- [intent_replay_fixtures.json](files/data/intent_replay_fixtures.json)
- [verification_status.json](files/data/verification_status.json)
- [source_input_receipt.json](files/data/source_input_receipt.json)
- [defect_log.json](files/data/defect_log.json)
- [final_executed_source_binding.json](files/data/final_executed_source_binding.json)
- [blockers.json](files/data/blockers.json)
- [interface_rfcs.json](files/data/interface_rfcs.json)
- [actual_path_request.json](files/data/actual_path_request.json)
- [contract_acceptance.json](files/data/contract_acceptance.json)
- [task_traceability.json](files/data/task_traceability.json)
- [test_p14_contract.py](files/code/test_p14_contract.py)
- [demo_execution.json](files/data/demo_execution.json)
- [f2508593-1-verification_status.json](files/data/f2508593-1-verification_status.json)
- [f8afeb71-1-blockers.json](files/data/f8afeb71-1-blockers.json)
- [c5643230-1-interface_rfcs.json](files/data/c5643230-1-interface_rfcs.json)
- [70e2cb02-1-defect_log.json](files/data/70e2cb02-1-defect_log.json)
- [lifecycle_execution.json](files/data/lifecycle_execution.json)
- [9c0e4c7f-1-demo_summary.json](files/data/9c0e4c7f-1-demo_summary.json)
- [service.py](files/code/service.py)
- [rules.py](files/code/rules.py)
- [cbe586b8-1-delivery_receipt.json](files/data/cbe586b8-1-delivery_receipt.json)
- [P17_CharacterPartyWallet_V0.1.zip](files/archives/P17_CharacterPartyWallet_V0.1.zip)
- [f0d2979d-1-README.md](files/documents/f0d2979d-1-README.md)
- [P17_API.md](files/documents/P17_API.md)
- [8fea69e4-1-integration_handoff.md](files/documents/8fea69e4-1-integration_handoff.md)
- [wallet_delta_contract.json](files/data/wallet_delta_contract.json)
- [wallet_concurrency_tests.py](files/code/wallet_concurrency_tests.py)
- [199cf48d-1-source_input_receipt.json](files/data/199cf48d-1-source_input_receipt.json)
- [delivery_manifest.sha256.tsv](files/data/delivery_manifest.sha256.tsv)
- [projection.py](files/code/projection.py)

