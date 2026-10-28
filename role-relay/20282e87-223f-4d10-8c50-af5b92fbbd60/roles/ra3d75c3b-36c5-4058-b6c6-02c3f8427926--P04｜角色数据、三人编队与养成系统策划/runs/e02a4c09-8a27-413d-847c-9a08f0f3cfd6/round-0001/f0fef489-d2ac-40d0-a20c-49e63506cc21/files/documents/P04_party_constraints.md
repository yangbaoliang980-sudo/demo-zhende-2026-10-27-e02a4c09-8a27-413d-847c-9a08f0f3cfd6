# P04｜三席位编队与合法性规范（隔离可测版本）

版本 `P04-PARTY-0.1.0-draft`；任务 `TASK-P04-S02-LOCAL-001`；适用 `REQ-005`，S06 后续实现参照 `REQ-027`。P01 已确认**同时三人上阵**，但总角色数量、阵型强制定位、英雄获取方式尚未批准（`DEC-004`）；本稿使用三个 P04 本地 mock ID，并非正式全球内容 ID。

## 1. 输入 / 输出 / 拥有权

输入对象示例：`{"ordered_character_ids":["MOCK_P04_CHAR_001","MOCK_P04_CHAR_002","MOCK_P04_CHAR_003"]}`，另有 P17 已获角色集合 `owned_character_ids`、只读 P04 内容表 `character_skeleton.json` 及 P22 内容校验结果。输出仅是 `VALID` 或错误码，并给出可读角色信息和 P03 临时槽映射供 P15 构筑候选使用。P04不实现运行时、网络消息、存档或现金交易；真实域模型由 P17、DTO 由 P13、物理持久事务由 P21 提供。

- **战斗入场必须恰好3席**：列表长度必须等于3，索引 `[0,1,2]`，顺序保留。编队管理页如何展示空席位由 P17/UI 独立决定，不使不满编队进入战斗。
- **字符实例唯一**：同一 `character_id` 在一队只能出现一次；不能把不同的槽位名称视作不同拥有实例。本稿不强制“攻击+防御+治疗各一”，角色定位不成为额外配队禁令。
- **存在性 / 归属**：引用必须在 P04 当次只读 catalog 中解析；拥有集合必须含该角色。缺行不得创建默认角色；缺用户归属不得默默补发角色。
- **静态样例数量**：三条 P04 原型能演示一次标准三人编队，不声明用户有且仅有三名角色，也不允许把 P03 的第四 mock 槽当正式可获取角色。
- **位置与名称**：0、1、2 为有序 slot，不等于前中后战斗行规则。`position_hint` 是展示建议，不改变受击概率、目标、P02 排序。

## 2. 确定性验证优先级（遇到多项异常只返回首个）

1. `E_PARTY_PAYLOAD_TYPE`：编队不是对象/字段 `ordered_character_ids` 不是列表。
2. `E_PARTY_SIZE`：数组长度不为3。先判断数组长度，超限不会被忽略或截断。
3. `E_CHARACTER_ID_TYPE`：任一ID不是非空字符串。不得尝试隐式整数转字符串。
4. `E_PARTY_DUPLICATE`：重复角色ID。按索引顺序检查；不得仅检查角色定位。
5. `E_CHARACTER_NOT_FOUND`：内容表不存在此ID、内容行丢失或引用无法加载。先于拥有检查。
6. `E_CHARACTER_NOT_OWNED`：角色存在但用户还未获得。始终拒绝，不自动授权。
7. 所有条件满足 `OK`；返回原索引顺序作为编队只读候选。

无论成功或失败，P04 此检验本身不会修改钱包、卡组、存档、BattleState。P17 应在获批 DTO 上将上述语义实现为单一事务的前置条件；P32 验证失败前后的状态不变。

## 3. P03 卡组贡献边界

P04贡献表为**兼容桥接**，只允许 `MOCK_P04_CHAR_001→MOCK_P03_CHAR_A`、`002→B`、`003→C`。由 P03 只读原件确认：A 对应 `MOCK_P03_CARD_A_EDGE` / `MOCK_P03_SKILL_A`，B 对应 `...B_WALL` / `...SKILL_B`，C 对应 `...C_MEND` / `...SKILL_C`。未映射的D必须拒绝 `E_P03_SLOT_UNMAPPED`，不能从本岗生成 `MOCK_P04_CHAR_004`。若专属牌 owner 与映射不符，则 `E_SIGNATURE_OWNER_MISMATCH`，不得修改 P03 原卡。

S02 的9张测试牌结构是：STRIKE 2、BARRIER 2、RECOVER 1、EMBER 1，加3名已上阵角色各1张专属牌。每张卡有独立实例ID，P15/P13负责分配正式实例ID及牌堆行为。P04不固定正式牌数，不批准P03禁用的 BUFF / DEBUFF 卡。角色升级不直接改P03卡的 `cost`、`effect.amount`、`target_rule` 或 `mock_playable`；若后续需要角色数值影响卡牌，提交版本化 RFC 给 P03/P05/P13/P14，而非静默乘系数。

