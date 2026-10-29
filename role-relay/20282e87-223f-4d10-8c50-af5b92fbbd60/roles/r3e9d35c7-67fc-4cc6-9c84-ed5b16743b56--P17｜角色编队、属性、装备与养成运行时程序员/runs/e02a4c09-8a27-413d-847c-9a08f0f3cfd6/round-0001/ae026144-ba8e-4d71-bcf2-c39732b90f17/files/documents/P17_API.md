# P17 API 与业务事务说明

任务 `P17-S05-S06-S07-META-001`；发布标识 `P17-META/0.1.0-isolated`。关联 IC-09、IC-10、IC-17、IC-20。本文是本岗位隔离接口交付，不是 P13/P21/P11/P18 对生产接口的接收签名。

## 1. 调用与所有权

```python
from character_party_runtime import (
    MetaPlanner, load_catalog, empty_state, command,
    FrozenMessage, atomic_proposal, restore_state,
)

catalog = load_catalog()                 # P04 原始测试内容；装备默认关闭
planner = MetaPlanner(catalog)           # 默认外部证据端口关闭
snapshot = empty_state(catalog)          # 空隔离状态；没有免费余额或角色
request = command(snapshot, "demo:request-1", "SET_PARTY", {
    "ordered_character_ids": [
        "MOCK_P04_CHAR_001", "MOCK_P04_CHAR_002", "MOCK_P04_CHAR_003"
    ]
})
result = planner.plan(request, snapshot)
assert result.reason == "E_CHARACTER_NOT_OWNED"
assert result.candidate is None
```

真实成功流程见 `examples/lifecycle_demo.py`：它明确使用 `tests/support/FixtureAuthority` 和 `AtomicMemoryModel`。这些对象只用于测试，不能绑定到生产 composition root。

| 对象／方法 | 输入 | 输出与责任 |
| --- | --- | --- |
| `Catalog` | 冻结内容对象 | 校验角色、成长费用、装备定义；不批准内容发布 |
| `load_catalog()` | 包内 P04 原件；可显式开启 equipment_test_fixture | 隔离内容实例；返回值包含来源哈希和完整内容哈希 |
| `empty_state()` | 明确的 profile／store／continuity | 空状态夹具；正式账号创建仍归整合及 P21 受理流程 |
| `command()` | 当前只读快照、请求 ID、类型、payload | 不可变命令；正式调用者也可按相同形状构造消息 |
| `MetaPlanner.plan()` | 不可变命令＋不可变快照 | PlanResult；不写入权威状态或外部存储 |
| `MetaPlanner.validate_for_commit()` | 完整候选＋P21 当前快照 | 在提交边界重算；候选必须逐字节匹配重新生成结果 |
| `MetaPlanner.character_attributes()` | 快照＋角色 ID | 带 revision／内容哈希的只读四属性数据 |
| `MetaPlanner.party_export()` | 完整合法三人队伍 | P17 完整导出，保留 support、技能、装备、P03 引用 |
| `MetaPlanner.party_snapshot()` | 同上 | 原 P13 PartySnapshot 形状；必须与完整导出一起交接 |
| `MetaPlanner.wallet_snapshot()` | 当前快照 | 原 P13 WalletSnapshot；只读可用／预留余额 |
| `atomic_proposal()` | 自包含角色候选 | 原 P13 AtomicCommitProposal 的技术投影；跨 P11/P18 候选明确拒绝 |
| `restore_state()` | 调用者提供字节、预期 SHA、store、continuity | 重新解码并校验完整状态；没有磁盘读取／写入 |
| `UnboundP21.submit()` | 任意候选 | 抛出 E_P21_NOT_BOUND_NO_STATE_COMMITTED，不发生扣款 |

`FrozenMessage.raw` 是不可变规范 UTF-8 字节；每次 `.value` 返回全新对象。修改调用方取得的字典不会修改原快照或候选。规范化、复杂度界限和整数范围直接复用未修改的 P13 codec。

## 2. 命令与状态版本

命令严格包含以下字段，不接受额外的 `trusted`、`owner`、`amount`、`cost`、`durable` 等自报字段：

