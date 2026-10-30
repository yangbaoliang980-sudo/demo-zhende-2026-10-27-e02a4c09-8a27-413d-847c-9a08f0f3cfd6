# P21｜本地存档、版本迁移与恢复交付

**已交付可运行的隔离物理存档实现、持久化 API、存档 Schema、备份与恢复工具、版本迁移、测试及灾难模拟证据。最终 ZIP 已在新解压目录复跑：104 项测试全部通过，25 项 JSON Schema 检查通过。**

任务编号：`P21-S05-S06-S07-SAVE-001`
交付版本：`P21-PERSISTENCE/0.1.0-isolated`
当前状态：**ISOLATED_PERSISTENCE_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED**

本次交付使用真实 SQLite 文件执行事务与恢复。正式接入仍缺 P13 实际路径授权、目标平台、P11/P17 钱包映射及相关接口受理；P32 独测、P33 人工验收、P35 独审、真实 Anki 与整游戏 E2E 均未代签通过。

## 一、完整成果下载

| 文件 | 实际大小 | 内容 |
| --- | --- | --- |
| **P21_LocalSave_V0.1.zip** | **4,563,265 字节** | 379 个实体文件：运行源码、Schema、测试、迁移恢复工具、128 份未修改上游原件、原始日志、失败源码快照及实际测试备份 |
| **P21_delivery_receipt.json** | **283,663 字节** | ZIP、清单与 23 个独立导出的实际大小和 SHA-256；最终新解压复跑命令、原始输出、退出码与逐场景证据 |

ZIP 的 SHA-256：

纯文本

`05ec1111199f90da2f3e3f814048256ef21264e6a229c4163113de51836f3f23`

已实际完成 ZIP CRC 检查、**379 个包内文件与生成目录逐字节比对**、**23 个独立导出与包内对应文件同名同字节检查**，以及新解压目录运行前后的文件不变性检查。主清单记录其余 378 个文件；清单自身与 ZIP 由包外交付回执绑定，避免循环哈希。

### 必交文件与阅读入口

**运行和测试请使用完整 ZIP。** 单独下载的 Python 入口依赖包内其他模块。

| 文件 | 用途 |
| --- | --- |
| README.md | 启动、演练、验证命令与能力边界 |
| P21_API.md | 原子提交、一致读取、持久查询、错误返回和领域适配接口 |
| save_migration_plan.md | 已实现的 v1→v2 迁移、只读备份、恢复步骤与旧版限制 |
| atomic_commit_tests.py | 104 项完整测试入口 |
| save_tool.py | 校验、查询、备份、差异比较、精确恢复和迁移 CLI |
| disaster_simulation_report.md | 故障模拟方式、实际结果、失败历史和验证范围 |
| integration_handoff.md | 下游接收与后续授权接线说明 |
| P20_recovery_response.md | 对 P20 持久未决操作、恢复状态及到账证明的具体交接回复 |
| delivery_manifest.json | 逐件相对路径、实际大小、SHA-256、格式/版本、源输入、接收方及修改白名单 |

完整源码位于包内：

- runtime/persistence/p21_persistence/
- schema/save/
- tests/save_unit/
- tools/
- recovery_logs/

## 二、已实现的物理事务与恢复行为

### 1. 三个领域文档使用同一个物理事务

活动存档文件为 game.p21-save.sqlite3，包含三份完整领域文档：

| 文档 | 领域 owner | 提交边界 |
| --- | --- | --- |
| ledger | P11 | 学习账本；有钱包变化时与 meta 一次提交 |
| meta | P17 | 角色、队伍、唯一钱包、来源批次和领域操作记录 |
| stage | P18 | 关卡进度、出战记录、首通消耗及待核对状态；奖励与 meta 一次提交 |

同一业务事务中的**文档更新、首通唯一键、持久回执、提交序号和状态哈希**在一个 SQLite 事务内提交。提交前，在物理写锁内重新调用原领域校验器，并检查记录版本和原状态 SHA。

P21 负责落盘与完整性；计奖资格、成长费用、负债、首通资格仍由原 owner 决定。具体端口与实际调用边界见 P21_API.md。

### 2. 跨重启防重与结果未知处理

已实现原事务 ID 与原请求 SHA-256 的持久绑定：

