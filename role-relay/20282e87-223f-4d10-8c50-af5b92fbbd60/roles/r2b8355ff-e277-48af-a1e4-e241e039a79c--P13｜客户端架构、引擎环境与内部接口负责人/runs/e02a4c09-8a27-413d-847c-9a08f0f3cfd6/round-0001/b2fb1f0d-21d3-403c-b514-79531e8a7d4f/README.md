# P13｜客户端架构、引擎环境与内部接口交付

**本岗位的可执行隔离交付已完成：实际工程盘点、路径映射、架构 ADR、内部 DTO／Schema、框架源码、接口 Mock、运行探针、作者测试和原始证据均已形成实体文件。**

**目标游戏 Runtime 仍为 BLOCKED；真实引擎启动、真实 Anki 联动、P21 生产事务、整套战斗竖切及独立验收均为 NOT_RUN。** 本次提供的 Python 框架可以独立运行，但其运行结果不证明游戏引擎或正式业务已经接通。

任务 ID：P13-S00-ARCH-001
上游任务：P01 TASK-00-02
交付版本：P13-CLIENT-ARCH/0.1.0-isolated
内部契约版本：YLTT-INTERNAL/0.1.0-isolated

本轮由 P13 直接完成，未创建子角色，未修改其他岗位的原始业务源码，未执行跨模块合并或 GitHub 写入。

## 一、完整成果下载

### 完整交付包

**P13_ClientArchitecture_V0.1.zip**

实际大小 **2,635,479 字节**，包含 **176 个文件**。其中交付清单记录其余 **175 个文件**，清单自身由包外交付回执绑定，避免循环哈希。

ZIP 的 SHA-256：

纯文本

`3324610eff8d923269cf784300187b1012fa38a4fffe0c158af2bd914c02b553`

### 可单独下载的主要文件

下列对应文件与 ZIP 中的文件保持**相同名称、相同原字节**；已经逐一比较。

| 文件 | 包内相对路径 | 实际大小 |
| --- | --- | --- |
| README.md | README.md | 7,574 字节 |
|  | architecture/engineering_inventory.tsv | 1,426,020 字节 |
| actual_path_mapping.json | architecture/actual_path_mapping.json | 16,790 字节 |
| do_not_touch.txt | architecture/do_not_touch.txt | 962 字节 |
| architecture_adr.md | architecture/architecture_adr.md | 10,739 字节 |
| internal_api_contracts.json | contracts/internal/internal_api_contracts.json | 5,900 字节 |
| internal_dto.schema.json | contracts/internal/internal_dto.schema.json | 93,217 字节 |
| verification_status.json | architecture/verification_status.json | 9,162 字节 |
| integration_handoff.md | architecture/integration_handoff.md | 5,473 字节 |
|  | delivery_manifest.sha256.tsv | 381,966 字节 |
| delivery_receipt.json | 包外回执 | 11,292 字节 |

交付清单逐件记录了相对路径、实际大小、SHA-256、格式、版本、源输入哈希、原作者／owner、接收方、修改白名单和验证范围。外层回执包含 exports 与 archive，其中数值均由实际文件计算。

**ZIP CRC、重新解压后的全量文件核验、独立导出字节核验，以及重新解压后的隔离示例运行均已通过。** 具体命令、退出码和输出保存在交付回执中。

## 二、实际工程核验结论

### 已读取并核验的输入

本轮先解包、读取实际文件，再建立输入绑定。核验结果如下：

| 项目 | 本轮结果 |
| --- | --- |
| 收到的原始上传附件 | 3 个 |
| 递归去重后的 ZIP | 25 个 |
| 解包文件成员 | 1,268 个 |
| 转交包 manifest 记录 | 484 条通过 |
| 上游岗位内部交付清单记录 | 642 条通过 |
| 随本包保留的主要上游原字节文件 | 28 份 |
| 随本包保留的 P12 完整原 ZIP | 1 份 |
| 打包前复核原附件与解包文件是否被修改 | 3 个附件、1,268 个文件全部一致 |

实际读取范围包括 P01 基线、P02 战斗规则、P04 编队约束、P08 奖励语义、V6 冻结正文，以及 P11／P12 的相关接口和源码。P12 原始完整包的 SHA-256 仍为：

