# P18 关卡运行库 API 与事务约定

任务：`P18-S07-STAGES-001`；程序版本：`P18-STAGES/0.1.0-isolated`。本文件说明已经存在的 Python 实现。带 `proposal` 的接口是待 owner 接收的提案，不是 P13/P21 已发布契约。详细状态见 `verification_status.json`，逐文件来源见 `source_input_receipt.json`。

## 1. 边界与依赖

`stage_runtime/` 只读取配置并生成不可变候选，不产生 BattleResult，不实现敌 AI、角色养成规则、钱包算术或物理存档。运行时复用包内原字节 P13 codec/validator；`tests/support/p17_port.py` 调用原字节 P17 MetaPlanner 产生钱包和 XP 候选；`tests/support/p14_native.py` 调用原字节 P14 核心产生四项原生契约测试所需的结果。后两者属于隔离契约测试装配，不能作为正式工程适配器直接发布。

`StagePlanner(..., mode='isolated')` 是唯一支持的启动模式。传入生产模式会抛出 `E_PRODUCTION_BOOTSTRAP_BLOCKED`。默认 `ClosedAuthority` 不解析任何权威凭据；`UnboundP21.submit` 始终抛出 `E_P21_NOT_BOUND_NO_STATE_COMMITTED`。没有自报 `trusted=true` 的授权开关。

所有读取端口必须由受信任组合根注入。界面请求、旧存档或网络消息不能自行充当端口。SHA-256 用于绑定字节，不构成签名，也不能把调用者提供的数据变成权威证据。

## 2. 公共函数

| API | 输入与返回 | 使用条件 |
| --- | --- | --- |
| `load_catalog(root=PACKAGE_ROOT)` | 读取固定 P07/P05/P06 原件，返回 `Catalog` | 核验来源哈希、预算值、解锁图、敌人及 Boss 引用；候选配置必须关闭生产 |
| `empty_state(catalog, player_save_scope_id=..., store_instance=..., continuity_ref=...)` | 返回 revision 0 的不可变状态 | 仅创建候选初态；P21 决定何时建立真实存档 |
| `command(snapshot, catalog, request_id, kind, payload)` | 返回 `FrozenMessage` 请求 | 对重试保留原始请求字节，不用新 revision 重建同一个 request_id |
| `StagePlanner.plan(request, snapshot)` | `PlanResult` | 返回候选、重复 no-op、拒绝或阻塞；不提交 |
| `planner.validate_for_commit(candidate, current_snapshot)` | 重算并比对完整候选 | 必须在 P21 一致性边界内调用；来源变更或 revision 冲突即拒绝 |
| `prepare_atomic(planner, stage_candidate, stage_snapshot, meta_snapshot, wallet_port)` | 联合候选或重复结果 | 有奖励时必须提供 P17 快照与端口 |
| `validate_atomic(bundle, planner, stage_snapshot, meta_snapshot, wallet_port)` | `PlanResult` | 重验整个联合候选、投影及 P17 候选，仍不提交 |
| `progress_view(snapshot, catalog)` | 完整 P18 只读视图 | 组合根必须传入 P21 已提交快照；此 API 不自行查询存储 |
| `p13_view(snapshot, catalog)` | 原 P13 `StageProgressView` | 若存在 review/quarantine 会拒绝有损投影 |
| `planner.resume(snapshot, battle_id)` | 原入场参数和权威 BattleSnapshot | 同一 active battle；不是创建新战斗 |
| `planner.lookup_terminal(snapshot, battle_id)` | 已确认终局记录或 None | 要求当前存储 fence 一致；不等同真实事务状态查询 |
| `restore_state(raw, catalog, authority)` | 校验后的不可变快照 | 必须用备份之外的权威 store head 核验连续性 |

`FrozenMessage.raw` 是 P13 规范化 UTF-8 JSON 字节，`.sha256` 是其摘要，`.value` 返回独立解析值。对 `.value` 的更改不会修改原快照。

`PlanResult.status` 为 `CANDIDATE`、`DUPLICATE_NO_OP`、`REJECTED` 或 `BLOCKED`。`CANDIDATE` 仅证明可提交候选已经生成。边界解析的 `ContractError`、`StageError` 在 `plan` 中转换为结果；构造非法 `FrozenMessage`、加载坏配置及提交重验可能直接抛出异常，调用方应作为拒绝处理，不能继续提交。

## 3. 请求结构

所有请求严格拒绝未知字段。外层为：

```json
{
  "schema_version": "P18-COMMAND/0.1.0-isolated",
  "request_id": "request.example",
  "player_save_scope_id": "save.example",
  "store_instance": "store.example",
  "continuity_ref": "continuity.example",
  "expected_revision": 0,
  "catalog_sha256": "64位实际摘要，由command函数生成",
  "kind": "ENTER",
  "payload": {}
}
```

