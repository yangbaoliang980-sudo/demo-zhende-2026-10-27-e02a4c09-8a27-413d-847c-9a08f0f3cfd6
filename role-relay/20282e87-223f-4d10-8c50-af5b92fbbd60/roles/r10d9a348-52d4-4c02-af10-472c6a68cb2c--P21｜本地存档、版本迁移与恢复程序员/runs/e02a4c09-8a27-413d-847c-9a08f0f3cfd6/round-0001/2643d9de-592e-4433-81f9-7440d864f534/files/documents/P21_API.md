# P21 持久化 API：0.1.0-isolated

状态：作者实现和隔离验证；IC-19 的本岗实现版本，不代表 P13/P11/P17/P18 已接受新契约。相关变更申请见 `interface_rfcs.json`。唯一物理写入 owner 为 P21。

## 1. 入口与受信任边界

```python
from p21_persistence import (
    Store, Record, Request, Update, Mutation, Claim,
    Snapshot, SaveError, CommitUnknown, digest, encode, decode,
)
```

包路径为 `runtime/persistence/p21_persistence/`。本包工具通过 `tools/bootstrap.py` 加入此路径，并引用 `sources/` 中逐字节保留的原领域代码。正式装配路径需 P13 审定；不能直接覆盖一个已有 `runtime` Python 包。

API 是本进程受信任代码端口。外部 JSON、UI、Anki 通信不得传入 Python 回调、路径、校验器或自报的 owner 来取得写权限。领域适配器与路径由受信任装配层创建。`Store` 不提供 HTTP、IPC、自动寻找 Anki 数据库或扫描用户文件的能力。

## 2. 创建、打开和一致读取

```python
Store.create(directory, anchor_path, records,
             profile_id=..., store_instance=None, continuity_ref=None,
             schema_version=2, mode="isolated") -> Store
Store(directory, anchor_path, expected_store_instance=...,
      reader_version=2, fault=None) -> Store
store.snapshot() -> Snapshot
store.read_consistent(project) -> object
store.status() -> dict
```

`create` 要求保存目录不存在或为空、外部连续性记录不存在、父目录已明确创建。需要提供 ledger/meta/stage 三份经 owner 初始化的完整 `Record`。初始化不决定角色数量、币种、初始收益或正式内容。`mode` 只接受 `isolated`，不能用参数打开生产模式。当前观察环境之外的平台尚未受理，Windows 明确拒绝。

`Store(...)` 只打开已存在的指定数据库，不创建空存档、不重置连续性文件。`expected_store_instance` 必须与保存标记、数据库和连续性记录一致。`anchor_path` 必须位于保存目录之外；它不能来自备份 manifest 或 UI 自报字段。

`Snapshot` 含 `store_instance`、`continuity_ref`、`profile_id`、`sequence`、`schema_version`、`state_sha256`、`chain_sha256` 和只读 records 映射。每个 Record 的 payload 是不可变规范 JSON bytes；`.value` 返回新的 Python 对象。`read_consistent` 的投影函数在同一次锁定读取中执行，必须是纯函数。读取期间所有领域、回执与 head 同一版本。

`status()` 返回 READY、MIGRATION_REQUIRED 或 RECOVERY_REQUIRED，并带原因码、实例和高水位。故障时不伪造余额或实例。`adapters.p13_status` 用原 P13 validator 输出 SaveStatusView；物理迁移待处理投影为 READ_ONLY。

## 3. 一个业务事务如何提交

```python
request = Request(
    transaction_id="owner.tx.stable-id",
    request_sha256=original_request_sha256,
    kind="STUDY_LEDGER_WALLET",
    expected_store_instance=trusted_instance,
    expected_continuity_ref=trusted_continuity,
)

def decide(snapshot):
    # 在此调用领域 owner 的纯计划/校验端口；不做网络、UI 或其他写入。
    # 由 owner 提供完整 after Record；不得自行计算奖励规则。
    return Mutation(
        updates=(Update(ledger_after, snapshot.records["ledger"].sha256),
                 Update(meta_after, snapshot.records["meta"].sha256)),
        claims=(),
        result={"owner_result_reference": "approved-domain-result"},
    )

answer = store.execute_once(request, decide)
```

