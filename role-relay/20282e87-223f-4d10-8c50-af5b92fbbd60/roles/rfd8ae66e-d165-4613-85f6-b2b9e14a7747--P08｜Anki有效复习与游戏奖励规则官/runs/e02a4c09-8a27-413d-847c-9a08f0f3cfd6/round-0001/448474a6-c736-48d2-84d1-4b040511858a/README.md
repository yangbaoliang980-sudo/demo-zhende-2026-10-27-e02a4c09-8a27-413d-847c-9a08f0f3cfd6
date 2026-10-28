# P08｜Anki 有效复习与游戏奖励规则交付

**P08 的实体交付已完成：四份主文件、四键真值表、撤销补偿算例、下游用例和作者验证证据均已生成。当前状态为 LOCAL_POLICY_DELIVERED / FORMAL_AWARD_BLOCKED。**

任务 ID：P08-S04-S05-POLICY-001
版本：P08-REWARD-POLICY/0.1.0-proposal

本版包含 **31 条分级规则、84 行四键真值表、58 条下游逻辑用例、13 个数学示例，以及 16 项实际执行的校验器作者测试**。正式四键奖值、已消费权益处置和无学习日资源仍未获得用户批准，不能据此指挥 P11 真实发奖。

## 一、完整交付文件

**完整包：**

包内共 **62 个文件**，ZIP 大小 **2,523,333 字节**，已通过 CRC 检查及重新解压后的逐件哈希、政策静态复核。具体记录见 。

ZIP 的 SHA-256：

纯文本

`c61826ec9af75cbd0a426f13b3f9c40f852f83f69c11093655fb4214419e612f`

阅读入口：。完整包内的入口名称为 README.md。

### 四项强制成果

| 实体文件 | 包内完整相对路径 | 实际大小 | 已完成内容 |
| --- | --- | --- | --- |
|  | spec/anki/reward_semantics/study_policy_draft.md | 18,083 字节 | 真实复习资格、判断优先级、四键候选、分类资源、发放时点、跨日、封顶、反刷及关卡边界 |
|  | spec/anki/reward_semantics/four_rating_policy_matrix.tsv | 18,719 字节 | 21 类条件 × 4 个评分键，共 84 行；正式金额均为 UNSET |
|  | design/anki_rewards/undo_compensation_options.md | 8,519 字节 | 未消费、部分消费、全部消费、恢复、重复撤销、四种补偿候选及人工裁决门槛 |
|  | design/anki_rewards/quarantine_resolution_policy.md | 7,026 字节 | 隔离原因、影响范围、解除证据、操作权限、复核及审计要求 |

逐件相对路径、实际大小、完整 SHA-256、格式／版本、源输入哈希、接收人及修改白名单，已写入 。清单覆盖包内其余 **61 个文件**；清单自身及 ZIP 的哈希由外层交付回执固定。

## 二、本版规则的关键结论

以下候选的具体依据、状态及边界均已落入四份主文件，不能把候选解释为正式配置。

### 1. 四键推荐同额基础收益，Again 保留合格资格

在**同一真实事件证据、同一类别、同一额度状态**下，推荐方案如下：

| 评分 | 能否构成合格真实复习 | 推荐收益候选 | 不应附加的奖励倾向 |
| --- | --- | --- | --- |
| Again | 可以，不能仅因未记住而否定 | 基础向量 B(category) | 不扣基础收益，也不设置“答错额外奖” |
| Hard | 可以 | 同一基础向量 | 不因困难降档 |
| Good | 可以 | 同一基础向量 | 不增加评分奖金 |
| Easy | 可以 | 同一基础向量 | 不额外提高币量、稀有率、卡牌强度或行动资源 |

**B 是待批准的符号，不是“每次 1 代币”。** P05 已交付的等额数字属于影子测试输入，本版没有把它升级为正式经济参数。

