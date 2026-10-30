# P21｜本地存档、版本迁移与恢复交付

任务：`P21-S05-S06-S07-SAVE-001`  
版本：`P21-PERSISTENCE/0.1.0-isolated`  
状态：**ISOLATED_PERSISTENCE_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED**

本包交付真实 SQLite 物理存档程序、原领域代码适配器、存档 Schema、备份与恢复 CLI、v1→v2 迁移、可执行故障测试和原始运行证据。所有新增源码位于本隔离包。P13 的 P21 三条正式路径映射仍为空且禁止写入，未覆盖正式工程，未执行跨模块合并。

## 1. 先运行什么

完整解压 ZIP 后，进入 `P21_LocalSave_V0.1`。已验证环境是 Linux x86_64、Python 3.12.14、SQLite 3.53.1。核心程序和主测试仅使用 Python 标准库；领域代码原件随包提供。

```bash
python -B tools/verify_delivery.py
python -B atomic_commit_tests.py
python -B tools/preflight.py
python -B tools/run_demo.py --output ../P21_demo_run
```

含义：

| 命令 | 正常结果 | 证据范围 |
| --- | --- | --- |
| verify_delivery | exit 0 | 本包逐文件字节、SHA-256、上游原件不变性 |
| atomic_commit_tests | exit 0 | 作者隔离单元、契约、真实进程中断等测试；默认证据写到新临时目录 |
| preflight | **exit 3 / BLOCKED** | 如实列出正式接入缺失条件，不代表单元测试失败 |
| run_demo | exit 0 | 原 P11/P17/P18 算法 + 明示测试输入 + 真实 P21 磁盘存储 |

`../P21_demo_run` 必须尚不存在。不要把这些命令指向真实游戏或 Anki 的数据目录。Windows 路径/锁/同步探针尚未交付，当前实现会以 `E_PLATFORM_NOT_PROBED` 拒绝在 Windows 上运行。

## 2. 已实现的事务边界

唯一活动数据库是保存目录中的 `game.p21-save.sqlite3`，包含三个完整领域文档：

| 文档 | 领域 owner | 物理提交边界 |
| --- | --- | --- |
| ledger | P11 | 学习账本；与钱包变更一起提交；隔离等无收益状态可只更新账本 |
| meta | P17 | 角色、三人队伍、唯一钱包、来源批次、领域操作记录 |
| stage | P18 | 关卡进度、出战记录、首通消耗、待核对状态 |

同一业务事务中的文档更新、首通唯一键、持久回执及全局提交序号在一个 SQLite 事务内提交。P21 不决定学习计奖资格、经验增长、费用、负债或首通资格，领域 owner 的原校验器在物理写锁内重新校验候选。

学习 `ledger+meta`、养成 `meta`、关卡 `stage+meta` 使用同一套物理提交机制。学习旧钱包字段与 P17 原生来源批次钱包之间尚无获批的无损转换，本包默认拒绝这一未绑定端口，**没有新建第二份游戏钱包**。学习原代码测试使用明确标注的测试映射，不能用于正式收益。

## 3. 持久、防重、恢复已经提供什么

- 原事务 ID 与原请求 SHA-256 绑定。相同请求返回原回执，不重复执行领域回调；同 ID 不同载荷拒绝。
- 全部文档的 revision 与 before SHA 做提交前比较。读视图在同一个锁和 SQLite 读取事务内产生。
- 提交回执、请求哈希及首通唯一键持久保留；本版不提供清理这些防重记录的接口。
- 成功回执只有在 SQLite 提交与保存目录外的连续性记录同步完成后返回。提交后响应丢失返回 `E_COMMIT_UNKNOWN`，调用者查询原事务，不生成新事务重试。
- 文档校验和、回执哈希链、SQLite integrity check、身份围栏和连续性记录联合检查；损坏后冻结写入，并尽力保留原始数据库及 sidecar 的只读副本。
- 一致备份带 SHA-256、大小、完成封印；备份内的 head 不是恢复权威。
- 精确恢复只接受与独立连续性记录完全相同的已确认提交位置，保留损坏原件，不运行奖励回放。
- 旧备份只能检查、差异比较或放到冻结的审查目录。丢数据型恢复、跨设备恢复和整个磁盘连同连续性记录一起回滚都不能由本包自动授权。
- 物理格式 v1→v2 逐版本迁移；先保留只读备份，DDL 与迁移回执同事务。旧 reader 1 拒读 v2，领域原字节不变。

