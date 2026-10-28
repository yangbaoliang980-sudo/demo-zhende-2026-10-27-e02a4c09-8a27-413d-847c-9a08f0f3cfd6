# 内部契约语义｜YLTT-INTERNAL/0.1.0-isolated

## 1. 权限、范围与版本

形状 owner 为 P13，实际领域 producer 见 `internal_api_contracts.json`。本版在 P13 隔离包内冻结，可用于各 owner 的独立 Mock 开发；不声称 IC-05、IC-10、IC-17、IC-18、IC-19 等外部合同已被其 owner 接收。有关更改必须经过 `interface_rfcs.json` 中的 RFC。

运行参数 `isolated` 不授权生产。`require_isolated('production')` 抛出 UnboundPort；包内没有生产引导入口。修改 `production_authorized` 布尔值不能补齐源工程、政策、真实身份、物理事务或独立验收。

消息中的 owner、trusted、durable 自报字段不得赋予能力。权限来自明确的 composition root、原 owner 的已核验实现与 P21 的权威查询。PortRegistry 的检查用于防止装配错误，不构成恶意同进程代码的隔离机制。

## 2. 序列化

每个公开 DTO 必须包含 `contract_version` 和 `dto_type`，只能使用固定版本。全部对象关闭 additionalProperties，未知 tag/字段拒绝。Schema 为 Draft 2020-12；`contracts.py` 是只覆盖本包关键词的封闭子集校验器，不冒充通用 JSON Schema 实现。独立 `jsonschema` 的结构算法对照与跨字段语义测试分开记录。

线格式限制：UTF-8 无 BOM，最大 1,048,576 字节，嵌套深度最多 32，值/键节点最多 100,000；这些是隔离解析安全界限，不是游戏内容规模审批。JSON Schema 的数组上限仍须同时满足字节与复杂度界限。

键限 ASCII Schema 名；字符串不包含控制字符或孤立 surrogate；所有数字为安全整数，bool 不作为整数；浮点/指数形式数字、NaN/Infinity、重复键全部拒绝。对象按键 ASCII 顺序编码，数组保持输入顺序，UTF-8 不做 Unicode 归一化，不输出多余空白。完整规范字节的 SHA-256 是指纹。不能将排序后的目标数组替换原数组再计算同一命令指纹。

P02 的 command fingerprint 具体化为完整 `BattleCommand`（含版本、battle_id、command_id、expected_revision、kind、payload）的规范字节 SHA-256。重试必须保留原 expected_revision；若为旧 command_id 改 revision，便是不同指纹，不能伪装原请求重试。`canonical_vectors.json` 固定 25 组跨语言向量。

## 3. 战斗 DTO

| DTO | 生产/接收 | 核心约束 |
|---|---|---|
| BattleCommand | P19 用户输入；内部 SYSTEM 命令由受控调度端口 | PLAY_CARD 必须有 actor/card_instance/显式目标；END_TURN 与 SYSTEM payload 为空；ABORT 有 reason_code |
| BattleSnapshot | P14 → P15/P16/P19/P29 | 只读视图副本；固定 rules/content 版本、revision、phase、牌区、单位、RNG、last_event_seq |
| BattleState | P14 私有权威状态的共享序列化形状 | snapshot + accepted_commands；接收者不得写入 |
| BattleEvent | P14 → 只读消费者 | 每场单调 seq；包含 command_id、revision、event_type 和封闭 payload |
| BattleCommitBatch | P14 → P19/P29 | 完整提交批次；previous_revision+1 等于 snapshot.revision；事件连续且都绑定同一场/命令/revision |
| BattleReply | P14 → 发起者 | COMMITTED 必须包含批次；重复或拒绝不再发布批次 |
| BattleResult | P14 → P18 | 不可变终局引用；绑定 battle_id、终局 revision/seq、stage/profile、内容/规则版本与快照/回放哈希 |
| DeckPatchCandidate | P15 → P14 | 候选牌区移动、费用变化、RNG 前后状态；绑定命令/快照指纹与 expected_revision；无 HP 写入口 |
| EnemyIntent / PhaseProposal | P16 → P14 | 只声明版本化意图或阶段候选，不修改 HP/phase |

BattleSnapshot 的卡实例必须恰好出现在一个牌区；owner_unit_id 必须引用现有单位；单位/同阵营槽位/状态实例不得重复；HP 不超过 max_hp。TERMINAL 只对应 WIN/LOSS/DRAW，ABORTED、FAULTED 不转成失败奖励。Schema 并不验证卡定义合法性、伤害公式或真实战斗终局，均由 P14/P22 按上游合同验证。

所有已接受命令的去重检查由 P14 优先执行。相同 ID/相同指纹 → DUPLICATE_NO_OP，保持状态与 seq；相同 ID/不同指纹 → COMMAND_ID_COLLISION。首次非法请求不能改变权威状态。费用、牌区、伤害/治疗/状态、死亡、终局与 receipt 在 P14 的同次提交中完成。P15 的 energy_delta 是候选，不是另一次扣费。