| 字段 | 意义 |
| --- | --- |
| `schema_version` | 必须为 `P17-COMMAND/0.1.0-isolated` |
| `request_id` | 账号内请求唯一 ID；成功请求永久保留规范字节指纹 |
| `profile_id` | 受益账号；与当前快照、证据端解析结果一致 |
| `store_instance` | P21 当前存储实例标识；旧实例不能提交 |
| `continuity_ref` | P21 连续性证明引用；不能由 P17 推断旧备份安全 |
| `expected_revision` | 元系统整体验证基准 |
| `expected_wallet_revision` | 钱包验证基准 |
| `content_sha256` | 内容、费用和测试装备开关的完整指纹 |
| `kind` | 下表中的封闭命令类型 |
| `payload` | 对应类型的封闭对象 |

| kind | payload 字段 | 业务效果 |
| --- | --- | --- |
| APPLY_GRANT | grant_ref | 解析 P11/P18 证据；同一事务候选包含资源、角色、XP、装备与唯一性记录 |
| LEVEL_UP | character_id、from_rank、to_rank | 验证相邻等级、累计 XP、配置费用；角色和钱包同候选变化 |
| SKILL_UP | character_id、from_rank、to_rank | 验证相邻 rank、角色等级条件和配置费用 |
| SET_PARTY | ordered_character_ids | 恰好三名已拥有且唯一的角色，保留索引顺序 |
| SET_EQUIPMENT | character_id、items | items 为 slot／instance_id 数组；空数组表示卸下全部；默认关闭 |
| RESERVE | quote_ref、reservation_id | 根据外部成本凭证锁定确切来源批次；可用转预留 |
| RELEASE | reservation_id | 原预留批次返还可用；已兑现的预留不可释放 |
| CAPTURE | quote_ref、reservation_id | 重验原成本绑定后预留转已消费；不能更换用途 |
| SPEND | quote_ref | 根据 P18 解析的成本凭证直接消费；已有活动预留时拒绝旁路扣费 |
| REVOKE_STUDY | reversal_ref | 按 P11 解析的撤销引用回收完整未消费学习来源；已消费／预留则阻塞 |

没有 FREE_GRANT、DAILY_GRANT、CASH_PURCHASE、FORCE_BALANCE、RESTORE_REWARD、任意扣款金额或无限角色补发命令。

状态版本为 `P17-STATE/0.1.0-isolated`，包含元 revision、wallet_revision、角色、三席位、装备实例、来源批次、预留、消费凭证、权益凭证和成功请求指纹。初始 `[null,null,null]` 仅表示尚未编队，不能导出战斗队伍。本版没有不完整队伍的战斗入口。

## 3. 资格端口和学习政策边界

`EvidencePort` 由受控 composition root 绑定，暴露三个只读方法：`resolve_grant(ref)`、`resolve_quote(ref)`、`resolve_reversal(ref)`。每个方法返回已解析的 FrozenMessage 或 None。默认 `ClosedEvidence` 全部返回 None。

接收到 `issuer="P11"` 并不证明资格。本包只在调用受控端口取得对象后检查 issuer 与业务域一致性；测试 registry 是合成授权，不能当真实身份凭据。正式绑定需要原 owner 对真实身份、政策版本、预算、撤销因果关系和存储一致性负责。

### 授予输入

`P17-GRANT-INPUT/0.1.0-proposal` 包含 grant_ref、issuer、profile_id、source_kind、identity、eligibility_ref、policy_version、policy_sha256、resources、characters、xp、equipment。resources 为正整数 resource_id／amount 项；XP 为角色 ID／正数量项。同一来源可产生多个资源批次，但整批成功或整批无候选。

本版学习来源仅允许资源授予，不允许学习引用直接授予角色／装备／XP。角色获取、XP、装备的真实取得条件仍由 P18 与内容／政策 owner 提供。本包生命周期用 P04 的测试事件作合成来源。

| 来源 | identity 精确字段 | 唯一性处理 |
| --- | --- | --- |
| STUDY | source_id、collection_lineage、family_id | 连同 profile_id 构造家族键；不含日期、评分、政策或投递 ID |
| STAGE_FIRST_CLEAR | campaign_id、stage_id | 连同 profile_id 构造首通键；故意拒绝额外 battle_id |
| STAGE_REPEAT | campaign_id、stage_id、battle_id | 每个独立战斗结算凭证最多兑现一次 |

权益 key 的 SHA-256 由上述作用域规范字节计算。权益的经济内容另外计算 semantic_sha256，排除可以变动的投递引用，但包含政策与奖励内容。同键同内容重复返回 DUPLICATE_NO_OP；同键改变数值或政策返回 E_ENTITLEMENT_COLLISION。

