# 《言灵旅团》P02 核心战斗状态机与确定性结算规范

- 规则版本：`P02-BATTLE-0.1.0-draft`；任务：`TASK-01-01`；阶段：S01，预留 S03/S07 扩充
- 文档状态：`LOCAL_SPEC_PRODUCED / P13_DTO_PENDING / P32_RUNTIME_TEST_NOT_RUN / P35_REVIEW_NOT_RUN`
- 来源：P01 `P01-S00-V0.1` ZIP（SHA-256 `139034e2179fbe35c4ac5f3240b0df435b03b9a70f5507263ee97b7e8b022a89`），P01 `REQ-005/006/007/008/009/015/019/021/023/024`、V6.0 P02 职责。实际工程授权路径与 P13 DTO 尚未提供。
- 权限：本版仅是**独立暂存的版本化技术语义草案**。不更改 P03 卡牌数据/P05 数值/P06 敌人/BOSS 内容/P13 DTO/P14 战斗源码/P15 牌堆实现，也不授权仓库合并。所有示例值仅为测试夹具值（`TEST_ONLY`），不构成平衡参数。

## 0. 本版确定和未确定的界面

**确定的技术语义（本规则版本内）**：战斗命令串行化、唯一状态写入者 P14、原子提交、重复命令防重、纯逻辑事件与动画分离、效果结算全序、伤害先抵盾后扣血、立即标记死亡、反应队列排空后统一判定胜负、活体 BOSS 阈值提案先于后续行动但晚于致死和终局判断、同归于尽为 DRAW（技术性结算结果，不自动映射用户奖惩）。

**未由 P02 决定的产品内容**：初始角色/卡/BOSS 数量（DEC-004）、牌的费用和伤害值（P03/P05）、每回合回能量/抽牌数量/手牌上限/弃牌策略（P03/P05/P15）、无学习日是否供牌或能量（DEC-003）、失败/平局奖励或惩罚（P01/USER）、BOSS 数值与阶段阈值和阶段附加效果（P06/P05）、战斗时长/回合限制（P01/USER）。这些字段由测试专用 `fixture_policy` 明确注入；不可据此推断真实游戏参数。

## 1. 单一事实来源和提交

`BattleState` 是单场战斗的唯一权威快照；只允许 P14 对生命、护盾、资源费用、牌区、状态、回合、Boss 阶段提案标记、事件序号和结束状态进行提交。P15 提供 `DeckPatch` 候选；P03 卡牌定义/P06 敌方行为提供**只读配置/候选意图**；其余岗位消费 P14 已提交的事件，不得由 UI 或动画写回伤害。

所有接受的命令都携带 `battle_id`、唯一 `command_id`、`expected_revision` 和命令字段。以 `battle_id` 选唯一序列化队列；P14 在一个写事务中执行：读取 revision → 检查命令ID碰撞及前提 → 冻结所需内容参数 → 展开效果、触发、终局 → 写入新快照、命令指纹与逻辑事件 → revision 恰好 +1。禁止半次扣费、双写、动画回调插入结算。`COMMAND_COMMITTED` 作为最后一个逻辑事件，包含此次 `revision`；事务失败时不发布先前缓冲事件。

**去重检查优先于版本检查**：已接受命令的相同 `command_id` 且相同规范化指纹返回 `DUPLICATE_NO_OP`，不写快照、无新逻辑事件，旧业务 ACK 可以复用但不是新事件；同 ID 不同指纹返回 `COMMAND_ID_COLLISION`，不写快照。首次非法命令（无目标、费用不足、错误阶段、旧revision、无牌、非法卡面、终局后请求）返回明确拒绝码，既不记为已处理也不修改快照。无论成功或拒绝，客户端消息发送多次均不得造成多次物理扣费。

指纹的提案算法：按字段名 ASCII 字典序排列 JSON 对象键，数组保持原序，UTF-8 无多余空白，所有数值用整数和布尔（无浮点/NaN/Infinity），对完整命令字节算 SHA-256。该规范需要 P13 归属的内部 DTO/RFC 确认，不能将这里的 `TEST_ONLY` 快照直接视为现存 DTO。

## 2. 阶段图和合法命令

持久状态 `CREATED`、`PLAYER_READY`、`ENEMY_READY`、`PLAYER_TURN_PENDING`、`TERMINAL`、`ABORTED`、`FAULTED`。初始 `SYSTEM_START` 在一次提交内完成 `PLAYER_ENTRY_INTERNAL`，不另外发布 `PLAYER_TURN_PENDING`；`RESOLVING` 仅为单事务内部计算态，不发布为可由玩家交互的独立快照。

