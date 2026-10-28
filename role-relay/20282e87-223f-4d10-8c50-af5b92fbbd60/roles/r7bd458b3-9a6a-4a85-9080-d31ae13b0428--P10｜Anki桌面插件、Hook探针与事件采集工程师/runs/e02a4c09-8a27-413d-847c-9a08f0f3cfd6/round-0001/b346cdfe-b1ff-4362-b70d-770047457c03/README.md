# P10｜Anki Hook 探针与事件采集交付

**本轮已交付探针报告、可执行复核程序和完整证据包。真实 Anki 目标版实测仍为 BLOCKED；S05 插件、持久 outbox 和安装包尚未实现，事件能力保持 QUARANTINED。**

任务 ID：P10-S04-PROBE-001
交付版本：P10-PROBE-REPORT/0.1.0
关联需求：REQ-011、REQ-025；边界关联：REQ-012、REQ-026
关联接口：IC-14、IC-15

本轮**真实复习样本为 0、真实 Undo 样本为 0、实际发奖为 0**。依据你给出的本岗第十条——世代或 Undo 证据缺失时只交探针报告及 QUARANTINED 标志——本次交付限定在报告与可执行复核附录，没有生成会被误认为正式成果的空壳插件或安装包。

## 一、实际交付文件

**完整包包含 57 个实体文件，已完成 ZIP CRC 检查、重新解压后的逐件哈希验证，以及作者测试输入的一致性检查。**

| 文件 | 实际大小 | 内容及适用范围 |
| --- | --- | --- |
|  | 271,956 字节 | 完整报告、源码复核工具、测试、消费源快照、原始执行记录和交接文件 |
|  | 15,187 字节 | Hook 静态观察、身份与崩溃缺口、最小采集边界、验证分级 |
|  | 9,544 字节 | **环境前置检查与固定源码 AST 提取工具**；不注册真实 Hook |
|  | 6,425 字节 | 实际环境与输入检查输出；明确标注**不是四评分／Undo 原始样例** |
|  | 834 字节 | 来源世代、事件身份、Undo 关联均 UNVERIFIED；禁止发奖 |
|  | 725 字节 | **不可安装的交付描述**；不是 Anki 安装清单 |
|  | 54,076 字节 | 56 个其他包内文件的路径、大小、SHA-256、版本、来源、接收人及修改白名单 |
|  | 4,012 字节 | ZIP／清单哈希、最终验证结果与保存阻塞回执 |

完整包 SHA-256：

纯文本

`214d2600c67a9b5909542ad5f7737f29c6fe950e14addd8ab7b29f016b0990c2`

外层回执 SHA-256：

纯文本

`2f364b773c8b6986781ad121dd8f24e46263490ee8c0d1fe2e286532c36d8571`

包内还包含配置／停用／卸载说明、版本化 RFC、14 项真实场景的未执行记录、18 项报告检查器单元测试，以及下游交接文件。完整路径与逐件哈希可直接在清单中核对。

## 二、已经实际核验的上游输入

两份上传附件及内层 ZIP 已实际读取、解包和校验，没有仅根据文件名或清单推断内容。

| 核验项目 | 本次结果 |
| --- | --- |
| 原始附件记录 | 103＋4，共 107 条 |
| 去重后的 ZIP | 15 个，成员 CRC 全部通过 |
| 归档文件成员 | 612 个 |
| relay 清单大小与 SHA-256 | 260 条通过，包含嵌套封装中的重复交接 |
| P08／P09 内部交付清单 | 146 条通过 |
| P09 完整包 | 与交接声明的 d2418d56…ff702a 一致 |
| P09 固定提交绑定 | 本地完整包的 Git blob 与 6b826ac5…b5fc6a0 对应 |
| V6 固定提交绑定 | 本地冻结正文的 Git blob 与 8c370d73…98f641 对应 |

这些数字表示文件完整性检查次数，不能解释为功能测试数量。完整记录位于包内 evidence/intake/。

已读到的 P08 内容是有效复习与奖励语义 **proposal**；P09 内容是字段协议建议和“真实观察数为 0”的报告。**未找到获批的 P12 通信 Schema、P13 实际路径映射、目标 Anki 环境或字段采集授权。**这个缺失结论限定于本次附件及核验过的两个固定项目树，不推断你其他仓库或电脑上的情况。

## 三、本轮得到的具体技术结论

为给后续实现留下可复核依据，我读取了 Anki 官方固定提交：

纯文本