P11 原有 `RewardIntent` 的 operation_key／family_key／desired_active／policy_snapshot／source_evidence_ref／resolution_ref，以及 `WalletDelta.source_after` 中的历史会计量，尚未获得与本模型无损转换的批准。**本包不是 P11 原 WalletPort 的即插即用实现。** `check_contracts.py` 实际加载原类型检查了这个差异，正式适配状态为 BLOCKED。详见 RFC-P17-003。

### 撤销与未决部分

REVOKE_STUDY 只处理外部 P11 明确解析出的撤销引用。它检查原政策哈希和原来源；只有该来源所有资源都没有消费和预留时才生成全部回收候选。若存在已消费或预留，返回 `BLOCKED / E_RECONCILIATION_REQUIRED`，不返回局部扣款候选，也不改变任何资产。

这个返回值是交回 P11/P08 的业务门禁，不会替 P11 写入 PENDING_RECONCILIATION。部分回收、未来抵扣、追溯已购角色、负债、豁免以及撤销后恢复授予，都必须另有批准政策与版本化接口。目前重放已撤销家族拒绝重新发放，不能以换 request_id 绕过。

DEC-001/002/003 仍待上游批准，因此测试中 `10` 个学习单位只是测试数量，不代表 Again／Hard／Good／Easy 正式收益。程序不读取学习天数来擅自设定无学习日赠送或锁定规则。

## 4. 钱包会计、锁定与并发

每个来源资源批次固定保存 quantity、available、reserved、spent、revoked，满足：

```text
quantity = available + reserved + spent + revoked
available >= 0; reserved >= 0; spent >= 0; revoked >= 0
```

resource 的可用和预留余额由所有批次求和得到。余额、数量、revision 都是 P13 规范下的安全整数；bool、负发放、重复资源行和溢出拒绝。升级的费用只能取自已绑定内容，不接受 payload 自报成本。

分摊顺序由 P17 决定：先按 created_revision，再按 lot_id 排序；同一输入可重算。消费会把可用转为 spent；预留把可用转为 reserved；释放按原 allocations 原路返回；兑现按原批次从 reserved 转 spent。所有来源始终可以追溯，其他来源余额充足也不能用于填补撤销缺口。

预留同时绑定 reservation_id、spend_key、cost_sha256、resources、allocations。一个用途只能有一个活动预留。同一用途消费后，以不同 quote_ref 重放仍 no-op；改变金额则碰撞拒绝。已释放的 reservation_id 不可重用，可在新 ID 下重新申请同一尚未消费的用途。

建议 P21 锁定顺序为 profile → wallet → request；候选提供 rank 10/20/30 的稳定锁键。测试模型使用单个 RLock 覆盖整个快照，证明的范围是模型中的串行一致性与候选重算，未证明数据库隔离级别、跨进程锁或断电恢复。

同 ID、同完整规范请求优先检查为重复；同 ID、不同指纹拒绝。原请求重试必须保留原 expected_revision。一个尚未被受理的请求如果遇到 revision 冲突，可重新读取并生成新候选；提交结果 UNKNOWN 时必须先查原事务，不能换 ID 猜测重试。

## 5. 完整候选与 P21 原子提交

`P17-CANDIDATE/0.1.0-isolated` 包含完整 request、request SHA、before SHA、after_state、after SHA、P13 wallet_delta、evidence_binding、required_counterpart_owner、明确的未提交状态和锁顺序。角色进展、钱包消耗、来源归属、预留与 request receipt 已处于同一个不可变 after_state。

`WalletDeltaCandidate` 中的 changes 与 allocations 只投影可用／预留变化。预留状态、已消费累计、撤销累计、权益去重和角色变更仍在完整领域候选里。**仅保存 wallet_delta 会丢失业务数据，禁止这样接线。**

其 wallet_before_sha256 明确绑定规范化 P13 WalletSnapshot；完整来源与所有元状态由候选 before_sha256 绑定。P21 必须二者都校验，不能只比较余额相同就认为候选没有过期。

角色升级和编队等自包含 P17 操作可导出原 P13 `AtomicCommitProposal`；这仍只是协调提案。P11/P18 联合事务需要原 owner 的候选与共同的 P21 resolver，`atomic_proposal` 对这类候选返回 E_COUNTERPART_COMMIT_CONTRACT_UNBOUND，不生成假的成功提交。

正式 P21 接收端至少必须：

1. 在一个一致读取／锁定边界获取 P17、P11/P18、store 和 continuity。
2. 优先查询已受理 request_id 和规范指纹；拒绝碰撞及旧实例。
3. 对 P17 候选调用 `validate_for_commit`；外部证据 resolver 必须处于相同一致性边界。
4. 在同一个物理事务中保存领域变更、钱包、源分摊、权益去重、request receipt 以及跨域候选。
5. 只有持久提交成功后发布权威回执；超时不假定失败，使用原事务查询。

