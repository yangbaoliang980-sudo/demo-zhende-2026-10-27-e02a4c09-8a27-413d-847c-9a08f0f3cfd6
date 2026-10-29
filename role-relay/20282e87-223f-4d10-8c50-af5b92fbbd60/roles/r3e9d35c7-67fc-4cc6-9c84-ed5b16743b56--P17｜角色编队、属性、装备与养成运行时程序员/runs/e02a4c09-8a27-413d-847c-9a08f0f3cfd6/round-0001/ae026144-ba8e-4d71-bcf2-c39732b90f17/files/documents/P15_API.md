# P15 API｜纯候选与 P14 单次提交

版本 `P15-DECK-RUNTIME/0.1.0-isolated`；共享消息保持 `YLTT-INTERNAL/0.1.0-isolated`。任务 `TASK-02-01`；需求关联 REQ-005/006/015/019/021/024；IC-04 内容 owner=P03、IC-05 提交 owner=P14、IC-08 消息/表现合同 owner=P13。

## 1. 编队与构筑输入

```python
from deck_runtime import build_deck, recipe_from_p03

recipe = recipe_from_p03(
    original_catalog_bytes, original_deck_fixture_bytes,
    common_owner_slots=(0, 0, 1, 1, 2, 2), mode="isolated",
)
build = build_deck(
    verified_party_message, frozen_catalog, recipe,
    battle_id="fixture:example", seed=1, mode="isolated",
)
deck_projection = build.deck.value()
```

归属槽位数组必须由测试输入显式给出；该例不是正式归属策略。PartySnapshot 结构必须有三个唯一角色、唯一 unit_id 和槽位 0/1/2；实际角色合法性仍由 P17/P04 证明。`mode="production"` 拒绝，因为本轮缺真实 P17、P22 内容和正式路径授权。

`DeckBuildCandidate` 包含未提交的 DeckState 和 provenance。DeckState 只含卡实例、draw/hand/discard/exhaust 和 RNG。**没有 energy、HP、phase、revision、outcome 的写入口。** 创建真实 BattleState 的职责仍是 P14/授权装配入口；P15 不提供 commit/apply-to-BattleState API。

实例 ID 为 `p15inst:` 加 SHA-256，输入是 battle_id、完整 PartySnapshot 哈希、完整 recipe 哈希和序号。seed 不影响实例身份，只决定洗牌。该 ID 形式是隔离实现命名空间，正式编码待 P22 接收。

## 2. 纯函数验证

```python
from deck_runtime import plan

decision = plan(command, snapshot, frozen_context)
if decision.candidate is not None:
    candidate = decision.candidate   # P13 FrozenMessage[DeckPatchCandidate]
    intent = decision.action_intent  # 本地引用证据，不作为额外 wire payload
else:
    rejection_code = decision.code
```

`PlannerContext` 冻结 battle_id、Catalog、DeckPolicy 与 PartySnapshot；其完整 SHA 存入本地决策证据。输入必须具有明确 rules/content/policy 版本。P15 读源配置的费用，不接受客户端自报费用；无浮点/NaN/bool-as-int。卡实例必须在手牌且属于存活的本方 actor；专属牌的 definition_id 必须匹配角色。所有显式目标一次性校验，保留原顺序，不删掉非法目标、不自动改选目标。

输出 DeckPatchCandidate 绑定 `battle_id / command_id / expected_revision / command_sha256 / snapshot_sha256 / policy_version / rng_before / rng_after`。`moves` 是有序 remove-then-insert 操作，to_index 按移除后的目标牌区解释；同牌区移动用于初始洗牌重排。费用变化、牌区和 RNG 都是候选，没有先行资源预留或扣费。

ActionIntent 只记录 card_id、actor_id、card_instance_id、显式 target_ids、effect_ids、内容/效果定义哈希及候选哈希。效果数值和 HP/胜负由 P14 冻结的 Action/Effect 执行。当前 P13 没有独立 ActionIntent DTO，不能把本地证据字典塞进 DeckPatchCandidate；正式形状已登记 RFC。

线格式无身份、未知字段、重复 JSON 键/目标、错误类型或契约版本抛原 P13 ContractError；能建立合法身份的领域拒绝返回 `Decision(status="REJECTED", deck_patch=null, action_intent=null)`。坏配置的构造失败不伪造成成功候选。

## 3. request_id、重试与缓存

V6 的 request_id 在当前 P13 线格式中对应 **command_id**。不能同时加一个 request_id 字段，P13 会按未知字段拒绝。完整命令指纹包含 expected_revision、目标数组顺序和契约版本；重试必须保留原 ID、原 revision 和原始载荷。

纯 `plan(..., prior=decision)` 在相同完整命令下复用原证据；同 ID 不同指纹返回 COMMAND_ID_COLLISION。`DeckPlanner.evaluate()` 提供有界线程安全缓存，最大 4096 个身份，满时拒绝新请求，不淘汰旧身份后偷偷重算。拒绝证据也保留；改变状态后若想发起新业务动作，应先确认原请求是否被 P14 接受，再使用新业务 ID。

