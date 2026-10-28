# P04｜角色数据、三人编队与养成系统

执行阶段：S02 角色骨架，兼顾 S06 后续接口准备

## 一、上游材料核验

已实际读取上传的转交包，并通过 GitHub 连接核对 V6.0 固定提交。

| 核验项目 | 结果 |
| --- | --- |
| 外层转交包 | 23 个原附件，大小及 SHA-256 全部匹配 |
| P01 完整交接 ZIP | 16 项，CRC 校验通过 |
| P02 完整交付 ZIP | 15 项，CRC 校验通过 |
| P03 完整交付 ZIP | 17 项，CRC 校验通过 |
| P03 卡牌配置 | 10 张测试卡牌，其中 8 张启用、2 张禁用 |
| P03 构筑样例 | 24 个有序三人编队测试样例 |
| V6.0 固定提交 | `8c370d731c323f86ff19642f4cc73f818498f641` |
| P13 正式路径映射与 DTO | BLOCKED |
| P22 正式内容 ID / Schema | BLOCKED |
| P05 正式经济预算 | BLOCKED |
| P08 学习资源政策 | BLOCKED |

本岗采用隔离研发交付：制作可机读、可独立校验的角色内容及测试数据，不把测试数值冒充正式平衡参数，不覆盖其他岗位文件。

P01 的 `DEC-004` 尚未批准初始角色数量。因此本次制作三个角色结构样例，是为了验证三人编队与不同角色的卡池贡献，并不代表首发角色数量已经冻结。

## 二、P04 正式交付文件

P04 S02 角色骨架与养成完整交付包

ZIP · 20 份文件 · 38,736 字节 · 已重新解压校验

下载 P04 完整交付 ZIP
SHA-256：`8a6c28d2eb87a4955ec702f57180c365cef19366d64295923ed8b9a0294382bc`

四份强制成果均为真实生成的独立文件：

| 文件 | 内容 |
| --- | --- |
| character_skeleton.json | 三角色属性、定位、成长公式、技能与卡牌引用 |
| party_constraints.md | 三人编队规则、错误码、合法性与事务边界 |
| progression_costs.tsv | 21 条获取、等级提升及技能升级记录 |
| character_deck_contribution.tsv | 角色对 P03 卡池贡献及精确引用关系 |

完整 ZIP 还包含字段字典、生命周期样例、28 条验收案例、Python 校验脚本、原始 P03 只读数据快照、执行日志、阻塞报告、上下游交接表和逐文件 SHA-256 清单。

## 三、三角色结构样例

璃火

ATTACK｜攻击型

生命

## 96

攻击

## 17

防御

## 5

支援

## 3

关联专属卡：`{c.card}`

千澄

DEFENSE｜防御型

生命

## 132

攻击

## 8

防御

## 15

支援

## 4

关联专属卡：`{c.card}`

羽铃

HEAL｜治疗型

生命

## 108

攻击

## 7

防御

## 7

支援

## 17

关联专属卡：`{c.card}`

以上均为 Lv1 测试属性，不是正式平衡参数；角色名称和正式内容 ID 仍待审批。
## 四、实际执行验证

作者静态断言

# 485

最终执行通过

负向校验

# 34

实际断言通过

三人排列

# 6/6

与 P03 原测试牌组匹配

完整包校验

# PASS

CRC 与 19 项文件哈希通过

已模拟角色获取、设置三人队伍、累计经验、消耗训练代币、升级以及 JSON 序列化与重新读取，状态与预期一致。代币测试为 `15 − 4 − 4 − 6 = 1`。

验证命令：

Bash

```
python content/characters/validate_character_content.py
```

该命令已在交付包原目录及重新解压的独立目录执行，退出码均为 `0`。

验证边界： 内存 JSON 往返不等于真实游戏退出重启；P17 运行时代码、P21 落盘事务、P32 独立测试与 P35 审查均标记 `NOT_RUN`，未宣称通过。

## 五、交接状态

| 后续负责人 | 交接目标 | 状态 |
| --- | --- | --- |
| P03 | 角色专属卡关联复核 | 待接收 |
| P05 | 成长数值与资源成本审批 | BLOCKED |
| P22 | 正式内容 ID 与 Schema 检查 | BLOCKED |
| P13 | 工程路径及 DTO 映射 | BLOCKED |
| P17 | 编队、获取、养成和钱包业务实现 | 待接收 |
| P21 | 原子存档及实际重启验证 | NOT_RUN |
| P32 / P35 | 独立测试及审查 | NOT_RUN |

