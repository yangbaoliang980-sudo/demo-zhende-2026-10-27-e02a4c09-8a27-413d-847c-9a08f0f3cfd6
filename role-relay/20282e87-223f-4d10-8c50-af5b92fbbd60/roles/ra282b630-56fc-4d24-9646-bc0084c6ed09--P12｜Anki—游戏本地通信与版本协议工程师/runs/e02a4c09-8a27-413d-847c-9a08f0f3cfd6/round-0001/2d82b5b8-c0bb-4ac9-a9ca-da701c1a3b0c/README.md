# P12｜Anki—游戏本地通信与版本协议交付

**P12 的可执行隔离实现已完成：协议 Schema、游戏侧限权入口、本机通信适配器、持久 outbox 参考组件、双端 Mock 和重放测试均已交付。最终作者测试 73/73 通过，3/3 项真实双进程退出恢复通过。**

**正式 S05 接入仍为 BLOCKED；真实 Anki 联动、真实游戏引擎接入、P21 生产事务及独立验收均为 NOT_RUN。**

任务 ID：P12-S04-S05-TRANSPORT-001
交付版本：P12-ANKI-TRANSPORT/0.1.0-isolated
关联接口：IC-14、IC-18

本轮由我直接完成，未创建子角色。P11 原始源码保持不变，未覆盖真实工程，未执行跨模块合并或发布。

## 一、完整成果下载

**完整包包含 145 个实体文件。下一位取得 ZIP 后，可以直接阅读源码、运行测试、核验交付字节。**

| 文件 | 实际大小 | 内容 |
| --- | --- | --- |
| P12_AnkiTransport_V0.1.zip | 1,206,963 字节 | 完整源码、协议、样例、测试、上游引用、原始日志、RFC 和交接材料 |
| P12_README.md | 8,541 字节 | 阅读入口、实际能力、验证分层、运行命令和正式阻塞 |
| P12_ipc_schema.json | 21,136 字节 | 双端一致的封闭协议 Schema |
|  | 1,055 字节 | 精确版本接收与拒绝规则 |
|  | 107,656 字节 | 逐件路径、大小、SHA-256、版本、源输入哈希、接收人及修改白名单 |
| P12_delivery_receipt.json | 3,867 字节 | ZIP／清单绑定、重解压核验结果及分层验证结论 |

完整包 SHA-256：

纯文本

`2da7038354b81edbd0e8b9d15dca8fcb72adfea323fef265e2198de7b6dd041a`

外层交付回执 SHA-256：

纯文本

`660a916760efe3e37a63a49916b0d1bdfac2cf0a97c63a6601ac4817a350b185`

清单记录包内另外 **144 个文件**，不包含自身哈希；外层回执绑定清单和 ZIP，避免循环引用。ZIP 已通过 CRC 检查，重新解压后的逐件大小与哈希检查也已通过。

## 二、本轮实际实现了什么

### 1. 版本化 Envelope 与限权解析器

当前协议版本为：

纯文本

`YLTT-ANKI-TRANSPORT/0.1.0-isolated`

这是**供隔离测试使用的冻结版本**，尚未冒充正式联合接收的 Anki 协议。

已实现三类请求：

| 请求 | 用途 |
| --- | --- |
| HELLO | 确认明确的协议版本交集 |
| SUBMIT_EVENT | 将一个来源事实交给 P11 处理 |
| QUERY_STATUS | 在配对作用域内查询既存账本结果 |

解析器已经实现：

- 单帧 JSON 上限 **32,768 字节**。
- 嵌套深度上限 **12 层**，值与键节点总数上限 **512**。
- 拒绝重复 JSON 键、非法 UTF-8、BOM、未配对 surrogate、NaN／Infinity、浮点数及不安全整数。
- 拒绝未知协议、未知版本、未知消息类型、额外字段和不合法的事件因果形状。
- 拒绝钱包金额、信任布尔值、管理命令、笔记正文、磁盘路径等越权字段。
- 检查配对来源、集合谱系和受益范围；查询不能跨作用域暴露其他输入。

