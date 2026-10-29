# P15｜牌堆、抽牌与出牌候选运行库交付

**已完成可执行的 S02 隔离运行库、作者测试、实际 P14 契约验证及完整交接包。** 任务对应 P01 的 **TASK-02-01**，交付版本为 **P15-DECK-RUNTIME/0.1.0-isolated**，沿用 **YLTT-INTERNAL/0.1.0-isolated** 消息格式。

**最终 148 项作者测试全部通过，新解压目录复跑结果一致。正式工程接入仍为 BLOCKED；P32 独测、P33 人工、P35 独审、目标引擎和 Anki 联调均为 NOT_RUN。**

## 一、完整成果下载

| 文件 | 实际大小 | 内容 |
| --- | --- | --- |
| **P15_DeckRuntime_V0.1.zip** | **5,549,301 字节** | 完整源码、测试、配置、样例、上游原件及执行证据，共 **190 个文件** |
| **delivery_receipt.json** | **97,994 字节** | ZIP 与 25 个独立导出的大小、SHA-256、包内路径，以及新解压目录的实际命令、退出码和原始输出 |

ZIP 的 SHA-256：

纯文本

`f19cb1114015a2a2f28f972bbda936ee3773f82d14cf90c81fde61c8ef38ea82`

已实际通过 ZIP CRC 检查、190 个包内文件字节核对，以及 **25 个独立导出文件与包内对应文件的同名、同字节比对**。包内清单记录其余 189 个文件；清单自身与 ZIP 由包外回执绑定，避免循环哈希。

### 主要文件单独下载

| 文件 | 用途 |
| --- | --- |
| README.md | 阅读入口、运行命令、能力与验收边界 |
| P15_API.md | 纯候选接口、幂等语义、P14 接线要求 |
| integration_handoff.md | 下一位接收与正式接入说明 |
| deck_patch_schema.json | P13 原 DeckPatchCandidate、Move、Rng 定义的独立投影 |
| invalid_play_cases.json | **38 个完整非法请求输入及期望结果** |
| deck_determinism_tests.py | 固定种子、RNG 历史、跨进程确定性测试 |
|  | 卡牌费用、归属、目标、启用状态、来源哈希与测试映射 |
| example_requests.json | 实际执行的请求、答复、候选证据及提交批次 |
| verification_status.json | 作者测试、契约、真机与独立验收的分层状态 |
| source_input_receipt.json | 固定版本、原附件、原 ZIP、输入文件及 SHA-256 |
|  | 逐文件路径、大小、SHA、格式／版本、源输入哈希、接收人和修改白名单 |

## 二、本轮实际实现

### 1. 编队构筑与确定性牌堆

已实现不可变 DeckState、卡实例身份、三席编队构筑，以及 draw / hand / discard / exhaust 四个牌区的候选操作。

构筑过程校验编队槽位、角色、实例归属和专属卡关联；按固定配方生成实例。**P03 的 24 个有序编队配方均已实测。** 实例 ID 绑定场次、完整编队哈希、配方哈希和序号，洗牌种子只影响牌序。

洗牌沿用 P02 的 **xorshift32-v1 + 降序 Fisher–Yates**，保存 initial_seed / state / draw_count，从牌堆左端抽牌。已验证：

- 抽牌堆为空时，按显式政策洗回弃牌堆。
- 消耗区不回流。
- 手牌达到上限后停止抽取，不额外消耗牌或 RNG。
- 无牌可抽时返回短缺信息。
- 空牌堆、单张牌和零抽牌请求不会多消耗 RNG。
- P02 **F014** 的牌序与 RNG 状态直接对照通过。

核心源码可单独查看：deck.py、builder.py。完整依赖和测试位于 ZIP 内。

### 2. 纯函数出牌校验与费用候选

已实现纯函数验证与 DeckPatchCandidate / ActionIntent 候选生成，检查内容包括：

- 场次、契约版本、规则版本、内容版本与 expected_revision。
- 当前阶段是否允许出牌。
- 卡实例是否存在、是否仍在手牌、是否属于出牌角色。
- 角色是否存活，专属牌归属是否匹配。
- 所有显式目标是否存在、存活、阵营正确、数量合法。
- 冻结内容中的费用是否可支付。
- 禁用卡、伪造费用字段、伪造 HP 字段和未定义的 DOT 重叠。

**非法领域请求不产生候选；合法请求只返回费用变化、牌区移动和 RNG 变化候选。费用余额、HP、效果、revision 与终局均由 P14 原运行库提交。**

当前共享 DTO 没有独立 ActionIntent 定义，因此本包将其保留为不可变的本地引用证据，记录卡牌、目标和效果引用；向 P14 发送的仍是原合同中的 DeckPatchCandidate。源码见 planner.py。

