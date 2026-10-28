# P11｜StudyLedger 独立源码与证据交付

**已实现并验证本岗独立账本内核；正式 S05 接入和真实授奖仍为 BLOCKED。**

任务 ID：`P11-S05-LEDGER-001`。版本：`P11-STUDY-LEDGER/0.1.0-isolated`。作者岗位：P11。下游接收：P12、P21、P32、P33、P35，协同P13/P17及上游契约owner。接收状态：PREPARED_NOT_ACKNOWLEDGED。

本包是在核验上传附件与GitHub固定提交后开展的独立研发。未取得P13实际路径映射，因此没有写入真实工程的`runtime/anki/ledger/`或`runtime/anki/reward_transactions/`，没有合并、提交PR或发布任何游戏版本。

## 阅读入口

| 文件/目录 | 内容 |
|---|---|
| `study_ledger_state_machine.md` | 身份、五态、授权/提交边界、Undo/恢复、隔离与备份缺口 |
| `ledger_runtime/service.py` | 实际P11业务源码：持久收件接口、幂等、墓碑、权益事务协调、复核与对账 |
| `ledger_runtime/types.py`、`ports.py`、`audit.py` | 本地DTO/端口提案、关闭的默认门禁、守恒与来源校验 |
| `ledger_invariants.json` | 机器可读不变量、具体测试关联与证据限制 |
| `event_replay_fixtures.json` | 26个可直接执行的合成事件重放场景 |
| `compensation_log.jsonl` | 实际回放产生的13条撤销/恢复及未决差额审计记录 |
| `reconciliation_and_recovery.md` | 直接运行方式、崩溃/未知提交/旧备份与隔离恢复说明 |
| `interface_rfc.md` | 提交P08/P12/P13/P17/P21/P10的版本化契约请求，尚未获接收 |
| `tests/`、`verification/` | 作者测试、故障注入、重放驱动及逐件验证工具 |
| `source_input_receipt.json`、`sources/` | 已消费上游路径、原字节SHA-256及固定Git绑定；只读快照 |
| `evidence/` | 实际命令、输入哈希、stdout/stderr、退出码、失败修复链和逐步回放结果 |
| `formal_prerequisites.json`、`path_mapping_request.json` | 具体缺项、责任方及未映射的正式路径 |
| `verification_status.json`、`defect_log.json` | 分层验证状态及5项已修复作者缺陷，独立复测未运行 |
| `downstream_handoff.json`、`delivery_manifest.sha256.tsv` | 接收对象、实体文件大小/哈希/版本/输入哈希/修改白名单 |

`tests/support/simulated_ports.py`是合成政策/身份/钱包端口；`tests/support/sqlite_atomic_model.py`是测试专用持久原子存储模型。二者均不是其他岗位的正式源码。模拟器必须在显式标记目录中创建`*.p11-sim.sqlite`，没有真实Anki/游戏适配器。

## 已执行结果

| 层级 | 本轮结果 | 证据 |
|---|---|---|
| 附件/嵌套ZIP完整性 | PASS：16个不同ZIP、739个成员、330条转交清单 | `evidence/intake/` |
| 上游内部清单 | PASS：202条大小及SHA-256 | `evidence/intake/upstream_manifest_checks.json` |
| 最终作者单元与模拟端口测试 | PASS：51/51，其中6项实际子进程退出并重开 | `evidence/author_run_003/` |
| 声明式模拟重放 | PASS：26/26，含1000次重投、隔离恢复、消费补偿和备份栅栏 | `evidence/author_run_004/replay/` |
| 正式接入前置检查 | BLOCKED，退出码3 | `evidence/author_run_004/preflight.stdout.log` |
| 正式契约/目标机/真实Anki E2E | NOT_RUN | `verification_status.json` |
| P32独测/P33人工/P35独审 | NOT_RUN | 未代签任何独立回执 |

51项测试和26个场景有覆盖重叠，不相加为不同功能数。修复前5项实际失败保留在`evidence/author_run_002/`；该目录中的`failing_sources.zip`只用于历史复现，不能集成。最终源码对应`author_run_003`的修复后哈希；随后新增的前置检查CLI及回放驱动由`author_run_004`另行执行。

## 快速复现

在解压后的本包根目录执行；Python标准库即可，本轮实际Python 3.12.14：

```bash
python -B -m ledger_runtime preflight
python -B -m unittest discover -s tests -p 'test_*.py' -v
python -B -m verification.replay --output /tmp/p11-replay-review
python -B verification/verify_delivery.py
```

第一条应退出3并输出BLOCKED。其余命令分别验证作者实现、模拟事件与交付字节；不能将成功结果写成真实Anki联动通过。Windows复现者应自行选择可写的回放输出目录；本轮没有在Windows运行。

## 已处理的核心问题

同一证据充分的事件反复投递只保留一份有效授权。Undo先到时保存墓碑，迟到原完成不发奖。同身份不同载荷只隔离冲突，不自动追回原权益。提交结果未知时查询同一事务，不因接收消息或超时重试额外发奖。已消费撤销只按获批规则处理可追溯原剩余量，未决暴露量不变成债务；恢复使用原政策快照及当前保留权益，只补差额。

本包的Q=10仅复用P08合成数学夹具，正式四键金额仍为空。日界、预算、币种、消费归属、负债、豁免和未来抵扣没有由P11擅自定案。

## 仍然阻塞的正式工作

P10没有真实事件/Undo/epoch证明；P08/P01没有获批PolicyRecord；P09正式映射、P12通信、P17钱包、P21原子存储及独立备份水位、P13实际路径/内部DTO、P34目标环境和P38授权尚未取得。各项具体工件与责任方列于`formal_prerequisites.json`，缺失版本/哈希保留null。

不能仅靠P11代码判断“所有防重记录也一起回滚”的旧备份；P21必须提供可信恢复边界或外部权威证据。不能从P10尚未采集入队的事件生成奖励。正式适配、独立测试与最终整合由各owner及用户指定EXT-INTEGRATOR继续处理。

## 接收规则

先验证ZIP外层回执，再运行逐件清单检查。交付清单不自含其自身SHA；外层`P11_delivery_receipt.json`绑定清单SHA与ZIP SHA。所有源码变更记录原base SHA及ChangeRequest；`sources/`禁止改写，证据日志只能新增版本。

本独立包的作者写入白名单不等于真实工程授权。接收方可以独立审查、测试和准备正式适配；未经用户指定EXT-INTEGRATOR和P13实际路径映射，不进行跨岗位覆盖式合并。