SYSTEM_* 只能通过受控内部调度调用 P14，不能从 P19 的用户命令邮箱进入。当前 `CommandMailbox` 用户端只接受 PLAY_CARD/END_TURN；ABORT 的授权流程未实现。P13 不执行战斗状态机，也不把静态样例的 END_TURN 后态冒充实际 P14 结算。

RNG 状态记录 `xorshift32-v1`、initial_seed、state、draw_count。其演算与洗牌规则仍由 P14/P15 接收 P02 提案后实现。`DeckPatchCandidate` 必须在 P14 重新核验基准版本及 RNG before 后使用；不能直接把候选变成第二个权威状态对象。

## 4. 角色、钱包和存档 DTO

PartySnapshot 有且仅有 3 个槽位 0/1/2，不等于正式可收集角色总数为 3。角色唯一性继承 P04 的草案约束，未加入“攻击/防御/治疗各一”的强制定位限制。正式角色 ID 仍归 P22。

WalletSnapshot 由 P17 提供只读可用/预留余额；禁止负可用余额和重复资源项。WalletDeltaCandidate 由 P17 产生，包含 expected_wallet_revision、before SHA、intent SHA、按资源变化和来源分摊。来源分摊必须与变化一致；学习、首通、重复掉落、获批补偿和角色消费分域。这里不决定 Undo 后负债、消费追溯分配算法、发奖金额或日界政策。

P11 原来的 WalletDelta.source_after 是独立提案中的内部结构。新 DTO 不自动把它删掉或映射为通用字典；P17/P21 须在 RFC 中决定完整无损的生产模型。当前形状只用于隔离边界验证。

AtomicCommitProposal 是 P21 待接收的协调提案，domain_candidate_sha256 引用完整领域候选，并非仅凭一个哈希即可持久化。其 resolver、校验与事务生命周期要由 P21 定义；本包没有 execute_once、数据库、备份或崩溃恢复实现。

CommitProofView 只表达 P21 查询得到的技术投影：transaction_id、request_sha256、store_instance、sequence、receipt_sha256、snapshot_sha256、high_watermark、continuity_ref。sequence 不得高于水位。任何客户端自行构造相同形状，都不能变成权威回执。

CommitLookupView：COMMITTED 必须有绑定同 transaction/store/watermark/continuity 的 proof；ABSENT 必须有已证明的实例/水位/连续性但无 commit proof；UNKNOWN 不允许携带 commit proof。未知提交结果应查询原事务，不能改 transaction_id 重试授奖。

StageProgressView 只读展示解锁与首通 ID，P18 保留 stage 级永久首通键与 battle 级重复领取键的区别。SaveStatusView 只报告运行可用性，READY 必须有存档实例/格式/水位。AssetRef 仅引用 P22 的 asset_id、内容版本和导出哈希；不提供磁盘任意路径。资源导入及 PLACEHOLDER/APPROVED 由 P30 管理。

## 5. P11/P12 只读投影

StudyStatusQuery 绑定 `{source_id, collection_lineage, beneficiary_id}` 作用域和 inbox_id。P12 从配对作用域构造查询，不能让远端自填另一受益范围。

StudyStatusView 只表达当前账本状态、原因和 P21 查询投影，不返回钱包金额、笔记正文、管理命令或存档路径。APPLIED/REVERTED/QUARANTINED/PENDING_RECONCILIATION/业务 REJECTED 必须绑定持久提交投影；NOT_FOUND 必须绑定连续性观测；UNKNOWN 不做否定或成功承诺。

该投影应在一个一致读取边界得到。P11/P21 接收后必须明确查询过程中状态变化、旧备份/世代变化和投影过期的处理；不能顺序读取几个可变字段就宣称同一快照。P12 现有重查/验证要求保持有效，不能因为新增 DTO 就取消二次权威核验。

P12 传输前置拒绝可没有账本状态或回执；那不是本 DTO 的持久业务 REJECTED。ACK_QUARANTINED 不等于到账，REVERTED 不等于新增奖励，PENDING 不承诺完全没有经济变化，历史 ACK 不等于当前余额。`YLTT-ANKI-TRANSPORT/0.1.0-isolated` 原线协议保持原字节。

## 6. 兼容、变更和验收

只接受精确隔离版本；没有自动协商到未知 minor 的逻辑。修改字段、可接收值域、意义、排序、错误映射或指纹必须新版本+新向量；解释/测试补充可采用交付补丁但不能改变已冻结字节。以新包提供修订，保留旧包及双方 base SHA，不能原地改历史证据。

P13 作者测试验证解析与边界，P32 需要独立复测；P14/P17/P21 的业务实现、P19/P29 的视图、真机、真实 Anki 和 E2E 另列 NOT_RUN。各接收方只能签自己的接收记录；当前回执状态为 PREPARED_NOT_ACKNOWLEDGED。
