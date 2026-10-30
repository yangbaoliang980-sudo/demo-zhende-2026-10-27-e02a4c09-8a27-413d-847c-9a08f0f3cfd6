# P21 对 P20 持久未决操作请求的交接回复

关联：P20-RFC-005 / P20-PENDING-RECOVERY/0.1.0-proposal；同时涉及 P20-RFC-001/002/003。  
P21 版本：P21-PERSISTENCE/0.1.0-isolated。  
状态：**隔离内核实现已交付；跨接口受理与 P20 正式接线 BLOCKED**。

原件基线：`sources/P20/P20_API.md`，SHA-256 `faa2adaa768a8355cecab14055ebdcd06a9dc68b51f8dd51ba1afadd120b8e47`。原 P20 API 文件未修改。

## 已补齐的 P21 能力

| P20 需求 | 本包实际提供 |
| --- | --- |
| atomic receipt/commit | 领域文档、首通唯一键、原请求 hash 与回执同一 SQL 事务；重启后可查 |
| retention/continuity | 永久保存事务回执；独立连续性记录；拒绝仅回滚保存目录造成的旧历史 |
| authoritative absence | Store.lookup 在实例/连续性/完整性全部成立时才返回 ABSENT；其他错误 UNKNOWN |
| migration failure readonly | status + 原 P13 SaveStatusView；冻结写入、保留原件；UI 可继续用现有只读导航 |
| 同一快照显示 | read_consistent 将 ledger/meta/stage/head 在同一锁内交给受信任投影函数 |

原 P13 `CommitLookupView` 和 `SaveStatusView` 未改 schema，已通过原 validator。实际 API 是 `Store.lookup()`、`adapters.p13_lookup()`、`adapters.p13_status()`。

## 不能把现有测试宿主直接换成此 Store

P20 当前 Reply 严格绑定外层 `request_id` 与规范意图 SHA，接受 COMMITTED_SIMULATION 等既定状态，并拒绝 durable=true。本包回执绑定的是领域 transaction ID 与领域原请求 SHA；两者不能从名称相似推断相等。P20 上游原有内存发布器也不是本包已经改写的文件。

因此 P13/P20 需要固定一个版本化网关合同，明确外层完整意图到领域事务的持久关联、回复的可信来源、会话与实例围栏，以及跨重启查询映射。P21 已准备 P21-RFC-005，但没有替 P13 选字段、替 P20 放宽校验或合并任何 UI 源码。

## 接线后应保留的行为

提交前保留原意图、ID、hash、原实例/连续性/revisions。COMMITTED 后以同实例当前一致视图展示结果；响应丢失则查询原事务。UNKNOWN、存档回滚、锚点缺失、迁移/恢复冻结时保留未决操作并暂停新的经济操作。不能清空浏览器未决记录、生成新 ID 或用新空存档确认旧操作不存在。

精确恢复不回放奖励；旧备份恢复保持隔离待核对。领域操作返回 CANDIDATE 仍不能显示成功；UI 不直接授奖/扣款。P21 的物理层错误可映射为现有只读提示，但具体 UI 版本改变由 P20 owner 执行。

## “正式已入账”仍未启用

P21 回执原始 origin 固定为 `P21_SQLITE_ISOLATED`。P11 旧模型的允许枚举只有生产/模拟，本包兼容投影固定 `P21_SIMULATOR`，即使 durable=true 也只能说明隔离存储写入成功。

真实事件、账号/collection/inbox、计奖策略、可信 authority、P11↔P17 原生钱包映射、当前可用钱包与 Undo 状态的一致读取尚未形成获批生产链。本包未运行真实 Anki，P20 “正式已入账”分支继续 BLOCKED。

## 接收工件

完整包中的 P21_API.md、runtime/persistence/p21_persistence/adapters.py、test_contracts.py、test_native_crash.py、interface_rfcs.json 及 recovery_logs/author_final_002/。本回复不是 P20 已确认接收，也不是 P32/P35 已验收；接收状态仍 PREPARED_NOT_ACKNOWLEDGED。