上例是 API 结构示例；可执行业务样例见 `tools/run_demo.py`。不要复制示例 ID 到实际业务。

### 3.1 记录与事务类型

| kind | 允许更新 | 必须更新 | 原因 |
| --- | --- | --- | --- |
| STUDY_LEDGER_WALLET | ledger、meta | ledger | 隔离/拒绝可没有钱包变化；有收益时必须由绑定的 P17 端口产生 meta |
| CHARACTER_WALLET | meta | meta | 角色/队伍/钱包在 P17 完整文档中同写 |
| STAGE_PROGRESS_WALLET | stage、meta | stage | 入场或隔离可无钱包变化；奖励由原 P18/P17 联合候选给出 |
| SCHEMA_MIGRATION | 内部维护 | 不由调用者提交 | 只允许内置逐版本迁移执行 |

每个更新的 owner 与领域 schema tag 必须不变，revision 恰好 +1，before SHA 必须等于锁内当前值；同一事务不能更新同一个文档两次。`Mutation.result` 必须是 JSON object，非法值在写入前拒绝。领域 schema 变更需 owner 新版本迁移，不借物理升级修改业务字段。

`Claim(namespace, key, semantic_sha256)` 是永久防重键。在 `(profile_id, namespace, key)` 上有 SQL 唯一约束；P18 首通使用其原始新首通 key，绑定关卡稳定身份，不把 battle_id 当首通身份。已有相同语义返回 E_CLAIM_ALREADY_CONSUMED，语义冲突返回 E_CLAIM_COLLISION，整个事务回滚。

### 3.2 实际时序

1. 获取跨进程文件锁；检查标记、SQLite、所有文档校验和、回执链和独立连续性记录。
2. `BEGIN IMMEDIATE`；校验请求实例与连续性围栏。
3. 已有相同 ID/原请求 hash/kind 时直接返回原回执，不再次运行 decide；冲突则拒绝。
4. 调用 owner 校验/决策；检查完整 after 记录、revision、before SHA、记录集合和首通键。
5. 在同一 SQL 事务写文档、claims、回执、sequence 和 state/chain head。
6. COMMIT。随后以临时文件、fsync、原子 replace、父目录 fsync 更新独立连续性记录。
7. 完成上述步骤才返回 COMMITTED。COMMIT 结果不确定或提交后响应路径失败时返回 E_COMMIT_UNKNOWN；不会谎报 ABSENT。

SQLite 配置固定为 `journal_mode=DELETE`、`synchronous=EXTRA`、`foreign_keys=ON`；本轮在实际 Linux 环境进行了目录同步与锁探针。硬件断电、存储控制器行为和目标 Windows 文件系统尚未验证。

## 4. 查询与回执

```python
store.lookup(transaction_id, request_sha256=None) -> dict
adapters.p13_lookup(store, transaction_id, request_sha256=None) -> FrozenMessage
```

| 查询状态 | 含义 | 调用者动作 |
| --- | --- | --- |
| COMMITTED | 在已校验连续性实例中找到原持久回执 | 展示原结果；读取同实例当前视图；不重复授奖 |
| ABSENT | 在可验证连续性范围内确认此 ID 不存在 | 仍须上游使用同一原请求和身份处理，不能自行重建业务事件 |
| UNKNOWN | 存档冻结、损坏、回滚、身份缺失或读取不可确认 | 保留原意图/ID/hash，冻结新的经济操作，等待恢复或核对 |