来源事件暂时映射到 P11 已交付的本地事件提案。**P12 没有自行生成真实事件身份，也没有假定目标 Anki 一定存在某个恢复 Hook。** event_id、family_id 未获证明时可以表达为空，并进入 P11 的隔离路径。

具体实现位于：

纯文本

`contracts/anki_transport/ipc_schema.json
runtime/anki/transport/ipc_server_client/protocol.py
runtime/anki/transport/ipc_server_client/bridge.py`

### 2. ACK 与 P21 提交结果绑定

游戏侧入口不会仅凭收到报文、进入队列或事务调用返回就发送成功 ACK。

适配层会重新查询当前业务结果，并核验提交引用、作用域、实例、水位、请求哈希、耐久标记和权威查询结果；无法确认时返回 RETRY_LATER。本轮实际使用的是 **P21 模拟事务凭证**，没有将其标记为生产凭证。

| 传输结果 | 实际含义 | outbox 行为 |
| --- | --- | --- |
| ACK_APPLIED | 当前权益已有核验的提交结果；重复投递不会再次授奖 | 标记已确认，保留原输入与摘要 |
| ACK_QUARANTINED | 该次输入已持久隔离，未因此授奖 | 保留并继续查询，不能视为最终消费结束 |
| RETRY_LATER | 提交、查询、因果关系或对账仍未解决 | 保留原输入，按边界查询或重投 |
| REJECTED | 传输前置拒绝，或有凭证的业务拒绝 | 保留供责任方处理，停止盲目重试 |
| STATUS / REVERTED | 已确认撤销或有效 Undo 墓碑 | 不作为新增奖励 ACK |
| STATUS / NOT_FOUND | 连续性已确认的查询快照中未发现该输入 | 可重投同一原始输入，由 P11 再次防重 |

这里特意保留了 P11 的业务状态差异：

- **撤销不映射成 ACK_APPLIED。**
- **待对账不冒称“完全没有经济变化”。** 例如 Undo 已部分回收、仍有已消费差额时，返回未决状态。
- **传输前置 REJECTED 不承诺持久收件。** 它通过 ledger_state=null 与有持久凭证的业务拒绝区分。
- 查询结果是时点结果。游戏 UI 不能消费 ACK 后自行加钱，也不能将历史 ACK 当作当前钱包余额。

具体映射、时序和对 P11 RFC 的回应已写入：

纯文本

`contracts/anki_transport/protocol_spec.md
contracts/anki_transport/ack_retry_sequence.md
contracts/anki_transport/interface_rfc.md`

### 3. 本机通信、断线重连和持久 outbox

已实现的通信候选只接受字面量 **127.0.0.1**，使用临时端口、随机配对密钥、每次连接的新挑战值，以及绑定方向和原请求的 HMAC。

实现中没有公网监听、域名回退、代理、广播或遥测入口。HMAC 提供认证和完整性，**不提供加密，也不证明来源事件真实**；真实来源证据仍由 P10／P11 的相应边界处理。

outbox 参考组件已实现：

- 原 Envelope 持久入队后再发送。
- 联网前持久记录本次尝试及下次查询状态。
- 超时、断开或进程退出后，优先查询既存 ledger 结果。
- 同一 message_id 不允许更换载荷；同一事件重复入队复用原投递身份。
- 重试有退避、抖动和每次工作调用的请求预算。
- 隔离项持续留存和跟踪。
- 容量不足明确报错，不淘汰未确认数据。
- 迟到的旧尝试不能覆盖较新的确认结果。

**这个 outbox 由独立插件 Mock 使用，本轮没有安装 Anki 插件或修改采集逻辑。** Hook 发生后、outbox 持久入队前的采集缺口，仍需要 P10 在真实插件中处理。

### 4. 文件交换与 IPC 比较已经交付

比较文件覆盖了私有目录文件交换、Unix domain socket、Windows named pipe 和 loopback TCP 的平台、权限、断网与服务端关闭条件。

