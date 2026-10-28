# P11｜对账、故障恢复与下游复现说明

本页适用于本独立候选包。生产P12/P17/P21适配尚未提供；以下命令不连接Anki或游戏。

## 可直接执行

环境：Python 3.11及以上；本轮实际为Linux、Python 3.12.14、SQLite 3.53.1。只使用标准库。先解压完整包，在包根运行：

```bash
python -B -m ledger_runtime preflight
python -B -m unittest discover -s tests -p 'test_*.py' -v
python -B -m verification.replay --output /tmp/p11-replay-review
python -B verification/verify_delivery.py
```

第一条正确结果是BLOCKED、退出码3。测试和重放成功退出0，只证明本地业务及模拟端口行为。最后一条检查逐件大小及SHA-256，不能证明功能。不要把前置检查退出3改成0以制作“全绿”报告。

`verification.replay`读取`event_replay_fixtures.json`的26个合成场景。每步保留输入动作、实际输出、状态和钱包值，每场景保留最终账本、来源审计、钱包和提交凭证。`compensation_log.jsonl`是其中实际运行产生的撤销/恢复与未决差额记录，所有条目都标有模拟范围。

## 收件后异常退出

若只有接收事务已提交，收件箱仍有PENDING_RECONCILIATION记录，钱包未增加。重新打开P21适配器后调用`process(inbox_id)`，继续使用同一稳定处理事务ID。没有收件凭证时，发送方继续保留原输入。不能从日志里猜一个新event_id重新投递。

## 原子处理过程中退出

测试在以下6处实际执行`os._exit(71)`：持久接收之后、写账本之前、写账本之后钱包之前、写钱包之后COMMIT之前、COMMIT之前、COMMIT之后回复之前。父进程确认子进程退出且未输出ACK，然后重新打开测试数据库并重投同一事件。

前5处重开后未出现半笔奖励；最后一处重开前权益已提交，重放查询原凭证且不增加第二份。原始观察在`evidence/author_run_003/unit.stdout.log`。这些是进程崩溃测试，不是断电、磁盘损坏或Windows文件系统验证。

## 提交结果不明

先查询原tx_id。COMMITTED则核验原凭证并返回当前族状态；权威ABSENT允许用原tx_id重试；UNKNOWN保持无授奖ACK，不能以新tx_id“补发”。接口异常也不能作为未提交的证明。

本地回放`P11-REPLAY-023`实际模拟了提交成功但回复丢失：第一次结果ack=null，钱包10；恢复权威查询后重投仍是10。

## 隔离释放

先用`pending_cases()`获取案件及当前版本。补充材料必须由原owner出具，并固定源输入哈希、适用epoch/环境、批准政策或P21提交回执。可信EvidencePort将复核证据绑定到原输入、案件版本和具体动作后，调用`resolve`。任何字段缺失、错误目标或版本过期都不能直接改APPLIED。

`P11-REPLAY-016`演示：缺政策→持久隔离→进程重启→补齐合成政策但普通重投仍隔离→绑定新增证据复核→一次入账。原隔离历史完整保留。

已消费撤销仍为待裁决；不存在获批豁免/抵扣合同则保持未决。解决UI或工具只能调用P11公开接口，不能修改case_index、钱包余额、来源归属或历史审计。

## 旧备份恢复

P21首先证明恢复边界并设置栅栏。P11只对比独立检查点、操作凭证和账本/钱包快照，不自行搬动存档。旧快照与外部水位不一致时，拒绝新的经济操作；如果存储不能安全记录隔离材料，应返回背压且无ACK，让P12保留待传事件。

P21恢复其权威副本或依据已批准合同完成对账后，保留旧分支，提供新连续性凭证，再恢复处理。`P11-REPLAY-024`展示了这个明确前提下的模拟流程。无外部证据的整盘回滚不能自动判定曾经发奖，必须BLOCKED；创建新的epoch、存档槽或空数据库都不能代替对账。

## 已消费权益审计

重点场景为`P11-REPLAY-012`。G/R/S/A/T/U/K/M的每一步取自模拟P17实际输出，再由P11验证，P21模拟事务一次写入。13条补偿/恢复记录可沿`inbox_id → reward_intent → atomic transaction_id → commit_receipts → wallet/source_after`追踪。

来源不明时见`P11-REPLAY-015`：已有余额保持不动，PENDING_RECONCILIATION。共享币种中其他来源保护见`P11-REPLAY-014`：额外来源100不因Anki Undo被扣除。

## 修复链及独立复测

`evidence/author_run_002/`保留5项实际失败及`failing_sources.zip`。这是修复前源码，不能集成。复现时将该ZIP解压到另一个目录，再按其run_receipt中的5个unittest名称执行。修复后的base/target SHA、原因和唯一修复owner在`defect_log.json`；当前完整51项作者测试为PASS。

P32应对正式适配后的固定提交独立复测并新增证据；不能把作者结果改名。P33执行目标机人工流程；P35分别审SPEC、UNIT、CONTRACT、RUNTIME、E2E。当前这些独立项均NOT_RUN。