上例是字段说明，摘要文字不是有效请求。可执行示例使用下面的 `command`/Harness，不复制占位摘要。

| kind | payload 的精确字段 | 作用 |
| --- | --- | --- |
| `ENTER` | `stage_id, battle_id, entry_ref, seed` | 校验解锁、单活动战斗和入场权威凭据；冻结战斗参数 |
| `SETTLE` | `result` | 处理原 P13 形状的 P14 BattleResult，判定首通/重复/非通关 |
| `CLOSE` | `battle_id` | 只接受权威 ABORTED/FAULTED 快照；P14 此时没有 BattleResult |
| `REVOKE` | `control_ref` | 解析权威撤销凭据，保留审查记录；真实端口尚未收到 |

`ENTER` 冻结 save scope、battle、stage、chapter、catalog 哈希、P07 图/奖励哈希、P06 敌人/Boss 图哈希、PartySnapshot 及其哈希、种子、战斗规则/内容版本和前置首通回执。敌人/Boss 配置通过引用传递，P18 不执行 Boss 阶段逻辑。正式内容加载、编队和种子如何交给 P14 由 P13/P14 接受接口后接线。

入场必须是三个已拥有且不同的角色；拥有权和完整编队由 P17 权威投影保证，P18 再检查原 P13 三槽 DTO 与角色去重。推荐等级没有被转换为硬门槛。本包只接受原件中的零入场/重试费用；增加费用须由 P05/P13/P17/P21 接口处理，不能自行扣款。

## 4. 首通与终局身份

首通逻辑身份严格为：

```text
["STAGE_FIRST_CLEAR", player_save_scope_id, canonical_stage_id]
```

`first_clear_key` 对该数组执行原 P13 canonical JSON + SHA-256。四组实际测试向量在 `first_clear_keys.json`。battle_id、终局修订号、chapter、内容版本、奖励版本、设备、文件名和 store instance 均不进入首通身份。因此，同一关卡的两个不同 battle_id 获胜只有一个首通。

重复奖励的 P18 身份为：

```text
["STAGE_REPEAT_CLEAR", player_save_scope_id, canonical_stage_id, battle_id, terminal_revision]
```

同一 battle 的更高终局修订号只进入对账，不生成新的奖励。重复投递与换 request_id 均无法重新领奖。本包默认重复奖励关闭、金额为零；正金额重复奖励只在明确标注 `SYNTHETIC_TEST_ONLY` 的测试 Catalog 中验证机制，不修改 P07/P05 原表。

P17 原接口按 profile 内 `{campaign_id, stage_id}` 判定首通，本包隔离适配要求 `P17.profile_id == player_save_scope_id`，并固定 `campaign_id='YLTT_STAGE_SCOPE'`。这不是把章节名写入权益键。P17 重复权益绑定具体 battle；修订高水位继续由 P18 保持。正式账号多存档映射、重命名和迁移待 RFC 接收，不能默认账号 ID 就等于存档 scope。

终局必须匹配已提交 admission，并由 `resolve_battle` 返回同一权威结果及最终快照。校验包括 stage、scope、battle、版本、种子、玩家 unit、最终快照摘要、修订号、事件序号及胜负存活状态；胜利另外核验敌人引用数量和前置通关回执。客户端伪造胜利、未知关卡、未入场终局、未来/旧修订、结果身份碰撞、关卡串换均不生成奖励候选。

## 5. 端口提案

`ports.py` 定义四个只读方法，返回 `FrozenMessage | None`：

| 方法 | 所有者与证据 |
| --- | --- |
| `resolve_store(scope)` | P21：scope/store/continuity、当前 stage revision、state_sha256、CONSISTENT/COMMIT_UNKNOWN/RECONCILIATION_REQUIRED |
| `resolve_entry(reference)` | P13 协调 P17/P14/P21：与 scope/stage/battle/catalog 绑定的原 PartySnapshot、battle content/rules 引用 |
| `resolve_battle(battle_id)` | P14 权威终局与 BattleSnapshot，经 P13/P21 提供一致读取；绑定 admission_sha256 |
| `resolve_control(reference)` | P14/P21：原胜利结果、admission_sha256、单调更高撤销 revision；目前仅合成夹具 |

完整字段与版本见 `stage_runtime_contract.json`；实际校验函数位于 `state.py`、`service.py`。端口必须在 P21 的锁或等价 CAS/一致读内解析。单独进行一次哈希检查后再无保护地提交存在竞态，本包不声称能代替 P21 保证并发与持久性。

`WalletPort.propose(grant, snapshot)` 和 `validate(grant, candidate, snapshot)` 交给 P17 算术和来源账。grant 只包含原配置金额与入场角色 XP，P18 不能在结算请求中接受用户提供的金额。XP 给入场角色，而不是结算时临时切换后的编队。

