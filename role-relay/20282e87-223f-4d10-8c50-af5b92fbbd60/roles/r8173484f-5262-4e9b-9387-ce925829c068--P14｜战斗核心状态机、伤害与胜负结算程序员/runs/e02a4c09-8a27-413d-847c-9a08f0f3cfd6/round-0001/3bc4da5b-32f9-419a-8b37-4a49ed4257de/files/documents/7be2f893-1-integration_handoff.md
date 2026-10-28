# P14 接收与后续接入说明

任务 `TASK-01-02`；交付 `P14-BATTLE-CORE/0.1.0-isolated`。此文件供接收方复现与评估，不是跨模块合并授权。P14 没有修改任何上游原件或正式工程。

## 1. 接收顺序

1. 使用包外 `delivery_receipt.json` 的 archive 字段核验 ZIP 大小和 SHA-256；解压到一个新目录。
2. 在包根执行 `python -B tools/verify_delivery.py`，核验清单、实际文件集合和 78 份保留的原字节输入。清单不列自身，清单 SHA 在包外回执中。
3. 执行 README 的单元测试、无渲染示例与回放；保留接收者自己的命令、环境、源码 SHA、stdout、stderr 和退出码。
4. 阅读 `handoff/IC05_API.md`、`battle_result_schema.md` 与 `handoff/p02_projection_contract.md`，明确每条已接收或仍未接收的语义。
5. 正式工程接入前由 P13 重新出具 actual_path_mapping，用户指定 EXT-INTEGRATOR 后再做映射和装配。不得把本包根目录直接覆盖到原工程。

所有准备的接收记录均为 `PREPARED_NOT_ACKNOWLEDGED`。没有把作者测试作为接收者签收或独立验收。

## 2. 交给各接收方的具体文件

| 接收方 | 固定文件入口 | 本次已可执行的部分／仍需原 owner 的内容 |
|---|---|---|
| P15 | `handoff/IC05_API.md`、`battle_core/ports.py`、`examples/fixture_ports.py` | 用同一 basis 生成 DeckPatchCandidate；费用只由候选指定。负向候选和 draw report 扩展见 RFC-003 |
| P16 | `handoff/IC05_API.md`、`battle_core/resolver.py`、`handoff/interface_rfcs.json` | 单意图执行、DOT 前置终局与无目标 SKIP；真实 AI、多敌批次、阶段提交需原 owner |
| P19／P29 | `battle_event_samples.json`、`battle_snapshot.json`、P13 原 presentation_adapter_spec | 仅消费已提交 Batch／Snapshot。显示副本不能改权威数据；真实 UI／动画生命周期尚未测试 |
| P32 | `resolution_replay_tests/**`、`verification_status.json`、`evidence/runs/**` | 复跑 101 项，保留 4 项缺历史的 BLOCKED；另补独立合同、目标环境与异常测试 |
| P33 | README、示例执行记录、目标环境阻塞项 | 无渲染 CLI 可复现；实际游戏窗口、输入与动画测试仍 NOT_RUN |
| P35 | 清单、回执、输入绑定、失败日志、RFC、验证分层 | 独立审查所有权、来源、事实与宣称范围；本包未代签任何审核结论 |
| P13 | `handoff/contract_acceptance.json`、路径请求、7 项 RFC | P14 已接收隔离形状；正式路径、事件缺项及阶段扩展需 P13 版本处理 |
| P02／P03／P05／P22 | 投影说明、来源回执、阻塞清单 | 核准正式效果、费用与数值政策、内容 ID。不得让测试内容自动变为生产内容 |
| P01 | `handoff/task_completion.json`、`handoff/blockers.json` | 记录 TASK-01-02 的隔离成果与后续激活条件；规模仍由 P01 冻结 |
| EXT-INTEGRATOR | 完整包、清单、API、原依赖 | 待用户指定和授权后实施整合；当前没有实施合并 |

每条接收文件的实际大小和 SHA 见 `handoff/downstream_receipts.json`；完整逐件记录见 `delivery_manifest.sha256.tsv`。

## 3. 环境与依赖

本轮实测：Linux x86_64、CPython 3.12.14。实际版本和 PATH 发现记录在 `evidence/environment.json`。引擎可执行文件、目标 OS 及目标电脑未取得；这不推断用户其他位置没有工程。未启动真实引擎、Anki 或游戏窗口。

本包为纯 Python 标准库运行库，复用 `upstream/P13/runtime/framework/yltt_framework/` 原 codec 与契约校验模块。P13 原校验器依赖其相对目录中的 Schema，接收时必须保留本包目录层级。不得仅复制一个 `core.py` 后宣称依赖完整。

`jsonschema==4.25.1` 仅供可选的第二种算法对照，当前缺失且安装网络请求受限。普通运行、101 项作者测试及回放不需要它。失败启动与后续 BLOCKED 记录均保留，没有以安装尝试替代验证成功。

本包不含生产牌堆规则、AI 选择、前端、物理存档、Anki 协议或奖励落盘。`upstream/` 中的未执行脚本只是保留证据，不代表这些脚本都在 P14 本轮跑过。P13 的 54 项和 P12 的 46／73 项上游历史结果也没有计入本轮 97 项通过数。

## 4. 实际路径和修改白名单

P13 原路径表仍把 P14 的规划路径标为 `BLOCKED_NOT_MAPPED`。本包的 `battle_core/**`、`resolution_replay_tests/**` 是独立工件路径，正式实际路径为 null，`production_write_authorized=false`。

P14 可维护本包自己的源码、测试、示例、工具、说明和证据；`upstream/**` 属原 owner，只读保留。真实工程写入白名单为空。下游可以在新副本中复测，缺陷应带复现日志回 P14 修复，不能让其他岗位无授权接管源码。

如需改变 DTO、事件或结果语义，用 `handoff/interface_rfcs.json` 中的 ChangeRequest，绑定旧 schema／规格 SHA 与本版源码。保留双方 base SHA，不覆盖上游。如果接收方已有不同文件，先比较其 base SHA 与本包清单，再由原 owner 出补丁版本。

## 5. 正式接入仍需取得的证据

`handoff/blockers.json` 已逐项登记责任方。最直接的门槛是 P13/P01 的真实工程固定提交及路径授权、P15/P16 的真实 provider 固定版本、P22 的正式内容注册与 P02/P03/P05 的批准政策、P34 的目标环境、P32/P33/P35 的独立回执。S07 还需阶段命令、epoch 与行动槽合同；S08 整合须等用户另行指定人员。

这些缺项不阻止接收者运行本包的真实内存结算，但阻止把它报告为正式游戏已接通、完整 BOSS 多阶段完成或真实 Anki 联动通过。