- 相同 ID、相同原请求返回原回执，不再次运行领域回调。
- 相同 ID、不同载荷拒绝。
- 首通唯一键与奖励记录同事务写入，并保留防重历史。
- 提交后响应丢失返回 E_COMMIT_UNKNOWN，调用者查询原事务。
- 只有存档完整性、实例和连续性均可验证时，查询才会返回确认的 ABSENT；无法确认时返回 UNKNOWN。

成功回执在 SQLite 提交及保存目录外的连续性记录同步完成后返回。回执原始来源固定为 **P21_SQLITE_ISOLATED**，不会仅凭 durable=true 变成正式学习收益证明。

### 3. 只读备份、损坏保全与恢复

备份由一致快照生成，包含数据库大小、SHA-256、提交位置及完成封印；生成的备份文件设为只读。未完成或校验失败的备份不能被识别为有效备份。

发现损坏后冻结写入，保留数据库、相关 sidecar 和保存标记的原始副本。此次还交付了**实际损坏数据库、只读保全副本、恢复报告和对应哈希**，位于：

纯文本

`recovery_logs/forensic_demo_001/`

已实现的自动恢复只接受：**备份的提交位置与独立连续性记录完全一致，且保存身份可验证。** 恢复保留损坏原件，替换后重新校验，再解除冻结；不会回放奖励。

旧备份可以检查、比较和放入冻结的审查目录。会丢弃较新历史的恢复保持 BLOCKED，需 P01/用户授权及领域对账。

### 4. 逐版本迁移与旧读者限制

已实现并测试本组件物理格式 **v1→v2**：

- 升级前保留只读备份。
- DDL、版本提升、迁移审计和回执在同一事务中完成。
- 迁移保持领域 payload 原字节不变。
- 可先在备份副本上演练，源备份保持不变。
- reader 1 拒绝读取已迁移的 v2 存档。

这里的 v1/v2 是本次隔离组件明确创建的物理版本，没有将其冒称为已取得的真实游戏历史存档版本。详情见 save_migration_plan.md。

## 三、实际验证结果

以下结果以**最终 ZIP 新解压目录的复跑**为准，重复运行不累计为新增覆盖。

| 验证层级 | 实际结果 | 证明范围 |
| --- | --- | --- |
| P21 作者设计与代码复核 | COMPLETED_AUTHOR_REVIEW | 本岗事务、所有权、恢复与证据边界 |
| 完整自动化测试 | **104 PASS，0 FAIL，0 ERROR，0 skip** | 原子性、防重、并发、契约、损坏、迁移及回归 |
| 原领域契约测试 | **18 PASS，包含在 104 项内** | 原 P11/P17/P18/P13 代码；测试事件、规则和战斗证据明确标注 |
| 真实进程 SIGKILL | **19 PASS，包含在 104 项内** | 8 个基础提交点、4 个迁移点、7 个原领域数据中断点 |
| JSON Schema 校验 | **25 项检查 PASS** | 四个 Schema、实际程序输出与拒绝样例 |
| SQLite 容量耗尽 | **PASS** | 数据库引擎实际返回 SQLITE_FULL，跨记录无半提交 |
| 备份及连续性文件 ENOSPC | **PASS** | 注入 OS 磁盘满错误，检查不完整备份和提交后未知结果 |
| 损坏文件保全与精确恢复 | **PASS** | 原件哈希一致；恢复前后提交位置一致；奖励回放为 0 |
| ZIP、全部包内文件及独立导出 | **PASS** | 379 个文件、23 个独立导出 |
| 新解压目录运行前后不变性 | **PASS** | 379 个文件未改变 |
| 正式接入前置检查 | **BLOCKED，exit 3** | 路径、目标平台及正式接口条件未齐备 |
| P32 独测、P33 人工、P35 独审 | **NOT_RUN** | 未代签 |
| 目标引擎、Windows、真实 Anki、整游戏 E2E | **NOT_RUN** | 未执行 |
| 真实硬件断电、填满整个物理卷 | **NOT_RUN** | 本轮未执行这两类目标设备测试 |

环境为 **Linux x86_64、Python 3.12.14、SQLite 3.53.1**。当前代码明确阻止未经探针的 Windows 路径。

