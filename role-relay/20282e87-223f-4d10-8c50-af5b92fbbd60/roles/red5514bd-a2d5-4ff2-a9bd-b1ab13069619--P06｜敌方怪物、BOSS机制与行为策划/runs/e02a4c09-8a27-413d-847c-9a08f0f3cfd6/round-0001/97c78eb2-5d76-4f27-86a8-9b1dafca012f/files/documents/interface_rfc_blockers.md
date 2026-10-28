# P03｜接口变更申请、阻塞台账与恢复规则

- P03局部版本 `P03-CARDS-0.1.0-draft`，上游P01 ZIP SHA-256 `139034e2179fbe35c4ac5f3240b0df435b03b9a70f5507263ee97b7e8b022a89`；P02 ZIP SHA-256 `969c7e7688f795aaea80abddc0c4ed949f5f6b9d8588c2e787a0f9da1fb06501`。
- 原V6 GitHub固定提交 `8c370d731c323f86ff19642f4cc73f818498f641`，经已连接GitHub只读核对职责；未对任何仓库做写操作。
- 主观平衡参数、字符槽、零学习策略与后续卡牌规模不能视为用户认可。P03本次仅交付**本地内容候选和静态fixture**。

| 阻塞ID | 状态 | 唯一解除owner | 缺失资料 / 解除条件 | 不影响当前哪些工作 |
| --- | --- | --- | --- | --- |
| P03-BLK-01 | BLOCKED | P13 | `actual_path_mapping.json`、真实工程路径及授权、正式 BattleState/Card/EffectIntent DTO版本和目标环境 | 隔离卡牌数据与本地校验 |
| P03-BLK-02 | BLOCKED | P22 | 正式 card_id/effect_id/skill_id/character_id 唯一性规则、Schema及全域registry | `MOCK_P03_*` 内部无悬空引用校验 |
| P03-BLK-03 | BLOCKED | P04 | 正式可选角色、三人合法性、角色定位、专属skill/关联角色ID | 四测试角色槽24排列fixture |
| P03-BLK-04 | BLOCKED | P05 | 正式卡费用、伤害/盾/治疗、能量预算、状态修正数值边界 | mock非正式数值静态算术 |
| P03-BLK-05 | BLOCKED | P08 | 学习资源语义、词性卡映射、未复习资源基线与不诱导复习政策 | 内容结构，不执行学习奖励 |
| P03-BLK-06 | PENDING_USER_DECISION | P01 | `DEC-003`零学习日基础动作资源，`DEC-004`正式初始角色/卡数量 | 不影响隔离牌样例的结构质量 |
| P03-BLK-07 | BLOCKED | P02 | BUFF/DEBUFF 的修正次序、状态叠层与去重/回放规则 | 把两张提议卡设置 `mock_playable=false` |
| P03-BLK-08 | NOT_RUN | P15 | 未交付真实 DeckPatch/抽弃牌、合法性运行与场景断言 | 24个纯构筑fixture与选择静态预期 |
| P03-BLK-09 | NOT_RUN | P32/P35 | 缺P32独立测试日志及P35审查门禁 | P03自行执行只读静态校验 |

## 待签RFC（PROPOSED / NOT_ACCEPTED）

- `P03-RFC-IC03-001` → P22（抄送 P04/P13）：请求正式内容ID命名空间、card/effect/skill/character交叉引用及scope校验。旧Schema的base SHA=**MISSING**，禁止声称向既有Schema打过补丁。
- `P03-RFC-IC04-001` → P13/P15（P03内容owner）：请求版本化 `card_id` ↔ 运行 `card_instance_id`、费用目标结构、用牌者与专属牌拥有关系、HAND→DISCARD 候选语义；P15产生候选、P14唯一提交。旧 DTO base SHA=MISSING。
- `P03-RFC-IC08-001` → P13（抄送 P19/P29）：将P14逻辑 `DAMAGE_APPLIED`、`HEAL_APPLIED`、`SHIELD_GRANTED`、`STATUS_APPLIED` 映射至只读表现。P03不新建战斗事件名，不发布UI事件到引擎。
- `P03-RFC-STATUS-001` → P02/P05/P13/P22（P01跟进）: 当前DOT仅P02夹具可表达；BUFF/DEBUFF需要正式 modifier 先后、状态生命周期、叠层、效果上限、下限、去重、回放和展示契约。未接受之前不许在P15中合法出牌。

## 变更与恢复

P15拒绝真实卡配置：固定记录 `card_id`、场景 `case_id`、P03内容哈希、P02版、P13 Schema版、P15构筑/验证原始结果；P22 Schema问题退P22，P03内容问题由P03单卡返工，P02公式问题退P02。**不由P03更改引擎/结构Schema**。

收到另一分支竞争变更：双方保留 base SHA、old/new 值和接口版本，提交 ChangeRequest 给契约owner，不覆盖式合并；同问题两轮无新增证据，升级P01。任何授权实体文件的合并由用户另外指定EXT-INTEGRATOR。所有下游回执为 `PREPARED_NOT_ACKNOWLEDGED`。