纯文本

`2da7038354b81edbd0e8b9d15dca8fcb72adfea323fef265e2198de7b6dd041a`

两个指定仓库的固定树也已读取，并将收到的相关文件字节与树中的 Git blob／大小绑定：

- 岗位资料固定提交：8c370d731c323f86ff19642f4cc73f818498f641
- P12 归档固定提交：c371925947ce6bbd97c1f5b6b4d0f0bc8cd8382c

盘点表共 **2,272 行**，明确区分“已取得并计算 SHA-256 的实际文件”“远端树元数据”和“当前工具发现记录”。远端树条目没有被冒充为已读取的全部源码内容。来源绑定与核验结果均随包保留，阅读入口见 README.md。

### 未取得可启动的目标游戏工程

在本次附件及指定固定树的核验范围内，**未取得可识别的目标游戏引擎工程**。当前执行主机的 PATH 未发现 Godot、Unity、.NET 或 Anki；也没有取得用户目标电脑的环境证据。

本轮实际执行环境为 Linux x86_64、Python 3.12.14、Node v24.22.1。环境发现命令和版本命令已经运行，原始输出与退出码已保存。

据此作出的结论是：

- **环境发现检查已执行，正式前置门禁返回 BLOCKED / exit 3。**
- **没有启动真实游戏引擎进程，启动结果为 NOT_RUN。**
- 引擎选择保持 UNDECIDED。
- 上述结论只覆盖本次收到的输入和执行主机，不推断用户其他位置没有游戏工程。

引擎比较、实际环境记录、待补环境字段及后续探针入口见 architecture_adr.md 和完整包中的 architecture/engine_runtime_comparison.md。

## 三、本次实际实现的架构与框架

### 1. 实际路径映射和修改边界

已核验并冻结本交付包内的 P13 隔离路径：

纯文本

`architecture/**
contracts/internal/**
runtime/framework/**`

actual_path_mapping.json 同时保存作者环境中的实际绝对路径和可移植的包内相对路径。

**正式工程路径仍为 null，production_write_authorized 为 false。** 其他岗位的规划路径均标为 PLANNED_NOT_ACTUAL / BLOCKED_NOT_MAPPED，没有据此创建或覆盖真实工程目录。

上游附件、原始解包目录和保留的上游文件均列入只读保护范围。接收方应在独立解压目录使用本包；正式工程映射需要取得真实源码及授权后另行出具。具体约束见 actual_path_mapping.json 和 do_not_touch.txt。

### 2. 唯一写入者与接口 owner

本轮把业务权威、物理提交和显示适配明确分开：

| 状态或能力 | 唯一责任边界 |
| --- | --- |
| BattleState、战斗费用、HP／护盾、胜负和战斗 revision | **P14** 权威提交 |
| 卡组变化与出牌费用候选 | **P15** 提交候选，由 P14 校验并提交 |
| 敌方意图、行动与阶段候选 | **P16** 生成候选，不直接修改 BattleState |
| 钱包与养成业务变化 | **P17** 唯一钱包业务路径 |
| 学习事实的资格、幂等及撤销语义 | **P11** 负责其账本领域 |
| 关卡进度与关卡结果消费 | **P18** 负责进度领域 |
| 跨域原子落盘、提交凭证、恢复连续性 | **P21** 负责物理事务 |
| 最终 UI 快照绑定及显示适配入口 | **P19** |
| 临时动画表现 | **P29** 通过 P19 适配入口执行 |

关联 IC 的 owner 也按上游记录保留：**IC-02、IC-08 为 P13；IC-05 为 P14；IC-19 为 P21；IC-25 为 P32。** P13 冻结自己的内部数据形状，没有替其他 owner 批准其正式业务合同。

这些边界已经进入契约注册表、端口定义和装配检查。实际框架源码依赖检查覆盖 9 个核心模块，未发现循环依赖或禁止的业务实现导入。详见 internal_api_contracts.json。

### 3. 内部 DTO、Schema 与兼容规则

已经交付：

