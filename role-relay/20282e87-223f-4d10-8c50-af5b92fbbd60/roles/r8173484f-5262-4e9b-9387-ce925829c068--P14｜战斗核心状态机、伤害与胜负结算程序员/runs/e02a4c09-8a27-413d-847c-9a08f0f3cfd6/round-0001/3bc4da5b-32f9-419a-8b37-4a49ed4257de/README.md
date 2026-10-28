# P14｜战斗核心状态机、伤害与胜负结算交付

**已完成可执行的隔离战斗核心、确定性回放、作者单元测试及完整交接文件。** 当前版本为 **P14-BATTLE-CORE/0.1.0-isolated**，对应上游任务 **TASK-01-02：无渲染战斗状态单次提交核心**，沿用 P13 的 **YLTT-INTERNAL/0.1.0-isolated** DTO。

**验证结果：101 项作者测试中，97 项通过、4 项因上游历史信息不足保持 BLOCKED/skip、0 项失败。正式工程接入仍为 BLOCKED；P32/P33/P35 独立验证、真实引擎与 Anki 联调均为 NOT_RUN。** 具体分层结论已写入交付文件。

## 一、成果下载

### 完整交付包与回执

- **P14_BattleCore_V0.1.zip**
实际大小 **3,393,475 字节**，包含 **180 个文件**。
实际大小 **36,739 字节**，记录 ZIP、17 个独立导出文件的实际大小与 SHA-256，以及新解压目录中的复跑命令、退出码和原始输出。

ZIP 的 SHA-256：

纯文本

`a439f32c482117e29586f98350d63a0e2a1ddd7efd4c7578f3cd05a42b4f6068`

**ZIP CRC、180 个解压文件的字节核验、17 个独立导出文件与包内文件的同名同字节比对，均已实际通过。** 包内清单记录其余 179 个文件；清单自身和 ZIP 由包外回执绑定，避免循环哈希。

### 主要文件单独下载

| 文件 | 用途 | 实际大小 |
| --- | --- | --- |
| README.md | 总入口、运行命令、范围与验证结论 | 10,916 字节 |
| IC05_API.md | P15/P16 接口、提交语义、P19/P29 读取方式 | 8,125 字节 |
| battle_result_schema.md | 不可变结果、字段、哈希与消费边界 | 5,464 字节 |
| battle_event_samples.json | 实际结算产生的事件批次 | 96,203 字节 |
| battle_snapshot.json | 示例最终只读快照 | 1,616 字节 |
| battle_state.json | 示例最终状态及已提交命令回执 | 3,483 字节 |
| battle_result.json | 示例实际生成的 WIN 结果 | 576 字节 |
| verification_status.json | 作者测试、合同检查、独立验收分层状态 | 3,278 字节 |
| integration_handoff.md | 下一位接收与正式接入说明 | 5,748 字节 |
|  | 逐件路径、大小、SHA、版本、来源、接收方和修改白名单 | 428,430 字节 |
| source_input_receipt.json | 上游原件、固定版本、父 ZIP 与文件哈希绑定 | 419,283 字节 |

