# 存档迁移与恢复：已实现流程和批准边界

任务 `P21-S05-S06-S07-SAVE-001`；物理格式 `P21-SQLITE/1`、`P21-SQLITE/2`。这是有源码与执行证据的迁移说明。v1/v2 是本隔离组件明确创建的两个物理版本，**不是声称已经取得两版真实游戏历史存档**。P11/P17/P18 的领域 schema 没有被本岗升级。

## 1. 支持矩阵

| 源物理格式 | reader 1 | reader 2 | 写入 | 迁移 |
| --- | --- | --- | --- | --- |
| v1 | 可校验/读取 | 可校验/备份 | 经济写入返回 E_MIGRATION_REQUIRED | 唯一已实现邻接步骤：1→2 |
| v2 | E_READER_TOO_OLD | 可读 | 经完整校验可写 | ALREADY_CURRENT，无新增事务 |
| 未知/更高版本 | 拒读 | 拒读 | 禁止 | 没有降级或猜测性解析 |
| 损坏/身份冲突/连续性缺失 | UNKNOWN/冻结 | UNKNOWN/冻结 | 禁止 | 先保全与核对，不迁移损坏源 |

版本检查由 `PRAGMA application_id`、`PRAGMA user_version`、`store_meta.schema_version/min_reader_version` 和回执链中的版本转换联合完成。当前 v2 将 min reader 设为 2；不会因只新增表就宣称旧程序可以安全读取新存档。

## 2. 1→2 实际变化

源 DDL：`schema/save/001_initial.sql`；升级 DDL：`schema/save/002_maintenance_audit.sql`。v1 的 documents、transactions、claims、store_meta 保持数据；v2 新增 maintenance_audit。每个迁移审计关联一个全局 sequence、源/目标版本、只读备份 SHA-256 和源 chain hash。

一次升级在同一 SQLite 事务内执行：新增表、提升版本与 min reader、生成 SCHEMA_MIGRATION 回执、更新全局 head、写入审计行。校验器检查迁移回执与审计表双向完整匹配。文档 payload、revision、钱包净额、角色、关卡和首通键不变；仅全局提交序号因维护事务 +1。

## 3. 对活跃隔离存档执行迁移

1. 指定实际保存目录、独立连续性文件和预期实例；校验原存档及完整链。
2. 将一致快照备份到新的保存目录外路径，使用 SQLite backup API；记录数据库 SHA/大小，写 manifest 和最后的 complete 封印；文件设为只读。
3. 重新取得物理写锁，核对当前 head 与备份 head 完全一致。若备份期间出现其他变更，E_MIGRATION_BACKUP_STALE，禁止在过期备份上升级。
4. 在 BEGIN IMMEDIATE 内执行邻接升级。异常离开事务时完整回滚；不部分提交 DDL。
5. SQLite COMMIT 后，发布外部连续性记录。发布或响应不确定时按 E_COMMIT_UNKNOWN 处理，重开后核验真实 schema 与迁移回执，不盲目重复迁移。
6. 保留旧备份目录。源版本的备份仍可独立只读检查，不能自动取代新版本已确认的数据。

```bash
python -B tools/save_tool.py migrate --store /path/to/save --anchor /path/to/authority/head.json --instance trusted-instance --destination /path/to/new-before-upgrade-backup
```

路径是参数结构说明，不是本次真实项目的授权路径。复现时优先用 `tools/run_demo.py` 创建的新测试目录。

## 4. 在备份上先演练

包内 `examples/v1_backup/` 是本轮实际生成的可验证 v1 测试备份。

```bash
python -B tools/save_tool.py inspect-backup --backup examples/v1_backup
python -B tools/save_tool.py rehearse-migration --backup examples/v1_backup --destination ../P21_rehearsal
```

演练在新副本中执行同一 `_upgrade`，复核三个领域文档原字节一致和源备份 SHA 未变。候选目录使用 `RECOVERY_REVIEW_ONLY` 标记和 `FROZEN.json`，没有生成新的外部连续性记录。应用层禁止经济写入；文件可供 P32/P35 检查。报告示例见 `examples/migration_rehearsal.json` 和 `recovery_logs/cli_rehearsal_001/`。

## 5. 中断时应该看到什么

