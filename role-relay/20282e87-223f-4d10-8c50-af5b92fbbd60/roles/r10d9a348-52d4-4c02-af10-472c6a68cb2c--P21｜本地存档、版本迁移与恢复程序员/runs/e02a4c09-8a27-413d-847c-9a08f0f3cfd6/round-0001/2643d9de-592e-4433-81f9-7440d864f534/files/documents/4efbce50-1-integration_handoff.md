# P21 交接与复现说明

交付版本 `P21-PERSISTENCE/0.1.0-isolated`；任务 `P21-S05-S06-S07-SAVE-001`。本说明供下游接收源码、独测和未来授权整合使用；没有执行跨模块仓库合并。

## 已经固定的输入

本轮从 14 个附件解包，递归读取包含在其中的 ZIP 原字节，检查 108 个去重归档、8,198 个文件成员和 787 个 relay manifest 条目。全部 CRC/大小/hash 核验未发现失败。完整原始索引在 `evidence/input_inventory.json`；详细 Git 比对和选取的源码原件在 `source_input_receipt.json`。

固定职责仓库提交：`8c370d731c323f86ff19642f4cc73f818498f641`。固定 P20 归档提交：`8b7e2043a7168d779c72668106b25fcfd8b828d6`。直接 Git blob 相符的上传件为 9 张 PNG 与 1 个 relay ZIP；其余 4 个上传 ZIP 是重打包容器，通过内部 manifest 和嵌套原包核验，不谎称容器本身在 Git 固定提交中。

选取 128 份原件随包，包含 P11、P18、P18 带入的 P17/P13 原代码、必要配置/测试端口及 P20 接口文字。它们保留原字节，只用于复用、适配和契约验证；不表示所有 8,198 个文件都做了语义审查。P20 完整包 SHA-256 为 `175c51607c175e483ec21e0000cbcc211407cffb09c8dc206648d867df187513`。

P13 当前对 `runtime/persistence/**`、`schema/save/**`、`tests/save_unit/**` 的正式 actual path 都是 null、write_allowed=false。本包这些路径仅为新隔离交付目录内的相对路径。不能把本包目录树当成对正式工程的覆盖授权。

## 接收后直接复跑

```bash
python -B tools/verify_delivery.py
python -B atomic_commit_tests.py
python -B tools/save_tool.py inspect-backup --backup examples/stage_backup
python -B tools/preflight.py
```

前三条预期 exit 0，最后一条预期 exit 3/BLOCKED。测试默认把日志放到新临时目录，不污染包内文件。若显式 `--output`，选择新目录，保留 stdout、stderr、run_receipt、test_results、源码快照和逐场景 JSON。不要覆盖本包已经保存的历史失败或最终通过证据。

可执行演练：

```bash
python -B tools/run_demo.py --output ../P21_new_demo
python -B tools/recovery_demo.py --output ../P21_new_recovery_demo
python -B tools/save_tool.py rehearse-migration --backup examples/v1_backup --destination ../P21_new_migration_review
```

上述目录必须不存在。示例数据、测试奖励、测试关卡与合成权威均带隔离标识，不是正式 MVP 内容范围。

四个 JSON Schema 的额外验证使用 jsonschema 4.23.0。此依赖只用于 oracle，不属于运行时。可在接收方自己的隔离 Python 环境安装后执行：

```bash
python -B tools/validate_schemas.py
```

没有该依赖时返回 NOT_RUN/exit 3，不影响标准库主测试。作者的依赖实际版本清单在 `recovery_logs/schema_oracle_001/schema_results.json`。

## 端口接收关系

