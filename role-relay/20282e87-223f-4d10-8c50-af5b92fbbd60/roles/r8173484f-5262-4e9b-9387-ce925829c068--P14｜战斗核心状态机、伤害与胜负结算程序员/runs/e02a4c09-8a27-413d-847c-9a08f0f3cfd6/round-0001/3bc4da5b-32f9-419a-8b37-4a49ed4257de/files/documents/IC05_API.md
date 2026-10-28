# P14 IC-05｜可直接接线的隔离 API

版本 `P14-BATTLE-CORE/0.1.0-isolated`；公开消息沿用 P13 `YLTT-INTERNAL/0.1.0-isolated`。只运行于新隔离目录。Python 3.12；核心不依赖引擎、渲染、时钟、数据库或第三方包。

## 1. 最小复现

```python
from examples.demo import build_demo
from battle_core.replay import replay

core, commands, scripted_p15, scripted_p16 = build_demo()
for cmd in commands:
    if cmd.value["kind"].startswith("SYSTEM_"):
        reply = core.submit_system(cmd)   # 只由可信宿主调度
    else:
        reply = core.submit(cmd)          # P13 BattlePort 用户入口
    assert reply.value["result"] == "COMMITTED"
    assert reply.value["code"] == "OK"

snapshot = core.snapshot("fixture:demo")
result = core.result()
again = replay(core.export_replay())
assert again.state().raw == core.state().raw
assert again.result().raw == result.raw
```

`build_demo()` 是带明示脚本输入的演示装配，不是生产入口；`mode="production"` 会报依赖未满足。正式装配必须等待 P13 映射、真实 provider、内容与环境证据，以及用户指定的整合者。

## 2. 命令入口

| API | 输入 | 返回／效果 |
|---|---|---|
| `core.submit(command)` | FrozenMessage 或可验证的 BattleCommand 对象；仅 PLAY_CARD／END_TURN | 不可变 BattleReply |
| `core.submit_system(command)` | 仅 SYSTEM_START／SYSTEM_ENEMY_ACTION／SYSTEM_ENTER_PLAYER_TURN | 可信宿主调度入口；不能直接暴露给 UI 或网络 |
| `core.abort(command)` | kind=ABORT，payload.reason_code | 显式退出能力；安全点关闭，无 BattleResult |
| `core.snapshot(battle_id)` | 当前场次 ID | BattleSnapshot 的不可变消息；value 为新副本 |
| `core.state()` | 无 | BattleState（含命令回执），供诊断／回放验证 |
| `core.result()` | 无 | 当前 BattleResult 或 None |
| `core.committed_batches()` | 无 | 不可变已提交批次序列，不含被拒绝或回滚的事件 |
| `core.resolution_traces()` | 无 | P14 私有调试 trace，不是第二套 BattleEvent seq |
| `core.export_replay()` | 无 | 已提交输入链；`value()` 可导出，`sha256` 为版本化摘要 |

无合法 wire 身份的请求（未知字段、重复键、错误版本、重复目标、bool 冒充整数等）抛 P13 `ContractError`，不伪造 ACK。能识别身份但不合法的请求返回 `BattleReply(result="REJECTED", commit=None)`。

已通过通道和 battle_id 的请求，优先查已接受 ID。重复时不调用 provider、不改变 seq/revision、不再次发布旧批次。更换 ID 再打已弃置实例会得到 CARD_NOT_IN_HAND，不能凭新 ID 二次扣费。

## 3. P15 接口与职责

复用 P13 的端口形状：

```python
def propose(command: FrozenMessage, snapshot: FrozenMessage) -> FrozenMessage:
    # 返回 P13 DeckPatchCandidate；只产生纯候选
    ...
```

候选必须绑定 battle_id、command_id、expected_revision、完整 command_sha256、**本次实际收到的 snapshot.sha256** 和冻结 policy_version。RNG before 必须完全等于 basis；after 的 seed 不变、draw_count 不倒退，state 必须可由 xorshift32 真实推进得到。

P14 不在 Action 模型中存成本，不重算折扣／费用合法性，不选抽牌、不洗牌。P14 只应用可信 P15 的 `energy_delta`，检查安全整数、结果余额非负、PLAY_CARD 费用方向、牌实例守恒和实际移动有效性；消费的牌必须落入 P03 对应动作声明的牌区。候选失败时连同已经缓冲的费用、牌区和事件全部抛弃。

P14 会在 PLAY_CARD、END_TURN、SYSTEM_START、SYSTEM_ENTER_PLAYER_TURN 调用 P15。END_TURN 的无迁移也要显式 no-op 候选；不偷偷决定保留或弃掉手牌。