## 6. 联合事务必须保持的条件

`P18-ATOMIC-BUNDLE/0.1.0-proposal` 包含完整 stage candidate、完整 P17 wallet/character candidate、期望 meta 摘要、body 摘要，以及通过原 P13 校验的 `AtomicCommitProposal` 投影。投影的 `transaction_kind=STAGE_PROGRESS_WALLET`，`domain_candidate_sha256` 绑定整个联合 body。投影通过 Schema 不能证明扩展接口已被 owner 接收。

P21 实现时须在同一物理事务内：校验最新 stage/meta/store/continuity 和权威来源；调用 `validate_atomic`；建立首通唯一约束；更新 stage/终局高水位/first-clear tombstone/解锁依据；提交 P17 钱包与角色 XP 完整后态；保存请求指纹、奖励来源及最终回执。仅在持久提交后发布成功。原 P17 单域 `atomic_proposal` 没有被修改或绕过来冒充联合提交。

此包的内存模型用一把锁和一次记录引用替换同时发布两个域及模拟回执。它覆盖故障注入、重复提交和并发竞争，所有回执 `durable=false`。它无法证明 fsync、掉电恢复、数据库隔离、外部进程并发或跨设备恢复。

提交状态未知时，先由 P21 查询原 request/transaction 回执。在查明前阻止新关卡，不用新 ID 再发奖励。request_id 相同但完整请求不同是碰撞，不能当成功重试。候选过期时读取新快照后重建新请求；若原事务已经提交，只读回执并结束。

## 7. 失败、撤销与恢复

LOSS/DRAW 关闭本次 attempt，允许按正常资格重试，不首通、不解锁、不改 Wallet。ABORTED/FAULTED 必须有 P14 权威快照，不能由页面关闭直接伪造。退出重进复用 admission 和原 P14 snapshot；已有终局必须结算，不能重新开始同一 battle。

结算前撤销：保留撤销墓碑，旧胜利不能领奖。结算后撤销或权威终局升级：保留原首通键、历史奖励和 Wallet，只置审查/对账状态；依赖关卡被阻止，已在途依赖关卡胜利进入隔离。P18 不自行负扣、返还、消除首通、放开重领或恢复权益。隔离记录携带完整可追溯证据，由 P07/P14/P21 查明；解除 hold 的正式接口尚未提供。

`restore_state` 校验结构、首通集合、终局对应关系、revision 历史、scope/store/continuity，并核对备份之外的 P21 store head。恢复更旧存档、改变 store/continuity 或缺失权威 fence 均阻塞。复制同一旧备份并让它自证最新不能防回滚；此问题必须由 P21 处理。本包包含跨 Python 子进程字节重载测试，不等于真实存档重启验收。

## 8. 容量与迁移

原 P13 codec 限定单消息 1 MiB、深度 32、节点 100000、安全整数范围 ±(2^53−1)；P18 集合限制 4096。完整联合候选可能先于集合上限达到消息上限，此时拒绝整个候选，不截断历史。首通墓碑与去重记录不能为缩小存档被删除。长期分段、归档摘要、内容新增/改 ID、跨 store 恢复和 alias 迁移由 P13/P21/P22 提供版本化方案；当前代码拒绝未批准迁移。

## 9. 可执行例子

完整包内运行 Python 3.12，无需安装第三方依赖：

```bash
python -B -m stage_runtime
python -B tools/replay_demo.py
python -B tools/author_tests.py
python -B stage_reward_tests.py
python -B tools/replay_p07.py
python -B tools/check_contracts.py
python -B tools/check_determinism.py
python -B tools/preflight.py
```

最后一条预期退出 3 / BLOCKED；并非失败日志。其余命令成功时退出 0。`stage_reward_tests.py` 是完整作者测试中的奖励/恢复/事务子集，测试数量不能相加。

用于理解调用顺序的已执行隔离代码在 `examples/stage_lifecycle.py`。其事件包含原请求、候选、联合 bundle 和内存回执，输出保存在 `examples/lifecycle_execution.json`。正式程序不应导入 `tests/support/`。

## 10. 原始 P07 场景兼容边界

原 67 个案例中，35 个由 `tools/replay_p07.py` 执行并比较原件的所有期望字段，32 个记录 NOT_RUN。界面动作的投影只验证领域状态不变，不代表 P20 页面已运行。另有自编单元/契约测试覆盖类似风险，不能据此给未重放原案例补 PASS。

特别待确认：P07-ST-030 的高修订补投，本实现进入 review hold，较原夹具的空 review 更严格，原案例未计 PASS；P07-ST-031 预设同时存在两次已接纳战斗，与图配置单活动战斗限制需 owner 澄清。作者并发测试验证竞争入场 CAS 拒绝过期一方、随后两次合法胜利只有一次首通；不声称复现了 ST-031 的历史导入场景。
