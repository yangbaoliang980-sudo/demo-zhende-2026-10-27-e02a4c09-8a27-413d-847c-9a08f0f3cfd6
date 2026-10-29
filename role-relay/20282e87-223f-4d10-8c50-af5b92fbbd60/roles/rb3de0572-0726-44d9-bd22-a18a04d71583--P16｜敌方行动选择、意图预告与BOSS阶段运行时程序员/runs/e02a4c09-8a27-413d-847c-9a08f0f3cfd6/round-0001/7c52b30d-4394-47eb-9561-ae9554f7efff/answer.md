# P16｜敌方行动、意图预告与 BOSS 阶段候选运行库交付

**已完成可执行的 P16 隔离运行库、固定输入回放、原 P14 单行动槽契约验证和完整交接包。最终 182 项作者测试全部通过，最终 ZIP 在新解压目录复跑结果一致。**

任务编号为 **P16-S03-AI-001**，交付版本为 **P16-ENEMY-AI/0.1.0-isolated**。正式工程接入、行为状态持久提交和 BOSS 阶段受理仍为 **BLOCKED**；P32 独测、P33 人工、P35 独审及目标引擎、UI、Anki、整游戏 E2E 均为 **NOT_RUN**。完整分层结果见 verification_status.json。

## 一、完整成果下载

| 文件 | 实际大小 | 内容 |
| --- | --- | --- |
| **P16_EnemyAI_V0.1.zip** | **11,197,353 字节** | 195 个实体文件：源码、测试、配置原件、回放、接口说明、RFC、失败与通过日志 |
| **delivery_receipt.json** | **52,374 字节** | ZIP 与 27 个独立导出的实际大小、SHA-256、包内路径，以及新目录复跑的命令、退出码和原始输出 |

ZIP 的 SHA-256：

纯文本

`6d535b2894cfbaa2dc52a829d2b4353ccc4c5c91c08fcbf0f5498d67e1fbf69d`

已实际完成 ZIP CRC 检查、**195 个包内文件字节核对**和 **27 个独立导出文件的同名、同字节比对**。包内清单记录其余 194 个文件；清单自身与 ZIP 由包外回执绑定，避免循环哈希。上述结果和新目录复跑记录均在交付回执中。

### 主要文件单独下载

| 文件 | 用途 |
| --- | --- |
| README.md | 阅读入口、能力范围、运行命令与验收边界 |
| P16_API.md | EnemyAction、预告、行为候选、PhaseProposal 和接收规则 |
| integration_handoff.md | 下一位接线、复测和正式接入说明 |
| intent_replay_fixtures.json | 86 组完整请求、实际输出、输出哈希及源期望字段核对 |
|  | 30 条 BOSS／阶段边界记录，含实际结果和阻塞状态 |
| enemy_intent_schema.json | P13 原 EnemyIntent、PhaseProposal 定义的独立投影 |
| source_input_receipt.json | 上游版本、固定来源、原附件及文件 SHA-256 |
|  | 逐文件路径、大小、SHA、格式／版本、源输入哈希、接收人及修改白名单 |

核心源码也可单独查看：planner.py、phases.py、types.py、content.py、p14_adapter.py。**运行时请使用完整 ZIP，以保留原 P13/P14 依赖和测试输入。**

## 二、本轮实际实现

### 1. 合法行动选择与确定性

实现了 P06 原配置中的普通怪、精英和 BOSS 行为循环，覆盖状态、冷却、蓄力、释放、恢复、目标轮换及合法性守卫。

本版 P06 使用固定循环，**每次 AI 决策消耗 0 个 RNG 值**。运行库仍验证 initial_seed / state / draw_count 的一致性，并保留原随机状态；没有擅自引入随机选招规则。相同输入在三个不同 PYTHONHASHSEED 的独立 Python 进程中得到一致执行摘要。实现和约束见 P16_API.md。

### 2. 提前预告与实际出招匹配

publish_intent 生成不可变预告，绑定场次、敌方实例、行动槽、阶段代次和内容哈希；`resolve_intent` 在执行时重验冻结记录。

已实现的合法偏差包括：

- 锁定单体目标死亡、移除或失去可选资格时，明确跳过，不替换目标。
- 群攻只筛除原名单中的失效目标，不增加新目标。
- 蓄力缺失、提前、过期或冷却阻塞时，返回明确原因和零伤害结果。
- owner 已受理阶段变化时，取消旧攻击并提出等待行为。
- 死亡、终局、反应未排空时，返回 NO_OP／DEFER，不提出消费行动槽。

next_forecast 明确标记为**条件性后继预测**；正式下一回合预告仍需基于 P14 提交后的新快照生成。相关完整输入和输出可在 intent_replay_fixtures.json 中复核。

### 3. BOSS 阶段提议与重复抑制

实现了整数阈值比较、有序阶段提议、死亡优先、阶段历史去重和缺图降级建议。

以 P06 的最大 HP 125 配置为例：

| 检查点变化 | P16 结果 |
| --- | --- |
| 76 → 75 | 提议进入 P2 |
| 38 → 37 | 提议进入 P3 |
| 80 → 30 | 按顺序提出 P2、P3；要求同批受理、一次等待、零额外行动 |
| 80 → 0 | 死亡优先，不提出阶段 |
| 已提议／已提交阶段再次检查 | 不重复提议，不新增行动机会 |

**P16 只产生 PhaseProposal 和受理要求，不写入 phase 或 HP。** 当前 P14 尚未实现阶段受理端口，这部分实际提交保持 BLOCKED。证据见 。

