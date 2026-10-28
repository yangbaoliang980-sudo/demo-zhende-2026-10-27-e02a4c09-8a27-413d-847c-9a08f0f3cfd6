# P02 → P13 隔离语义投影的验证范围

版本 `P14-P02-PROJECTION/0.1.0-isolated`。实现位于 `resolution_replay_tests/p02_adapter.py`，仅供测试，不是生产迁移器，不修改任何 P02／P13 原文件。原始文件与 SHA 见 `evidence/source_input_receipt.json`。

## 输入如何形成

P02 的原始 initial_state、commands、fixture_card_catalogue 和 fixture_policy 构造 P13 消息与 P14 私有内容投影。预期输出仅在断言阶段读取，不用于生成核心结算结果。P15 的测试候选手工显式声明费用 delta 和牌移动；不会在 P14 内重新实现抽牌／洗牌／费用算法。

状态 ID、revision、HP、盾、费用、牌区、效果数值与测试政策原值保留。P02 的 `formation_order` 对应 P13 `slot`，`remaining_owner_turns` 对应 `remaining_triggers`；状态 ID 与来源单位使用明确的隔离映射。P02 无 exhaust 牌区，在本组初态补空数组。卡内容版本与候选政策版本使用 `fixture:*`，不是正式 P22 ID。

已执行的夹具初态均有 RNG draw_count=0，因此可把初始 state_u32 作为 initial_seed。若将来收到 draw_count 非零而无初始 seed 的旧状态，此适配器会阻塞，不猜造种子历史。F014 的候选明确携带两次 xorshift 后的 state=67634689 与声明牌序，核心只核验状态跃迁与移动守恒。

回合号依据 P02 完整回合夹具：ENEMY_READY → PLAYER_TURN_PENDING 时递增；进入下一 PLAYER_READY 不再递增。首轮作者误读的实现已修复；上游规格和夹具从未改动。

## 输出如何比较

状态比较覆盖战斗身份、revision、phase、turn_number、energy、所有单位 HP／盾／存活／状态、BOSS 当前／已提议阶段、hand／draw／discard、RNG、胜负。**不比较旧 event_cursor 和旧 processed_commands**，因为两版事件数量及命令规范字节不同。exhaust 与 P13 新增字段另由原校验器和本版测试约束，不能从本投影得出旧版逐字段等价结论。

P02 的终局字段只用 WIN／LOSS／DRAW，退出时为 null；P13 将退出表示为 phase/outcome=ABORTED，因此 F025 投影时 outcome 映射回 null，仍保留 phase=ABORTED。没有把退出伪造为战败或生成 BattleResult。

答复将 P02 ACCEPTED 映射为 P13 COMMITTED，空错误码映射为 OK；其余拒绝代码比较原值。事件比较保留投影后的顺序、数量和表中可映射字段；**不比较旧 seq 原值**。P13 事件连续 seq、批次 revision、字段闭合等另外用原校验器与本版测试验证。每个可执行场景还会重执行回放，比较 P13 完整状态、批次和结果规范 bytes。

| P02 事件 | P13 比较内容 |
|---|---|
| COMMAND_ACCEPTED | 事件类型；新版信封由 P13 校验 |
| ENERGY_SPENT | amount、energy_after |
| CARD_MOVED | instance_id、from_zone、to_zone |
| CARD_DRAWN | 转为 draw → hand 的 CARD_MOVED |
| DECK_SHUFFLED | 按 resulting_order 转为 discard → draw 的 CARD_MOVED；不是批准新的洗牌事件合同 |
| EFFECT_STARTED | effect_index、单目标数组 target_unit_ids |
| DAMAGE_APPLIED | source_unit_id、target_unit_id、raw、absorbed、hp_loss、overkill |
| SHIELD_GRANTED | SHIELD_CHANGED：target_unit_id、delta、shield_after |
| HEAL_APPLIED | target_unit_id、实际 amount、hp_after |
| STATUS_APPLIED | STATUS_CHANGED：status_id、target_unit_id、operation=ADDED |
| STATUS_DURATION_UPDATED | STATUS_CHANGED：operation=UPDATED／REMOVED |
| BOSS_PHASE_PROPOSED | unit_id、to_phase_id |
| ENEMY_ACTION_SKIPPED | unit_id、reason_code |
| BATTLE_ABORTED | reason_code |
| 其余可表达事件 | 保留类型及除旧 type／seq 外的可比 data 字段 |

以下旧中间事件在 P13 冻结 Schema 中没有对应类型，因此从本次比较中排除：`TRIGGER_QUEUED`、`TRIGGER_STARTED`、`STATUS_TICKED`、`ENERGY_REFRESHED`、`ENEMY_ACTION_STARTED`、`ROUND_ADVANCED`、`DECK_RECYCLED`。部分过程在 P14 私有调试 trace 中可追踪，但 trace 不冒充公开事件或第二套权威序号。RFC-002 请求原 owner 处理正式事件兼容。

## 4 个明确阻塞的历史场景

F010／F011／F021／F028 的 processed_commands 只有旧 command SHA，缺少对应完整原请求以及 P13 新回执的 committed_revision／事件范围等必要历史。旧 hash 不能逆推出新 canonical bytes，也不能证明新指纹身份。

四例保持 `BLOCKED`，在 unittest 中使用 skip，报告不计入 PASS。需要 P02/P13 提供完整历史与版本化迁移；没有删除原例或重写成伪造的“通过样例”。当前 P13 格式下的同 ID 同指纹重试、碰撞、旧 revision、新 ID 重打弃牌等已另外通过真实提交历史测试。

本轮结论是 **29 个旧场景在上述语义投影下 PASS，4 个 BLOCKED**；旧格式逐字节合同兼容仍为 BLOCKED。`evidence/p02_projection_results.json` 记录每例结果和实际输出哈希。P32 独测与 P35 独审未执行。
