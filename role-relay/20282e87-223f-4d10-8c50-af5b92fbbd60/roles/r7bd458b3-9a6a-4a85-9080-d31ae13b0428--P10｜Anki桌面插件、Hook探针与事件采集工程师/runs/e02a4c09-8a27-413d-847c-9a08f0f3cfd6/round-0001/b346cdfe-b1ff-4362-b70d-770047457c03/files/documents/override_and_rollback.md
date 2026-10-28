# 人工覆写、改错与版本回滚

格式：P09-OVERRIDE/0.1.0-proposal。日志示例全为SYNTHETIC；时间为合成固定时间，不是用户操作记录。P09只提供语义和内存重放器，不替P21实现磁盘事务或用户认证。

## 覆写绑定

每一记录绑定scope_ref、subject_ref、profile_id/profile_sha256、observation_sha256、mapping_version/mapping_sha256。分类对象、模板、授权档案或字段内容改变，旧覆写不自动扩散。没有使用“词面字符串全局覆写”，避免同形异义词、不同模板和不同牌组互相污染。

日志字段还包括event_id、sequence、actor_ref、authorization_ref、reason_code、recorded_at、action、expected_head、before_category、after_category、target_event_id、previous_event_sha256、event_sha256。没有原始词条正文、邮件地址或完整牌组。actor_ref须由实际UI/权限系统证明；本包固定syn:actor仅为测试。SHA链可检测意外改动，**不提供身份签名、权限认证或防恶意重算的保证**。

## 三种追加操作

| 操作 | 结果 | 禁止情况 |
|---|---|---|
| SET | 明确设一个类别，含UNKNOWN | 非八类值；不匹配当前binding |
| CLEAR | 取消当前人工覆盖，回到规则；日志仍保留 | 删历史记录代替CLEAR |
| ROLLBACK | 追加一条事件，恢复同binding历史事件的after_category | 跨对象/跨快照/跨规则引用；不存在或未来目标；环形目标 |

每次追加需expected_head和before_category匹配重放结果，表示乐观并发检查；并发磁盘提交仍由P21实现。事件序号必须连续，event_id唯一；previous_event_sha256链连续；event_sha256为除自身外整条canonical JSON的SHA。

示例日志5条依次为：双词性项→NOUN；更正→VERB；回滚第1条→NOUN；CLEAR→按原始双词性规则UNKNOWN；人工明确UNKNOWN。作者测试逐条复现这五个状态，另测篡改、陈旧快照、模板变化、并发头冲突和跨对象回滚拒绝。

## 规则版本回滚

规则版本和原字节SHA必须共同固定。重新加载旧规则文件需校验这两个值；保留新旧文件，不覆盖旧版本。mapping_release_registry.json本次只有一个真实交付的proposal，active_production_version和previous_approved_version均null。

fixtures/rollback_rules.synthetic.json是人为制造的旧版本，仅为验证“旧结果→新结果→旧结果”一致性；它不代表存在历史正式映射。测试夹具省略adj-na别名，使对应输入在旧夹具UNKNOWN、当前候选NA_ADJECTIVE、恢复夹具再UNKNOWN。实际已批准版本回滚仍NOT_RUN。

真实启用时须由契约owner/P22固定注册版本，P01登记范围，P32独测并经P35相应门禁。激活旧版本只能改变获准的后续判定或复核预览；不能以旧事件+新分类/新规则构造第二次奖励。已经发放的学习权益保持原事件、原政策与原分类快照，需要转换类型或处理已消费权益时提交P08/P11/P17/P21差额流程。

交付冲突须记录本方base SHA、对方base SHA、ChangeRequest和接收owner，不覆盖式合并。同问题连续两轮返工无新证据升级P01。首次提案尚无正式base，RFC中的base_sha256为null，不填伪造零值。