### 3. 重复点击、revision 与异常重试

当前合同中，岗位要求里的 request_id 对应 **P13 command_id**。完整请求指纹包含 revision 和目标顺序；重试应保留原 ID 与原载荷。

P15 的进程内缓存保留相同请求的原始候选或拒绝证据；相同 ID、不同指纹返回碰撞拒绝。**成功提交的最终防重由 P14 的已接受命令回执负责。**

实际 P14 契约测试已验证：

- **24 次并发相同请求只提交、扣费一次。**
- 已成功提交的同 ID 重发，不再次调用 P15 provider。
- 换新 ID 再打已经离开手牌的实例，不扣费。
- 同 revision 的两个不同请求，仅一个能提交。
- 三个提交前中断点均可回滚，原请求可重试。
- P14 在效果阶段拒绝时，费用和牌区一起回滚。
- 一次成功提交同时包含费用、移牌和效果。

对应实现见 commands.py、p14_adapter.py。

## 三、实际验证结果

### 分层状态

| 验证层级 | 本轮结果 | 证明范围 |
| --- | --- | --- |
| P15 作者设计复核 | **COMPLETED_AUTHOR_REVIEW** | 所有权、纯候选边界、输入来源与宣称范围 |
| 作者单元及隔离契约测试 | **148 PASS，0 FAIL，0 skip** | 新目录复跑一致；其中 25 项为 P14 契约与回合入口测试 |
| P13 原校验器检查 | **作者验证 PASS，168 条消息** | 实际命令、快照、候选、答复和提交批次等 |
| 实际 P15 重算回放 | **PASS** | 从原始请求重新计算，比较答复、候选证据、提交批次和最终状态 |
| 三个独立 Python 进程 | **PASS** | 不同 PYTHONHASHSEED 下执行摘要一致 |
| 原始输入未修改检查 | **PASS** | 4 个上传附件、2,930 个展开成员、70 份交付内原件 |
| ZIP、导出及新目录复跑 | **PASS** | 190 个文件、25 个独立导出 |
| 可选 jsonschema 算法对照 | **NOT_RUN；依赖 BLOCKED** | 当前 Python 未安装该依赖 |
| 正式工程前置检查 | **BLOCKED，exit 3** | 实际路径、真实输入与目标环境缺项 |
| P32 独测、P33 人工、P35 独审 | **NOT_RUN** | 未代签 |
| 目标引擎、UI／动画、Anki、P21、整套游戏 E2E | **NOT_RUN** | 未执行 |

详细状态见验证文件；逐项原始日志与执行时源码快照保存在包内 evidence/runs/。原字节复核记录另可下载：input_immutability_check.json。

### 实际运行样例

样例使用**真实 P15 运行库与未修改的 P14 原库**进行隔离契约装配；P17 编队与 P16 敌方输入明确标为测试夹具。

| 观测项 | 实际结果 |
| --- | --- |
| 请求数 | 18 |
| P14 提交数／最终 revision | 12 |
| 被拒绝请求 | 3 |
| 同 ID 重发 no-op | 3 |
| ENERGY_SPENT 事件 | 3 |
| 弃牌洗回次数 | 2 |
| RNG 消耗步数 | 16 |

这些结果来自实际执行，记录于 demo_summary.json。最终状态和回放文件已在新解压目录重新计算并核对。

### 本轮发现并修复的缺陷

交接接线检查发现 **P15-DEF-001**：当 P14 以原包名 battle_core 导入时，旧 P15 适配器引用的另一模块名下的 CandidateRejected 与其不是同一个 Python 异常类型。费用不足因此被 P14 误判为内部故障，进入 FAULTED。**当时没有扣费，但非法请求改变了战斗状态。**

修复只发生在 P15：适配器现在要求装配端显式传入当前 P14 使用的 CandidateRejected。修复后实测返回 REJECTED / ENERGY_INSUFFICIENT，权威状态全部字节保持不变。

**原 FAIL 日志、失败时源码、修复后 PASS 和回归测试均保留。** P32 复测及 P35 关单仍为 NOT_RUN，见 defect_log.json。

## 四、上游核验与正式接入阻塞

本轮已解包读取四份实际附件及包内原 ZIP，完成 **45 个唯一 ZIP** 的展开与完整性处理，并核验 **668 条转交清单记录、384 条相关上游内部清单记录**。

P14 输入绑定用户指定固定提交：

纯文本

`bc2b2daae2a1e784fb136f0a4e32cc84d84d84c6`

其原 ZIP 与原源码均保留；交付完整性工具还会将保留的 P14 文件再次与原 ZIP 对照。

正式接入当前仍有以下缺项：

