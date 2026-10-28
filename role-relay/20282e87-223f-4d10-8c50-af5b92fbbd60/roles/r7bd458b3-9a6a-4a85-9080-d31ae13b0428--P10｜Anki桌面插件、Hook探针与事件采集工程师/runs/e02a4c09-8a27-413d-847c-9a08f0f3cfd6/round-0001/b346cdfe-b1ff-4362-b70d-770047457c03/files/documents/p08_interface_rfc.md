# P08｜版本化接口语义提案

任务：P08-S04-S05-POLICY-001。提案版：P08-REWARD-POLICY/0.1.0-proposal。所有行状态为PROPOSAL，接收状态为PREPARED_NOT_ACKNOWLEDGED。没有修改任何跨岗正式Schema。

## 接口清单

| RFC | 接口/owner | 本次请求 | 基线版本与base SHA |
|---|---|---|---|
| P08-RFC-014-001 | IC-14 / P12；事实来自P10 | 区分源事件身份、投递身份、来源世代、指纹、撤销目标、恢复/替换关系、目标Anki版本与能力回执；无法证明时明确UNVERIFIED | 正式Schema未取得；MISSING |
| P08-RFC-015-001 | IC-15 / P09 | 提供八类语义的实际字段可见性、确定优先级、UNKNOWN回退、人工纠正与映射版本；同事件换标签不重奖 | 正式映射未取得；MISSING |
| P08-RFC-016-001 | IC-16 / P08 | 本包提供政策索引、四键真值表、未签PolicyRecord、来源证据与数学期望；请求P11/P17/P32接收 | P08本次首提0.1.0-proposal；不是已存在正式合同 |
| P08-RFC-017-001 | IC-17 / P11；P17/P21协作 | 学习事实、授奖授权、实际提交分离；权益向量与原事务唯一关联；原族恢复差额、混合来源消费证据、撤销待裁决与配额同步提交 | 正式合同未取得；MISSING |
| P08-RFC-018-001 | IC-18 / P12 | 奖励日/补偿未决状态的只读查询语义；ACK_APPLIED与ACK_QUARANTINED仅凭对应P21持久回执；响应丢失查询原事务 | 正式ACK合同未取得；MISSING |
| P08-RFC-019-001 | IC-19 / P21，经P13接收内部DTO需求 | 证明来源消费分摊、同事务授奖/撤销与备份水位；恢复同一族的已保留量，禁止另开新存档重领 | 正式物理事务与内部DTO未取得；MISSING |

IC-14、IC-15、IC-16、IC-17、IC-18、IC-19、IC-20的owner取自本次核验的V6原文，详见source_input_receipt的SRC-V6。P08不能因提出RFC而取得P12/P13/P21的路径所有权。

## PolicyRecord候选最小信息（PROPOSAL）

需包含：政策ID及不可变版本；需求ID和决策ID；适用来源、集合/玩家权益作用域、事件类型与目标版本；四键语义与实际量；类别映射版本与正式资源ID；计量、舍入、存储上限、封顶与延期规则；原日策略；Undo/redo/已消费补偿选项；无学习日来源边界；生效/退役与追溯范围；能力证据、原始用户批复哈希及P01回执；P32/P35对应验收记录。

本包的JSON把这些未取得项目留为null，并显式`production_authorized=false`。不能通过把该布尔值改成true来完成批准；新版本还须验证来源、审批、能力、接口、路径、目标环境与独立证据。`CONFIRMED`约束与`PolicyRecord已批准`不可混为一谈。

## 契约测试消费说明（PROPOSAL）

`policy_cases.json`是逻辑输入/期望，不冒充P12正式消息。每例固定`execution_status=NOT_RUN`；P32必须在收到正式字段映射与实现提交后创建执行适配与独立结果，不把本包的静态校验结果改名为运行结果。真实契约不支持的条件应报告BLOCKED并回报owner，不能悄悄删掉期望。

`compensation_arithmetic_cases.json`只验证数学等式和边界，不处理事件队列、状态持久化、幂等锁或钱包含义。跨进程实现、竞态、崩溃恢复、世代变化和旧备份都需要P32独立运行证据。

## 冲突与接收（CONFIRMED）

收到替代输入后记录原SHA与新SHA、源commit/路径、原因和ChangeRequest。未签合同的base_sha为null/MISSING，不得填零值或猜commit。保留上游文件原字节，不直接改P09分类、P10采集、P11账本、P12协议、P17钱包、P21存档或P07关卡配置。整合需用户指定EXT-INTEGRATOR和P13实际路径映射。
