# P16 API 与 IC-07 / IC-12 接收说明

版本 `P16-ENEMY-AI/0.1.0-isolated`。以下是已实现的 Python 接口；共享消息形状仍是 P13 原 `YLTT-INTERNAL/0.1.0-isolated`。本地行为扩展属于待受理提案，不能将其直接塞进 P13 关闭额外字段的 DTO。

## 1. 输入来源与权限

`Catalog` 从 P06 原字节构建。打包入口 `bundled_catalog()` 同时核对 enemy_specs 和 boss_phase_graph 的固定 SHA。行为政策使用已实现语义的固定摘要，规则变化必须显式升级，不静默解释新政策。源字节留在不可变 `ContentBlob`，每次 `.value` 返回新对象。

所有业务 API 接受 P13 `BattleSnapshot` 和不可变 `BehaviorSnapshot`。后者绑定 battle_id、actor_id、revision、snapshot_sha256，携带 P13 当前缺少的字段。它必须来自可信 owner 的已提交状态或明确版本的测试夹具；不能由 UI 选择值、动画进度或本岗缓存冒充。

| BehaviorSnapshot 字段 | 含义 |
| --- | --- |
| `schema_version` | 固定 `P16-BEHAVIOR/0.1.0-proposal` |
| `battle_id / actor_id / revision / snapshot_sha256` | 与输入原快照精确绑定 |
| `enemy_slot` | 本敌下一次行动机会序号，从 1 开始；不等同动画次数 |
| `state_id` | P06 行为循环状态，或已被 owner 接受的 `DEGRADED_STRIKE` |
| `phase_epoch / phase_committed_ids` | owner 提供的阶段历史，不由 P16 增写 |
| `heavy_cooldown` | 随后被阻塞的本敌行动槽数量 |
| `charge` | 不可变 Charge 或 null，包含释放技能、锁定目标、代次、ready_slot、创建 token |
| `last_successful_single_target_slot` | 上次成功单体伤害目标的阵位，初值 -1 |
| `entry_wait_pending / degraded` | owner 已接受的等待/降级状态 |
| `targetable_ids` | 当前玩家合法目标集合；P13 Unit 尚未承载 targetable |
| `pending_reactions` | 来自 P14 检查点；大于 0 时只 DEFER |
| `graph_available` | 逻辑图可用性；不能用图片是否加载成功代替 |

P16 只读使用 HP、护盾、终局和阶段。`EnemyAction` 中的基础伤害是内容说明；实际扣血必须由 P14 按已冻结技能配置计算。P16 不接收或返回可直接执行的任意 HP 写入。

## 2. 核心调用

```python
from enemy_ai import bundled_catalog, publish_intent, resolve_intent
from examples.fixture_inputs import snapshot, context

catalog = bundled_catalog()
snap = snapshot()                  # 明确的隔离夹具，不是正式存档
behavior = context(snap)            # 明确的行为扩展夹具
preview = publish_intent(snap, behavior, catalog)
candidate = resolve_intent(snap, behavior, catalog, preview.announcement)

print(preview.view.value)
print(candidate.intent.value)        # 原 P13 EnemyIntent
print(candidate.behavior_candidate.value)
```

此例已由同一实际实现的作者测试覆盖。真实接线需 owner 提供输入，不能照搬 `examples/fixture_inputs.py` 的测试数值。

### publish_intent(snapshot, behavior, catalog) → Decision

在玩家下一次决策窗口前调用。稳定选择下一敌方行动槽的技能和目标，返回 `Announcement` 和只读视图。正常情况下 `disposition=PREVIEW_CANDIDATE`，不产生行为更新候选，也不改变 RNG。

Announcement 记录原快照 SHA、revision、turn_number、enemy_slot、state_id、phase_epoch、内容与图哈希、行为语义哈希、完整行动以及 guard_reason。`intent_token` 是这些字段的确定性摘要，便于回放和防错；**它不是授权签名**。输入仍须由可信 owner 装配。

目前 P14 没有预告存储字段。本包不会把“生成了预告候选”称为“预告已被 P14 原子提交”。生产 UI 必须等 owner 提供正式存储/读取端口。

### resolve_intent(snapshot, behavior, catalog, announcement) → Decision

在 P14 对敌方入口 DOT、反应、死亡和终局检查完成后调用。只接受当前 `ENEMY_READY` 快照。先验证语义版本及绑定，再检查关闭/待排空/死亡/待阶段受理，随后验证冻结行动和合法偏差。

| 情况 | 返回/处理 |
| --- | --- |
| 同快照、同种子、同冻结记录 | 同输出字节；不消耗 RNG |
| 锁定单体死亡、移除或失去 targetable | SAFE_SKIP，无替换目标 |
| 群攻部分目标失效 | 仅删原名单失效项；视图标 `LOCKED_TARGETS_FILTERED` |
| 预告本来就是零目标/冷却跳过，之后条件改善 | 保留已冻结跳过，不偷换成攻击 |
| 释放标记缺失、提前、过期 | 明确跳过；提出清标记和合法后继 |
| 蓄力与正冷却矛盾、未知技能/状态 | `AiError`，不生成可执行候选 |
| 内容、槽位、turn、阶段代次或行为语义不匹配 | 拒绝旧预告；不暗中重选 |
| owner 已提交更高 epoch 且有合法 ENTRY_WAIT | 取消旧攻击，零伤害等待，偏差 `PHASE_REPLACED` |
| 缺逻辑图且基础技能有效 | `DEGRADATION_RECOMMENDATION`，必须经 P14 决策 |
| 已死行动者、终局、反应待排空 | NO_OP / TERMINAL / DEFER，无行为提交候选 |

