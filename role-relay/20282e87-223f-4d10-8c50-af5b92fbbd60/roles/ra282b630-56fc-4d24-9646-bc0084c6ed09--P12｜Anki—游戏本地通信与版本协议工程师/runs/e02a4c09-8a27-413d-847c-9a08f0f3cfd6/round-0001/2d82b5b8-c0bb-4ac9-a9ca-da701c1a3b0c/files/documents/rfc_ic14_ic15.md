# P10｜IC-14 / IC-15 来源证据接收提案

版本：P10-RFC-IC14-IC15/0.1.0-proposal。任务 P10-S04-PROBE-001。状态 PROPOSAL / PREPARED_NOT_ACKNOWLEDGED。IC-14 owner=P12；IC-15 owner=P09。关联 P08-RFC-014-001 及 P09-FIELD-OBS/0.1.0-proposal。

正式 P12 Schema、版本和 base SHA 均为 null / NOT_RECEIVED；本文件不替代已有合同，不在其他岗位路径定义 DTO/Envelope。P09 建议的输入仅供分类，不能承担复习事件唯一性。

请求 P12 接收的语义边界是：区分真实源事实身份、技术投递身份、Undo 目标、恢复/替换关系、来源谱系、版本及可观察性回执。目标版、来源世代或 Undo 关联未证明时，必须能表达不可验证；不通过时间等待、换消息版本或重新生成 UUID 解禁。具体命名、类型、序列化、兼容性、认证和 ACK 由 P12 冻结。

当前参考提交有 state_did_undo，却没有声明 state_did_redo/state_did_revert。通用 operation_did_execute 不接收完整 Undo 返回结构。P12 不应先冻结依赖不存在 Hook 或假设字段的正式合同；需在目标版真实样本到齐后接收 P10 证据。counter、last_step、revlog 标识等能否进入身份构造须 P10 证明、P12/P08/P38/P01 接收，当前未选择任何策略。

未来 outbox ACK 必须以 P12 获批语义和持久接收证明为准，ACK_QUARANTINED 不等于已发奖。捕获前崩溃缺口不能用 outbox 重试掩盖。当前没有传输消息样例；sample_inventory.json 的空数组不能被转换为有效事件。

请求 P09 接收：目标字段仍未观察，GameCategory/StudyUnit/品詞 等来自其合成档案，P10 不据此假定真实字段存在。待获准的 note type/template、最小类别标签和字段状态取得后，按批准版本提供脱敏快照；默认不读取 lemma/context 或整套笔记内容。

隐私与字段扩权由 P38，政策与修正族语义由 P08，用户决策与范围登记由 P01；本岗不能批准这几个方向的变更。正式工程路径由 P13 提供，跨模块整合仍由用户指定的 EXT-INTEGRATOR 负责。

本次只将该提案写入交付包，未通过邮件、Slack、GitHub issue 或 PR 发给其他人。未来收到冲突输入时保留双方 base SHA 和具体 ChangeRequest；未知 base SHA 保持 null，不能填全零或伪造旧版本。