本轮实际实现和验证的是 Linux 环境中的 loopback TCP 候选。正式目标平台与选型仍等待 P13／P34。Python 官方文档明确提示 socket 行为存在平台差异；Windows named pipe 的访问控制也需要单独设计和核验，不能用 POSIX 权限测试替代。[Python 3.12.16 documentation](https://docs.python.org/3.12/library/socket.html?utm_source=chatgpt.com)

**Windows／macOS 目标测试均为 NOT_RUN。** Windows 私有文件 DACL 辅助实现尚未提供，代码会明确阻断该路径。P38 审查输入已准备，但没有代签审核结论。

## 三、上游核验与复用结果

三份上传附件及包内 ZIP 均已实际解包、读取相关源码并核验。

| 核验项目 | 结果 |
| --- | --- |
| 去重后的 ZIP | **21 个，CRC 全部通过** |
| 文件成员 | **933 个** |
| relay 清单记录 | **403 条通过** |
| P08／P09／P10／P11 内部清单 | **307 条最终通过** |
| 保留的上游引用文件 | **27 个，保持原字节** |
| P10 真实复习样本 | **0 个** |
| P13 实际路径映射 | **未取得** |

P11 完整包与固定提交 d6e09fe07d1c3674b242ea59dd05231a3cd8acdb 中的 Git blob 内容对应；V6 正文与 8c370d731c323f86ff19642f4cc73f818498f641 对应。逐项来源、原始字节哈希和绑定记录见包内 source_input_receipt.json。

**本轮复用了 P11 的实际账本实现。** sources/P11/ 中的业务源码及测试模拟器保持不变；P12 只在自己的适配层完成协议映射。

“未取得实际路径映射和正式接入工件”的结论，仅覆盖本次附件及指定固定仓库树，不推断其他未提供工程不存在。

## 四、实际验证结果

完整验证记录见 verification_status.json。

| 验证层级 | 本轮结果 | 证明范围 |
| --- | --- | --- |
| 作者解析器与 P11 ACK／状态契约 | **PASS，46 项** | 封闭解析、版本拒绝、回执和业务状态协作 |
| 作者套接字与 outbox 测试 | **PASS，27 项** | 本机通信、认证、损坏帧、断线及队列边界 |
| 上述完整测试汇总 | **PASS，73/73** | 两项合计，不重复计数 |
| Schema 算法交叉核验 | **PASS，2,369 个实例** | 与 jsonschema 4.25.1 的校验结果一致 |
| Linux 真实双进程退出恢复 | **PASS，3/3** | 实际进程退出与重新启动后的查询、重放 |
| 正式接入前置检查 | **BLOCKED，退出码 3** | 正式依赖尚未齐备 |
| 正式设计／合同独立审核 | **NOT_RUN** | 未获正式联合接收 |
| 真实 Anki、真实游戏引擎、P21 生产事务 | **NOT_RUN** | 未执行真实联动 |
| P32 独测、P33 人工、P35 独审、P38 审核 | **NOT_RUN** | 未代签独立结论 |

三项进程恢复场景分别是：

1. 服务端在事务提交前退出。
2. 服务端提交成功后、ACK 返回前退出。
3. 客户端收到 ACK 后、提交 outbox 确认前退出。

这些场景确实启动了不同 PID 的两端进程，并在故障后恢复运行。最终模拟余额均为 **10**、钱包版本均为 **1**，没有二次授奖。这里的 **10 来自 P08／P11 合成数学夹具，不是正式四键奖值**。原始记录见 进程恢复汇总（附件：summary.json）。

本轮环境为 Linux x86_64、Python 3.12.14、SQLite 3.53.1。这些结果不覆盖断电、磁盘故障或用户目标电脑。

早期工具失败也保留了记录，包括 P08 清单基目录判断错误、初始网络／套接字限制及样例生成工作目录错误；对应修正和复验记录见 defect_log.json。

## 五、下一位直接复现的方法

在解压后的 P12_AnkiTransport_V0.1 根目录，使用 Python 3.12：

Bash

```
python -B verification/preflight.py

python -B -m unittest discover \
  -s mocks/anki_transport \
  -p '*_tests.py' -v

python -B -m mocks.anki_transport.process_replay \
  --output /tmp/p12-process-review

python -B verification/verify_delivery.py
```

第一条预期返回 **BLOCKED／退出码 3**。其余命令成功时返回 0。

普通程序和测试只使用 Python 标准库；Schema 算法交叉检查的可选依赖单独列在 requirements-dev.txt。套接字测试要求执行环境允许创建本机 socket。

下一位需要查看的主要源码路径为：

纯文本

`runtime/anki/transport/ipc_server_client/protocol.py
runtime/anki/transport/ipc_server_client/bridge.py
runtime/anki/transport/ipc_server_client/ports.py
runtime/anki/transport/ipc_server_client/wire.py
runtime/anki/transport/ipc_server_client/local.py
runtime/anki/transport/ipc_server_client/outbox.py

mocks/anki_transport/ack_replay_tests.py
mocks/anki_transport/parser_contract_tests.py
mocks/anki_transport/wire_outbox_tests.py
mocks/anki_transport/process_peer.py
mocks/anki_transport/process_replay.py`

## 六、正式接入阻塞与交接责任

| 接收方／责任方 | 仍需补齐的具体工件 |
| --- | --- |
| **P13** | 真实工程固定提交、引擎、actual_path_mapping.json、内部 DTO、P12 修改白名单和宿主线程边界 |
| **P10** | 目标 Anki 完整版本，以及真实完成、Undo、恢复、自然重复、旧备份的字段与身份关联证据 |
| **P11／P21** | 正式 IC-18 映射、生产原子提交／查询凭证、实例水位和恢复连续性合同 |
| **P13／P34** | 目标 OS／架构、候选 IPC 实测、端点发现、权限及目标环境行为 |
| **P38** | 本机绑定、字段最小化、授权用途、留存／删除和 Windows DACL 审核 |
| **P08／P01、P09／P22、P17** | 正式批准的奖励政策、分类映射／资源 ID，以及钱包来源归属接口 |
| **P32／P33／P35** | 固定正式版本的独立自动化、人工及证据门禁 |
| **用户指定 EXT-INTEGRATOR** | 后续跨模块整合授权与实际集成提交 |

已经准备了 **8 个接收方、53 条具体工件交接记录**，状态均为 PREPARED_NOT_ACKNOWLEDGED。

P13 实际映射批准前，包内 contracts/、runtime/、mocks/ 仍是隔离交付布局，不能直接作为覆盖真实工程的授权。

## 七、持久保存还差一次明确授权

**上述文件已经生成并可通过本次链接下载；持久保存尚未完成。**

最后的保存动作被**自动审批拒绝**。审核理由是：这六份文件包含非公开项目源码和审计材料，需要你明确授权将这些具体内容保存到本人当前账户的 ChatGPT 文件区。

要完成这最后一步，请明确授权：

> 允许将本次 P12 的 P12_AnkiTransport_V0.1.zip、P12_README.md、P12_ipc_schema.json、P12_protocol_version_matrix.tsv、P12_delivery_manifest.sha256.tsv 和 P12_delivery_receipt.json，保存到我自己的当前账户 ChatGPT 文件区。

---

## 本次归档的原始文件

- [pos_mapping_rules.json](files/data/pos_mapping_rules.json)
- [anki_field_observations.md](files/documents/anki_field_observations.md)
- [mapping_release_registry.json](files/data/mapping_release_registry.json)
- [classification_spec.md](files/documents/classification_spec.md)
- [p01_requirements_baseline_v6.txt](files/documents/p01_requirements_baseline_v6.txt)
- [p01_requirements_traceability.tsv](files/data/p01_requirements_traceability.tsv)
- [v6_freeze.txt](files/documents/v6_freeze.txt)
- [field_protocol_proposal.md](files/documents/field_protocol_proposal.md)
- [study_policy_draft.md](files/documents/study_policy_draft.md)
- [undo_compensation_options.md](files/documents/undo_compensation_options.md)
- [quarantine_resolution_policy.md](files/documents/quarantine_resolution_policy.md)
- [four_rating_policy_matrix.tsv](files/data/four_rating_policy_matrix.tsv)
- [QUARANTINED.json](files/data/QUARANTINED.json)
- [preflight.stderr.log](files/other/preflight.stderr.log)
- [hook_probe_report.md](files/documents/hook_probe_report.md)
- [prerequisites.json](files/data/prerequisites.json)
- [sample_inventory.json](files/data/sample_inventory.json)
- [P11_StudyLedger_V0.1.zip](files/archives/P11_StudyLedger_V0.1.zip)
- [eb9febc0-1-README.md](files/documents/eb9febc0-1-README.md)
- [defect_log.json](files/data/defect_log.json)
- [54e96c2a-1-delivery_manifest.sha256.tsv](files/data/54e96c2a-1-delivery_manifest.sha256.tsv)
- [15bc6522-1-downstream_handoff.json](files/data/15bc6522-1-downstream_handoff.json)
- [event_replay_fixtures.json](files/data/event_replay_fixtures.json)
- [failing_sources.zip](files/archives/failing_sources.zip)
- [regression.stderr.log](files/other/regression.stderr.log)
- [regression.stdout.log](files/other/regression.stdout.log)
- [1704a210-1-preflight.stdout.log](files/other/1704a210-1-preflight.stdout.log)
- [P11-REPLAY-001.json](files/data/P11-REPLAY-001.json)
- [P11-REPLAY-002.json](files/data/P11-REPLAY-002.json)
- [P11-REPLAY-003.json](files/data/P11-REPLAY-003.json)
- [P11-REPLAY-004.json](files/data/P11-REPLAY-004.json)
- [P11-REPLAY-005.json](files/data/P11-REPLAY-005.json)
- [P11-REPLAY-006.json](files/data/P11-REPLAY-006.json)
- [P11-REPLAY-007.json](files/data/P11-REPLAY-007.json)
- [P11-REPLAY-008.json](files/data/P11-REPLAY-008.json)
- [P11-REPLAY-009.json](files/data/P11-REPLAY-009.json)
- [P11-REPLAY-010.json](files/data/P11-REPLAY-010.json)
- [P11-REPLAY-011.json](files/data/P11-REPLAY-011.json)
- [P11-REPLAY-012.json](files/data/P11-REPLAY-012.json)
- [P11-REPLAY-013.json](files/data/P11-REPLAY-013.json)
- [P11-REPLAY-014.json](files/data/P11-REPLAY-014.json)
- [P11-REPLAY-015.json](files/data/P11-REPLAY-015.json)
- [P11-REPLAY-016.json](files/data/P11-REPLAY-016.json)
- [P11-REPLAY-017.json](files/data/P11-REPLAY-017.json)
- [P11-REPLAY-018.json](files/data/P11-REPLAY-018.json)
- [P11-REPLAY-019.json](files/data/P11-REPLAY-019.json)
- [P11-REPLAY-020.json](files/data/P11-REPLAY-020.json)
- [P11-REPLAY-021.json](files/data/P11-REPLAY-021.json)
- [P11-REPLAY-022.json](files/data/P11-REPLAY-022.json)
- [P11-REPLAY-023.json](files/data/P11-REPLAY-023.json)
- [P11-REPLAY-024.json](files/data/P11-REPLAY-024.json)
- [P11-REPLAY-025.json](files/data/P11-REPLAY-025.json)
- [P11-REPLAY-026.json](files/data/P11-REPLAY-026.json)
- [summary.json](files/data/summary.json)
- [replay.stderr.log](files/other/replay.stderr.log)
- [replay.stdout.log](files/other/replay.stdout.log)
- [delivery_consistency.json](files/data/delivery_consistency.json)
- [findings.json](files/data/findings.json)
- [github_p10_tree.json](files/data/github_p10_tree.json)
- [github_v6_tree.json](files/data/github_v6_tree.json)
- [intake_archives.py](files/code/intake_archives.py)
- [0b7f2182-1-intake_report.json](files/data/0b7f2182-1-intake_report.json)
- [16d34503-1-upstream_manifest_checks.json](files/data/16d34503-1-upstream_manifest_checks.json)
- [ledger_invariants.json](files/data/ledger_invariants.json)
- [__main__.py](files/code/__main__.py)
- [audit.py](files/code/audit.py)
- [ports.py](files/code/ports.py)
- [service.py](files/code/service.py)
- [types.py](files/code/types.py)
- [5060fd81-1-path_mapping_request.json](files/data/5060fd81-1-path_mapping_request.json)
- [reconciliation_and_recovery.md](files/documents/reconciliation_and_recovery.md)
- [ba7a6b13-1-source_input_receipt.json](files/data/ba7a6b13-1-source_input_receipt.json)
- [compensation_arithmetic_cases.json](files/data/compensation_arithmetic_cases.json)
- [policy_cases.json](files/data/policy_cases.json)
- [policy_record.proposal.json](files/data/policy_record.proposal.json)
- [study_ledger_state_machine.md](files/documents/study_ledger_state_machine.md)
- [task_receipt.json](files/data/task_receipt.json)
- [crash_worker.py](files/code/crash_worker.py)
- [simulated_ports.py](files/code/simulated_ports.py)
- [sqlite_atomic_model.py](files/code/sqlite_atomic_model.py)
- [test_ledger.py](files/code/test_ledger.py)
- [replay.py](files/code/replay.py)
- [a407b72c-1-run_author_checks.py](files/code/a407b72c-1-run_author_checks.py)
- [04da9e7a-1-verify_delivery.py](files/code/04da9e7a-1-verify_delivery.py)
- [491ec078-1-verification_status.json](files/data/491ec078-1-verification_status.json)
- [P11_delivery_receipt.json](files/data/P11_delivery_receipt.json)
- [interface_rfc.md](files/documents/interface_rfc.md)
- [compensation_log.jsonl](files/other/compensation_log.jsonl)
- [relay-materials-1-a9385ef43d.zip](files/archives/relay-materials-1-a9385ef43d.zip)
- [relay-materials-2-c668973fc2.zip](files/archives/relay-materials-2-c668973fc2.zip)
- [P12_AnkiTransport_V0.1.zip](files/archives/P12_AnkiTransport_V0.1.zip)
- [INTEGRATION.md](files/documents/INTEGRATION.md)
- [README.md](files/documents/README.md)
- [acceptance_matrix.tsv](files/data/acceptance_matrix.tsv)
- [ack_retry_sequence.md](files/documents/ack_retry_sequence.md)
- [change_requests.json](files/data/change_requests.json)
- [error_codes.tsv](files/data/error_codes.tsv)
- [ipc_schema.json](files/data/ipc_schema.json)
- [protocol_spec.md](files/documents/protocol_spec.md)
- [protocol_version_matrix.tsv](files/data/protocol_version_matrix.tsv)
- [references.json](files/data/references.json)
- [security_review_p38.md](files/documents/security_review_p38.md)
- [transport_comparison.md](files/documents/transport_comparison.md)
- [659c19a9-1-defect_log.json](files/data/659c19a9-1-defect_log.json)
- [delivery_manifest.sha256.tsv](files/data/delivery_manifest.sha256.tsv)
- [downstream_handoff.json](files/data/downstream_handoff.json)
- [author_design_review.md](files/documents/author_design_review.md)
- [core.stderr.log](files/other/core.stderr.log)
- [core.stdout.log](files/other/core.stdout.log)
- [oracle.json](files/data/oracle.json)
- [oracle.stderr.log](files/other/oracle.stderr.log)
- [oracle.stdout.log](files/other/oracle.stdout.log)
- [dependency-install-approved.log](files/other/dependency-install-approved.log)
- [dependency-install.log](files/other/dependency-install.log)
- [observed_tool_failures.json](files/data/observed_tool_failures.json)
- [schema_validator_environment.json](files/data/schema_validator_environment.json)
- [final_source_binding.json](files/data/final_source_binding.json)
- [audit_inputs.py](files/code/audit_inputs.py)
- [engineering_findings.json](files/data/engineering_findings.json)
- [github_source_tree.json](files/data/github_source_tree.json)
- [786423a5-1-github_v6_tree.json](files/data/786423a5-1-github_v6_tree.json)
- [input_audit.json](files/data/input_audit.json)
- [source_git_bindings.json](files/data/source_git_bindings.json)
- [upstream_manifest_checks.json](files/data/upstream_manifest_checks.json)
- [upstream_manifest_checks_attempt_001.json](files/data/upstream_manifest_checks_attempt_001.json)
- [receipt.json](files/data/receipt.json)
- [ack_replay_tests.py](files/code/ack_replay_tests.py)
- [export_vectors.py](files/code/export_vectors.py)
- [01_hello.request.json](files/data/01_hello.request.json)
- [01_hello.response.json](files/data/01_hello.response.json)
- [02_review.request.json](files/data/02_review.request.json)
- [02_review.response.json](files/data/02_review.response.json)
- [03_review_replay.request.json](files/data/03_review_replay.request.json)
- [03_review_replay.response.json](files/data/03_review_replay.response.json)
- [04_query_applied.request.json](files/data/04_query_applied.request.json)
- [04_query_applied.response.json](files/data/04_query_applied.response.json)
- [05_undo.request.json](files/data/05_undo.request.json)
- [05_undo.response.json](files/data/05_undo.response.json)
- [06_restore.request.json](files/data/06_restore.request.json)
- [06_restore.response.json](files/data/06_restore.response.json)
- [07_wrong_version.request.json](files/data/07_wrong_version.request.json)
- [07_wrong_version.response.json](files/data/07_wrong_version.response.json)
- [08_quarantine.request.json](files/data/08_quarantine.request.json)
- [08_quarantine.response.json](files/data/08_quarantine.response.json)
- [09_causal_gap.request.json](files/data/09_causal_gap.request.json)
- [09_causal_gap.response.json](files/data/09_causal_gap.response.json)
- [vector_manifest.json](files/data/vector_manifest.json)
- [parser_contract_tests.py](files/code/parser_contract_tests.py)
- [process_peer.py](files/code/process_peer.py)
- [process_replay.py](files/code/process_replay.py)
- [schema_oracle.py](files/code/schema_oracle.py)
- [support.py](files/code/support.py)
- [wire_outbox_tests.py](files/code/wire_outbox_tests.py)
- [path_mapping_request.json](files/data/path_mapping_request.json)
- [requirements-dev.txt](files/documents/requirements-dev.txt)
- [bridge.py](files/code/bridge.py)
- [local.py](files/code/local.py)
- [outbox.py](files/code/outbox.py)
- [protocol.py](files/code/protocol.py)
- [wire.py](files/code/wire.py)
- [rfc_ic14_ic15.md](files/documents/rfc_ic14_ic15.md)
- [43976083-1-task_receipt.json](files/data/43976083-1-task_receipt.json)
- [preflight.py](files/code/preflight.py)
- [run_author_checks.py](files/code/run_author_checks.py)
- [verify_delivery.py](files/code/verify_delivery.py)
- [verification_status.json](files/data/verification_status.json)
- [P12_delivery_receipt.json](files/data/P12_delivery_receipt.json)
- [P12_README.md](files/documents/P12_README.md)
- [P12_delivery_manifest.sha256.tsv](files/data/P12_delivery_manifest.sha256.tsv)
- [P12_ipc_schema.json](files/data/P12_ipc_schema.json)
- [P12_protocol_version_matrix.tsv](files/data/P12_protocol_version_matrix.tsv)