| 缺项 | 责任方与当前处理 |
| --- | --- |
| P15 正式 actual_path_mapping 与写入授权 | **P13**；三条规划路径仍为 null / write_allowed=false，生产修改白名单为空 |
| 真实、带版本和哈希的合法编队快照 | **P17**；当前只使用明确标记的三席夹具 |
| 正式卡牌、配方、公共牌实例归属和费用政策 | **P03／P02／P05**；当前使用显式测试配置 |
| 正式内容 ID 与实例命名规范 | **P22**；当前命名空间限于隔离环境 |
| 负向候选、ActionIntent、构筑输入与抽牌报告的正式合同 | **P13／P14**；已准备版本化 RFC |
| 引擎、目标操作系统与可构建工程证据 | **P13／P01**；当前证据来自 Linux、Python 3.12 作者环境 |
| 独立测试、独立审查与最终合并 | **P32／P35／用户指定的 EXT-INTEGRATOR**；尚未执行 |

特别保留两项接口限制：

1. **公共牌 owner 尚未冻结。** P03 公共模板无 owner，P13/P14 却要求每个实例有 owner。本包强制测试配方显式提供归属槽位，未将其批准为产品规则。
2. **P14 当前只有一个 entry_draw_requested。** 适配器要求初始抽牌数、回合抽牌数与该字段一致；不同数目的正式接通需 owner 更新合同。

相关实体交接文件：

## 五、下一位直接复现

解压完整 ZIP，进入 P15_DeckRuntime_V0.1，使用 Python 3.12：

Bash

```
python -B tools/verify_delivery.py

python -B tools/author_tests.py

python -B -m deck_runtime

python -B tools/replay_example.py

python -B tools/check_contracts.py

python -B tools/preflight.py
```

前五条成功时退出码为 **0**；最后一条当前应返回 **3 / BLOCKED**。核心运行库、测试、示例及回放只依赖 Python 标准库。

已准备 **12 个接收方、68 条带实际文件哈希的交接记录**，均为 **PREPARED_NOT_ACKNOWLEDGED**，见 downstream_receipts.json。

P14 可据 API 接收候选提供方，P19 可读取错误语义和请求样例，P32/P35 可对本次 ZIP 固定哈希独立复测与审查。正式路径审批仍由 P13 处理，跨模块源码最终合并由用户指定的 **EXT-INTEGRATOR** 执行。

---

## 本次归档的原始文件

- [source_input_receipt.json](files/data/source_input_receipt.json)
- [builder.py](files/code/builder.py)
- [planner.py](files/code/planner.py)
- [06c45882-1-input_immutability_check.json](files/data/06c45882-1-input_immutability_check.json)
- [b75d7867-1-demo_summary.json](files/data/b75d7867-1-demo_summary.json)
- [3fc42b47-1-defect_log.json](files/data/3fc42b47-1-defect_log.json)
- [blockers.json](files/data/blockers.json)
- [interface_rfcs.json](files/data/interface_rfcs.json)
- [f6fdd7c0-1-path_mapping_request.json](files/data/f6fdd7c0-1-path_mapping_request.json)
- [b829da11-1-contract_acceptance.json](files/data/b829da11-1-contract_acceptance.json)
- [relay-materials-1-c617d116d7.zip](files/archives/relay-materials-1-c617d116d7.zip)
- [relay-materials-2-d3f598c365.zip](files/archives/relay-materials-2-d3f598c365.zip)
- [relay-materials-3-02e8113369.zip](files/archives/relay-materials-3-02e8113369.zip)
- [relay-materials-4-dc22516766.zip](files/archives/relay-materials-4-dc22516766.zip)
- [README.md](files/documents/README.md)
- [P15_DeckRuntime_V0.1.zip](files/archives/P15_DeckRuntime_V0.1.zip)
- [P15_API.md](files/documents/P15_API.md)
- [invalid_play_cases.json](files/data/invalid_play_cases.json)
- [deck_patch_schema.json](files/data/deck_patch_schema.json)
- [verification_status.json](files/data/verification_status.json)
- [deck.py](files/code/deck.py)
- [commands.py](files/code/commands.py)
- [task_traceability.json](files/data/task_traceability.json)
- [delivery_receipt.json](files/data/delivery_receipt.json)
- [downstream_receipts.json](files/data/downstream_receipts.json)
- [integration_handoff.md](files/documents/integration_handoff.md)
- [deck_determinism_tests.py](files/code/deck_determinism_tests.py)
- [card_legality_table.tsv](files/data/card_legality_table.tsv)
- [example_requests.json](files/data/example_requests.json)
- [delivery_manifest.sha256.tsv](files/data/delivery_manifest.sha256.tsv)
- [p14_adapter.py](files/code/p14_adapter.py)