P16 输出的 `observed_outcome` 只是只读输入的守卫判断，不是 BattleResult。最终胜负只由 P14 决定。

## 3. Decision / EnemyAction 的提交边界

Decision 包含 `action`、原共享 `intent`、本地 `view`、`announcement`、`behavior_candidate`、RNG 原值及明确 disposition/reason。所有实体不可变；`.value` 返回副本。

EnemyAction 字段为 `skill_id / intent_dictionary_id / kind / target_ids / base_amount_per_hit / hit_count / future_release_base_amount`。这不是替代 P14 `Action` 配置的执行命令。P14 按 skill_id 读取受信内容，P16 不能通过预告改伤害。

BehaviorCandidate 只包含以下可提议字段：下一 enemy_slot、state_id、heavy_cooldown、单体游标、charge、entry_wait_pending、degraded。**没有 hp、shield、current_phase_id、phase_epoch、revision、energy 或 wallet 写权限。**

候选携带 expected_revision、快照哈希、行为源哈希、内容 SHA 和原 intent_token。`slot_key` 绑定场次+敌方实例+行动槽，故同槽重算不能成为另一次业务机会；`candidate_id` 绑定本次完整候选。

P14 受理条件是 `ONLY_IF_ACTION_RESOLVED_ACTOR_ALIVE_AND_BATTLE_ONGOING_AT_SLOT_END`。根效果、反应或终局改变实际情况时，由 P14 丢弃相应行为变化；P16 不预先假定动作已经成功。拒绝、中断和回滚不消费槽。`view.slot_consumed` 始终 false，`slot_consumption_proposed` 单独标识是否提出消费。

`next_forecast` 仅描述本次成功后可能进入的循环状态/技能；目标为 null、certainty 明确是条件预测。正式下一回合锁定预告必须以 P14 提交后的新快照再次调用 `publish_intent`。

## 4. 阶段提议

```python
from enemy_ai import PhaseCheckpoint, propose_phases

plan = propose_phases(
    snapshot_after_drained_root,
    owner_behavior_snapshot,
    catalog,
    PhaseCheckpoint(root_command_id, before_hp, trigger_event_seq),
)
```

Checkpoint 的 before_hp 是根事务/owner-entry DOT 批次开始前 HP；输入快照中 actor.hp 是根效果与合法反应排空后的 HP。P16 不计算其中的伤害、治疗或反应。trigger_event_seq 必须已出现在检查点事件边界内；身份关联由 P14 的实际事务负责。

阈值使用整数交叉乘积，边按严格增大的 phase rank 遍历，并设遍历上限。多个阈值返回多个原 P13 `PhaseProposal`，而不是直接跳过中间边。proposal_id 与当前 P14 的 `BOSS_PHASE_PROPOSED` 身份算法一致；root command 和图哈希等 P13 未承载的信息放在独立 `evidence` 中。

一批非空提议提出一个最终阶段、一次 epoch 提升、一次等待、零额外行动的受理要求。空提议不重置等待或冷却。阶段图缺失只提供保留当前 phase 的降级建议。所有 PhasePlan 均 `authoritative_state_changed=false`。

**P14 v0.1 没有阶段受理命令。`inspect_phase_proposal` 仍抛出 `PHASE_COMMIT_CONTRACT_UNBOUND`，本包实测并保留这个阻塞。**

## 5. P14 原端口的可运行范围

`P14SingleSlotAdapter(catalog, behavior, announcement, rejection_type=..., scope='ONE_SLOT_CONTRACT_TEST_ONLY')` 实现 P14 原 `EnemyPlanner.propose(snapshot)`。

P14 在事务内部提供 post-DOT 快照时，适配器只重绑 snapshot SHA/revision，其他行为事实来自明确输入。它不会从回合数猜测轮换游标，不持有“已成功执行”缓存，不提交 BehaviorCandidate，也不承诺连续回合保存了行为数据。

装配端必须传入实际 P14 所使用的 `CandidateRejected` 类，防止同名不同模块的异常类型被误判为内部故障。本包用原 P14 实测拒绝不会改成 FAULTED。

当前三项共享限制必须由 owner 修复后才可正式接入：行为状态/冻结预告未承载；多敌有序行动口未绑定；P14 固定 target_count 不支持有效群攻目标数量变化。单槽测试中的技能配置是 P06 数值的明确测试映射，不是批准正式内容。

## 6. IC-12 表现接收

P19/P27 读取 `view.phase_id`、`phase_epoch`、字典 intent ID、action.kind、基础伤害/段数、future_release_base_amount、锁定目标和偏差原因。基础伤害标签固定 `BASE_DAMAGE_NOT_HP_LOSS`。实际伤害数字/HP/护盾变化只能读取 P14 提交事件。

图片与动画没有参与运行库的选择输入。缺阶段图片属于资源后备；缺逻辑阶段图才是 AI 降级建议。P06 的缺图与禁动画用例只验证逻辑投影不变，本轮没有运行 UI、图片导入或动画系统。

## 7. 错误与版本处理

输入快照旧版、错误 binding 或内容版本直接抛 `AiError`；调用端可交 P14 拒绝或安全关闭，不得继续旧招。动作取消返回清晰 reason；待排空与阶段受理返回 DEFER。运行库无持久状态，重启/中断后以同一固定输入可重新计算。

目标版本接受范围、本轮未受理部分、base SHA 与 RFC 见 `handoff/contract_acceptance.json` 和 `handoff/interface_rfcs.json`。P12 的 Anki 跨进程协议、P21 存档事务及 P22 正式内容规范均未被改写。