规则同时保留了一个重要限制：**四键等额只能消除单次评分差价，不能独自证明长期没有刷取诱因。** 如果故意按 Again 增加后续复习次数，按次奖励仍可能产生收益优势。因此，完整行为路径仍需 P05/P39 评估；不能未经能力证明和用户批准，就擅自实施“同卡每天只奖一次”。

### 2. 区分真实复习、权益资格和实际到账

规则把处理过程分为来源、完成、身份、政策、交易五层：

- 按钮点击、展示答案、UI 请求，不等于真实完成提交。
- 同一身份、同一指纹重投，返回原结果，不新增权益。
- 同一身份却修改评分或载荷，隔离冲突输入，不能直接推翻原已发权益。
- 可信 Undo 优先于其目标的迟到完成；撤销先到时保留目标关系，不能让迟到事件重新领取。
- 正常调度产生的同卡下一次真实完成，与 Undo 后的重答分别判断。
- 只有 P21 的持久提交凭证能够支持“已经到账”。

**P10 无法证明目标版本的事件身份或 Undo 关联能力时，相关来源停止自动授奖，进入隔离。** 等待一段时间不能替代能力证明。

### 3. 已消费权益撤销，不默认变成玩家债务

补偿文件比较了四种候选：

| 候选 | 处理方式 | 当前是否获批 |
| --- | --- | --- |
| 隔离并人工裁决 | 保留既得资产，记录差额，核对关联消费和原事务 | 未获批；P08 推荐作为首版待选路线 |
| 保留已消费权益 | 经用户批准转为一次性补偿，继续绑定原复习关系 | 未获批 |
| 未来同来源、同币种抵扣 | 后续收入按批准规则部分抵扣，钱包保持非负 | 未获批 |
| 可逆冻结关联权益 | 在能精确定位且可恢复的前提下限制相关权益 | 未获批，且实现成本较高 |

一个已经写入文件并实际复算的**合成数学示例**：

> 原授予 10，已消费 7，撤销时回收可证明未消费的 3，则剩余 7 是“待裁决权益差额”，不是默认玩家欠款。
> 如果之后证明原复习恢复有效，原已消费的 7 应计入已给权益，只需处理差额 3，不能再发完整的 10。

该示例没有规定真实奖额，也没有执行钱包操作。混合来源、来源分摊不明、已豁免或已抵扣后再恢复，都必须进入关联对账，不能简单套公式扣余额。

### 4. 跨日、分类和封顶均有明确边界

跨日补发按可证明的**原发生日及当时适用政策**处理，不能以接收日期重开配额。同一事件隔天重发不产生新奖；跨日 Undo／恢复沿用原复习关联链及原日归属。

本版没有假设 Anki 默认日界，也没有自行冻结时区、每日上限或追溯期限。文件中的 null／UNSET 表示尚未确定，不能解释为“无限额”或数值零。

分类方面明确区分：

- **已有批准映射返回 UNKNOWN**：按其通用资源分支处理。
- **整个映射合同缺失**：不能假装已有 UNKNOWN 回退规则并发奖。

资源类型已提供“统一学习凭证＋分类用途标签”和分类型材料两组候选，正式资源 ID、数量及价值均待 P09/P05/P22 等岗位接收。

## 三、P07 的实际成果已接收核验，并给出边界回执

本次补齐并读取了正文精确链接中的 **P07 完整成果 ZIP**，其 **1,214,430 字节**和 SHA-256 与交接声明一致。该新成果 ZIP 不在本次上传的 36 个附件或给定 GitHub 固定提交文件树中，因此已分别记录“固定提交正文”和“精确链接取得的完整包”，没有混写来源。

P08 已形成 ，其中明确：

- 学习奖励、关卡首通、重复掉落及补偿保持不同业务来源。
- Anki Undo 不删除关卡首通键，不直接撤销战斗结果。
- 学习资源已用于养成或通关时，处理关联学习权益差额，不自动降级或抹掉章节。
- P07 的免费入口仍是隔离测试夹具；正式无学习日政策仍待 DEC-003。
- 本次接收级别为**候选设计参考接收**，尚未解除 P07 的正式 PolicyRecord 门禁。

