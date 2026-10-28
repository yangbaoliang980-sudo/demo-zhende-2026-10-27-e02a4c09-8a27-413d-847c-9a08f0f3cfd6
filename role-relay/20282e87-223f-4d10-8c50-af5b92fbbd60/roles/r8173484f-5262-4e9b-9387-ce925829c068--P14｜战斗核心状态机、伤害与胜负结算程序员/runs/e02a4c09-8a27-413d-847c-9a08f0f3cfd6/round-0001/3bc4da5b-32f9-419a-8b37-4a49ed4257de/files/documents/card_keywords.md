# P03｜卡牌关键词与扩展成本审查

版本：`P03-CARDS-0.1.0-draft`；范围：`S01-S02 TEST_ONLY`，**非正式词典合同**。本岗不修改 P22 的 Schema；`effect_code` 为 P02 夹具用语，若正式 DTO 不匹配由 P13/P22 出具版本化映射。

| 关键词 | P03解释 | 目标 | 契约证据 | 风险 / 审批状态 |
| --- | --- | --- | --- | --- |
| `DAMAGE` | 非负整数原始伤害，经P02规则先盾后HP | 存活敌方单体 | P02 F001/F020/F027 | 内容样例可本地静审，需P05定数值 |
| `SHIELD` | 非负整数加盾，盾上限与溢出策略未定 | 存活友方单体 | P02 F002 | 超上限效果仍为BLOCKED，需P05/P13 |
| `HEAL` | 恢复 `min(max_hp-hp, amount)` | 存活友方单体 | P02 F003 | 不可复活死亡单位 |
| `STATUS:DOT` | 施加一次 `OWNER_TURN_ENTER` 触发的样例状态 | 存活敌方单体 | P02 F024/F031/F033 | 重复应用叠层与唯一状态ID需P02/P13/P22审定 |
| `STATUS:BUFF` | **未定义的提议**，未来增强自身伤害 | 存活友方单体 | P02无正式修正时序 | BLOCKED；成本估计高：时序、叠层、伤害再计算、事件/回放、UI |
| `STATUS:DEBUFF` | **未定义的提议**，未来降低敌伤害 | 存活敌方单体 | P02无正式修正时序 | BLOCKED；成本估计高：敌方意图、叠层、数值下限、测试与UI |

**新增关键词审查结论**：S01-S02 实际活动 mock 保持 `DAMAGE/SHIELD/HEAL/STATUS(DOT)`，不引入新公式。`BUFF/DEBUFF` 已提供结构化示例，`mock_playable=false`；需要P02/P05/P06/P13/P22签署时序、修正的排序与异常策略，P01审批额外成本后才可开放。不能将这份成本分类当作工时实测。

目标选择：所有活动样例要求 `EXPLICIT_SINGLE`、`target_count=1`、存活目标，attack/DOT=ENEMY，shield/heal=PLAYER，不依靠UI自动换目标。没有默认自动目标选择。

触发码 `ON_PLAY` 是P03数据标签，不是P13已接受的引擎事件；`DAMAGE_APPLIED` 等事件只允许P14在权威提交后产生。UI表现参见 `card_effect_event_map.tsv`，提议并不作为事件生成指令。
