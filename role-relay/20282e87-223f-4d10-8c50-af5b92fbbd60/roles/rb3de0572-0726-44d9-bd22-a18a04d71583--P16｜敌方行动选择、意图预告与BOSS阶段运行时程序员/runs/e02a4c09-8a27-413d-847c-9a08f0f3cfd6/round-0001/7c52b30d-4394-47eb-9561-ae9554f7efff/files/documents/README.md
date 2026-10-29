# P16｜敌方行动、意图预告与 BOSS 阶段候选运行库

任务：`P16-S03-AI-001`。版本：`P16-ENEMY-AI/0.1.0-isolated`。
共享 DTO 沿用 `YLTT-INTERNAL/0.1.0-isolated`；敌方内容沿用 P06 原件 `P06-ENEMY-0.1.0-proposal`。

**已完成实际 Python 源码、182 项作者测试、86 条 P06 用例投影回放、真实 P14 单行动槽契约验证。正式工程接入、行为状态持久提交与 BOSS 阶段受理仍为 BLOCKED。**

本岗依据当前用户明确指定的 P16 请求启动。P01 原 `task_register.tsv` 没有 P16 独立任务行，本包使用局部任务 ID，并关联 `TASK-03-01` 的 S03 接收工作；未冒充 P01 补签。S07 内容只作既有 P06 配置的隔离边界预研，不代表正式 S07 阶段启动。

## 1. 直接复现

解压后进入 `P16_EnemyAI_V0.1`，使用 Python 3.12。实际作者环境为 Python 3.12.14 / Linux；只依赖标准库，不需要安装第三方包。

```bash
python -B tools/verify_delivery.py
python -B tools/author_tests.py
python -B tools/replay_fixtures.py
python -B tools/check_contracts.py
python -B -m enemy_ai
python -B tools/replay_demo.py
python -B tools/preflight.py
```

前六条应退出 0；最后一条当前应退出 **3 / BLOCKED**。Windows 可使用已安装 Python 的实际命令，如 `py -3.12 -B tools/author_tests.py`；本次没有在 Windows 执行，不能据此宣称目标真机通过。正常复现不需要重新生成样例文件。

## 2. 本次实体内容

| 相对路径 | 作用 |
| --- | --- |
| `enemy_ai/types.py` | 不可变输入、EnemyAction、Announcement、Decision、PhaseCheckpoint 与 PhasePlan |
| `enemy_ai/content.py` | P06 原字节读取、哈希绑定、行为政策版本检查、图校验 |
| `enemy_ai/inputs.py` | P13 快照与 P16 行为扩展绑定、RNG 历史、阶段历史和状态校验 |
| `enemy_ai/planner.py` | 预告、锁定目标重验、冷却/蓄力守卫、纯行为更新候选 |
| `enemy_ai/phases.py` | 排空检查点的有序阶段提议、稳定一次性身份、降级建议 |
| `enemy_ai/p14_adapter.py` | 原 P14 单行动槽隔离接线；明确拒绝生产范围 |
| `intent_replay_fixtures.json` | 86 组完整请求、实际输出、输出 SHA 与 P06 期望字段核对 |
| `boss_transition_cases.tsv` | 30 条 BOSS/阶段边界记录，包含原期望、实际结果摘要哈希与阻塞状态 |
| `enemy_intent_schema.json` | P13 原 EnemyIntent / PhaseProposal 的逐定义投影 |
| `tests/enemy_ai_unit/` | 作者单元、P06 源期望投影、P14 原库契约与跨进程回放测试 |
| `examples/demo_execution.json` | 实际预告→结束玩家回合→P14 敌方结算→同 ID 重试记录 |
| `evidence/runs/` | 实际命令、退出码、原始 stdout/stderr、执行时源码 ZIP 与哈希 |
| `handoff/` | RFC、路径请求、阻塞、接收回执、接口接受范围 |
| `upstream/` | 未修改上游源码/配置及 P06、P13、P14 原 ZIP |

文件大小、SHA-256、版本、源输入哈希、接收人和修改白名单在 `delivery_manifest.sha256.tsv`。清单列出其余所有包内文件；清单自身与最终 ZIP 由包外 `delivery_receipt.json` 绑定，避免循环哈希。

## 3. 已实现的业务行为

P06 的 18 个正常循环状态可选择已定义技能：普通单体攻击、精英攻击/蓄力/释放/恢复，以及三阶段 BOSS 的单体、群攻、蓄力和恢复。目标按阵位、单位 ID 稳定排序；只在**成功单体伤害的候选提交条件满足时**提出推进轮换游标。

本版 P06 是固定循环，**每次 AI 决策消耗 0 个 RNG 值**。运行库仍校验 seed/state/draw_count 的 xorshift32 历史并完整保留随机状态。固定输入可跨独立 Python 进程复现，不使用时钟、全局随机数或动画帧选择招式。

`publish_intent` 为下一敌方行动槽生成预告候选。`resolve_intent` 在 P14 已完成 DOT、反应和终局检查后重新验证冻结预告。锁定单体失效则跳过；群攻只删除失效目标，保留原顺序，不增加新目标。护盾影响最终实际扣血，不改写预告中的基础伤害。

