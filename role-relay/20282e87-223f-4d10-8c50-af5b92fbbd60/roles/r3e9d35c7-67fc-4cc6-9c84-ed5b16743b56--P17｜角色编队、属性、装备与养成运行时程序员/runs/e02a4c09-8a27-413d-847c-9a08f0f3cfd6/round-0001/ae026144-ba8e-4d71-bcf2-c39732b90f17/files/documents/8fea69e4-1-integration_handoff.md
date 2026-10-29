# P17 下游接收与集成说明

交付版本 `P17-META/0.1.0-isolated`。本文件供用户后续指定的 EXT-INTEGRATOR 与 P15/P20/P21/P32/P33/P35 使用。全部接收记录为 PREPARED_NOT_ACKNOWLEDGED；没有代签任何岗位。

## 已有证据与接收顺序

先保留本包及包外 delivery_receipt.json，核对 ZIP 的大小／SHA，再解压运行 `tools/verify_delivery.py`。逐文件清单不包含自身；清单自身和 ZIP 由包外回执绑定，避免循环哈希。

运行作者测试、原 P13 契约检查、完整示例回放和跨进程确定性检查。保留新的独立输出，并与 `evidence/runs/author_final/`、`contracts_final/` 等原始记录区分。作者通过不能替代 P32 与 P35 的独立结论。

正式接入前运行 `tools/preflight.py`。本版返回 exit 3 是预期的阻塞状态，不是需要删除的报错。四条正式路径全部未映射，P21 实现未收到；没有可通过改一个布尔值解除的放行捷径。

## 接收方与具体输入

| 接收方 | 接收的实体文件／数据 | 下一项职责 |
| --- | --- | --- |
| P13 | `actual_path_request.json`、`interface_rfcs.json`、`wallet_delta_contract.json`、`P17_API.md` | 裁定正式路径、DTO、复合候选 resolver 与容量边界；保留双方 base SHA |
| P21 | `character_party_runtime/`、`runtime/meta/`、`wallet_concurrency_tests.py`、候选实例及事务说明 | 实现权威快照、原子提交、唯一键、durable lookup、备份连续性；不能只存 WalletDelta 投影 |
| P11 | RFC-P17-003、来源会计实现、学习撤销测试 | 处理 RewardIntent／source_after 的无损适配与 P08 政策；学习资格仍由 P11 决定 |
| P18 | 来源唯一键、授予／成本输入提案、首通及重复领取测试 | 提供已验证终局与预算引用；将阶段状态与钱包纳入同一事务 |
| P15 | `examples/party_export.json`、`examples/p13_party_snapshot.json`、P04 原关联表 | 接收角色／技能／专属卡引用；构筑与抽弃牌仍由 P15 负责 |
| P20 | 属性读取 API、只读 Party／Wallet 输出、错误码 | 绑定角色养成 UI；界面只能提交命令，不能直接改余额或等级 |
| P04/P05/P22 | 受保留原件、装备测试说明、内容指纹 | 审核正式成长成本、装备／角色数据、全球 ID 与 Schema；测试数值不能直接发布 |
| P32 | 全部源码、夹具、作者日志、4 个缺陷修复证据 | 独立运行、补充真实持久化与接口测试；测试失败返 P17 修复 |
| P33 | 可运行 Python 示例及实际行为表 | 待目标客户端可运行后执行人工流程验收；本轮不代签 |
| P35 | ZIP 回执、来源收据、逐文件清单、分层状态、失败记录 | 独立证据门禁；不得用作者日志替代独立结论 |
| EXT-INTEGRATOR | 完整 ZIP 与全部 RFC | 只有用户明确委派后才能合并；本包不指定该人员身份 |

带实际大小和 SHA 的逐项交接记录在 `downstream_receipts.json`。这些记录只表示工件已准备，未表示已发送外部消息或接收者已确认。

## P21 接线必须保留的一体性

角色升级候选同时改变角色等级、对应来源 available/spent、消费凭证、wallet_revision、领域 revision 和 request receipt。只有所有内容一起成功才可发布成功回执。失败后不得出现扣钱而没升级，也不得出现升级却未记成本。