SIGKILL 测试实际终止了子进程，并检查其 -9 退出码、重开状态及净额。真实硬件断电仍需另行验证；SQLite 原子提交也依赖底层文件系统与同步行为。[sqlite.org](https://www.sqlite.org/atomiccommit.html?utm_source=chatgpt.com)

分层状态与环境证据：

### 原领域程序的实际净额演练

原 P17/P18 代码配合明确的测试入场和终局证据，得到以下结果：

| 操作 | 钱包可用余额 | 角色/进度结果 |
| --- | --- | --- |
| 普通关首次结算 | 3 | 每名测试角色累计经验 4 |
| 重复提交同一结算 | 3 | 首通和经验没有再次增加 |
| 测试 Boss 首次结算 | 15 | 每名测试角色累计经验 22 |
| 原 P17 升级 | 11 | 升级与消耗 4 一次提交 |
| 重新打开保存目录 | 11 | 等级、经验、关卡与净额一致 |

原 P11 学习状态机演练为 **复习 10 → Undo 0 → Restore 10**。这条测试使用明确的旧钱包测试映射，**正式 P11→P17 原生钱包接入仍为 BLOCKED**，没有将其写成真实 Anki 到账通过。

## 四、发现的缺陷已修复，失败证据已保留

本轮作者复核共复现并修复 **7 项 P21 自身缺陷**：

1. P17 重复请求的原文与自报哈希绑定不足。
2. P18 同类绑定问题。
3. SQL 已提交但 COMMIT 返回异常时，错误分类未保持“结果未知”。
4. 迁移审计行缺失未被检测。
5. 畸形回执未统一进入冻结错误路径。
6. 核心回调的非对象结果可能形成无法重读的回执。
7. 保存标记畸形时未完整进入冻结与原件保全路径。

失败时源码、原始输出和后续复测均随包保存，最终 104 项测试包含这些回归用例。**独立复测及关单仍为 NOT_RUN。** 详见 defect_log.json。

## 五、上游核验与剩余阻塞

本轮实际递归读取了收到的附件及包内原 ZIP，完成：

- **14 个上传件**核验。
- **108 个去重 ZIP** 的检查。
- **8,198 个展开文件成员**的字节读取与哈希。
- **787 条 relay manifest 检查，0 失败**。
- **128 份相关上游原件**随包保留，最终复跑确认未改变。

固定职责提交为 8c370d731c323f86ff19642f4cc73f818498f641；固定 P20 归档提交为 8b7e2043a7168d779c72668106b25fcfd8b828d6。直接与 Git blob 相符的上传件是 9 张 PNG 和 1 个 relay ZIP；另外 4 个上传 ZIP 是重打包容器，已通过内部清单与嵌套原包核验，没有将它们误报为 Git 中的同字节容器。

逐件来源、版本和 SHA-256 在 source_input_receipt.json。

### 正式接入缺项

| 缺项 | 责任方与需要的工件 |
| --- | --- |
| 实际工程路径及修改权限 | **P13**：实际仓库、固定 base commit、三条路径映射与修改白名单 |
| 引擎、目标 OS 与存储探针 | **P13/P34**：目标设备、SQLite/锁/同步与构建入口证据 |
| P11/P17 学习钱包无损绑定 | **P11/P17/P13**：获批的 project/materialize/validate 或统一新接口 |
| 真实学习事件与 ACK 链 | **P10/P08/P12/P11**：身份、规则、通信及确认边界的固定工件 |
| P20 原意图到持久事务的映射 | **P13/P20**：外层请求 ID/hash 与领域事务、实例、连续性的版本化契约 |
| 旧备份、跨设备及整盘回滚策略 | **P01/P11/P17/P18/P36**：授权和领域对账；本地连续性文件不能识别整盘同时回滚 |
| 独立门禁及最终合并 | **P32/P33/P35**；跨模块合并由用户指定 **EXT-INTEGRATOR** 执行 |

P13 原映射中的三条 P21 正式路径仍为 actual_production_path=null、`write_allowed=false`。本次新增内容全部位于隔离交付目录。

已准备 **6 项版本化 RFC** 和 **12 个接收方交接条目**，分别标为 PREPARED_NOT_SUBMITTED、`PREPARED_NOT_ACKNOWLEDGED`：

## 六、下一位直接复现

完整解压后进入 P21_LocalSave_V0.1：

Bash

```
python -B tools/verify_delivery.py
python -B atomic_commit_tests.py
python -B tools/preflight.py
```

最终 ZIP 新目录中，这三条的实际退出码依次为 **0、0、3**。第三条表示正式接入条件缺失。

运行领域与恢复演练：

Bash

```
python -B tools/run_demo.py --output ../P21_demo_run
python -B tools/recovery_demo.py --output ../P21_recovery_demo
```

检查真实生成的测试备份，并在副本上迁移：

Bash

```
python -B tools/save_tool.py inspect-backup --backup examples/stage_backup

python -B tools/save_tool.py rehearse-migration \
  --backup examples/v1_backup \
  --destination ../P21_migration_rehearsal
```

输出目录必须尚不存在。迁移演练结果保持冻结审查状态，原备份不变。

**下一接收方可直接使用完整包开展 P11/P17/P18 端口受理、P32 自动化复测、P33 目标机恢复验证及 P35 证据审查。P20 的正式“已入账”分支继续保持关闭，跨模块合并等待用户指定的 EXT-INTEGRATOR。**

---

## 本次归档的原始文件

- [P21_LocalSave_V0.1.zip](files/archives/P21_LocalSave_V0.1.zip)
- [89c172e9-1-source_input_receipt.json](files/data/89c172e9-1-source_input_receipt.json)
- [04971dde-1-downstream_receipts.json](files/data/04971dde-1-downstream_receipts.json)
- [023fe25b-1-README.md](files/documents/023fe25b-1-README.md)
- [P21_API.md](files/documents/P21_API.md)
- [save_migration_plan.md](files/documents/save_migration_plan.md)
- [save_tool.py](files/code/save_tool.py)
- [atomic_commit_tests.py](files/code/atomic_commit_tests.py)
- [disaster_simulation_report.md](files/documents/disaster_simulation_report.md)
- [4efbce50-1-integration_handoff.md](files/documents/4efbce50-1-integration_handoff.md)
- [59ab4eeb-1-delivery_manifest.json](files/data/59ab4eeb-1-delivery_manifest.json)
- [dbc963c8-1-verification_status.json](files/data/dbc963c8-1-verification_status.json)
- [6358072c-1-environment_observed.json](files/data/6358072c-1-environment_observed.json)
- [25e8929b-1-defect_log.json](files/data/25e8929b-1-defect_log.json)
- [39a6580a-1-actual_path_request.json](files/data/39a6580a-1-actual_path_request.json)
- [ff69b8c1-1-blockers.json](files/data/ff69b8c1-1-blockers.json)
- [P21_delivery_receipt.json](files/data/P21_delivery_receipt.json)
- [a9c2d419-1-interface_rfcs.json](files/data/a9c2d419-1-interface_rfcs.json)
- [0d69c6e5-1-task_traceability.json](files/data/0d69c6e5-1-task_traceability.json)
- [b1cac929-1-author_review.md](files/documents/b1cac929-1-author_review.md)
- [P20_recovery_response.md](files/documents/P20_recovery_response.md)
- [P21_save_head.schema.json](files/data/P21_save_head.schema.json)
- [P21_atomic_request.schema.json](files/data/P21_atomic_request.schema.json)
- [P21_commit_receipt.schema.json](files/data/P21_commit_receipt.schema.json)
- [P21_backup_manifest.schema.json](files/data/P21_backup_manifest.schema.json)
- [P20_Menu_1280.png](files/images/P20_Menu_1280.png)
- [P20_Party_1280.png](files/images/P20_Party_1280.png)
- [P20_Growth_1280.png](files/images/P20_Growth_1280.png)
- [P20_Chapters_1280.png](files/images/P20_Chapters_1280.png)
- [P20_Settlement_1280.png](files/images/P20_Settlement_1280.png)
- [P20_Learning_Quarantine.png](files/images/P20_Learning_Quarantine.png)
- [P20_Migration_Failed.png](files/images/P20_Migration_Failed.png)
- [P20_Menu_390.png](files/images/P20_Menu_390.png)
- [P20_Restart_Pending.png](files/images/P20_Restart_Pending.png)
- [relay-materials-1-1d9857f540.zip](files/archives/relay-materials-1-1d9857f540.zip)
- [relay-materials-2-29da14dfaa.zip](files/archives/relay-materials-2-29da14dfaa.zip)
- [relay-materials-3-359996fd72.zip](files/archives/relay-materials-3-359996fd72.zip)
- [relay-materials-4-279d81665e.zip](files/archives/relay-materials-4-279d81665e.zip)
- [relay-materials-5-93fd453ebe.zip](files/archives/relay-materials-5-93fd453ebe.zip)
- [relay-materials-6-4a55082585.zip](files/archives/relay-materials-6-4a55082585.zip)
- [relay-materials-7-9e66ba3f56.zip](files/archives/relay-materials-7-9e66ba3f56.zip)