玩家入口顺序：处理 DOT → 排空反应 → 判终局 → 更新存活者状态时长 → 请求 P15。此时传入的是**事务私有、未发布、revision 仍为上次提交值的 post-DOT basis**。P15 应只据它形成候选，不把它发布为已提交快照。最终若候选拒绝，前面本事务的 DOT 同样回滚。终局已成立则完全不调用 P15。

当前 P13 端口缺负向候选答复与 requested_draw_count。隔离适配允许抛 `CandidateRejected(code)`；缺 provider 抛 `DependencyUnavailable`。测试的 `entry_draw_requested` 显式从夹具政策注入，只用于 DRAW_SHORTFALL 记录，不控制抽哪些牌。正式语义等待 `P14-RFC-003`，不能把 Python 异常接口直接当成已批准 wire 协议。

## 4. P16 接口

```python
def propose(snapshot: FrozenMessage) -> FrozenMessage:
    # 返回一个 P13 EnemyIntent；不写 HP、turn、phase 或 RNG
    ...
```

敌方入口先处理 DOT／反应／终局，再消费意图。意图绑定 battle_id、当前 expected_revision、content_version 和存活敌 actor。技能效果来自本场冻结内容投影，UI 的目标或伤害自报不覆盖配置。目标列表保留顺序；未配置 fallback 时非法目标拒绝，只有明确 `no_valid_target="SKIP"` 才能跳过，不自动换目标。

当前 P13 端口只返回单个 EnemyIntent，未定义有序多敌批次及行动槽续接。本版仅执行单存活敌的该入口，多敌拒绝 `ENEMY_BATCH_CONTRACT_UNBOUND`，不默默漏掉其他敌人，也不临时替 P16 写 AI。

PhaseProposal 形状可校验，正式提交仍未绑定。当前已实现根效果／反应结束且非终局时的跨阈提案与防重复标记，不变更 current_phase_id；待提交阶段存在时阻止旧敌行动。阶段 epoch、取消蓄力和 ENTRY_WAIT 需要原 owner 批准的新合同。详见 RFC-004／005。

## 5. P19／P29 读取

使用 COMMITTED 答复的完整 BattleCommitBatch。`previous_revision + 1 == snapshot.revision`；本批事件连续、同场次／同 command／同 revision，以 COMMAND_ACCEPTED 开始，以 COMMAND_COMMITTED 结束。被拒绝或重复答复的 commit 为 null。

显示更新以 batch.snapshot 或重新查询的最新 snapshot 为准。伤害数字使用 DAMAGE_APPLIED 中的实际 raw／absorbed／hp_loss／hp_after／shield_after；治疗 amount 是实际应用量。动画不向 core 回写 HP。跳过、取消、丢失旧动画回调后由 P19 按最新快照归位。

本包的“禁／跳过动画等价”证明限于纯逻辑输入未含动画，以及消费端读取／修改副本不能写回状态；真实引擎动画取消和主线程 UI 生命周期未执行，不能记 E2E PASS。

## 6. 事务、中断和故障

串行临界区内，P14 构造新 state、receipt、batch、result、trace 与 replay entry，全部验证后执行一次记录引用替换。快照查询只读旧提交或新提交。重入写命令返回 REENTRANT_COMMAND；并发同请求只有一次提交。不同并发命令的受理顺序应由宿主队列固定；回放比较的是同一有序输入，不声称线程竞争顺序相同。

三个实际注入点为 after_deck_patch、after_resolution、before_publish。提交前 BaseException 中断保持原权威记录，原请求可重试。提交点之后若答复丢失，应重试同 ID／同原 revision 或查最新快照，不换 ID 再执行。

反应上限或内部安全故障：先抛弃游戏事务，再从旧状态构造独立的安全记录。只提交 COMMAND_ACCEPTED、BATTLE_FAULTED、COMMAND_COMMITTED；费用／牌区／HP／盾／RNG／回合均保持旧值，phase/outcome 进入 FAULTED，revision 增一。返回 COMMITTED **加故障 code** 表示安全关闭已提交，不表示原出牌成功；不会生成 BattleResult。该解释已作为 RFC-007 交原合同 owner 审阅。

若安全记录本身也不能编码，异常传播，旧状态保留。没有物理存档或崩溃后恢复声明。

## 7. 接收条件

本页与源码／测试按交付清单固定。P15／P16 接真实实现时必须保留版本、SHA、来源内容及 owner 回执；改 DTO 先由 P13 出新版本，不直接编辑本包 `upstream/`。发现失败回 P14 修其独占源码，P32 复测，P35 独审。所有正式工程合并等待用户指定的 EXT-INTEGRATOR。