| 中断点 | 重开后的允许状态 | 已执行证据 |
| --- | --- | --- |
| 备份复制过程中/封印前 | 不完整备份不可检查为有效；活跃存档不变 | 备份中断和 ENOSPC 用例 |
| 新增审计表后、COMMIT 前 | 完整 v1，新增表不存在，领域字节不变 | DDL 异常 + 真实 SIGKILL |
| COMMIT 前 | 完整 v1 | 真实 SIGKILL |
| COMMIT 后、连续性文件前 | 完整 v2；校验链上旧 checkpoint 后前移连续性记录 | 真实 SIGKILL |
| 连续性发布后、回复前 | 完整 v2；重试返回当前版本，不再次改变净额 | 真实 SIGKILL |
| 恢复替换后、验证解冻前 | 保持 FROZEN；再次执行精确恢复可完成 | 恢复中断注入 |

这些结果证明本轮测试环境中的进程崩溃与错误分支。没有进行真实硬件断电或 Windows 故障注入，不能将 SIGKILL 当作断电验收。

## 6. 损坏后的保全

一旦检测到物理页错误、文档/回执哈希错误、迁移审计缺失、身份或回滚问题，停止经济写入。保全流程不会更改领域净额：

- 在恢复前复制现存数据库、journal/WAL/SHM（若存在）和 store marker，逐件记录大小与 SHA，副本只读。
- 如果发现非空 rollback journal，在 SQLite 进行正常未提交事务恢复之前先复制原数据库及 journal。
- 写入冻结标记。若磁盘满到无法保存证据/标记，当前对象仍冻结；新打开者仍必须通过相同完整性和连续性检查。不会因备份写失败就跳过校验。
- 分析 `compare_backup` 的身份、sequence、文档 revision/hash 差异。损坏活跃库不能产生可信差异时，先保留原件，只读检查备份；不凭余额猜测修复。

不能调用 SQLite repair、删除回执、抹掉首通标记、清除冻结文件或创建新连续性记录来“修好”生产数据。任何会丢弃已确认历史的方案必须由 P01/用户批准，P11/P17/P18 提交领域对账计划，保留审计，再由 P21 提交新实施版本。

## 7. 唯一允许自动完成的恢复

`recover_exact` 只接受备份的整个 head 精确等于独立连续性记录，且 store marker/实例/profile 匹配。

该流程保留损坏原件与残留 sidecar，先置恢复冻结，原子替换指定数据库，然后验证数据库、链、head 与外部记录；成功才移除冻结标记。报告 `data_loss=false`、`awards_replayed=0`。同一已提交事务查询/重试仍返回原回执，不重跑学习或首通奖励。

```bash
python -B tools/recovery_demo.py --output ../P21_recovery_demo
```

演练只能创建一个不存在的新目录，生成测试记录后破坏其数据库头；拒绝旧备份激活，再以精确备份恢复。它会保存损坏原件，比较恢复前后 head，并断言重复事务不会执行奖励回调。它不接受已有真实保存目录。

## 8. 旧备份为何不能直接“恢复后继续发奖”

若独立连续性记录的 sequence 是 8，备份只有 5，简单恢复会遗忘 6—8 的消费、撤销或首通记录。即使备份本身 SHA 正确，也不能证明重新出现的学习事件或首通奖励尚未处理。

因此旧备份 `stage_restore` 只创建冻结审查副本，`recover_exact` 返回 E_DATA_LOSS_OR_FOREIGN_RESTORE_BLOCKED。这里没有按余额差自动补发、重置请求 ID 或省略历史日志的代码。跨设备恢复也必须先确立可信连续性来源。

独立记录位于保存目录之外，能检测测试中的“只回滚保存目录”。如果整个磁盘连同该记录一起被回滚，本版没有外部可信时间/序号可鉴别。这个限制记录为正式 BLOCKED，不把本地 SHA 校验当作反回滚安全服务。

## 9. 后续版本的交接要求

P11/P17/P18 领域迁移需各 owner 提供固定 schema、纯转换、输入输出哈希、守恒断言、拒绝条件和批准。P21 包装邻接版本的物理事务与只读备份，不能自行修剪旧来源批次或改变学习负债规则。

正式启用还需要 P13 actual_path_mapping 与 DTO 受理、P34 目标 OS/SQLite/文件系统探针、P32 故障矩阵复跑、P33 目标机体验、P35 证据门禁。独测和验收状态均见 `verification_status.json`，不由本说明代签。