全部来源、版本、实际路径及哈希见 。另外，P01 松散决策 TSV 只有表头，本次采用完整内层包中的 12 行实际决策；两份原字节均保留，没有覆盖修补上游。

## 四、实际验证结果

| 验证层级 | 本次结果 | 证据范围 |
| --- | --- | --- |
| 原始及内嵌 ZIP、逐层清单 | **PASS** | 10 个唯一 ZIP、296 条清单项；包含封装层重复核验 |
| 消费源快照及来源绑定 | **PASS** | 14 份；核对 Git blob 或原 ZIP 成员链 |
| 政策、四键矩阵及引用静态检查 | **PASS** | 31 条规则、84 行矩阵 |
| 撤销／恢复与抵扣数学检查 | **PASS** | 13 个合成示例 |
| 校验器作者测试 | **PASS，16/16** | 验证 Easy 差额、缺 Again、假批准、负数、来源篡改等错误能够被拒绝 |
| 正式前置检查 | **BLOCKED，退出码 3** | 缺少批准、能力、合同、路径及目标环境证据 |
| ZIP 重新解压、逐件哈希与政策静态复核 | **PASS** | 交付字节及静态数据可复核 |
| 独立设计审核／P35 SPEC | **NOT_RUN** | 无独立回执 |
| P11/P17/P21 业务单元、正式契约、并发及故障注入 | **NOT_RUN** | 无真实实现接入证据 |
| P32 独测、P33 人工、目标机及真实 Anki E2E | **NOT_RUN** | 没有运行证据 |

**58 条下游逻辑用例的真实执行数仍为 0；真实 Anki 事件观测数和真实发奖数均为 0。** 校验器作者测试没有被写成学习账本测试通过。

原始命令、stdout、stderr、退出码及哈希在包内 design/anki_rewards/evidence/author_run_001/。打包辅助脚本曾发生一次语法错误，已修复；失败日志、失败脚本字节及修复说明均保留。最终交付复核记录在外层回执中。

解压后可在包根直接复算：

Bash

```
python -B design/anki_rewards/verification/verify_sources.py
python -B design/anki_rewards/verification/verify_policy_artifacts.py
python -B -m unittest discover -s design/anki_rewards/verification -p 'test_*.py' -v
python -B design/anki_rewards/verification/verify_manifest.py
python -B design/anki_rewards/verification/verify_policy_artifacts.py --formal
```

前四项应退出 0；最后一项应明确输出 BLOCKED 并退出 3。

## 五、下游接手与尚未解除的阻塞

待裁决文件已单独提供：。

| 责任方 | 仍需提供的关键输入 |
| --- | --- |
| P01 → 用户 | DEC-001 四键实际收益、DEC-002 已消费权益处置、DEC-003 无学习日政策、DEC-011 能力退化体验的书面批准 |
| P09 | 固定版本词类映射、UNKNOWN 回退、实际字段观察与哈希 |
| P10 | 目标版四键、身份、Undo、redo、旧备份的能力报告及脱敏原始证据 |
| P05 | 正式学习预算、资源价值、封顶、舍入、存储及溢出边界 |
| P13 | actual_path_mapping.json、真实工程固定提交、写入白名单和内部 DTO |
| P12／P17／P21 | 正式传输合同、钱包来源分摊、原子事务与恢复回执 |
| P22／P34 | 正式内容 ID／Schema，以及目标 OS、引擎、Anki 精确版本和环境指纹 |
| P32／P33／P35 | 各自独立测试、人工旅程与分级门禁回执 |

包内 downstream_handoff.json 已按 **P09/P10/P11/P12/P17/P21/P32/P35** 等接收需要绑定文件与 SHA，接收状态统一为 PREPARED_NOT_ACKNOWLEDGED。

