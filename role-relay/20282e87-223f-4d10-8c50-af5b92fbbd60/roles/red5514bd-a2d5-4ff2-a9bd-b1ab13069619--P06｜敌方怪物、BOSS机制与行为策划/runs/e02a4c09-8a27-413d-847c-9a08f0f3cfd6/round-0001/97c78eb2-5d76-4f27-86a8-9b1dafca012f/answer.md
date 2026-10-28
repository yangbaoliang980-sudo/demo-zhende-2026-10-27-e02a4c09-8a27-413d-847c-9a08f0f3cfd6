# P06｜敌方怪物、BOSS机制与行为交付

**已完成 P06 的实体内容交付及作者静态验证。当前状态：LOCAL_CONTENT_DELIVERED / FORMAL_INTEGRATION_BLOCKED。**

任务 ID：P06-S03-ENEMY-001
内容版本：P06-ENEMY-0.1.0-proposal

本次交付包含 **3 类敌人机制样本、13 个动作定义、18 个循环状态、89 条固定输入与期望结果用例**，以及验证工具、原始日志、源文件快照和完整哈希清单。S03 部分覆盖单怪与意图；精英及 BOSS 部分作为后续阶段的机制与边界交付。**这些样本尚未成为正式游戏配置，P16 AI 和 P14 引擎运行仍为 NOT_RUN。**

## 一、完整交付文件