- **21 类公开 DTO**。
- **19 类战斗事件形状**。
- **21 个可执行校验的 JSON 样例**。
- **25 个规范 JSON／SHA-256 对照向量**。
- 明确版本、字段封闭规则和兼容矩阵。

DTO 覆盖战斗命令、状态、快照、事件批次、结果、卡组候选、敌方意图、编队、钱包、学习状态投影、事务提案、提交证明、进度、存档状态和资源引用。

解析与验证源码已经实现版本检查、未知字段拒绝、重复 JSON 键拒绝、安全整数约束、不可变消息及跨字段语义校验。样例中的 fixture:* 是明确标注的合成 ID，正式内容 ID 仍由 P22 提供。

当前版本是**供独立开发使用的隔离冻结版本**。涉及 IC-05、IC-19 及其他 owner 的行为变更仍需对应版本化接收回执。完整结构见 internal_dto.schema.json。

### 4. 可以独立运行的框架源码

runtime/framework/yltt_framework/ 已包含以下实际实现：

| 组件 | 已实现能力 |
| --- | --- |
| 严格解析与规范编码 | 输入边界检查、稳定指纹、不可变消息副本 |
| 端口注册与装配检查 | 拒绝重复 provider、错误 owner 和未绑定的正式端口 |
| 有限容量线程邮箱 | 入队、背压、所属线程检查、消费预算与关闭语义 |
| 战斗事件顺序守卫 | 批次顺序、重复、缺口和快照恢复判断 |
| 通用脚本化 Mock | 对明确配置的输入返回固定响应；未知输入显式报错 |
| 隔离示例 | 展示排队、端口返回、事件接收和重复识别 |

线程邮箱的状态明确区分：

纯文本

`QUEUED_NOT_COMMITTED
PORT_RETURNED_UNVERIFIED
PORT_EXCEPTION_OUTCOME_UNKNOWN`

因此，排队成功或端口返回不会被当作业务已提交，也不会生成奖励 ACK。

P19／P29 的契约定义了显示租约、最终快照绑定、过期回调忽略及取消表现后的状态恢复要求。本轮只交付接口与测试替身，真实 UI 和动画仍由原岗位实现。

## 四、对 P12 交接的具体处理

本轮原样读取并复跑了 P12 的解析及 ACK／账本协作测试，**没有修改 P12 或其保留的 P11 源码**。

发现的主要接入问题是：P12 当前 bridge 读取了 P11 的部分私有账本结构。P13 已提供 StudyStatusQuery、StudyStatusView、CommitProofView 等内部投影提案，并将其登记为版本化 RFC，由原 owner 修改适配层。

这次交付保留了以下边界：

- P12 的 YLTT-ANKI-TRANSPORT/0.1.0-isolated 线协议保持原样。
- 内部学习状态投影不得让 UI 根据 ACK 自行加钱。
- 提交结果不确定时，仍需基于原事务身份查询。
- P21 的生产提交证明与恢复连续性不能由 Mock 凭证替代。
- 真实游戏宿主线程、端点发现和目标 OS 权限策略仍未验证。

包内共准备 **7 条 RFC／ChangeRequest**。其中还记录了 V6 中 P29 两处规划路径不一致的问题，保留来源 SHA 和对应位置，交原 owner／P01处理，没有覆盖式合并。

具体文件为 contracts/internal/interface_rfcs.json，接收说明见 integration_handoff.md。

## 五、实际验证结果

以下仅标记本轮确实执行过的验证；完整命令、退出码、原始日志及源码快照绑定见 verification_status.json。