| 当前状态 | 输入 | 前提 | 后态 | 操作说明 |
|---|---|---|---|---|
| CREATED | `SYSTEM_START` | 双方部署、内容ID及 seed 合法 | PLAYER_READY / TERMINAL | P14 完成战斗入口、首次玩家回合入口；入场状态异常按终局判定 |
| PLAYER_READY | `PLAY_CARD` | 本方、卡实例在手、费用足、目标合法、revision一致 | PLAYER_READY / TERMINAL | 一个受理出牌事务，胜负后不得回 PLAYER_READY |
| PLAYER_READY | `END_TURN` | 玩家有行动权、revision一致 | ENEMY_READY | 先结束玩家回合；终局不能再次结束 |
| ENEMY_READY | `SYSTEM_ENEMY_ACTION` | 首先完成敌方 OWNER_TURN_ENTER DOT 与终局检查，再消费 P06 版本化意图 | PLAYER_TURN_PENDING / TERMINAL | 敌方回合入口先 DOT、死亡反应和终局检查；存活者再按稳定顺序行动，无合法目标可按 P06 明示策略跳过 |
| PLAYER_TURN_PENDING | `SYSTEM_ENTER_PLAYER_TURN` | 非终局 | PLAYER_READY / TERMINAL | 开始玩家回合：先 DOT/触发/终局，再刷新回合资源/抽牌 |
| CREATED/PLAYER_READY/ENEMY_READY/PLAYER_TURN_PENDING | `ABORT` | 退出授权；事务未开始或序列化安全点 | ABORTED | 非胜败、无胜利奖励；中间态出于崩溃不能宣称提交 |
| 任意非终局 | 内部不变量/触发上限故障 | 有结构化 fault 证据 | FAULTED | 回滚失败事务，独立提交安全故障；不结算奖励 |
| TERMINAL/ABORTED/FAULTED | 任意玩法命令 | 永久结束/异常 | 不变 | `ALREADY_CLOSED`；同 ID 重试先走去重判定 |

> 状态图实体：`spec/battle/state_machine/battle_state_machine.mmd`；逐步事务次序：`turn_sequence.tsv`。`SYSTEM_*` 为受内部调度器驱动的命令类型，非 UI 可随意发送的玩家指令。`SYSTEM_ENEMY_ACTION` 的具体 AI 和意图归 P06/P14，`SYSTEM_ENTER_PLAYER_TURN` 的抽牌/区段修补候选归 P15。

## 3. 纯逻辑全序（P02 技术约束）

