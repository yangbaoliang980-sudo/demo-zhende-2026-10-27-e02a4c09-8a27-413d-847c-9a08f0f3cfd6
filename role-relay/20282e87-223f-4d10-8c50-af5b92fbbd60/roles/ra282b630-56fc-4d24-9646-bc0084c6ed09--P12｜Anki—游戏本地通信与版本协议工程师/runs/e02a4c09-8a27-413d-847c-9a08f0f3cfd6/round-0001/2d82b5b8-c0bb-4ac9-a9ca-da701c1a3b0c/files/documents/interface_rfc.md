# P11｜IC-16 / IC-17 / IC-18 协作接口提案

版本：`P11-PORTS/0.1.0-proposal`。生产授权：false。所有接收状态：PREPARED_NOT_ACKNOWLEDGED。正式合同 base SHA 未取得，必须记 null，不能填写猜测版本或全零值。

## 向契约 owner 的具体请求

| RFC | owner | 已提交的具体内容 | 请求的固定输入 |
|---|---|---|---|
| P11-RFC-016-001 | P08，协同P01/P09/P22 | `PolicyPort`、PolicyDecision及不可变政策快照校验 | 获批PolicyRecord、范围/生效/原日、正式资源与映射、完整额度规则、撤销/恢复能力、批准原文哈希 |
| P11-RFC-017-001 | P11，协同P17 | RewardIntent→WalletDelta、操作/族唯一键、来源审计等式和补偿未决语义 | P17版本化接口、消费分摊证明、WalletDelta版本/CAS语义、跨币/豁免边界 |
| P11-RFC-018-001 | P12 | ACK_RECEIVED与五态结果候选、提交未知态、持久隔离及查询方法 | 正式认证/Schema、ACK含义、重发与背压、支持的查询错误、outbox清理条件 |
| P11-RFC-P13-001 | P13 | 本地Event、快照、Intent/Delta/Receipt DTO提案与路径请求 | 游戏实际技术栈、内部DTO映射、actual_path_mapping、所有权白名单 |
| P11-RFC-P21-001 | P21，关联IC-19 | `execute_once/lookup/snapshot`原子端口提案、收件/钱包共事务及恢复栅栏要求 | 真正持久回执、唯一键、冲突处理、serializable或等价CAS、旧备份权威检查点 |
| P11-RFC-P10-001 | P10，经P12 | 消费可信来源操作、修正族、因果链和epoch证据，不自造Anki身份 | 目标版真实原始事件Schema及四键/Undo/恢复/自然重复/旧备份证据 |

## 本地调用接口

完整可执行定义在 `ledger_runtime/types.py` 和 `ledger_runtime/ports.py`。

```python
StudyLedger(store, wallet, evidence=None, policy=None)
service.receive(raw_bytes)                 # 持久收件；尚未授奖
service.process(inbox_id)                  # 业务判定及原子提交
service.handle(raw_bytes)                  # receive + process
service.query(inbox_id)                    # 只读当前状态与权威凭证
service.pending_cases()                    # 持久案件索引
service.resolve(inbox_id, evidence_ref, action="REPROCESS")
service.reconcile(independent_checkpoint)  # 只读；不恢复物理存档
```

`EvidencePort` 与 `PolicyPort` 默认关闭。输入报文不能自行声明可信，也不能通过把proposal中的`production_authorized`改为true启用正式奖励。可信接入层须校验授权工件原字节、适用来源/epoch/版本、目标环境、批准记录及独立门禁。

Event只包含来源事实和不透明引用，不包含由客户端指定的奖励数量、余额或“管理员放行”布尔值。本地JSON使用语义Again/Hard/Good/Easy，不能据此推断真实Anki按钮编码。分类配置及日界/奖励数量归政策快照；同事件标签或政策变化不进入新权益键。

## P17计算契约请求

`compute(intent, wallet_snapshot)`须为无副作用纯计算，返回WalletDelta或WalletHold。WalletDelta绑定Intent哈希、权益族、政策快照哈希、钱包版本及完整前态哈希，并提供逐资源变化、来源审计后态和未决标记。只读来源未知不能用总余额替代；消费、豁免、抵扣或跨币转换不能偷偷由一个授奖/撤销Delta引入。

P11只校验必要守恒、方向、作用域和非负约束，不选择FIFO/LIFO、价格、奖励日、额度、舍入或负债政策。预算和存储上限在Policy/P17/P21真实适配中必须同事务验证；本包不把`budget_ref`字符串当作已经实现额度算法。

## P21原子契约请求

1. 持久收件必须在发任何持久接收ACK之前完成；失败/容量不足则背压，无ACK。
2. 同一交易身份的同一请求幂等；同身份不同请求哈希必须冲突，不能覆盖。
3. `decide(snapshot)`看到同一可串行化账本/钱包/恢复水位；回调失败不产生副作用。
4. 账本、钱包、来源权益、补偿审计、提交凭证一次提交。多消费者、消费者重启及提交后响应丢失仍遵守唯一性。
5. `lookup`须区分COMMITTED、权威ABSENT、UNKNOWN；UNKNOWN不授权另开新交易补发。
6. 接收的提交凭证须绑定实例、交易身份、请求哈希、水位及账本/钱包摘要；凭证来源要经过真实适配器认证。
7. 恢复旧备份必须设置不可被该备份一并回滚的恢复/对账依据。无法证明完整性时不得静默创建空账本后自动发奖。

该回调提案不是已经冻结的P21架构；若owner拒绝回调方案，必须提供具有同等语义的候选+CAS接口并进行正式契约测试。当前SQLite模型属于`tests/support/`，不会由P11提供为正式存档适配。

## P12回执候选

| 候选 | 本地含义 | 是否允许把它当奖励到账 |
|---|---|---|
| ACK_RECEIVED | 原输入已持久收件，尚未处理 | 否 |
| ACK_QUARANTINED | 隔离材料有P21持久凭证 | 否 |
| ACK_PENDING_RECONCILIATION | 有持久待处理结果；可能有已批准部分回收，但差额未决 | 否 |
| ACK_REJECTED | 有持久拒绝记录 | 否 |
| ACK_REVERTED | 当前修正族已撤销且无未决差额，或有效墓碑 | 不是新增奖励 |
| ACK_APPLIED | 当前族权益有已核验P21提交凭证 | 只有正式适配器的真实凭证才可 |
| ack=null | 提交/查询/恢复连续性未证明，或输入超过本地边界未收件 | 否；发送方保留并重试/查询 |

ACK_QUARANTINED之后是否允许删除插件outbox副本，必须由P12/P10结合真实持久责任、故障恢复及留存政策决定；本提案不自行决定。P10现有QUARANTINED标志只是能力报告，不能被解析成一次已接收学习事件。

## 变更和接收

所有正式输入更换都需记录旧/新commit、路径和SHA-256及ChangeRequest。P11内核和本地DTO的下次版本不得覆盖上游源快照。需要不同权益归属、额外币种、未来抵扣或跨币转换时由相应owner裁决，不在适配器中默认上线。