| 验证层级 | 结果 | 证明范围 |
| --- | --- | --- |
| P13 作者单元／接口边界测试 | **PASS，54/54** | 解析、契约、端口、线程邮箱、事件顺序与 Mock 边界 |
| JSON Schema 算法对照 | **PASS，4,540 个实例** | 与 jsonschema 4.25.1 的结构校验结果一致 |
| Python／JavaScript 规范编码与 SHA 对照 | **PASS，25/25** | 固定向量的规范字节与哈希一致 |
| 作者所有权及源码依赖检查 | **PASS** | 5 个关联 IC、9 个核心模块、28 份保留上游文件 |
| 原样 P12 解析与 ACK／账本协作复跑 | **PASS，46/46** | 原 P12 隔离包中的对应测试 |
| 原始输入未修改检查 | **PASS** | 3 个附件、1,268 个解包文件字节一致 |
| ZIP、清单、导出和重解压核验 | **PASS** | 176 个包内文件及全部独立导出对应关系 |
| 重解压后的隔离示例 | **PASS，exit 0** | 合成输入与固定响应的框架接线 |
| 当前环境发现／正式前置检查 | **BLOCKED，exit 3** | 目标工程、设备及正式接收证据缺失 |
| 真实引擎启动、真实 UI／动画、Anki、P21 生产事务、E2E | **NOT_RUN** | 未执行 |
| P32 独测、P33 人工、P35 独审 | **NOT_RUN** | 未代签独立结论 |

Schema 对照另有 **432 个输入因线格式限制被排除**，未混入 4,540 个结构比较实例。

P12 原交付中的 73 项测试和 3 项双进程恢复结果作为**上游历史证据**随原 ZIP 保留；本轮重新执行的是上述 **46 项**，没有把历史结果计作新的 P13 实测。

## 六、下一位直接复现

解压完整 ZIP，进入 P13_ClientArchitecture_V0.1 根目录，使用 Python 3.12：

Bash

```
python -B architecture/tools/verify_delivery.py

python -B -m unittest discover \
  -s runtime/framework/tests \
  -p 'test_*.py' -v

python -B -m runtime.framework.yltt_framework.demo

python -B architecture/tools/check_architecture.py

python -B architecture/tools/preflight.py
```

前四条成功时返回 0。最后一条当前预期返回 **3 / BLOCKED**，这是正式前置条件尚未满足的实际状态。

普通框架与测试只依赖 Python 标准库。可选的 Schema 对照依赖已单独固定在 architecture/requirements-dev.txt，跨语言向量工具位于 architecture/tools/canonical_oracle.js。

环境探针与待执行的真实引擎探针源码位于：

纯文本

`runtime/framework/probes/probe_environment.py
runtime/framework/probes/fingerprint_tree.py
runtime/framework/probes/run_engine_probe.py`

真实引擎探针要求先核验源码树和可执行文件，再对新副本执行导入检查；本轮未执行该引擎探针。即使将来导入进程返回 0，也仍需单独验证主场景、渲染、目标平台构建和游戏运行。

## 七、当前交接状态与解除阻塞所需输入

已向 **17 个接收岗位准备 65 条带实际文件哈希的交接记录**，全部标记为 PREPARED_NOT_ACKNOWLEDGED。这表示工件已准备好供接收，不表示其他岗位已经签收或验收通过。

当前最直接的缺项是：

| 责任方 | 需要交付的具体输入 |
| --- | --- |
| **P01** | 真实游戏源码的固定 commit 或 ZIP／SHA-256、工程根、入口配置、现有 owner 和允许探针的路径授权 |
| **P34** | 目标 OS 完整版本、CPU 架构、硬件及驱动信息、引擎完整版本／可执行路径／哈希、目标 Anki 完整版本 |
| **P22** | 正式内容 ID 注册表、内容 Schema、版本和跨引用校验结果 |
| **P14** | 对相关战斗合同的接收回执，以及唯一 BattleState 提交、防重和 revision／seq 实现 |
| **P11／P12／P21** | 内部只读投影、适配版本、生产事务证明与恢复连续性合同；分别由原 owner 修订 |
| **P32／P35** | 针对固定交付哈希的独立复测、原始日志及分层验收回执 |

后续 S04／S05 的真实事件、奖励政策和生产事务依赖，以及 S08 的整合授权，已按阶段分别登记，没有把它们误当成本次隔离框架交付的前置条件。

**下一位可以直接取得本包，核验字节并运行独立测试；正式工程接入需在真实源码和目标环境到位后更新映射、执行引擎探针，并由对应 owner 接收合同。跨模块整合继续等待用户指定的 EXT-INTEGRATOR。**

---

## 本次归档的原始文件