这份缓存是 **进程内决策证据缓存**，没有成功执行含义，不是第二套 accepted_commands。P14 在 provider 调用之前检查自己的成功回执，已提交同请求返回 DUPLICATE_NO_OP；新 ID 再打已移走实例返回 CARD_NOT_IN_HAND。重新创建 P15 对象不影响已有 P14 成功回执的防重。该测试没有证明 P21 物理存档或断电恢复。

若重试时基准快照已变化，P15 缓存仍返回最初证据供审计；P14 适配器拒绝将旧候选应用到新 basis，报 CACHED_CANDIDATE_BASIS_CHANGED。P14 的实时 phase/revision 前置检查可能先拒绝，因此不声称所有跨状态 P14 BattleReply 都有相同 observed_revision 或原字节；保持相同的是 P15 已缓存的决策证据。

## 4. 与原 P14 接线

测试装配必须绑定实际 P14 的异常类。相同源码导入为 `battle_core` 与 `upstream.P14.battle_core` 时，两个 CandidateRejected 不是同一个 Python 类型。本包已移除硬编码导入；以下参数必须提供：

```python
from deck_runtime import DeckPlanner
from deck_runtime.p14_adapter import P14DeckAdapter
from battle_core.ports import CandidateRejected  # 与当前 BattleCore 同一份导入

provider = P14DeckAdapter(
    DeckPlanner(frozen_context),
    actual_p14_rules,
    rejection_type=CandidateRejected,
)
```

`provider.propose(command, snapshot)` 只返回 P13 DeckPatchCandidate，领域拒绝抛当前 owner 的 CandidateRejected。生产装配仍需实际路径与合同审批；本段不是部署授权。包内 `examples/support.py` 使用 vendored P14 的同源异常类；`tools/probe_p14_module_identity.py` 实测 P14 原包名装配。

初始化会核对规则/content/policy 版本、活动卡集合、角色归属、目标数与阵营、after_play_zone、完整效果顺序与数值、DOT 定义、源内容哈希。费用仍只存 P15 Catalog，P14 Action 中没有费用字段。

现有 P14 只有一个 `entry_draw_requested`，同时用于开局和以后玩家入口。本适配器要求它与 P15 initial_draw/turn_draw 三者相同；不匹配报 P14_ENTRY_DRAW_REPORT_UNBOUND。纯 P15 可计算不同数目，但在 P14 新合同批准前不能宣称其 DRAW_SHORTFALL 报告正确接通。

P14 玩家入口先执行 DOT/反应/终局，再给 P15 **未发布的 post-DOT 私有 basis**。P15 绑定实际收到的 basis SHA，不能自行查询或替换成旧公开快照。测试已验证：该 basis HP 已受 DOT 影响、revision 尚未增加；若候选拒绝，DOT 一起回滚；若 DOT 已致终局，P14 不调用 P15。

## 5. 牌区与 RNG 规则

洗牌只用 P02 提议的 xorshift32-v1，seed 范围 1..4294967295。降序 Fisher–Yates 在每次 i=n-1..1 消耗一个数，j=next_u32%(i+1)。保留 mod 方案以保持上游向量兼容，不声明密码学随机性。相同完整输入和 seed 产生相同顺序；不同种子不保证每次排列必不相同。

draw 从左端抽。draw 为空、discard 非空且政策允许时，先按原 discard 顺序洗牌，再迁回 draw；exhaust 不参与。一次需求只消耗实际需要的可用牌，手满后不再额外抽弃牌或继续 RNG；两区空时有限终止。初始 shuffle 是单独明确的开局政策。

牌区实例上限、移动上限及安全整数沿 P13 边界；候选超过 4096 个 move 时整次拒绝 PATCH_CAPACITY_EXCEEDED，不能拆成额外权威事务。zero count、empty/single pile 不额外消耗 RNG。验证 RNG 历史时采用对数跳步，不循环运行攻击者给出的巨大 draw_count。

END_TURN 的 KEEP/全弃、入口 SET/KEEP/ADD_CAPPED 费用变化、抽牌量、容量、回流和初始洗牌均由显式测试政策提供，无生产默认值。未知折扣、BUFF/DEBUFF、自动目标、复活或叠层不默许。

## 6. 接收与修复

所有正式输入必须给固定提交或路径、原字节 SHA、需求/合同版本、owner 接收证据及目标环境。修改共享 DTO 由 P13 发新版本；P14 拒绝/原子提交问题回 P14；P03 配方/费用含义回 P03/P05；P15 实现缺陷由 P15 修复。下游独立验证由 P32、人工由 P33、证据门禁由 P35。本轮仅准备回执文件，没有向其他人发送消息或代签。