蓄力只提出行为标记：锁定目标、释放技能、阶段代次、ready_slot 和创建 token；本次零伤害。释放缺标记、提前、过期、冷却阻塞均有明确零伤害结果和唯一循环后继。释放/取消后 CD2 的设置优先于同槽递减。候选必须由 P14 原子接受后才能改变业务状态。

BOSS 以整数分数比较检查点前后 HP。76→75 触发 P2；38→37 触发 P3；80→30 依次提议 P2、P3，受理要求是**一个原子批次、一次 epoch 提升、一次 ENTRY_WAIT、零额外行动**。80→0 不提阶段。已提/已提交阶段不会再次提议，治疗不会回退阶段。阶段提议 ID 与 P14 原有阶段事件的计算方式一致。

死亡、终局、反应未排空、有阶段待提交时返回明确 NO_OP/DEFER，不消费槽。缺阶段图只给 P14 降级建议：保留当前 phase，先一次零伤害提示，再进入既定基础攻击；P16 不自行切换 phase。已被 owner 明确标记的降级局不会因图恢复而重新进入阶段图。

**P06 没有召唤技能或召唤条件。本包的召唤提议始终为空，新增 SUMMON 内容会被拒绝。** 如需召唤，先由 P06 提交机制配置，再由 P13/P14 冻结召唤/槽位/上限合同；本岗没有擅增怪物机制。

## 4. 实际验证范围

| 层级 | 已观察结果 | 限制 |
| --- | --- | --- |
| 作者单元/隔离契约 | 182 项通过，0 失败、0 skip | 含下述投影与契约测试；不能相加为额外数量 |
| P06 原 89 条真值表 | 86 条 P16 字段投影执行通过；3 条 BLOCKED | 每条列出已核对与未验证字段，不声称 89 条完整游戏行为通过 |
| P14 原库契约 | 18 项作者测试通过 | 包括对已知不支持行为的拒绝/跳过反例；不是 18 项全功能集成通过 |
| P13 原校验器 | 140 条消息通过 | 84 快照、51 EnemyIntent、5 PhaseProposal；另 2 个非法快照按预期拒绝 |
| 跨进程确定性 | 3 个独立进程摘要一致 | `PYTHONHASHSEED=1/222/random`，重算 86 条输入 |
| 示例 | 3 请求、2 提交、1 次重复 no-op | 实际 P16+P14；P15/P17 输入为明示夹具 |
| P32/P33/P35 | NOT_RUN | 未代签独测、人工或独审 |
| 目标引擎/Windows/实际 UI/Anki/P21/整游戏 E2E | NOT_RUN | 不能据作者 Python 测试宣称可玩整合版 |

示例预告基础 8，P14 实际结算 raw=8、absorbed=4、hp_loss=4，角色 HP 50→46，最终 revision=2；同 ID 重试没有再次扣血，RNG 不变。BOSS 示例只返回 P2、P3 提议，当前阶段仍为 P1。

P06 原件中的旧 `runtime_test_status=NOT_RUN` 被原样保留，不擅改上游证据。P16 本轮新证据在自身 `evidence/`；它们证明的范围分别写明。

## 5. 缺陷与接入阻塞

P16-DEF-001：首次内容读取错误地使用 P13 的消息键名规范包装完整 P06 内容。P06 `source_hashes` 含 `SRC-P02-RULE` 等带连字符的合法内容键，P13 消息 codec 拒绝。修复为不可变原内容字节容器，只把正式 DTO 交 P13 codec。失败时源码、FAIL 日志与修复后 PASS 均保留。P32 复测/P35 关单仍 NOT_RUN。

P16-DEF-002：畸形目标或行为 ID 在集合去重前缺少类型校验，可能抛 TypeError 或被当成缺失目标。已改为先校验字符串类型与标识符；2 项新增回归通过。原失败记录保留于 `evidence/runs/malformed_ids_001/`，最终 182 项通过，独立关单仍 NOT_RUN。

正式接入目前受以下事实限制：P13 对 P16 的两条路径仍 null / write_allowed=false；共享快照没有行为游标、行动槽、冷却、蓄力、预告存储、targetable 或 phase_epoch 字段；P14 的 `inspect_phase_proposal` 明确拒绝受理；多敌批次未绑定；P22 正式内容 ID/Schema 与目标环境证据未到达。

本轮另实测出 P16-P14-GAP-001：P16 把群攻锁定名单从 3 人筛减为 2 人后，P14 的固定 `Action.target_count=3` 会跳过整次攻击。对应 RFC 请求 P14/P13 定义已筛减群攻的合法目标数量与事件语义；原 P14 源码没有被修改。

以上具体 base SHA、原因、唯一跟进 owner、复现测试和解除条件见 `handoff/blockers.json`、`handoff/interface_rfcs.json`。全部上游原件只读，生产写入白名单为空。

## 6. 接收路径

P14 接收候选 API、行为条件与阶段提议；P19 接收不可变预告视图和偏差原因；P27 接收 phase/意图关联而不由图片状态控制 AI；P32 直接复跑固定包；P33 在真实 UI/目标环境就绪后验证；P35 分层审查。本包接收记录为 `PREPARED_NOT_ACKNOWLEDGED`，只表示文件已准备，未替接收岗位签字。

跨模块合并仍由用户指定的 EXT-INTEGRATOR 处理。本次没有修改外部仓库、接管其他岗位源码或宣称发布。
