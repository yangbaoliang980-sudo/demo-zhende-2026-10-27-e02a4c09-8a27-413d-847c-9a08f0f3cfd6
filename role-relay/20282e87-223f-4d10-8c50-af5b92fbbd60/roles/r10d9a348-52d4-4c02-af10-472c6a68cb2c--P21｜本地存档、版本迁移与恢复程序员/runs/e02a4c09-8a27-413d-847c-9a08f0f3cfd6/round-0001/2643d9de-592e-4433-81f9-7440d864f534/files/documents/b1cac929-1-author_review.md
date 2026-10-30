# P21 作者复核记录

层级：`COMPLETED_AUTHOR_REVIEW`。这是本岗源码/契约/证据复核，不是 P35 独审、P32 独测或 P33 人工验收。

## 审查结论

本隔离实现把 P11、P17、P18 owner 的完整记录与物理防重回执放在同一个 SQLite 事务中。提交期重新运行原 owner 校验器，首次成功和原请求重试区分明确；恢复路径没有奖励回放和丢数据强制开关。原 P11/P17 钱包不兼容端口默认阻塞，未建立第二套游戏钱包。

逐项核查了记录所有权与 schema tag、请求原文/hash、revision/before hash、首通唯一键、完整性与连续性、版本向前迁移、只读原备份、损坏保全、返回结果未知、原始源码不变和测试数据来源。

## 实际发现并修复的缺陷

| 编号 | 问题 | 本岗修复 |
| --- | --- | --- |
| P21-DEF-001 | P17 重复提交前可改原命令但复用自报 hash | 查重复前重新计算完整原命令 hash |
| P21-DEF-002 | P18 同类原文/hash 绑定问题 | 重算原命令、校验 projection 与事务 ID |
| P21-DEF-003 | SQL 已提交但 COMMIT 返回异常被分成普通 I/O 错误 | 不可证明未提交时返回 E_COMMIT_UNKNOWN，后续查原回执 |
| P21-DEF-004 | 迁移审计行缺失未被发现 | 审计表与迁移回执双向完全匹配 |
| P21-DEF-005 | 畸形回执缺字段抛出原始 KeyError | 闭合结构检查与 E_STRUCTURE_CORRUPT/冻结处理 |
| P21-DEF-006 | 核心回调的非 object result 可写成无法重读的回执 | 任何 SQL 更新前拒绝 E_MUTATION_RESULT |
| P21-DEF-007 | 保存标记畸形导致未走冻结/保全路径 | 封闭标记形状检查，标记读取纳入统一冻结保护域 |

前 5 项在 `review_counterexamples_001` 的同次运行复现 3 failures、2 errors；第 6 项在 `envelope_counterexample_001` 复现 1 failure；第 7 项在 `marker_counterexample_001` 复现 1 error，另一个既有回归通过。失败时源码快照与原始输出保留；对应固定复测和最终完整 104 项测试均通过。独立复测、关单和验收状态一律 NOT_RUN，详见 `defect_log.json`。

## 未被作者审查代替的门禁

真实目标引擎/OS、Windows 文件锁与同步、物理断电/磁盘硬故障、原生 P11↔P17 学习钱包、真实 Anki Hook/Undo/ACK、P20 生产网关、长期容量与整个磁盘回滚策略，以及 P32/P33/P35 的独立回执均未完成。缺项见 `blockers.json`，不能在接力转述时改为 PASS。

## 实现参考

SQLite 官方 [Atomic Commit](https://www.sqlite.org/atomiccommit.html)、[PRAGMA](https://www.sqlite.org/pragma.html)、[Online Backup API](https://www.sqlite.org/backup.html) 用于核对事务、同步和备份语义。软件保证受底层存储同步假设限制。本轮证据限于 environment_observed.json 所记录的运行环境和可复现测试，未从文档推断目标机已通过。

Python/SQLite 来自执行环境，未随包重分发二进制。jsonschema 只用于作者的额外 Schema oracle，核心运行与主测试不依赖该包。上游项目原件保留原版权/来源标记，未自行宣布许可审核通过。