`lookup` 的 `proof` 含 `receipt`、`receipt_sha256`、`chain_sha256`。回执含原请求 hash、事务类型、实例、连续性引用、profile、提交序号、前后 state hash、前 chain、schema、三个 document heads、领域结果引用、origin、durable。文档 `schema/save/P21_commit_receipt.schema.json` 定义物理形状；数值范围、规范 bytes 和跨记录关系另由运行时代码校验。

回执中的 origin 固定 **P21_SQLITE_ISOLATED**。`durable=true` 不是计奖资格证明、Anki 事件真实性或生产授权。回执 SHA 是完整性校验，不是签名。外部调用者不能凭一个自报 JSON 对象取得经济权限。

查询同一 ID 时如果提供了不同原请求 hash，返回 E_TRANSACTION_ID_COLLISION。只查询 ID 的兼容端口适合 owner 已持有事务映射的场景；P20 外层 UI request ID 到领域 transaction ID/hash 的映射仍待固定，不能推导为已经接线完成。

## 5. 原领域适配器

### P17CommitAdapter(store, planner).submit(candidate, proposal=None)

使用未修改的 `character_party_runtime.atomic_proposal` 与 `MetaPlanner.validate_for_commit`。提交前重新计算原始 request hash；可选 proposal 必须和原候选生成的投影逐字节一致。仅接受自足 CHARACTER_WALLET 候选；需要 P11/P18 对应方的候选由原 P17 规则拒绝。锁内再校验当前完整 meta，角色与费用同文档提交。

### P18CommitAdapter(store, planner_factory, wallet_factory).submit(bundle)

完整 bundle 必须包含原 P18 stage candidate、原 P17 wallet_character_candidate 和原 P13 projection。提交前校验 projection、原请求 hash 及确定性事务 ID；锁内调用原 `validate_atomic`。

两个 factory 接收同一个 P21 Snapshot，并返回纯校验器。必须绑定同一读取时点的受信任 P13/P14 证据。`StoreFenceAuthority` 提供实际持久 stage 的实例/版本/hash；入场证据的 `party_source_sha256` 必须等于当前完整 meta hash。这个额外防过期检查已写成 RFC，未修改 P18 源码或让 UI 自报权威。

### P11AtomicAdapter(store, wallet_binding=None)

实现原 `AtomicStudyStore` 风格的 snapshot、lookup、execute_once。原 P11 状态机在锁内决定 Mutation，P21 调用原 `verify_audit`，只负责完整 ledger 与 meta 同写。

`wallet_binding` 需由 P17 提供：

```python
project(meta_record: Record) -> dict
materialize(delta, meta_record: Record) -> Record
validate(delta, before: Record, after: Record) -> None
```

当前默认 `UnboundLegacyWallet` 返回 **E_P11_P17_WALLET_BINDING_UNBOUND**。P11 旧 source accounting 与 P17 来源批次 schema 存在真实差异，未获得无损映射，不得静默插入一个新钱包或省略账务信息。测试绑定仅在 `tests/save_unit/support/`，runtime 不导入测试模块。

原 P11 CommitReceipt 只接受 `P21_PRODUCTION` 或 `P21_SIMULATOR`。本适配器将真实隔离 SQLite 回执投影为 `P21_SIMULATOR`，禁止声称生产。此限制已作为版本化 RFC；P20 的正式到账分支不受启用。

## 6. 备份、迁移与恢复 API

| API | 前置与结果 |
| --- | --- |
| store.backup(destination) | 新的保存目录外路径；一致读取 + SQLite backup；封印完成后返回 BACKUP_VERIFIED |
| inspect_backup(directory) | 只读验证封印、大小、文件 SHA、数据库、回执链；返回 manifest、Snapshot、原数据库 bytes |
| compare_backup(store, directory) | 比较身份、head、记录 revision/hash；不修改活跃数据 |
| stage_restore(directory, destination) | 新建 RECOVERY_REVIEW_ONLY 候选，FROZEN；不生成连续性权威 |
| store.recover_exact(directory) | 备份 head 必须精确等于独立当前记录；保留损坏原件/sidecar，原子替换、复核后解冻；不回放奖励 |
| store.migrate(backup_destination) | 若 v1：先完整备份，锁内重新比较 head，然后 DDL+审计+回执同事务升级到 v2；v2 返回 ALREADY_CURRENT |
| rehearse_migration(directory, destination) | 在备份副本上执行 v1→v2，原件不变；结果保持冻结审查状态 |