1. **入口验证**（无写入）：命令ID碰撞和重试、`battle_id/revision/phase/actor`、卡实例及所有已选择目标是否合法、值域和内容版本、余额能否覆盖费用。任一步拒绝均全不消费。玩家 `PLAY_CARD` 不能静默地将无目标攻击重定向到其他敌人。对于内部 `SYSTEM_ENEMY_ACTION`，如果 P06 已显式给定 `NO_VALID_TARGET=SKIP`，则允许在原子事务中跳过这次敌方动作并推进回合；未给 fallback 的不可冒充为默认策略。
2. **事务接收**：缓冲 `COMMAND_ACCEPTED`，冻结版本化 `EffectIntent` 与所有显式目标顺序。若多目标要求系统默认排序：按 `side_rank`(PLAYER=0, ENEMY=1)→`formation_slot/spawn_index` 升序→`unit_id` UTF-8 字节序；不能以 UI 图层顺序排序。
3. **唯一费用事务**：P15 的合法性/费用/牌区候选由 P14 再校验并在同一个 BattleState 提交。先缓冲 `ENERGY_SPENT` 再 `CARD_MOVED`（若该命令需要支付/弃牌），之后才能生效；被拒绝无费用事件。费用为非负整数，由外部获批配置提供，本规则绝不固定卡牌价格。
4. **效果展开**：按卡内 `effect_index` 升序、目标稳定顺序逐项处理，缓冲 `EFFECT_STARTED`。一次原子伤害先计算已批准修正量（若不存在则直接整数 amount），先扣护盾 `absorbed=min(shield,damage)`，余量才扣 HP `hp_loss=min(hp,damage-absorbed)`；统一缓冲 `DAMAGE_APPLIED`，记录 raw/absorbed/hp_loss/overkill；不使 shield/HP 为负。治疗仅给存活合法目标，封顶 max_hp；护盾增加只到配置上限，溢出策略须 P05/P13 明示，不得隐式溢出。
5. **死亡检查**：每次原子伤害或 DOT 落地立即判定 `hp=0`；第一次死亡缓冲 `UNIT_DIED`，该目标此后不能接收通常卡牌或敌方行为（除明确支持且批准的尸体效果，当前版本不支持）。死亡触发的合法 `ON_DEATH` 反应仍能被排队，死亡不自动清除已排队的合法反应。
6. **反应队列**：对各原子效果产生的触发按 `reaction_tier`→`parent_event_seq`→`source unit order`→`effect_index`→`trigger_id` 排队；采用宽度优先 FIFO：先完成当前根效果列，再一层层排队处理反应，反应新生成的子反应追加队尾。触发ID `(battle_id, root_command_id, source_unit_id, trigger_id, source_event_seq)` 同事务最多执行一次；最大反应处理次数 1024 属安全防死锁限制，超过则整事务回滚并 FAULTED，不当作胜利。
7. **终局归并**：仅在根效果、死亡与合法反应队列完全排空的**结算检查点**计算双方活体数量；玩家存活且全部敌方死亡=WIN；玩家全死且敌方存活=LOSS；双方全死=DRAW；双方都活=ONGOING。胜负是互斥的枚举，不得在 WIN 后又写 LOSS。`BATTLE_FINISHED` 仅一次。普通卡牌当场杀死最后敌人也不能被后续未处理的死亡反击绕过。
8. **BOSS 阶段提案**：只在非终局检查点，目标 BOSS 仍存活且与 P06 版本化阈值满足真实跨越条件、该 phase_id 未曾提案时，缓冲 `BOSS_PHASE_PROPOSED` 并登记已提案 ID。阈值只在 `TEST_ONLY` 夹具中给值；P06 才有权定义触发阈值/免疫/切阶段效果。提案不直接改变 `boss_current_phase`，后续 P06 候选/P14 提交需要 P13 契约版本。不准在同一次致死时先变阶段后复活；有多阈值同时跨越时按 P06 阶段 graph 的可达顺序逐个提案，不能无定义跳跃。
9. **回合推进与资源抽牌**：仅非终局才能结束玩家回合、开始敌方意图、进入下一玩家回合。双方回合入口统一顺序（敌方在 ENEMY_READY 接收 SYSTEM_ENEMY_ACTION 时亦先执行本方入口）：单位存活校验→本方 `OWNER_TURN_ENTER` DOT（按稳定单位顺序、状态插入序）→死亡与合法反应→终局→状态剩余次数处理→资源刷新→P15 牌堆规则补牌→`PLAYER_TURN_STARTED`→提交。抽牌不足时 P15 是否对弃牌洗牌由其获批策略决定；即使两区均空也不无限循环，不擅加疲劳伤害或凭空生成卡。
10. **提交**：检查 `BattleState` 全部不变量，分配递增逻辑事件 `seq`，缓冲 `COMMAND_COMMITTED(revision=previous+1)`，原子写入快照和事件及已接受命令摘要。视图/UI/轻动画只能消费事件，不能回调改写结算。关闭、加速、跳过或重播动画均不改变战斗种子、命令列表、快照和逻辑事件字节。

绝对禁止：用实时时钟、浮点不定序、主线程帧率、线程完成先后、界面卡牌控件索引、外部 Anki Hook 到达时刻或动画播放状态参与战斗随机性和排序。外部学习资源的入场发放必须由后续 S05 事务定义，不嵌在 P02 伤害公式中。

## 4. 固定随机性与 replay 语义

`replay_input = {spec_version, content_version, starting_snapshot, ordered_commands, initial_seed, rng_algorithm, deterministic_policy_version}`。如果上述全部字节相同，P14 必须产生完全相同的逻辑事件顺序及最终状态。`animation_enabled` 不属于 replay_input。

**提议的跨语言复现算法**：`xorshift32-v1`，seed 为 1..2^32-1 的无符号整数，初始 `rng_state=seed`；每次生成：`s ^= (s << 13)&0xffffffff; s ^= s >> 17; s ^= (s << 5)&0xffffffff`，每一步截断为 uint32，输出新 s，draw_count 加一。任何随机消耗只能由合同明示的逻辑步骤发起。P15 若要洗牌，候选采用 Fisher-Yates 从 i=n-1 到 1，逐次 `j=next_u32 % (i+1)`，交换数组 i/j，**数组左端是下一张被抽的牌**；该 `mod` 方案仅为 P02 回放夹具算法提案，需 P13/P15 契约确认后才能认定为正式引擎实现。