P06 原件没有召唤技能或召唤条件，因此本包保持空召唤提议，并拒绝未支持的 SUMMON 内容；没有补造 BOSS 机制。

### 4. P14 真实结算与重试边界

使用未修改的 P14 原运行库执行了单行动槽契约测试，覆盖护盾、扣血、过量伤害、死亡、重复请求、并发重试、旧 revision 拒绝及中断回滚。

实际示例结果为：

| 观测项 | 实际结果 |
| --- | --- |
| 请求数 | 3 |
| P14 提交数 | 2 |
| 同 ID 重试 no-op | 1 |
| 预告基础伤害 | 8 |
| P14 护盾吸收 | 4 |
| P14 实际扣血 | 4 |
| 角色 HP | 50 → 46 |
| 最终 revision | 2 |
| RNG | 未改变 |

这是**实际 P16＋原 P14 的隔离契约执行**；其中 P15 牌区输入和 P17 编队输入明确使用测试夹具。完整执行数据见 demo_execution.json，摘要见 demo_summary.json。

## 三、实际验证结果

以下数量存在包含关系，不能相加为额外测试总数。

| 验证层级 | 本轮结果 | 证明范围 |
| --- | --- | --- |
| 作者设计复核 | **COMPLETED_AUTHOR_REVIEW** | 所有权、纯候选边界与声明范围 |
| 最终作者测试 | **182 PASS，0 FAIL，0 error，0 skip** | 新解压目录复跑一致 |
| 原 P14 契约测试 | **18 项作者测试通过** | 包含正常行为和已知不支持行为的反例断言 |
| P06 原 89 条真值用例 | **86 条投影通过，3 条 BLOCKED** | 逐项记录已核对字段及未验证字段 |
| P13 原校验器 | **140 条合法消息通过** | 84 快照、51 EnemyIntent、5 PhaseProposal；另 2 个非法快照按预期拒绝 |
| 跨进程确定性 | **PASS** | 三个独立进程重算摘要一致 |
| 示例重新计算 | **PASS** | 从初始输入重算并比较完整执行结果 |
| 原输入未修改检查 | **PASS** | 4 个上传附件、61 个唯一 ZIP、3912 个展开成员、88 份保留上游原件 |
| 正式前置检查 | **BLOCKED，exit 3** | 路径、合同提交能力、正式内容和目标环境缺项 |
| P32／P33／P35 | **NOT_RUN** | 未代签独测、人工或独审 |
| 目标引擎、Windows、UI／动画、Anki、整游戏 E2E | **NOT_RUN** | 未执行 |

P06 的三个阻塞用例是 **P06-ET-059、P06-ET-061、P06-ET-076**，分别依赖阶段受理或权威命令历史，未将其冒充为完整运行通过。逐条记录见 p06_projection_results.json；原件复核见 input_immutability_check.json。

## 四、缺陷修复与尚未解除的接入阻塞

本轮实际修复了两项 P16 缺陷：

- **P16-DEF-001**：完整 P06 内容误用了 P13 消息键名编码规范。已改用不可变原内容容器，正式 DTO 仍交原 P13 codec。
- **P16-DEF-002**：畸形目标／行为 ID 在去重前未验证类型，可能抛 TypeError 或被当成缺失目标。已补充类型和标识符校验，并增加两项回归测试。

两项均保留失败时源码、原始失败日志和修复后测试记录；P32 复测、P35 关单仍为 NOT_RUN。见 defect_log.json。

正式接入仍有这些明确阻塞：

| 阻塞 | 跟进 owner |
| --- | --- |
| P16 两条正式路径仍为 null / write_allowed=false | **P13** |
| 共享快照缺少行为游标、冷却、蓄力、预告存储、targetable、phase_epoch 等字段 | **P13**；业务语义由 P14 配合 |
| 行为候选和冻结预告尚无权威原子提交端口 | **P14** |
| inspect_phase_proposal 仍返回 PHASE_COMMIT_CONTRACT_UNBOUND | **P14** |
| 群攻锁定名单由 3 人筛减为 2 人时，P14 固定 target_count=3 会跳过整次攻击 | **P14**；涉及 DTO 变化由 P13 出版 |
| 正式内容、内容 ID／Schema 和召唤配置未冻结 | **P06／P22** |
| 可构建工程、引擎和目标设备证据缺失 | **P13** |

**群攻筛减问题已经用原 P14 实际复现，没有修改上游代码掩盖限制。** 本包准备了 6 项带 base 文件 SHA 的版本化 RFC，状态均为 PREPARED_NOT_SUBMITTED。具体解除条件见 blockers.json 和 interface_rfcs.json。

## 五、下一位直接复现

解压完整 ZIP，进入 P16_EnemyAI_V0.1，使用 Python 3.12：

Bash

`python -B tools/verify_delivery.py
python -B tools/author_tests.py
python -B tools/replay_fixtures.py
python -B tools/check_contracts.py
python -B -m enemy_ai
python -B tools/replay_demo.py
python -B tools/preflight.py`

本次新目录实跑中，**前六条退出码均为 0，最后一条为 3／BLOCKED**。命令、原始输出和执行摘要已写入包外交付回执。

已准备 **11 个接收方、59 条带实际文件哈希的交接记录**，均为 PREPARED_NOT_ACKNOWLEDGED，见 downstream_receipts.json。P14 可接收候选接口与单槽验证，P19/P27 可读取意图和阶段表现数据，P32/P35 可对本次固定 ZIP 独立复测与审查。正式路径授权由 P13 处理，跨模块最终合并继续交由用户指定的 **EXT-INTEGRATOR**。