恢复命令不提供 `--force`、丢弃未知事务、重设高水位或跳过校验开关。读到旧版不兼容时禁止写入；`reader_version=1` 不能读取已升级 v2。

## 7. 错误与上层行为

`SaveError.as_dict()` 包含 code、detail、retryable。CommitUnknown 是专用子类。P11 兼容端口按原接口转换为 PortViolation 或原 CommitUnknown，不改原 P11 定义。

| 错误类别 | 代表 code | 含义与处理 |
| --- | --- | --- |
| 结果未知 | E_COMMIT_UNKNOWN | 可能已经提交；查询原 ID/hash，暂停新增经济操作 |
| 容量/锁 | E_DISK_FULL、E_BUSY | 本次不能确认成功；释放资源后仍按原事务查询/重试；提交后锚点满走 UNKNOWN |
| 候选失效 | E_STALE_RECORD、E_RECORD_REVISION、E_ENTRY_META_SOURCE_STALE | 重新读取并交给 owner 规划；不能偷偷改候选 hash |
| 身份/重复 | E_REQUEST_FENCE、E_TRANSACTION_ID_COLLISION、E_CLAIM_COLLISION | 拒绝；保留原输入和差异，交原 owner |
| 数据完整性 | E_CORRUPT、E_RECORD_CHECKSUM、E_RECEIPT_CHECKSUM、E_STRUCTURE_CORRUPT、E_MIGRATION_AUDIT | 冻结写入、只读保全、差异分析 |
| 连续性 | E_CONTINUITY_MISSING、E_CONTINUITY_MISMATCH、E_ROLLBACK_DETECTED、E_CONTINUITY_FORK | 不得新建权威或返回确认缺失；恢复/核对 |
| 冻结/版本 | E_FROZEN、E_READER_TOO_OLD、E_MIGRATION_REQUIRED、E_SCHEMA_TOO_NEW | 禁止写入；按版本与恢复流程处理 |
| 越权/未绑定 | E_PRODUCTION_NOT_AUTHORIZED、E_PLATFORM_NOT_PROBED、E_P11_P17_WALLET_BINDING_UNBOUND | 保持 BLOCKED，等待指定 owner 输入 |
| 恢复损失 | E_DATA_LOSS_OR_FOREIGN_RESTORE_BLOCKED | 仅可阶段化审查；P01/用户授权及领域对账后另交付实施版本 |
| 包装错误 | E_MUTATION_RESULT、E_JSON_*、E_IDENTIFIER、E_DOMAIN_SCHEMA_TAG | 拒绝整个候选；修复调用端，不截断或宽松纠正 |

可信 owner 的计划/校验异常会在事务退出时回滚并传播原异常，方便原 owner 定位；调用层应记录并冻结该业务尝试。P21 不把业务拒绝改写成新的奖励决定。

## 8. 已知容量和信任限制

单个规范 JSON 最大 1 MiB，深度 32、节点数 100,000、整数绝对值不超过 2^53−1。三个完整文档随历史增长，claims 的 state hash 编码也受 1 MiB 约束；数据库备份读取上限 128 MiB。当前每次操作完整校验历史，性能随历史长度增长。未做长周期容量验收，不承诺正式存档寿命；不能通过清理防重记录擅自优化。

本实现依赖所有游戏物理写入通过 P21、可靠的本地 SQLite/文件系统同步，以及装配层保护外部连续性记录。它不防持有系统文件写权限者重写整个数据库与锚点，不处理整盘同时回滚。相应改进必须由 P13/P34/P36 提供目标环境，P01 与相关 owner 审批范围。