完整源码位于 ZIP 内的 battle_core/**；测试位于 resolution_replay_tests/**；原始执行日志和每轮执行时的源码快照位于 evidence/runs/**。

## 二、本轮实际实现

### 唯一权威提交与防重

P14 是本库中 **BattleState 与 BattleResult 的唯一提交者**。P15 提交牌堆和费用候选，P16 提交敌方意图；牌区、费用、RNG、效果、死亡、终局、回执和事件均先在事务副本中计算，校验完成后一次替换已提交记录。

已实现并实测：

- 同 ID、同完整命令指纹重试，返回 DUPLICATE_NO_OP，不再次扣费、不增加 revision/seq、不调用候选提供方。
- 同 ID、不同指纹，返回 COMMAND_ID_COLLISION。
- 旧 revision、非法目标、已离开手牌的实例、错误候选绑定、无效 RNG 或牌区移动等被拒绝后，权威状态保持不变。
- 24 次并发相同请求只产生一次提交。
- 三个提交前中断点均完全回滚，原请求可以重试。

P14 的动作模型没有费用字段，费用来自 P15 候选；本轮没有另写一套抽牌、洗牌或费用计算规则。接口和异常语义见上面的 API 文件，实际证据见验证状态及包内 author_004 日志。

### 伤害、状态与胜负

已经实现伤害先扣盾再扣血、治疗封顶且不复活、显式配置的护盾上限、单层 DOT、连续命中、立即死亡判定，以及稳定顺序的反应队列。

胜负在合法反应排空后统一判定为 **WIN / LOSS / DRAW**。最后一个敌人的死亡反击仍可能造成同归于尽；同一场战斗只生成一次 BATTLE_FINISHED 和一个不可变 BattleResult。

回合号依据实际 P02 夹具处理：**敌方回合结束时递增，玩家回合入口保持已有回合号。** 首轮作者实现对该点的误读已修复，失败日志和当时源码保留在包内；上游规则和夹具没有被修改。修复记录（附件：defect_log.json）

### 快照、事件与确定性回放

只读消息复用 P13 原始 FrozenMessage：保存规范字节，读取内容时返回副本，显示端修改副本不会影响权威状态。

伪随机状态显式保存 initial_seed / state / draw_count。回放记录初态、规则与内容投影、来源哈希、已提交命令，以及实际收到的 P15/P16 候选，再重新执行结算。

本轮已验证：

- 相同输入重放后，状态、事件批次和结果的规范字节完全相同。
- 三个不同 PYTHONHASHSEED 的独立进程产生相同输出摘要。
- 导出的回放文件可在新解压目录执行，并与交付的状态、快照、结果和全部事件批次逐字节比对。

### BOSS 已完成的边界

已测试致死阈值、存活跨阈提案、死亡反击和 DOT 终局优先级。**致死时只结算一次终局，不再追加敌方行动。**

完整 S07 阶段提交仍然 **BLOCKED**：当前合同缺少阶段提交命令、epoch 和行动槽等信息。有待处理阶段提案时，本库会阻止继续旧阶段的敌方行动。该限制及接口请求已明确交给原 owner，未把阈值预检报告为完整多阶段 BOSS 实现。接口 RFC（附件：interface_rfcs.json）

## 三、实际运行结果与验证范围

### 无渲染战斗示例

示例实际执行了开局、攻击、加盾、治疗、结束回合、敌方攻击、下一回合施加 DOT，以及敌方入口 DOT 致死。

| 观测项 | 实际结果 |
| --- | --- |
| 提交次数／最终 revision | 10 |
| 事件总数／last_event_seq | 52 |
| BATTLE_FINISHED 的 seq | 51 |
| 最终结果 | WIN |
| 最终回合号 | 2 |
| P15 脚本候选调用次数 | 8 |
| P16 脚本意图调用次数 | 1 |

最后一次敌方回合在入口 DOT 后直接终局，没有第二次请求敌方意图。这里的结算由真实 P14 运行库执行；P15/P16 为明确标记的脚本测试输入，角色、卡牌和数值仍属隔离样例。快照与结果文件的实际哈希关系也已核验。

### 分层验证

| 验证层级 | 本轮状态 | 证明范围 |
| --- | --- | --- |
| P14 作者设计复核 | **COMPLETED** | 所有权、事务边界、来源与宣称范围自查 |
| 作者单元／回放测试 | **97 PASS、4 BLOCKED/skip、0 FAIL** | 共发现 101 项；新解压目录复跑结果一致 |
| P02 旧夹具 | **29 个语义投影 PASS、4 个 BLOCKED** | 不等于旧格式逐字节合同通过 |
| P03 效果样例 | **8 个已启用样例 PASS** | BUFF/DEBUFF 两个未批准提议保持禁用 |
| P13 原校验器合同检查 | **作者验证 PASS** | 实际命令、候选、状态、事件、批次与结果 |
| 导出回放原字节比较 | **PASS** | 状态、快照、结果和全部批次 |
| 原始输入完整性 | **PASS** | 原附件、展开成员及保留原件未改 |
| ZIP、导出与重解压核验 | **PASS** | 180 个文件、17 个独立导出 |
| 可选 jsonschema 算法对照 | **BLOCKED；算法对照 NOT_RUN** | 首次启动因缺依赖 FAIL，原日志保留；依赖下载受到网络权限限制 |
| 正式工程前置检查 | **BLOCKED，exit 3** | 路径、真实 provider、内容与目标环境缺项 |
| P32 独测、P33 人工、P35 独审 | **NOT_RUN** | 未代签 |
| 真实引擎、UI/动画、Anki、P21、E2E | **NOT_RUN** | 未执行 |

四个阻塞的旧场景为 **F010、F011、F021、F028**。它们只有旧命令哈希，缺少完整历史请求及新版回执范围，不能据此生成可靠的新指纹或迁移记录。当前 P13 格式下的重复请求、碰撞、旧 revision 等已经通过另外构造的真实提交历史验证。事件字段映射、排除项和比较范围见 p02_projection_contract.md。

## 四、上游核验与修改边界

本轮已解包读取实际转交附件，包括包内原 ZIP，并核验 **586 条转交清单记录、281 条相关上游内部清单记录**。交付包保留 **78 份上游原字节文件**；原始 3 个上传附件及 1,788 个展开成员完成未修改复核。

发现独立导出的 effect_priority.tsv 只有 **11 字节**，而已核验 P02 原 ZIP 内对应完整文件为 **5,253 字节**。本轮保留双方原字节与哈希，使用完整原包文件，没有覆盖异常导出件。

P13 原 actual_path_mapping.json 仍将 P14 的正式规划路径标为未映射、禁止写入。因此，本次成果位于新建隔离交付目录：

纯文本

`battle_core/**
resolution_replay_tests/**`

**正式工程实际路径仍为 null，生产写入白名单为空。** P14 对当前内部 DTO 的接收限于隔离实现，接收范围和保留项见 contract_acceptance.json。

## 五、下一位直接复现

解压完整 ZIP，进入 P14_BattleCore_V0.1，使用 Python 3.12：

Bash

```
python -B tools/verify_delivery.py

python -B -m unittest discover -s resolution_replay_tests -t . -p 'test_*.py' -v

python -B -m battle_core

python -B tools/replay_file.py examples/demo_replay.json

python -B tools/preflight.py
```

前四条成功时退出码为 0。最后一条当前应返回 **3 / BLOCKED**。运行库、上述测试、示例及回放只依赖 Python 标准库。

已准备 **15 个接收方、81 条带实际文件哈希的交接记录**，全部为 PREPARED_NOT_ACKNOWLEDGED。downstream_receipts.json

下一位 **P15** 可以直接按 API 接入纯候选接口；**P16** 接入单意图提供方并处理阶段合同；**P19/P29** 消费已提交批次与快照；**P32/P35** 对本包固定哈希独立复测和审查。真实工程映射、正式内容政策、目标环境及完整 BOSS 阶段的缺项已逐条登记责任方，见 blockers.json。最终跨模块整合继续由用户指定的 **EXT-INTEGRATOR** 执行。

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
- [P13_ClientArchitecture_V0.1.zip](files/archives/P13_ClientArchitecture_V0.1.zip)
- [94f54b46-1-acceptance_matrix.tsv](files/data/94f54b46-1-acceptance_matrix.tsv)
- [actual_path_mapping.json](files/data/actual_path_mapping.json)
- [architecture_adr.md](files/documents/architecture_adr.md)
- [author_review.md](files/documents/author_review.md)
- [authorization_basis.json](files/data/authorization_basis.json)
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
- [module_graph.json](files/data/module_graph.json)
- [bb8722c9-1-references.json](files/data/bb8722c9-1-references.json)
- [5f455d94-1-requirements-dev.txt](files/documents/5f455d94-1-requirements-dev.txt)
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
- [c5568985-1-source_input_receipt.json](files/data/c5568985-1-source_input_receipt.json)
- [downstream_receipts.json](files/data/downstream_receipts.json)
- [P14_BattleCore_V0.1.zip](files/archives/P14_BattleCore_V0.1.zip)
- [__main__.py](files/code/__main__.py)
- [core.py](files/code/core.py)
- [model.py](files/code/model.py)
- [replay.py](files/code/replay.py)
- [resolver.py](files/code/resolver.py)
- [rng.py](files/code/rng.py)
- [wire.py](files/code/wire.py)
- [battle_event_samples.json](files/data/battle_event_samples.json)
- [battle_result.json](files/data/battle_result.json)
- [battle_result_schema.md](files/documents/battle_result_schema.md)
- [battle_snapshot.json](files/data/battle_snapshot.json)
- [battle_state.json](files/data/battle_state.json)
- [952a86d4-1-author_review.md](files/documents/952a86d4-1-author_review.md)
- [contract_check.json](files/data/contract_check.json)
- [defect_log.json](files/data/defect_log.json)
- [demo_summary.json](files/data/demo_summary.json)
- [dependency_install_attempt.json](files/data/dependency_install_attempt.json)
- [environment.json](files/data/environment.json)
- [final_source_binding.json](files/data/final_source_binding.json)
- [input_conflicts.json](files/data/input_conflicts.json)
- [input_immutability_check.json](files/data/input_immutability_check.json)
- [github_p13_tree.json](files/data/github_p13_tree.json)
- [github_roles_tree.json](files/data/github_roles_tree.json)
- [input_inventory.json](files/data/input_inventory.json)
- [p02_projection_results.json](files/data/p02_projection_results.json)
- [upstream_manifest_verification.json](files/data/upstream_manifest_verification.json)
- [c26bf04e-1-demo.py](files/code/c26bf04e-1-demo.py)
- [demo_execution.json](files/data/demo_execution.json)
- [demo_replay.json](files/data/demo_replay.json)
- [fixture_ports.py](files/code/fixture_ports.py)
- [IC05_API.md](files/documents/IC05_API.md)
- [2bb04863-1-blockers.json](files/data/2bb04863-1-blockers.json)
- [contract_acceptance.json](files/data/contract_acceptance.json)
- [p02_projection_contract.md](files/documents/p02_projection_contract.md)
- [6e497529-1-path_mapping_request.json](files/data/6e497529-1-path_mapping_request.json)
- [task_completion.json](files/data/task_completion.json)
- [requirements-dev.txt](files/documents/requirements-dev.txt)
- [helpers.py](files/code/helpers.py)
- [p02_adapter.py](files/code/p02_adapter.py)
- [test_content_replay.py](files/code/test_content_replay.py)
- [test_core.py](files/code/test_core.py)
- [test_p02_vectors.py](files/code/test_p02_vectors.py)
- [check_contracts.py](files/code/check_contracts.py)
- [generate_samples.py](files/code/generate_samples.py)
- [preflight.py](files/code/preflight.py)
- [replay_file.py](files/code/replay_file.py)
- [run_checks.py](files/code/run_checks.py)
- [verify_delivery.py](files/code/verify_delivery.py)
- [role_activation_register.tsv](files/data/role_activation_register.tsv)
- [scope_matrix.tsv](files/data/scope_matrix.tsv)
- [P02_DELIVERY_README.md](files/documents/P02_DELIVERY_README.md)
- [P02_static_validation.log](files/other/P02_static_validation.log)
- [fixture_index.tsv](files/data/fixture_index.tsv)
- [resolution_examples.md](files/documents/resolution_examples.md)
- [terminal_phase_truth_table.tsv](files/data/terminal_phase_truth_table.tsv)
- [validate_spec_fixtures.py](files/code/validate_spec_fixtures.py)
- [battle_state_machine.mmd](files/other/battle_state_machine.mmd)
- [P03_DELIVERY_README.md](files/documents/P03_DELIVERY_README.md)
- [P03_static_validation.log](files/other/P03_static_validation.log)
- [card_catalog.json](files/data/card_catalog.json)
- [card_choice_cases.tsv](files/data/card_choice_cases.tsv)
- [card_dictionary.tsv](files/data/card_dictionary.tsv)
- [card_effect_examples.json](files/data/card_effect_examples.json)
- [character_card_pool.tsv](files/data/character_card_pool.tsv)
- [choice_scenarios.json](files/data/choice_scenarios.json)
- [deck_build_fixtures.json](files/data/deck_build_fixtures.json)
- [validate_card_content.py](files/code/validate_card_content.py)
- [card_effect_event_map.tsv](files/data/card_effect_event_map.tsv)
- [card_keywords.md](files/documents/card_keywords.md)
- [party_deck_rules.md](files/documents/party_deck_rules.md)
- [balance_parameters.tsv](files/data/balance_parameters.tsv)
- [card_adjustment_candidates.tsv](files/data/card_adjustment_candidates.tsv)
- [boss_phase_graph.json](files/data/boss_phase_graph.json)
- [enemy_specs.json](files/data/enemy_specs.json)
- [enemy_truth_cases.tsv](files/data/enemy_truth_cases.tsv)
- [intent_dictionary.tsv](files/data/intent_dictionary.tsv)
- [state_resolution_rules.tsv](files/data/state_resolution_rules.tsv)
- [effect_priority_11byte.tsv](files/data/effect_priority_11byte.tsv)
- [verification_status.json](files/data/verification_status.json)
- [README.md](files/documents/README.md)
- [50be3988-1-interface_rfcs.json](files/data/50be3988-1-interface_rfcs.json)
- [7be2f893-1-integration_handoff.md](files/documents/7be2f893-1-integration_handoff.md)
- [delivery_receipt.json](files/data/delivery_receipt.json)
- [delivery_manifest.sha256.tsv](files/data/delivery_manifest.sha256.tsv)