- [v6_freeze.txt](files/documents/v6_freeze.txt)
- [study_policy_draft.md](files/documents/study_policy_draft.md)
- [types.py](files/code/types.py)
- [policy_record.proposal.json](files/data/policy_record.proposal.json)
- [P12_AnkiTransport_V0.1.zip](files/archives/P12_AnkiTransport_V0.1.zip)
- [INTEGRATION.md](files/documents/INTEGRATION.md)
- [ipc_schema.json](files/data/ipc_schema.json)
- [protocol_spec.md](files/documents/protocol_spec.md)
- [protocol_version_matrix.tsv](files/data/protocol_version_matrix.tsv)
- [transport_comparison.md](files/documents/transport_comparison.md)
- [path_mapping_request.json](files/data/path_mapping_request.json)
- [bridge.py](files/code/bridge.py)
- [delivery_receipt.json](files/data/delivery_receipt.json)
- [P13_ClientArchitecture_V0.1.zip](files/archives/P13_ClientArchitecture_V0.1.zip)
- [94f54b46-1-acceptance_matrix.tsv](files/data/94f54b46-1-acceptance_matrix.tsv)
- [actual_path_mapping.json](files/data/actual_path_mapping.json)
- [architecture_adr.md](files/documents/architecture_adr.md)
- [author_review.md](files/documents/author_review.md)
- [authorization_basis.json](files/data/authorization_basis.json)
- [blockers.json](files/data/blockers.json)
- [code_layout.md](files/documents/code_layout.md)
- [66d6180a-1-defect_log.json](files/data/66d6180a-1-defect_log.json)
- [dependency_diagram.mmd](files/other/dependency_diagram.mmd)
- [do_not_touch.txt](files/documents/do_not_touch.txt)
- [ee1dd400-1-downstream_handoff.json](files/data/ee1dd400-1-downstream_handoff.json)
- [engine_runtime_comparison.md](files/documents/engine_runtime_comparison.md)
- [a35cdae5-1-engineering_findings.json](files/data/a35cdae5-1-engineering_findings.json)
- [engineering_inventory.tsv](files/data/engineering_inventory.tsv)
- [environment_observed.json](files/data/environment_observed.json)
- [pip_attempt_001.json](files/data/pip_attempt_001.json)
- [schema_oracle_environment.json](files/data/schema_oracle_environment.json)
- [1e93e628-1-final_source_binding.json](files/data/1e93e628-1-final_source_binding.json)
- [archive_links.json](files/data/archive_links.json)
- [archives.json](files/data/archives.json)
- [audit_archives.py](files/code/audit_archives.py)
- [final_immutability_check.json](files/data/final_immutability_check.json)
- [members.json](files/data/members.json)
- [p12_repo_tree.json](files/data/p12_repo_tree.json)
- [relay_manifest_checks.json](files/data/relay_manifest_checks.json)
- [roles_repo_tree.json](files/data/roles_repo_tree.json)
- [2f93a2ad-1-summary.json](files/data/2f93a2ad-1-summary.json)
- [efba321c-1-upstream_manifest_checks.json](files/data/efba321c-1-upstream_manifest_checks.json)
- [decisions_pending.tsv](files/data/decisions_pending.tsv)
- [task_register.tsv](files/data/task_register.tsv)
- [prd_scope_v0.md](files/documents/prd_scope_v0.md)
- [requirements_baseline_v6.txt](files/documents/requirements_baseline_v6.txt)
- [requirements_traceability.tsv](files/data/requirements_traceability.tsv)
- [battle_replay_fixtures.json](files/data/battle_replay_fixtures.json)
- [effect_priority.tsv](files/data/effect_priority.tsv)
- [interface_rfc_and_blockers.md](files/documents/interface_rfc_and_blockers.md)
- [battle_state_machine.md](files/documents/battle_state_machine.md)
- [turn_sequence.tsv](files/data/turn_sequence.tsv)
- [party_constraints.md](files/documents/party_constraints.md)
- [formal_prerequisites.json](files/data/formal_prerequisites.json)
- [integration_handoff.md](files/documents/integration_handoff.md)
- [module_graph.json](files/data/module_graph.json)
- [bb8722c9-1-references.json](files/data/bb8722c9-1-references.json)
- [5f455d94-1-requirements-dev.txt](files/documents/5f455d94-1-requirements-dev.txt)
- [source_input_receipt.json](files/data/source_input_receipt.json)
- [target_environment_requirements.json](files/data/target_environment_requirements.json)
- [abdde9dd-1-task_receipt.json](files/data/abdde9dd-1-task_receipt.json)
- [canonical_oracle.js](files/code/canonical_oracle.js)
- [check_architecture.py](files/code/check_architecture.py)
- [cfe0e6b2-1-preflight.py](files/code/cfe0e6b2-1-preflight.py)
- [record_run.py](files/code/record_run.py)
- [80cd2763-1-schema_oracle.py](files/code/80cd2763-1-schema_oracle.py)
- [bbc99e55-1-verify_delivery.py](files/code/bbc99e55-1-verify_delivery.py)
- [d0f99392-1-verification_status.json](files/data/d0f99392-1-verification_status.json)
- [api_version_matrix.tsv](files/data/api_version_matrix.tsv)
- [canonical_vectors.json](files/data/canonical_vectors.json)
- [contract_semantics.md](files/documents/contract_semantics.md)
- [AssetRef.json](files/data/AssetRef.json)
- [AtomicCommitProposal.json](files/data/AtomicCommitProposal.json)
- [BattleCommand.json](files/data/BattleCommand.json)
- [BattleCommitBatch.json](files/data/BattleCommitBatch.json)
- [BattleEvent.json](files/data/BattleEvent.json)
- [BattleReply.json](files/data/BattleReply.json)
- [BattleResult.json](files/data/BattleResult.json)
- [BattleSnapshot.json](files/data/BattleSnapshot.json)
- [BattleState.json](files/data/BattleState.json)
- [CommitLookupView.json](files/data/CommitLookupView.json)
- [CommitProofView.json](files/data/CommitProofView.json)
- [DeckPatchCandidate.json](files/data/DeckPatchCandidate.json)
- [EnemyIntent.json](files/data/EnemyIntent.json)
- [PartySnapshot.json](files/data/PartySnapshot.json)
- [PhaseProposal.json](files/data/PhaseProposal.json)
- [SaveStatusView.json](files/data/SaveStatusView.json)
- [StageProgressView.json](files/data/StageProgressView.json)
- [StudyStatusQuery.json](files/data/StudyStatusQuery.json)
- [StudyStatusView.json](files/data/StudyStatusView.json)
- [WalletDeltaCandidate.json](files/data/WalletDeltaCandidate.json)
- [WalletSnapshot.json](files/data/WalletSnapshot.json)
- [fixture_notice.json](files/data/fixture_notice.json)
- [interface_rfcs.json](files/data/interface_rfcs.json)
- [internal_api_contracts.json](files/data/internal_api_contracts.json)
- [internal_dto.schema.json](files/data/internal_dto.schema.json)
- [presentation_adapter_spec.md](files/documents/presentation_adapter_spec.md)
- [3930eab2-1-delivery_manifest.sha256.tsv](files/data/3930eab2-1-delivery_manifest.sha256.tsv)
- [fingerprint_tree.py](files/code/fingerprint_tree.py)
- [probe_environment.py](files/code/probe_environment.py)
- [run_engine_probe.py](files/code/run_engine_probe.py)
- [test_contracts.py](files/code/test_contracts.py)
- [test_framework.py](files/code/test_framework.py)
- [__init__.py](files/code/__init__.py)
- [codec.py](files/code/codec.py)
- [contracts.py](files/code/contracts.py)
- [demo.py](files/code/demo.py)
- [host.py](files/code/host.py)
- [path_guard.py](files/code/path_guard.py)
- [sequence.py](files/code/sequence.py)
- [testing.py](files/code/testing.py)
- [relay-materials-1-0e6d465d5f.zip](files/archives/relay-materials-1-0e6d465d5f.zip)
- [relay-materials-2-90d965dbc7.zip](files/archives/relay-materials-2-90d965dbc7.zip)
- [relay-materials-3-3b4d4286cc.zip](files/archives/relay-materials-3-3b4d4286cc.zip)

