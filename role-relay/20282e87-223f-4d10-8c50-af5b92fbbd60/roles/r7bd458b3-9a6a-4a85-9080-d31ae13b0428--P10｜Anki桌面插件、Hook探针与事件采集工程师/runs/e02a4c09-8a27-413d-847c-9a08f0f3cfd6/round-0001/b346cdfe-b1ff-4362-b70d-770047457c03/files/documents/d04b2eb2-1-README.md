# P10｜Anki S04 探针报告交付

**状态：PROBE_REPORT_DELIVERED / S04_TARGET_BLOCKED / QUARANTINED。**

任务 ID：P10-S04-PROBE-001。需求：REQ-011、REQ-025；边界 REQ-012、REQ-026。交付版：0.1.0。日期：2026-10-28（UTC+08:00）。

已实际解包核验两份上传附件及全部内层 ZIP，读取 P08/P09/V6 相关原文，并将官方 Anki 固定源码的 Hook 声明和调用路径与目标环境证据分开记录。缺目标 Anki/OS、字段授权、P13 路径映射、P12 正式 Schema 以及真实世代/Undo 证据。本岗按 V6 例外交付探针报告、QUARANTINED 标志及可执行复核附录。

**真实复习/Undo 样本为 0；未实现可安装插件、持久 outbox 或游戏联动。** 不允许将本包当 `.ankiaddon` 安装，不授权任何学习收益。本包目录不是正式工程 actual_path_mapping。

## 阅读入口

| 文件 | 作用 |
|---|---|
| `hook_probe_report.md` | 完整核验结果、固定源码观察、身份/崩溃缺口及下游交接 |
| `QUARANTINED.json` | 机器可读的本岗能力隔离标志，不是账本 ACK |
| `anki_hook_probe.py` | 实际可运行的环境/前置检查与源码 AST 提取附录；不接 Hook |
| `probe_log_redacted.txt` | 本次实际前置检查输出，明确不是四键/Undo 样例 |
| `addon_manifest.json` | 不可安装交付描述，不是 Anki 安装清单 |
| `deliverable_status.json` | 每项必交产物的实际交付/阻塞/未执行情况 |
| `sample_inventory.json` | 14 项真实场景全部 NOT_RUN，真实样本列表为空 |
| `configuration_disable_uninstall.md` | 可执行复核命令、当前无安装物的边界与后续停用要求 |
| `rfc_ic14_ic15.md` | 待 P12/P09 接收的版本化语义提案，不定义正式 IPC Schema |
| `source_input_receipt.json`、`reference_inputs.json` | 上游来源、成员链、版本及原字节哈希 |
| `evidence/author_run_002/` | 作者实际 stdout/stderr、退出码与执行前输入哈希 |
| `delivery_manifest.sha256.tsv`、`downstream_handoff.json` | 逐件大小/哈希/来源/接收人/写入限制和交接绑定 |

## 复核

从本目录运行：

```bash
python -B anki_hook_probe.py preflight
python -B anki_hook_probe.py scan-reference
python -B -m unittest discover -s verification -p 'test_report_guards.py' -v
python -B verification/verify_delivery.py
```

第一条应退出 3 并明确 BLOCKED；其余命令成功只证明对应的静态检查、报告工具和字节完整性。不能把这些结果改名为插件单元测试、正式契约、真实 Anki 运行或 E2E 通过。P32/P33/P34/P35/P38 独立结果均 NOT_RUN。

完整归档核验记录为 15 个唯一 ZIP、612 个成员、260 条 relay 清单及 146 条 P08/P09 内部清单；这些是完整性检查次数，不是独立功能用例。官方源码参考为 `ankitects/anki@d87cb22bf337c52257376f3abcec09c03a255ed4`，声明版本 26.09.3；它不是用户目标环境。

所有消费快照保留原字节，修改白名单为空。P10 仅可对其报告与检查附录提交带新版本的修订；正式工程写入白名单为空。清单不自哈希，清单及 ZIP 的哈希由包外 `P10_delivery_receipt.json` 固定。接收方不得只通过修改状态布尔值宣称解禁。

P11/P12/P32/P34/P36 可直接接收本包进行相应证据审查；P35 独审待执行。没有代签接收、推送 GitHub、发布插件或跨模块整合。继续真实 S04 须由 P34/P13/P38/P12/P08/P01 提供对应固定工件与环境；具体缺项在 `prerequisites.json`。