## 4. 成长、获取、钱包与技能

属性例仅以整数派生：`stat_at_level(L) = base_stats[stat] + (L-1) * per_level_growth[stat]`，L为1..5（都是未签署的fixture值）。P04提供四类示例属性：`max_hp`、`attack`、`defense`、`support`；**仅标注角色差异，不将它们接线至P02/P14伤害、护盾上限、回合顺序**。

- 获取：`ACQUIRE` 必须有经去重的外部权威奖励事件。测试仅以 `FIXTURE_STAGE_CLEAR_CHARACTER_GRANT` 为样例来源，真实获得归 P18/P05/P17/P21；重复事件不可发放第二次。
- 经验：`GRANT_XP` 仅累积该角色 `xp_total`，测试来源是 `FIXTURE_XP_GRANT`。等级升级必须经验累计达门槛，经验不因升级而扣除。
- 花费：`UPGRADE_LEVEL` / `UPGRADE_SKILL` 所需的 `MOCK_P04_TRAINING_TOKEN` 仅由测试关卡事件注入，不是实际掉落或 Anki 奖励。正式余额和可用/预留量由 P17 唯一管理；P21 单次原子持久提交。P04表里只有候选消耗，不自行向钱包直接写余额。
- 技能：rank1→2需角色等级≥3，rank2→3需等级≥5；rank增量只更新本岗技能等级条件，不修改专属卡结算。P05/ P03批准后才能追加实际技能倍率。
- 扣费前验证请求身份、目标角色与其当前等级/技能等级、XP阈值、最大等级、钱包可用余额和已预留资源。校验失败无钱包Delta，校验成功向 P17 提交候选；P17/P21负责原子写入、唯一业务事件、去重和事务冲突检测。
- 资源来源与去向必须成对登记，不能同时由学习事件与关卡奖励重复归账；尤其不得用 P04 规则授予 Anki 真复习奖励。P08、P11、P17及P21各司其职。

## 5. 升级与设备相关错误规则

| 触发 | 错误码 | 约束/默认行为 |
|---|---|---|
| 角色ID缺失 | `E_CHARACTER_NOT_FOUND` | 先于钱包扣减；拒绝 |
| 未拥有角色 | `E_CHARACTER_NOT_OWNED` | 拒绝 |
| 升级非相邻等级 | `E_LEVEL_STEP_INVALID` | 单次只允许 +1 |
| 达到等级上限再提升 | `E_LEVEL_CAP` | 拒绝，测试上限5非正式MVP上限 |
| 经验不足 | `E_XP_INSUFFICIENT` | 拒绝，XP累计不扣减 |
| 技能所需角色等级不足 | `E_SKILL_LEVEL_GATED` | 拒绝 |
| 技能rank跳级或超限 | `E_SKILL_STEP_INVALID` / `E_SKILL_CAP` | 拒绝 |
| 训练代币可用余额不足 | `E_WALLET_INSUFFICIENT` | 全部不变，不能部分扣费 |
| 重用相同命令ID、同一指纹 | `DUPLICATE_NO_OP` | 不再次扣费，P17/P21实现 |
| 命令ID相同但参数不同 | `E_COMMAND_ID_COLLISION` | 拒绝并保留原已执行凭据 |
| payload同一装备实例ID重复 | `E_EQUIPMENT_DUPLICATE` | **仅做坏数据检查**，不代表开放装备功能 |
| payload只有单装备但开关未批准 | `E_FEATURE_DISABLED` | 装备、稀有、好感、星级默认禁用，待DEC-009 |

装备检查次序：装备列表基本类型合法→重复实例ID检查→功能开关。即使开关关闭，也拒绝重复项为 `E_EQUIPMENT_DUPLICATE`；单个合格装备仍返回 `E_FEATURE_DISABLED`。不会创建装备效果、库存或价格，也不使装备进入 MVP。

## 6. 获取→编队→升级→序列化的可复现基准

参见 `content/characters/character_lifecycle_fixtures.json`：空账号开始，以本地fixture模拟三个角色获取、一次代币15授予、三个角色经验授予，设置有序编队，再升级璃火一次（4代币）和千澄两次（4+6代币），羽铃保持等级1。预期余额 `15 - 4 - 4 - 6 = 1`，三角色等级依次 `2/3/1`，最终 JSON 序列化后解码同值。**仅在验证脚本内内存 JSON 往返，不是游戏重启、不代表P21存档Schema、不得记为S06真机PASS。** P17/P21在S06需在进程退出、真正重新打开后复核资产、编队、等级、经验、技能rank、余额及事件去重记录。

## 7. 接口待审项

`IC-03` P22全球ID/Schema，`IC-09/IC-10` P17/P21养成与事务，`P03`卡内容；当前只有隔离静态检验。需 P13 actual_path_mapping、P22主registry、P05预算、P08源语义、P17业务代码、P21真实存档、P32独立测试、P35审查后才可升级状态。未经用户指定的 EXT-INTEGRATOR 不得跨模块合并。