| 接收方 | 可立即使用的实体文件 | 本岗已提供 / 仍需对方确认 |
| --- | --- | --- |
| P11 | adapters.py、P21_API.md、test_contracts.py | 账本+钱包物理事务、持久 lookup、Undo/Restore 测试；正式钱包绑定与回执 origin 版本尚缺 |
| P17 | adapters.py、test_contracts.py、test_native_crash.py | 原候选提交期重验、角色/队伍/钱包整体落盘；学习旧模型的无损 project/materialize/validate 需 P17 提供 |
| P18 | adapters.py、store.py、原生崩溃证据 | 原联合候选、首通 SQL 唯一键；确认入场证据和当前 meta 同源的版本化契约 |
| P13 | actual_path_request.json、interface_rfcs.json | 原 SaveStatusView/CommitLookupView 验证通过；真实路径、组合根、outer intent 映射仍待批准 |
| P20 | handoff/P20_recovery_response.md | 内核持久查询与恢复状态可用；现有 UI 回复版本不接受 durable=true，不能直接替换测试宿主 |
| P32 | 完整 ZIP、测试入口、原始证据 | 独立复跑同 SHA；7 个作者缺陷独立复测/关单仍 NOT_RUN |
| P33 | 运行入口、恢复工具与迁移说明 | 目标桌面、异常退出/断电、真实盘满、恢复可用性人工验收 NOT_RUN |
| P34 | environment_observed.json、probe_environment.py | 当前 Linux 探针；正式引擎/Windows/文件系统/SQLite 绑定待交付 |
| P35 | 清单、回执、状态、缺陷与日志 | 独立证据门禁 NOT_RUN，作者测试不能代签 |
| P36 | schema/save、save_migration_plan.md、CLI | 只读备份、版本演练、精确恢复；备份保留/跨设备/整盘回滚策略待批准 |

`downstream_receipts.json` 还包括 P01 与未来 EXT-INTEGRATOR，共 12 个准备好的交接条目，全部 `PREPARED_NOT_ACKNOWLEDGED`；未向他人发送消息或假造接收签字。

## 正式整合时的具体接口条件

授权整合者需先取得实际 base commit、P13 映射和修改白名单。将 P21 作为唯一物理 writer 装配，使用 owner 提供的已验证初始全量记录；本包不提供根据 UI 零余额自动初始化用户账户的逻辑。

P17 使用 P17CommitAdapter；P18 使用 P18CommitAdapter，并在同一锁内绑定可信证据快照和原 P17 校验器。P11 使用 P11AtomicAdapter，但必须先有经 P17/P11 受理的 LegacyWalletBinding 或新的统一领域接口。不能拷贝 `tests/support` 的测试映射成为生产钱包。

P20/P12 的操作网关需固定原意图到领域 transaction ID、request hash、实例和连续性的映射。回执发布与业务 ACK 以真实持久 COMMITTED 为前置；UNKNOWN 保留原请求、禁止新经济操作。当前 P20 只接受模拟回复的严格校验不可私自放宽；应提交新版本并由 P20 自己改源码，整合者在获授权后接线。

迁移/恢复工具只接收 P21 显式路径和已知 store instance。目标存储位置、权限、独立连续性文件保护、跨设备策略、历史容量和备份保留均需对应 owner 的固定工件。真实 Anki 协议和 outbox 属于 P12，不在本包实现或改写。

## 冲突、缺陷与证据交接

若收到新领域包或路径，先核对 base SHA 与新 SHA。差异记录为 ChangeRequest，保留双方原件；禁止覆盖原 `sources/` 后继续引用旧验证结果。既有失败快照保留在 `recovery_logs/review_counterexamples_001/` 与 `recovery_logs/envelope_counterexample_001/`。

所有本岗缺陷由 P21 修复；P32 复测、P35 独审。现在 7 项均为作者修复复测通过，独立关单 NOT_RUN；没有把另一个岗位的源文件改成自己的实现。若同一问题连续两轮返工没有新证据，按原 V6 升级 P01，不在此包扩展范围。

正式合并、桌面候选构建、整游戏与真实 Anki E2E 仍待用户指定 EXT-INTEGRATOR。此交付可以独立运行与审查，不能作为 S08 正式集成或发布通过的证据。