P21 应在同一权威快照下调用 `validate_for_commit`。它会重验请求指纹、profile、store、continuity、两种 revision、内容哈希和外部证据，并重新计算后态逐字节比对。不要直接对 candidate.after_state 赋值后再异步补校验。

P17 给出锁顺序建议，但本包没有数据库行锁或跨进程锁。实际锁粒度由 P21 实现并验证，不得以测试模型中的单个 RLock 推导数据库已经安全。

授予、首通、学习撤销、关卡消费等跨域事务还需要 P11/P18 的对应候选。单独调用 `atomic_proposal` 会明确拒绝；内存测试使用的 synthetic_counterpart 只是测试模型参数，生产端不得接收同名自报开关。

提交超时后的处理是查原 request_id／transaction_id。返回 UNKNOWN 时保持未知，禁止换 ID 再领一次。P21 必须在持久介质中保留去重信息，并在重新启动或旧备份加载时维持连续性。P17 的哈希不能代替这些物理保证。

## 已有接口差异

### P11 学习账本

原 P11 端口要求 compute(RewardIntent, wallet_snapshot) 返回自己的 WalletDelta 或 WalletHold；其 source_after 含会计源状态。本包基于 P13 的钱包投影并新增完整候选模型，两者尚未无损接合。不能删掉 source_after，也不能把 P11 的家庭状态写进 P17 的任意 JSON 字典后当成批准合同。

需 P11/P17/P13/P21 联合确认原始操作键／家族键、政策快照、来源凭证、恢复授予及未解决权益的映射。已消费撤销继续 BLOCKED，未引入未来债务、免费补偿或追溯取消角色。

### P13 战斗编队

原 PartySnapshot 的 EntityStats 缺 support、技能、装备和 P03 卡池关联。本包交两个投影：完整 P17 导出与原 P13 兼容 DTO。P15/P14 不得自动使用 support 放大卡牌效果，也不得把 P03 mock ID 当 P22 正式注册 ID。字段扩展通过 RFC-P17-004 处理。

### 装备与正式内容

P04 原稿明确 DEC-009 未批、装备默认关闭。本轮只在独立合成配置中完成装备运行机制测试。不要把 TEST_P17_BLADE 等测试定义导入正式内容库，也不要沿用测试加成当正式平衡值。

装备开关和所有定义纳入内容哈希。如果采用新内容，需要明确迁移合同及 P21 受理，不能为通过校验而手动改旧 snapshot.content_sha256。

## 已观察缺陷与修复边界

本轮边界测试实际发现 4 个 P17 缺陷：低层模块直接导入的循环依赖、长账号 ID 拼接导致 P13 ID 超长、坏权益 key 在去重前引起 TypeError、缺角色字段引起 KeyError。均由 P17 修复，保留 `boundaries_001` 的失败日志／源码与 `boundaries_002` 的通过日志，并在 `author_final` 全量回归。

这些缺陷的状态是作者修复并验证，不是 P32 复测或 P35 关闭。另有一次交付元数据复制路径错误，已据文件枚举修正；记录在 evidence/build_notes.json，不计入运行库单测缺陷。

## 未解除事项

具体缺失文件、版本、责任方及解除证据在 blockers.json。主要为：P13 正式路径／引擎／目标环境；P21 真实存储 API；P11 与 P18 对输入及联合事务的接收；P01/P08 对 DEC-001/002/003/009 的决策；P22 正式内容；P32/P33/P35 独立验收。

无学习日基础可玩策略和免费起始牌仍没有已批准政策。测试中的空状态没有免费奖励，原有资源的隔离操作也不以学习天数作隐含判断；这两点不能替代最终产品政策。

生产容量同样未放行：隔离状态有 P13 1 MiB 和数组技术界限，不能通过删除老请求凭证来降低大小。分段、压缩、历史保留与旧存档迁移必须由接口 owner 和 P21 承接。

本包没有改动原 P04/P05/P11/P13/P16 字节，没有改卡牌、敌方 AI、战斗状态、人物原画或 UI；没有执行 GitHub 写入、跨模块合并或最终发布。