`ankitects/anki@d87cb22bf337c52257376f3abcec09c03a255ed4`

该源码声明的版本为 26.09.3。**它只是本次静态参考，不是你已经指定或本轮实际运行的目标版本。**

### 1. 完成回调不能直接替代事件身份

这一提交声明的完成通知是：

Python

`reviewer_did_answer_card(reviewer, card, ease)`

参数没有直接声明原生复习唯一键或 Undo 目标。因此，不能把 card_id、评分值或回调时间拼起来，就宣布已经解决事件唯一性。[官方 Hook 声明](https://github.com/ankitects/anki/blob/d87cb22bf337c52257376f3abcec09c03a255ed4/qt/tools/genhooks_gui.py)

报告明确保留了两个不同场景：

- 正常调度形成的同卡下一次真实复习。
- Undo 后对同卡重新评分。

同卡再次出现本身不能证明它属于哪一种，也不能据此决定是否产生新权益。

### 2. Undo 有源码观察入口，关联能力仍未验证

这一提交声明了：

Python

`state_did_undo(changes: OpChangesAfterUndo)`

官方 Undo 成功路径会触发该通知。但在检查的 Hook 生成器中，没有 state_did_redo 或 state_did_revert 声明；对应 redo 成功路径也不能被当作已经验证的专用 redo 通知。[官方 Undo／redo 路径](https://github.com/ankitects/anki/blob/d87cb22bf337c52257376f3abcec09c03a255ed4/qt/aqt/operations/collection.py)

**这些源码事实尚不能证明撤销目标、连续 Undo、重做、重启和备份恢复之间的身份关联可靠。**本轮没有据此冻结身份算法。

### 3. 持久 outbox 不能自动补回“尚未入队”的事件

报告单独记录了这个实现风险：

> Anki 完成提交之后，如果在插件回调或插件持久入队之前异常退出，单靠 outbox 重试无法恢复一条从未进入队列的记录。

后续必须在目标版证明可用的官方只读能力能否识别、恢复这个缺口，或者明确降级并隔离受影响范围。不能为了实现所谓原子入队而修改 Anki SQLite 或调度器。

## 四、实际执行结果与未执行范围

| 验证层级 | 结果 | 能证明什么 |
| --- | --- | --- |
| 附件、内层 ZIP、清单完整性 | **PASS** | 收到的文件字节完整 |
| P09 包／V6 正文固定 Git blob 绑定 | **PASS** | 来源与指定提交对应 |
| 固定源码 Hook 参数提取 | **PASS** | 所查源码中的声明 |
| 报告检查器作者单元测试 | **PASS，18/18** | 篡改、路径越界、重复键和错误升级证据等边界 |
| 目标环境前置检查 | **BLOCKED，退出码 3** | 关键输入和目标运行环境缺失 |
| 四评分、Undo、redo、同卡重答、备份还原 | **NOT_RUN** | 没有真实运行样本 |
| 插件 outbox 单元测试、离线重试、停用回归 | **NOT_RUN** | 插件实现尚未开展 |
| 正式契约、目标机、真实 E2E | **NOT_RUN** | 未接入正式实现 |
| P32／P33／P34／P35／P38 独立验证 | **NOT_RUN** | 没有代签独立结果 |

作者原始命令、stdout、stderr、退出码和输入哈希位于：

纯文本

`evidence/author_run_002/`

解压后，在包根运行：

Bash

`python -B anki_hook_probe.py preflight
python -B anki_hook_probe.py scan-reference
python -B -m unittest discover -s verification -p 'test_report_guards.py' -v
python -B verification/verify_delivery.py`

第一条应返回 **BLOCKED／退出码 3**。后三条成功只证明各自的源码提取、报告工具测试和交付字节完整性，不能改称插件或真机通过。

## 五、下一位可以接手什么，仍缺什么

已为下游准备 **54 条文件与 SHA-256 交接记录**，状态统一为 PREPARED_NOT_ACKNOWLEDGED。

- **P11**：接收零真实样本、身份／Undo 未验证及禁止发奖结论。这里的 QUARANTINED 标志不是账本已经持久接收事件的 ACK。
- **P12**：接收固定源码观察、身份关联缺口和 IC-14 语义提案。
- **P09**：接收“真实字段仍不可观察”的回执，不把合成字段名转为真实字段假设。
- **P32／P34／P35**：接收检查源码、实际作者证据、目标机缺项和分级验证状态。
- **P36**：接收不可安装、不可发布的交付描述。

继续推进需要以下具体工件：

| 缺失输入 | 责任方 | 影响 |
| --- | --- | --- |
| Anki 完整版本／build、目标 OS／架构、环境指纹和可操作测试环境 | P34；实际设备信息由你提供 | 真实 S04 探针 |
| 真实工程固定提交、actual_path_mapping.json、写入白名单和禁改清单 | P13 | 正式目录写入 |
| 获准测试档案、note type／template 范围、具体字段与用途授权 | P38，经 P01 确认 | 真实字段采集 |
| P12 正式 Schema、兼容规则、身份／ACK 合同及接收回执 | P12 | S05 插件与正式传输 |
| 已批准奖励政策及相关接收记录 | P08／P01 | 后续真实发奖 |

addon_source/**、plugin_outbox_tests.py 和 .ankiaddon 安装包的缺口已逐项记录，没有用其他文件冒充完成。

## 六、保存状态与所需授权

**以上文件已经生成，可通过本次会话链接下载；未能完成持久保存。**

自动审批拒绝了将以下五份文件保存到 ChatGPT 文件区的操作：完整 ZIP、主报告、逐件清单、外层回执和 QUARANTINED 标志。审核理由是：这些文件包含项目资料，尚未明确授权这些具体内容向该目的地传输，且目的地的归属与可信性未被确认。拒绝后没有改用其他途径上传。

如果要完成这一步保存，需要你明确授权：

> 允许将本次 P10 的 P10_S04_Probe_Report_V0.1.zip、hook_probe_report.md、delivery_manifest.sha256.tsv、P10_delivery_receipt.json 和 QUARANTINED.json 保存到我自己的 ChatGPT 文件区。

推进真实 S04 时，请先提供**目标 Anki“帮助／关于”中的完整版本信息，以及目标操作系统版本**；其余路径、字段授权和协议工件按上表补齐。

---

## 本次归档的原始文件

- [README.md](files/documents/README.md)
- [P09_delivery_receipt.json](files/data/P09_delivery_receipt.json)
- [pos_mapping_rules.json](files/data/pos_mapping_rules.json)
- [unknown_fallback_cases.tsv](files/data/unknown_fallback_cases.tsv)
- [anki_field_observations.md](files/documents/anki_field_observations.md)
- [P09_Linguistic_Mapping_V0.1.zip](files/archives/P09_Linguistic_Mapping_V0.1.zip)
- [category_dictionary.json](files/data/category_dictionary.json)
- [classification_cases.jsonl](files/other/classification_cases.jsonl)
- [example_entries.synthetic.jsonl](files/other/example_entries.synthetic.jsonl)
- [field_profile.synthetic.json](files/data/field_profile.synthetic.json)
- [rollback_rules.synthetic.json](files/data/rollback_rules.synthetic.json)
- [mapping_release_registry.json](files/data/mapping_release_registry.json)
- [override_log.synthetic.jsonl](files/other/override_log.synthetic.jsonl)
- [resource_affinity_candidates.tsv](files/data/resource_affinity_candidates.tsv)
- [mapping_input.schema.json](files/data/mapping_input.schema.json)
- [mapping_output.schema.json](files/data/mapping_output.schema.json)
- [override_event.schema.json](files/data/override_event.schema.json)
- [delivery_manifest.sha256.tsv](files/data/delivery_manifest.sha256.tsv)
- [blockers.tsv](files/data/blockers.tsv)
- [classification_spec.md](files/documents/classification_spec.md)
- [downstream_handoff.json](files/data/downstream_handoff.json)
- [input_bindings.json](files/data/input_bindings.json)
- [run_result.json](files/data/run_result.json)
- [stderr.log](files/other/stderr.log)
- [stdout.log](files/other/stdout.log)
- [git_blob_bindings.json](files/data/git_blob_bindings.json)
- [intake_report.json](files/data/intake_report.json)
- [p08_github_tree.json](files/data/p08_github_tree.json)
- [v6_github_tree.json](files/data/v6_github_tree.json)
- [received_relay_materials.zip](files/archives/received_relay_materials.zip)
- [p01_requirements_baseline_v6.txt](files/documents/p01_requirements_baseline_v6.txt)
- [p01_requirements_traceability.tsv](files/data/p01_requirements_traceability.tsv)
- [p08_delivery_receipt.json](files/data/p08_delivery_receipt.json)
- [p08_interface_rfc.md](files/documents/p08_interface_rfc.md)
- [p08_resource_mapping_candidates.tsv](files/data/p08_resource_mapping_candidates.tsv)
- [p08_source_input_receipt.json](files/data/p08_source_input_receipt.json)
- [p08_study_policy_draft.md](files/documents/p08_study_policy_draft.md)
- [v6_freeze.txt](files/documents/v6_freeze.txt)
- [setup_probe.json](files/data/setup_probe.json)
- [field_protocol_proposal.md](files/documents/field_protocol_proposal.md)
- [formal_prerequisites.json](files/data/formal_prerequisites.json)
- [known_issues_and_history.md](files/documents/known_issues_and_history.md)
- [override_and_rollback.md](files/documents/override_and_rollback.md)
- [path_mapping_request.json](files/data/path_mapping_request.json)
- [demo.py](files/code/demo.py)
- [pos_mapper.py](files/code/pos_mapper.py)
- [requirements_traceability.tsv](files/data/requirements_traceability.tsv)
- [rfc_ic15_ic16.md](files/documents/rfc_ic15_ic16.md)
- [source_input_receipt.json](files/data/source_input_receipt.json)
- [source_notes.md](files/documents/source_notes.md)
- [reproduction_notes.md](files/documents/reproduction_notes.md)
- [run_checks.py](files/code/run_checks.py)
- [test_override_replay.py](files/code/test_override_replay.py)
- [test_pos_mapper.py](files/code/test_pos_mapper.py)
- [verify_delivery.py](files/code/verify_delivery.py)
- [verify_manifest.py](files/code/verify_manifest.py)
- [verify_source_inputs.py](files/code/verify_source_inputs.py)
- [verification_status.json](files/data/verification_status.json)
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
- [P08_delivery_receipt.json](files/data/e9673a528e697a51cdc55d683621cc08b53b9626834547e2ae5a966463459c24/P08_delivery_receipt.json)
- [P08_README.md](files/documents/P08_README.md)
- [study_policy_draft.md](files/documents/study_policy_draft.md)
- [undo_compensation_options.md](files/documents/undo_compensation_options.md)
- [quarantine_resolution_policy.md](files/documents/quarantine_resolution_policy.md)
- [P08_delivery_manifest.sha256.tsv](files/data/P08_delivery_manifest.sha256.tsv)
- [P08_p07_boundary_response.md](files/documents/P08_p07_boundary_response.md)
- [P08_source_input_receipt.json](files/data/06878cf96ef332619de530c1231d87c7b045016d7a21f2fca2d29cdffff643f1/P08_source_input_receipt.json)
- [P08_decisions_pending.tsv](files/data/P08_decisions_pending.tsv)
- [P08_Anki_Reward_Policy_V0.1.zip](files/archives/P08_Anki_Reward_Policy_V0.1.zip)
- [four_rating_policy_matrix.tsv](files/data/four_rating_policy_matrix.tsv)
- [relay-materials-1-3c7e523083.zip](files/archives/relay-materials-1-3c7e523083.zip)
- [relay-materials-1-e9818b1abe.zip](files/archives/relay-materials-1-e9818b1abe.zip)
- [P10_S04_Probe_Report_V0.1.zip](files/archives/P10_S04_Probe_Report_V0.1.zip)
- [QUARANTINED.json](files/data/QUARANTINED.json)
- [d04b2eb2-1-README.md](files/documents/d04b2eb2-1-README.md)
- [addon_manifest.json](files/data/addon_manifest.json)
- [anki_hook_probe.py](files/code/anki_hook_probe.py)
- [configuration_disable_uninstall.md](files/documents/configuration_disable_uninstall.md)
- [deliverable_status.json](files/data/deliverable_status.json)
- [faeeea49-1-delivery_manifest.sha256.tsv](files/data/faeeea49-1-delivery_manifest.sha256.tsv)
- [662cf5d1-1-downstream_handoff.json](files/data/662cf5d1-1-downstream_handoff.json)
- [eeba4d76-1-input_bindings.json](files/data/eeba4d76-1-input_bindings.json)
- [preflight.stderr.log](files/other/preflight.stderr.log)
- [preflight.stdout.log](files/other/preflight.stdout.log)
- [report_guard_unit.stderr.log](files/other/report_guard_unit.stderr.log)
- [report_guard_unit.stdout.log](files/other/report_guard_unit.stdout.log)
- [run_receipt.json](files/data/run_receipt.json)
- [static_reference.stderr.log](files/other/static_reference.stderr.log)
- [static_reference.stdout.log](files/other/static_reference.stdout.log)
- [anki_ref.json](files/data/anki_ref.json)
- [bf412b48-1-git_blob_bindings.json](files/data/bf412b48-1-git_blob_bindings.json)
- [intake.exec_output.log](files/other/intake.exec_output.log)
- [intake_archives_method.py](files/code/intake_archives_method.py)
- [intake_execution_receipt.json](files/data/intake_execution_receipt.json)
- [fbfce6f3-1-intake_report.json](files/data/fbfce6f3-1-intake_report.json)
- [p09_tree.json](files/data/p09_tree.json)
- [upstream_manifest_checks.json](files/data/upstream_manifest_checks.json)
- [v6_tree.json](files/data/v6_tree.json)
- [reproduction_and_revision_notes.md](files/documents/reproduction_and_revision_notes.md)
- [hook_probe_report.md](files/documents/hook_probe_report.md)
- [prerequisites.json](files/data/prerequisites.json)
- [probe_log_redacted.txt](files/documents/probe_log_redacted.txt)
- [reference_inputs.json](files/data/reference_inputs.json)
- [rfc_ic14_ic15.md](files/documents/rfc_ic14_ic15.md)
- [sample_inventory.json](files/data/sample_inventory.json)
- [fe6262c8-1-source_input_receipt.json](files/data/fe6262c8-1-source_input_receipt.json)
- [LICENSE](files/other/LICENSE)
- [collection.proto](files/other/collection.proto)
- [main.py](files/code/main.py)
- [__init__.py](files/code/__init__.py)
- [reviewer.py](files/code/reviewer.py)
- [undo.py](files/code/undo.py)
- [genhooks_gui.py](files/code/genhooks_gui.py)
- [source-version.txt](files/documents/source-version.txt)
- [p08_quarantine_resolution_policy.md](files/documents/p08_quarantine_resolution_policy.md)
- [p09_anki_field_observations.md](files/documents/p09_anki_field_observations.md)
- [p09_field_protocol_proposal.md](files/documents/p09_field_protocol_proposal.md)
- [p09_formal_prerequisites.json](files/data/p09_formal_prerequisites.json)
- [p09_source_input_receipt.json](files/data/p09_source_input_receipt.json)
- [run_author_checks.py](files/code/run_author_checks.py)
- [test_report_guards.py](files/code/test_report_guards.py)
- [ae91ab32-1-verify_delivery.py](files/code/ae91ab32-1-verify_delivery.py)
- [9e5209a7-1-verification_status.json](files/data/9e5209a7-1-verification_status.json)
- [P10_delivery_receipt.json](files/data/P10_delivery_receipt.json)
- [d04b2eb2-2-README.md](files/documents/d04b2eb2-2-README.md)
- [faeeea49-2-delivery_manifest.sha256.tsv](files/data/faeeea49-2-delivery_manifest.sha256.tsv)
- [662cf5d1-2-downstream_handoff.json](files/data/662cf5d1-2-downstream_handoff.json)
- [eeba4d76-2-input_bindings.json](files/data/eeba4d76-2-input_bindings.json)
- [bf412b48-2-git_blob_bindings.json](files/data/bf412b48-2-git_blob_bindings.json)
- [fbfce6f3-2-intake_report.json](files/data/fbfce6f3-2-intake_report.json)
- [fe6262c8-2-source_input_receipt.json](files/data/fe6262c8-2-source_input_receipt.json)
- [ae91ab32-2-verify_delivery.py](files/code/ae91ab32-2-verify_delivery.py)
- [9e5209a7-2-verification_status.json](files/data/9e5209a7-2-verification_status.json)
- [d04b2eb2-3-README.md](files/documents/d04b2eb2-3-README.md)
- [faeeea49-3-delivery_manifest.sha256.tsv](files/data/faeeea49-3-delivery_manifest.sha256.tsv)
- [662cf5d1-3-downstream_handoff.json](files/data/662cf5d1-3-downstream_handoff.json)
- [eeba4d76-3-input_bindings.json](files/data/eeba4d76-3-input_bindings.json)
- [bf412b48-3-git_blob_bindings.json](files/data/bf412b48-3-git_blob_bindings.json)
- [fbfce6f3-3-intake_report.json](files/data/fbfce6f3-3-intake_report.json)
- [fe6262c8-3-source_input_receipt.json](files/data/fe6262c8-3-source_input_receipt.json)
- [ae91ab32-3-verify_delivery.py](files/code/ae91ab32-3-verify_delivery.py)
- [9e5209a7-3-verification_status.json](files/data/9e5209a7-3-verification_status.json)