连续性文件必须在保存目录之外，由受信任的程序装配层选择和保护。它仍是本地文件，**不是密码学签名或外部反回滚服务**。同时回滚整个保存目录和该文件的情形尚未解决；正式策略见 `blockers.json` 的恢复阻塞项。

## 4. 可直接检查的演练结果

`tools/run_demo.py` 真正调用原 P17/P18 领域程序：普通关首次结算后余额 3、每人累计经验 4；重复提交同一结算不增加；测试 Boss 首通后余额 15、每人经验 22；原 P17 升级消耗 4，余额 11；重新打开保存目录后保持相同净额与角色等级。

学习演练调用原 P11 状态机：测试复习 10 → Undo 0 → Restore 10。此分支使用测试奖励规则和测试旧钱包绑定；不是 Anki 实际复习，也不是原生 P17 学习钱包接入。

原始输出在 `recovery_logs/demo_001/`，另有 `examples/demo_result.json`。该结果里的绝对路径是当时执行记录，复现时用自己的 `--output` 路径。

包内包含两份真正生成的测试备份，可立即执行：

```bash
python -B tools/save_tool.py inspect-backup --backup examples/stage_backup
python -B tools/save_tool.py rehearse-migration --backup examples/v1_backup --destination ../P21_migration_rehearsal
python -B tools/save_tool.py stage-restore --backup examples/stage_backup --destination ../P21_restore_review
```

迁移演练目录与恢复审查目录必须尚不存在。最后一条返回 exit 3 / `STAGED_READ_ONLY`，表示候选已经准备好但禁止激活。源备份保持原字节。

## 5. 文件入口

| 路径 | 内容 |
| --- | --- |
| runtime/persistence/p21_persistence/ | P21 物理事务、序列化、文件同步、恢复与原领域适配器源码 |
| schema/save/ | 两个 SQL 版本、四个 JSON Schema、物理格式说明 |
| tests/save_unit/ | 原子性、防重、损坏、迁移、原领域契约及 SIGKILL 用例 |
| atomic_commit_tests.py | 完整测试入口，保留命令、原始输出、退出码与执行源码快照 |
| tools/save_tool.py | 检查、查询、备份、比较、精确恢复与迁移 CLI |
| P21_API.md | 实际函数、端口契约、错误分类、查询与确认语义 |
| save_migration_plan.md | 已实现迁移与恢复步骤，旧版限制、损坏与数据损失边界 |
| disaster_simulation_report.md | 本轮实际结果、故障注入方式和未执行项目 |
| verification_status.json | 分层验证状态；独测、真机、E2E 单独标注 |
| source_input_receipt.json | 14 个附件、嵌套 ZIP 核验、固定提交与 128 份原件的来源和哈希 |
| actual_path_request.json / blockers.json | 正式路径请求与责任方明确的阻塞项 |
| interface_rfcs.json | 六项版本化 RFC，均未代替 owner 批准 |
| integration_handoff.md / handoff/P20_recovery_response.md | 下游接收与 P20 未决操作接线条件 |
| recovery_logs/ | 成功、失败、修复复测、崩溃子进程与工具原始证据 |
| delivery_manifest.json | 每件文件的实际大小、SHA-256、源输入、接收方、修改白名单 |

主测试结果以 `recovery_logs/author_final_002/test_results.json` 为准。最终 ZIP 新解压目录的复跑在包外交付回执中，不以重复运行累计覆盖数。主清单不哈希自身；其字节和 ZIP 由包外 `P21_delivery_receipt.json` 绑定，避免循环哈希。

## 6. 正式接入仍需谁做什么

P13/P34 提供实际工程、固定 base commit、三条路径授权、引擎和目标设备；P11/P17/P13 接受学习钱包的无损端口；P13/P20 固定 UI 原意图到领域事务的映射与可信回执来源；P12/P11 固定真实事件身份与 ACK 边界；P01 与领域 owner 批准丢数据恢复和容量策略。P32 独测、P33 人工、P35 独审均为 `NOT_RUN`。

本包的 `durable=true` 只表示隔离物理事务完成。原始 receipt origin 是 `P21_SQLITE_ISOLATED`；P11 旧枚举投影仍用 `P21_SIMULATOR`，绝不标为 `P21_PRODUCTION`。P20 的“正式已入账”分支保持阻塞。

下游可立即复测本包、审查 RFC 和接收源码。正式仓库变更及跨模块合并留给用户后续指定的 EXT-INTEGRATOR。本包不包含发布或自动集成操作。