上述义务是 RFC 的接收条件。本包 `AtomicMemoryModel` 没有持久事务能力，所有回执都固定标记 `durable=false`，并可注入发布前失败、发布后响应未知等情景。

## 6. 属性、装备与战斗数据

P04 原成长公式：`base + (level - 1) × growth`，四属性均保留整数。P05 的 15 条 Lv1–Lv5 投影用于作者回归对照。XP 保持累计，不与代币或四键奖励互相换算。

装备默认关闭；只有 `load_catalog(equipment_test_fixture=True)` 使用 `fixtures/equipment_test_only.json` 的三条合成定义。此开关会改变内容指纹，旧快照不能无版本迁移地直接加载。它不是正式功能批准开关。装备列表先检查重复实例，再检查开关，以遵守 P04 的拒绝优先级。

装备以实例唯一性管理；同一实例不能同时用于两个角色。替换某角色装备列表作为一个事务候选完成；非法新装备不会先卸掉旧装备。不自动从另一角色身上取下装备，需先明确卸下。装备没有本包自行决定的购买价、拆卸费或稀有度。

`PartyBattleExport` 保留全部四属性、level、skill_id／rank、装备实例与 P03 的来源映射。原 P13 EntityStats 只接受 max_hp、attack、defense，所以 `PartySnapshot` 是明确的兼容投影。support 等字段不得静默舍弃后称为完整角色合同。P13 扩展未接收前，P15/P14 必须根据已批准的消费口径决定使用哪一部分。

同一角色稳定 unit_id 不随槽位变化而变化。P03 的 mock character_id 作为独立 p03_link 保存，不把真实 character_id 原地改名。P17 没有实现抽牌、构筑牌堆、费用卡效果、HP 写入或角色 UI。

## 7. 状态重新载入与容量限制

`restore_state` 不访问磁盘；调用者提供的 expected_sha256、expected_store_instance、expected_continuity_ref 应来自 P21 的权威一致读取。哈希匹配只说明字节一致，不代表存档来源可信或旧备份已经被拒绝。

重新解码会校验角色来源、XP 授予之和、升级／技能对应消费凭证、装备来源及唯一性、来源会计守恒、活动预留与消费分摊、receipt 连续 revision 等。测试包括另一个实际 Python 进程从 stdin 重新载入后的数值一致性；目标游戏的启动／退出、磁盘 WAL、断电／掉盘和备份恢复没有执行。

本版沿用 P13 的 1 MiB 消息、数组及复杂度技术界限。累积记录不能无限增长，超过边界会拒绝新候选；不会自动丢弃旧去重凭证。这是隔离原型的容量限制，不是用户批准的奖励限额。正式分段快照、归档与去重保留协议由 P13/P21 按 RFC 承接。

## 8. 结果和错误

| 结果 | 含义 |
| --- | --- |
| CANDIDATE / VALIDATED_NOT_COMMITTED | 计算成功；权威状态仍未改变 |
| DUPLICATE_NO_OP | 已受理请求或已兑现权益的相同重放；无新候选 |
| REJECTED | 输入、归属、资源、配置或版本非法；无候选 |
| BLOCKED | 缺真实端口／政策或出现需上游处理的撤销暴露；无候选 |

常见错误：E_CHARACTER_NOT_FOUND、E_CHARACTER_NOT_OWNED、E_PARTY_SIZE、E_PARTY_DUPLICATE、E_LEVEL_STEP_INVALID、E_LEVEL_CAP、E_XP_INSUFFICIENT、E_SKILL_LEVEL_GATED、E_WALLET_INSUFFICIENT、E_FEATURE_DISABLED、E_EQUIPMENT_IN_USE、E_COMMAND_ID_COLLISION、E_REVISION_CONFLICT、E_WALLET_REVISION_CONFLICT、E_CONTENT_CONFLICT、E_STORE_INSTANCE、E_CONTINUITY_FENCE、E_ENTITLEMENT_COLLISION、E_RESERVATION_BINDING、E_RECONCILIATION_REQUIRED。

畸形 wire JSON 使用原 P13 ContractError。plan 会把已知输入错误转成拒绝结果；程序缺陷不会被通用 except 静默伪装成正常结果。直接调用低层规则函数可抛 DomainError，应由领域调用方处理。