**完整包：**[P06_Enemy_Delivery_V0.1.zip](https://chatgpt.com/library?file_id=libfile_f0f6d051d6d4819182e7c0c3477edf2d&account_id=personal)

- 包含 **43 个文件**，大小 **168,593 字节**。
- ZIP CRC 通过。
- 已重新解压，并再次执行文件清单核验、内容静态检查及校验器测试，退出码均为 0。
- 阅读入口：[README.md](https://chatgpt.com/library?file_id=libfile_3b18924563f08191868ca5f23898e03e&account_id=personal)。
- 完整验证回执：[P06_delivery_receipt.json](https://chatgpt.com/library?file_id=libfile_0a38429828688191b0c9d798e6e8b088&account_id=personal)。

ZIP 的 SHA-256：

纯文本

`0a2912acc81c594bba6fb93bd631ef77c412769adb2ad68f553914a44e1c1ce7`

四项强制成果均已生成，包内目录为 content/enemies/：

| 文件 | 实际大小 | 交付内容 |
| --- | --- | --- |
| [enemy_specs.json](https://chatgpt.com/library?file_id=libfile_8c57f05e579c8191999c920b417ee2a5&account_id=personal) | 25,799 字节 | 敌人 ID、技能、合法目标、循环、冷却、蓄力、免疫与异常退路 |
| [intent_dictionary.tsv](https://chatgpt.com/library?file_id=libfile_73b8ceb1f248819198ae8bb73c751414&account_id=personal) | 5,583 字节 | 13 条意图语义，区分当前伤害、未来重击和合法取消原因 |
| [boss_phase_graph.json](https://chatgpt.com/library?file_id=libfile_c55bbe7cbbf881919b54210e8b3f6c22&account_id=personal) | 6,305 字节 | 阶段阈值、提案顺序、终局与死亡出口、缺逻辑图退路 |
| [enemy_truth_cases.tsv](https://chatgpt.com/library?file_id=libfile_534f2d1f421881919ba0fd1d90733456&account_id=personal) | 201,375 字节 | 89 条固定状态、种子、操作及期望投影，逐条保留 NOT_RUN 标记 |

另附可编辑状态图：[boss_phase_graph.mmd](https://chatgpt.com/library?file_id=libfile_43feec1e27ac8191837958784749f796&account_id=personal)。

逐件相对路径、大小、完整 SHA-256、格式／版本、源输入哈希、接收岗位和修改白名单，已记录在 [delivery_manifest.sha256.tsv](https://chatgpt.com/library?file_id=libfile_0c03fb9df37881918a670b1d5a65615f&account_id=personal)。清单覆盖其余 42 个包内文件；清单自身及 ZIP 的哈希由外层交付回执固定。

## 二、上游材料已实际核验

本次已解包读取外层附件及 P01—P05 的完整内层 ZIP：

| 核验项目 | 结果 |
| --- | --- |
| 外层原始文件 | **34/34** 大小及 SHA-256 匹配 |
| P01 内层清单 | **15/15** 匹配 |
| P02 内层清单 | **14/14** 匹配 |
| P03 内层清单 | **16/16** 匹配 |
| P04 内层清单 | **19/19** 匹配 |
| P05 内层清单 | **19/19** 匹配 |
| 5 个内层 ZIP | 均实际打开，CRC 通过 |
| V6 原文 | 经 GitHub 读取固定提交，本地 SHA-256 与 Git blob 校验匹配 |
| P05 参数表与完整 ZIP | 与固定归档清单中的大小、SHA-256、Git blob 匹配 |

固定来源分别为：

- V6：8c370d731c323f86ff19642f4cc73f818498f641
- P05 归档：18e7cd9af350fad790a4970250b6b27c595a7868

**部分外层独立 TSV 只有表头。**例如独立 effect_priority.tsv 仅有 11 字节；本次采用 P02 完整 ZIP 中的 30 条优先级规则。P01 决策表也采用经核验的完整内层版本。具体记录及 13 份实际使用的只读源快照均已放入交付包，入口见 [README.md](https://chatgpt.com/library?file_id=libfile_3b18924563f08191868ca5f23898e03e&account_id=personal)。

## 三、已落成的敌人机制

所有 ID 使用 MOCK_P06_* 命名空间，并明确设置 production_enabled=false。下表中的 HP、基础攻击和初始盾沿用 P05 的测试预算；重击、群攻和循环安排是 P06 的机制候选，仍需重新评估与批准。

| 类型 | 名称及测试 ID | HP／初始盾 | 行动模式 |
| --- | --- | --- | --- |
| 普通 | 游离字屑，MOCK_P06_ENEMY_001 | 24／0 | 每次单体基础伤害 8 |
| 精英 | 锁页卫士，MOCK_P06_ENEMY_002 | 55／4 | 单体 12 → 蓄力 0 → 重击 24 → 整理 0 |
| BOSS | 失序校勘者，MOCK_P06_ENEMY_003 | 125／0 | 三阶段循环，包含单体 18、群攻每名 6、蓄力重击 36 |

BOSS 三个阶段的循环为：

| 阶段 | 循环 |
| --- | --- |
| P1「校勘」 | 单体 18 → 蓄力 0 → 重击 36 → 整理 0 |
| P2「散页」 | 群攻每名 6 → 蓄力 0 → 重击 36 → 整理 0 |
| P3「终句」 | 单体 18 → 群攻每名 6 → 蓄力 0 → 重击 36 → 整理 0 |

这些定义及其数值来源可以直接在 [enemy_specs.json](https://chatgpt.com/library?file_id=libfile_8c57f05e579c8191999c920b417ee2a5&account_id=personal) 中核对。

### 意图、蓄力与冷却

本版明确了以下行为：

- **预告显示基础伤害。**实际抵盾、扣血和过量伤害由 P14 的结算结果提供。
- **蓄力当次伤害为 0。**下一次敌方行动才尝试释放重击，中间保留完整玩家决策窗口。
- **重击释放后 HEAVY 冷却为 2。**阻塞随后两个本敌行动槽；整理、明确跳过和阶段等待也按规定递减。
- **单体目标锁定后不暗中更换。**预告目标失效时明确跳过；如果玩家已全灭，先按 P02 判定终局。
- **群攻不追加新目标。**只能从已预告名单中移除失效对象。
- **固定循环不消耗随机数。**种子仍随输入保留，避免预告读取或动画操作改变 RNG 状态。

完整预告文本、数值字段和合法偏差原因见 [intent_dictionary.tsv](https://chatgpt.com/library?file_id=libfile_73b8ceb1f248819198ae8bb73c751414&account_id=personal)。

## 四、BOSS 阈值与致死反例已经写入用例

阶段阈值候选为 **60% 和 30%**，采用整数比较。对于 125 最大 HP：

- P2 的触发边界为 **75 HP**。
- P3 的最大符合整数 HP 为 **37 HP**，不能四舍五入为 38。

阶段提案必须晚于伤害、死亡、合法反应排空及终局判断。**提案本身不改变当前阶段，只有 P14 受理后才提交。**

| 固定情况 | 期望行为 |
| --- | --- |
| 76 → 75 | 提出 P2，当前阶段等待 P14 受理后才改变 |
| P2 中 38 → 37 | 提出 P3 |
| 80 → 30，BOSS 存活且双方仍有活体 | 按顺序提出 P2、P3；受理后进入最终阶段，仅安排一次阶段等待 |
| 80 → 0，最后敌人死亡且玩家存活 | **WIN；无阶段提案、无回血、无复活** |
| BOSS 死亡，但其他敌人仍存活 | 战斗继续；死 BOSS 退出行动，不再切阶段 |
| BOSS 存活，但合法反应导致玩家全灭 | **LOSS 优先，不切阶段** |
| 双方在根效果及死亡反应后全部死亡 | **DRAW；不能先发 WIN 再发 LOSS** |
| 敌方入口 DOT 杀死最后 BOSS | 先结束战斗，不能补执行已预告重击 |

这些边界已进入 P06-ET-042、043—059 等用例，完整输入和预期见 [enemy_truth_cases.tsv](https://chatgpt.com/library?file_id=libfile_534f2d1f421881919ba0fd1d90733456&account_id=personal)。

阶段切换还明确禁止隐藏回血、复活、赠盾、清除 DOT、无敌帧和额外攻击。旧蓄力会被取消，重复阶段提案不能反复重置循环或冷却。

### 两种缺失情况分别处理

**缺阶段逻辑图：**基础攻击配置仍有效时，进入本局固定的降级行为模式，先给一次零伤提示，再持续预告基础攻击；保留最后已提交的 phase_id。基础招式也损坏时，拒绝加载或进入受控故障，避免无限空转。

**仅缺阶段图片：**阶段、伤害、蓄力、冷却和 RNG 不变。优先复用同敌可用卡面；全部图片缺失时仅提供明确标识的文字诊断显示，正式美术状态保持 BLOCKED。对应定义见 [boss_phase_graph.json](https://chatgpt.com/library?file_id=libfile_c55bbe7cbbf881919b54210e8b3f6c22&account_id=personal)。

## 五、实际验证结果与边界

已实际执行：

1. **内容静态校验**：检查源 SHA、技能与意图一致性、18 个循环状态后继、阶段可达性、单向阈值、终局出口、降级进展及用例算术。
2. **22 项校验器测试**：其中 21 项为负向变异，验证错误预告、阶段倒退、隐藏回血、缺退路、致死后切阶段以及假冒运行 PASS 等问题能够被拒绝。
3. **重新解压核验**：再次运行清单核验、内容校验和上述测试，均成功。

**89 条真值用例仍是期望数据，真实 AI 行为执行数为 0。**作者校验通过不等于 P16/P14 实现通过，原始命令、退出码和输出已保存在 [P06_delivery_receipt.json](https://chatgpt.com/library?file_id=libfile_0a38429828688191b0c9d798e6e8b088&account_id=personal) 及包内日志中。

| 验收层级 | 当前状态 |
| --- | --- |
| 源文件完整性核验 | **PASS** |
| P06 内容静态自检 | **PASS** |
| P06 校验器作者测试 | **PASS，22/22** |
| 复解压与文件哈希核验 | **PASS** |
| 独立设计审核／P35 SPEC Gate | **NOT_RUN** |
| P13 正式路径与 DTO、P22 ID／Schema | **BLOCKED** |
| P16 AI 单元运行、P14 真实结算／契约运行 | **NOT_RUN** |
| P32 独测、P33 人工、P35 独审 | **NOT_RUN** |
| 游戏真机、真实动画等价、Anki E2E | **NOT_RUN** |
| 正式工程写入及跨模块集成 | **BLOCKED** |

解压后可直接复算：

Bash

```
python design/enemies/verification/validate_enemy_content.py
python -m unittest discover -s design/enemies/verification -p "test_*.py" -v
python design/enemies/verification/verify_manifest.py
```

## 六、下游接收条件

包内已形成版本化 RFC、具体阻塞记录和接收文件对应表。关键未解除项是：

| 责任方 | 待补证据 |
| --- | --- |
| P13 | actual_path_mapping.json、真实工程基线、写入白名单及正式 DTO 版本 |
| P22 | 内容 ID 注册表及正式 Schema |
| P07 | 固定版本的关卡配置与节奏依据 |
| P05 | 针对本次蓄力、群攻和阶段循环重新评估的预算回执 |
| P01 | 敌人数量等范围批准及后续阶段接入确认 |
| P16／P14 | 实现与契约受理、固定提交及真实运行证据 |
| P32／P35 | 独立测试和分层审查结论 |

**P05 原先无阶段 BOSS 的“20 回合胜利”等结果不能直接沿用到本配置。**新循环引入了蓄力、整理、阶段等待和目标锁定，需要重新测算。

下一位可从完整包的 README.md 直接进入四项主产物、行动表、RFC、89 条用例和原始证据。接收状态均保留为 PREPARED_NOT_ACKNOWLEDGED；正式路径映射与跨模块整合授权仍按既定职责处理。