P09 可以据此开展映射工作，P10 可以据此准备目标版本能力探针，P11/P12/P17/P21 可以据此准备各自的候选实现与测试。**正式工程路径仍未获得映射授权，跨模块整合仍等待用户指定的 EXT-INTEGRATOR。**

## 保存审批说明

**上面的文件已经生成，可以直接下载；持久保存尚未完成。** 自动审批拒绝了上传完整包及附件的操作，理由是包内包含项目材料，审核将该保存操作判断为尚未取得明确授权的数据外传，且未确认目标保存服务的可信性。

如需继续完成持久保存，请明确批准：**“允许将本次 P08 完整交付包和上述附件保存到我的 ChatGPT 文件区。”**

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
- [balance_parameters.tsv](files/data/balance_parameters.tsv)
- [fixed_seed_simulation.py](files/code/fixed_seed_simulation.py)
- [simulation_results.csv](files/data/simulation_results.csv)
- [reward_abuse_cases.md](files/documents/reward_abuse_cases.md)
- [balance_report.md](files/documents/balance_report.md)
- [P05_S01_Balance_Delivery_V0.1.zip](files/archives/P05_S01_Balance_Delivery_V0.1.zip)
- [relay-materials-1-3559b922b7.zip](files/archives/relay-materials-1-3559b922b7.zip)
- [relay-materials-1-1b174d40f0.zip](files/archives/relay-materials-1-1b174d40f0.zip)
- [four_rating_policy_matrix.tsv](files/data/four_rating_policy_matrix.tsv)
- [4755dc7e-1b3f-44bd-8989-804160769681_P08_delivery_receipt.json](files/data/4755dc7e-1b3f-44bd-8989-804160769681_P08_delivery_receipt.json)
- [4755dc7e-1b3f-44bd-8989-804160769681_P08_README.md](files/documents/4755dc7e-1b3f-44bd-8989-804160769681_P08_README.md)
- [4755dc7e-1b3f-44bd-8989-804160769681_study_policy_draft.md](files/documents/4755dc7e-1b3f-44bd-8989-804160769681_study_policy_draft.md)
- [4755dc7e-1b3f-44bd-8989-804160769681_undo_compensation_options.md](files/documents/4755dc7e-1b3f-44bd-8989-804160769681_undo_compensation_options.md)
- [4755dc7e-1b3f-44bd-8989-804160769681_quarantine_resolution_policy.md](files/documents/4755dc7e-1b3f-44bd-8989-804160769681_quarantine_resolution_policy.md)
- [4755dc7e-1b3f-44bd-8989-804160769681_P08_delivery_manifest.sha256.tsv](files/data/4755dc7e-1b3f-44bd-8989-804160769681_P08_delivery_manifest.sha256.tsv)
- [4755dc7e-1b3f-44bd-8989-804160769681_P08_p07_boundary_response.md](files/documents/4755dc7e-1b3f-44bd-8989-804160769681_P08_p07_boundary_response.md)
- [4755dc7e-1b3f-44bd-8989-804160769681_P08_source_input_receipt.json](files/data/4755dc7e-1b3f-44bd-8989-804160769681_P08_source_input_receipt.json)
- [4755dc7e-1b3f-44bd-8989-804160769681_P08_decisions_pending.tsv](files/data/4755dc7e-1b3f-44bd-8989-804160769681_P08_decisions_pending.tsv)
- [4755dc7e-1b3f-44bd-8989-804160769681_P08_Anki_Reward_Policy_V0.1.zip.txt](files/documents/4755dc7e-1b3f-44bd-8989-804160769681_P08_Anki_Reward_Policy_V0.1.zip.txt)
- [four_rating_policy_matrix.tsv](files/data/75d5637641998a27259de410662c642c2bbb40935fc8e5cdf1a3b8eb010e8c45/four_rating_policy_matrix.tsv)
- [relay-materials-1-3c7e523083.zip](files/archives/relay-materials-1-3c7e523083.zip)

