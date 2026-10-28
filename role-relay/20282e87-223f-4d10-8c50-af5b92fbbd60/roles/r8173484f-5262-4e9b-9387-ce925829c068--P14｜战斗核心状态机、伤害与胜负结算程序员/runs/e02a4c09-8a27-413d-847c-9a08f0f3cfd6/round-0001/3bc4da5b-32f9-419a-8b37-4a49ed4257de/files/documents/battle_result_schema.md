# BattleResult｜不可变终局结果

**领域 producer／唯一提交 owner：P14。形状 owner：P13。**

合同版本 `YLTT-INTERNAL/0.1.0-isolated`，Schema 位于 `upstream/P13/contracts/internal/internal_dto.schema.json` 的 `$defs/BattleResult`。本说明没有修改原 Schema，也没有定义存档格式或奖励策略。P14 交付版本为 `P14-BATTLE-CORE/0.1.0-isolated`。

## 字段

所有字段必填，未知字段拒绝；整数必须是 0..2^53−1 范围内的整数，bool 不作为整数。ID 按 P13 原正则／长度边界验证。

| 字段 | 类型／约束 | P14 的含义 |
|---|---|---|
| `contract_version` | 固定字符串 | `YLTT-INTERNAL/0.1.0-isolated` |
| `dto_type` | 固定字符串 | `BattleResult` |
| `result_id` | ID | `result:` + 确定性摘要；绑定场次、stage、profile 和最终快照 |
| `battle_id` | ID | 当前单场战斗身份 |
| `terminal_revision` | 正整数 | 产生终局的那次原子提交 revision |
| `terminal_event_seq` | 正整数 | `BATTLE_FINISHED` 事件的 seq；不是末尾 `COMMAND_COMMITTED` 的 seq |
| `outcome` | WIN／LOSS／DRAW | 反应队列排空后的互斥胜负 |
| `stage_id` | ID | 由可信装配入口冻结的关卡身份；当前样例属 fixture |
| `profile_scope` | ID | 由可信装配入口冻结的玩家／档案作用域；不是 UI 自报奖励身份 |
| `rules_version` | ID 型版本字符串 | 当前为 `P02-BATTLE-0.1.0-draft` |
| `content_version` | ID 型版本字符串 | 对应本场已冻结的隔离内容投影 |
| `final_snapshot_sha256` | 64 位小写 hex | 最终完整 **BattleSnapshot** 的 P13 规范 JSON bytes 哈希 |
| `replay_input_sha256` | 64 位小写 hex | 下述 P14 回放输入摘要；不是回放 JSON 文件的直接哈希 |

## 生成与唯一性

BattleResult 与 BattleState、命令回执、事件批次在同一次记录替换中可见。计算步骤为：效果 → 死亡 → 合法反应排空 → 双方活体数 → 单个 `BATTLE_FINISHED` → `COMMAND_COMMITTED` → 最终快照哈希 → 结果校验 → 一次性发布。结果不包含自身哈希，快照也不嵌套该结果，避免循环哈希。

WIN：至少一个玩家存活且所有敌人死亡。LOSS：所有玩家死亡且至少一个敌人存活。DRAW：双方全灭。没有先写 WIN 再覆盖 LOSS 的路径。

终局后的新玩法命令返回 ALREADY_CLOSED；原已接受命令的同指纹重试先返回 DUPLICATE_NO_OP，不产生新结果或事件。同 ID 改 revision 仍是不同指纹，返回 COMMAND_ID_COLLISION。

ABORTED 和 FAULTED **不产生 BattleResult**。从外部已闭合旧快照启动的隔离观察实例，如果没有原结果证据，`result()` 返回 None；不会推算或补造旧 `terminal_event_seq`／奖励结果。持久恢复和结果索引由 P21 的后续合同负责。

## 不可变与只读语义

运行库保存 P13 原 `FrozenMessage`，其 `raw` 为不可变规范 bytes。`value` 每次解析为新的普通对象，外部修改该副本不会影响已提交状态／结果。P14 把状态、结果、事件历史和回放条目装进冻结记录，最后只替换一次记录引用；P15／P16 没有写该记录的接口。

这是内存内的聚合原子性，不是数据库事务、磁盘落盘成功或防止恶意同进程 Python 代码访问私有成员的安全沙箱。结果不含奖励金额，不自动消费首通，不是 P21 CommitProof，也不是 Anki ACK。

## 哈希规则

P13 规范 JSON：对象 ASCII 字段名排序，数组保留顺序，UTF-8，无多余空白，无浮点、NaN、重复键或 Unicode 归一化。完整 BattleCommand 连同 `expected_revision` 一起计算指纹。

本包 `battle_snapshot.json` 原字节正好是 `snapshot.raw`，无末尾换行，因此文件 SHA-256 与样例结果的 `final_snapshot_sha256` 相同。其他美化 JSON 的文件 SHA 与对象规范 SHA 可能不同，交付清单记录的是**实际文件 bytes**。

P14 回放摘要采用如下明确格式，避免整个历史受单 DTO 1 MiB 上限限制：

```python
h = SHA256()
h.update(b"P14-REPLAY/0.1.0-isolated\x00")
for part in [canonical_header, *canonical_entries]:
    h.update(len(part).to_bytes(8, "big"))
    h.update(part)
digest = h.hexdigest()
```

header 包含初始 BattleState、不可变规则／内容投影、来源 SHA、stage_id、profile_scope。每个 entry 包含完整已提交命令、可信调用通道、实际使用的 P15／P16 候选及其 basis SHA、故障码。拒绝／重复／提交前中断没有业务变化，不进入该已提交回放链。任何动画状态均不进入 header 或 entry。

回放把记录的候选当作输入，重新执行费用、伤害、死亡、阶段和胜负；不从历史快照抄写结果。正常和反应上限故障均有实际回放测试。外部任意异常的因果输入若未取得，返回 `EXTERNAL_EXCEPTION_REPLAY_REQUIRES_ORIGINAL_CAUSE`，不能声称已重现未知异常。

## 消费与验证

P19／P29 显示以终局快照为准，不能因动画结束再扣血。P18 如需消费结果，需通过后续正式合同验证场次、版本、scope、stage、终局引用及防重复消费；钱包和物理事务仍属 P17／P21。

本包已执行结果不可变、快照 SHA、回放 SHA、终局唯一、同归于尽、致死阈值和关闭后无新敌行动的作者测试。P32 独立合同测试、P35 审核、P21 生产消费与 E2E 均为 NOT_RUN。