P04 当前结论：`LOCAL_CONTENT_DELIVERED / FORMAL_INTEGRATION_BLOCKED`。

本岗独占内容已交付并完成本地静态验证。未修改 GitHub 原工程或其他岗位文件，未代行跨模块整合。下一位可以直接使用完整 ZIP、源输入哈希、接口阻塞记录和测试脚本继续工作。

---

## 本次归档的原始文件

- [requirements_baseline_v6.txt](files/documents/requirements_baseline_v6.txt)
- [decisions_pending.tsv](files/data/decisions_pending.tsv)
- [task_register.tsv](files/data/task_register.tsv)
- [handoff_receipts.tsv](files/data/handoff_receipts.tsv)
- [gate_issues.tsv](files/data/gate_issues.tsv)
- [P01_S00_V6_完整交接包.zip](files/archives/P01_S00_V6_%E5%AE%8C%E6%95%B4%E4%BA%A4%E6%8E%A5%E5%8C%85.zip)
- [battle_state_machine.md](files/documents/battle_state_machine.md)
- [effect_priority.tsv](files/data/effect_priority.tsv)
- [terminal_phase_truth_table.tsv](files/data/terminal_phase_truth_table.tsv)
- [battle_replay_fixtures.json](files/data/battle_replay_fixtures.json)
- [interface_rfc_and_blockers.md](files/documents/interface_rfc_and_blockers.md)
- [P02_DELIVERY_README.md](files/documents/P02_DELIVERY_README.md)
- [P02_S01_战斗状态机与确定性结算规则_V0.1_完整交付包.zip](files/archives/P02_S01_%E6%88%98%E6%96%97%E7%8A%B6%E6%80%81%E6%9C%BA%E4%B8%8E%E7%A1%AE%E5%AE%9A%E6%80%A7%E7%BB%93%E7%AE%97%E8%A7%84%E5%88%99_V0.1_%E5%AE%8C%E6%95%B4%E4%BA%A4%E4%BB%98%E5%8C%85.zip)
- [9c42e18d-card_choice_cases.tsv](files/data/9c42e18d-card_choice_cases.tsv)
- [9c42e18d-1-card_choice_cases.tsv](files/data/9c42e18d-1-card_choice_cases.tsv)
- [card_catalog.json](files/data/card_catalog.json)
- [card_choice_cases.tsv](files/data/card_choice_cases.tsv)
- [interface_rfc_blockers.md](files/documents/interface_rfc_blockers.md)
- [manifest.sha256.tsv](files/data/manifest.sha256.tsv)
- [P03_static_validation.log](files/other/P03_static_validation.log)
- [card_effect_examples.json](files/data/card_effect_examples.json)
- [P03_S01_S02_卡牌牌组与专属技能_V0.1_完整交付包.zip](files/archives/P03_S01_S02_%E5%8D%A1%E7%89%8C%E7%89%8C%E7%BB%84%E4%B8%8E%E4%B8%93%E5%B1%9E%E6%8A%80%E8%83%BD_V0.1_%E5%AE%8C%E6%95%B4%E4%BA%A4%E4%BB%98%E5%8C%85.zip)
- [party_deck_rules.md](files/documents/party_deck_rules.md)
- [P04_character_skeleton.json](files/data/P04_character_skeleton.json)
- [P04_party_constraints.md](files/documents/P04_party_constraints.md)
- [P04_progression_costs.tsv](files/data/P04_progression_costs.tsv)
- [P04_character_deck_contribution.tsv](files/data/P04_character_deck_contribution.tsv)
- [P04_S02_Character_Progression_Delivery_V0.1.zip](files/archives/P04_S02_Character_Progression_Delivery_V0.1.zip)
- [P04_character_skeleton.json](files/data/39a7728a53165c9ef8953fa5b232efe900a5d1a4a6fd40ffe038581ea6c39515/P04_character_skeleton.json)
- [P04_party_constraints.md](files/documents/17ecdadf9758fa0e0001872df60e122194d650c7c4ece0bb3f741d16ae8ccf31/P04_party_constraints.md)