动画禁用/开启动画的两组 fixture 要求 `expected_state` 与 `expected_events` 完全一致；只允许 presentation_metadata 不同。

## 5. 边界规则与错误协议

- **玩家无目标/已死亡/阵营错误/选择数量错误**：玩家 `PLAY_CARD` 整命令拒绝 `TARGET_INVALID`；不扣费、不消卡、不自动选另一对象。内部敌方动作仅可依 P06 已显式配置的 `NO_VALID_TARGET=SKIP` 提交跳过事件。`AUTO_TARGET` 只有在 P03/P06 明示并经 P13 DTO 合约批准后才能展开，默认不存在。
- **重复点卡**：同命令 ID/同指纹返回 `DUPLICATE_NO_OP`；同 ID 不同内容返回 `COMMAND_ID_COLLISION`；使用不同 ID 重复同一个已被移出手牌的实例返回 `CARD_NOT_IN_HAND`。分别覆盖。
- **疲劳**：draw 和 discard 都为空时返回 `DRAW_SHORTFALL` 事件（抽不足但不是非法命令）；不补占位牌，不自动扣血。若策略批准洗牌，使用同一 RNG 流，洗牌与抽牌位序可复现。
- **BOSS 阈值和致死同一动作**：先完成伤害、死亡、合法反应、终局；BOSS 已死或任何一方全灭进入终局，则**不生成阶段提案**。
- **同归于尽**：例如敌人被击杀时死亡反击导致最后存活英雄死亡，必须得到 DRAW，不得先发 WIN 与再发 LOSS。
- **回合重复**：同 ID 重复结束回合无事件；新 ID 在 ENEMY_READY 阶段请求 END_TURN 则 `PHASE_INVALID`。
- **连锁失控**：回环触发标记止重 + 单次事务 1024 次反应安全门槛。门槛不是战斗持续回合限制，也不影响经审批的 normal damage 规格。
- **非法数值**：HP / maxHP / cost / shield / amount 非负整数，maxHP 正，HP≤maxHP；任何溢出或未知配置为拒绝/内部安全故障，不进行无符号回绕。需要 P13 明确 64-bit 整数、serialization 与溢出策略。
- **异常退出**：ABORTED/FAULTED 不等于 LOSS，也不发生首通/失败奖励；是否支持持久续战、结算惩罚和离线缓存由其他 owner/用户裁定。

## 6. 下游接口提案（不是既有接口）

| Owner | 最小请求/响应语义 | 拒绝越权 |
|---|---|---|
| P13 | 版本化 BattleState/Command/LogicEvent/DeckPatch/Intent DTO，整数与排序、schema、canonical fingerprint | P02 不创建 P13 正式 DTO |
| P14 | 唯一提交者；按输入重放及 state revision/version CAS；纯逻辑事件和阶段提交 | P02 不实现引擎；P15 不直接扣费 |
| P15 | 验证后的抽牌、手牌迁移/弃牌/回能候选；固定 seed shuffle 顺序 | P15 不写 HP/energy/turn/revision |
| P03/P05 | 卡效果定义、目标/费用/数值、回合资源和弃牌政策 | P02 不覆盖卡配置与平衡 |
| P06 | 意图排序、目标选择、BOSS 阈值/phase graph/transition proposal | P02 不编敌人 AI 与阈值数值 |
| P16/P19 | 只读逻辑事件→卡面和血条等表现，缺动画仍逻辑等价 | UI 不触碰 BattleState |
| P32/P35 | P32 根据 fixtures 测 P14；P35独立审查证据和契约放行 | 本岗静态自检≠P32/P35 PASS |

关联 IC-02/IC-05/IC-07；契约 owner 由 V6 原文而非测试样本决定。正式 RFC 见 `../resolution/interface_rfc_and_blockers.md`。

## 7. 当前验收状态

P02 已可提交：实体状态规范、图、流程时序、优先级、真值表、回放夹具及静态可复核报告。P13 路径映射、内容 Schema 及 DTO 尚缺，故 `SPEC_IMPLEMENTATION_GATE=BLOCKED`；未执行 P14 单元/契约实测、UI 关闭动画实际对比、引擎运行或 Anki 端到端，均为 `NOT_RUN`。由 P32 执行独立运行测试、P35 出具独立审查结论后才可升级相应门禁。
