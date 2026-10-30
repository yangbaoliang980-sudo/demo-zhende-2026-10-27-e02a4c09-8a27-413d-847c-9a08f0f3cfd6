# P20 学习状态 UI 测试与边界

任务 `P20-S05-S06-S07-METAUI-001`。本文件区分实际作者验证、正式数据接入和独立验收。实际逐项结果以 `verification_status.json` 及 `evidence/` 原始输出为准。

## 状态映射

| 输入 | 已实现的显示 | 能否称为正式到账 | 本轮证据 |
| --- | --- | --- | --- |
| 未连接且无 query | Anki 未连接；尚未取得可核验记录 | 否 | JS + 浏览器 |
| 连接可用且无 query | Anki 连接可用；尚无查询记录 | 否 | 原生成夹具 + JS |
| APPLIED + P21_SIMULATOR | 测试记录已处理 | 否，即便模拟 SQLite receipt.durable=true | 原 P11 query、JS、浏览器 |
| APPLIED + 自报 P21_PRODUCTION | 待核对提交证明 | 否；正式受信任适配缺失 | JS 拒绝反例 |
| 正式 APPLIED + 已接受的一致读取/提交证明 | 预留“已入账”需求；当前不启用 | 需要正式适配后验证 | **BLOCKED：P11/P13/P21** |
| QUARANTINED | 待核对 · 已隔离；未计入可用奖励 | 否 | 原 P11 query、JS、浏览器 |
| PENDING_RECONCILIATION | 待核对 | 否 | 原 P11 query、JS、浏览器 |
| REJECTED | 已拒绝；保留原因 | 否 | 原 P11 query、JS、浏览器 |
| REVERTED | 已撤回；余额以当前钱包为准 | 否 | 原 P11 Undo 后 query + JS |
| REDELIVERY + 待处理记录 | 等待补发与待核对分别显示 | 否 | 原 P11 receive/query、JS、浏览器 |
| 查询结果不可确认 | 结果待确认或待核对 | 否 | 原 P11 lookup unavailable、JS、浏览器 |

## 实际执行方法

测试组合根在临时目录创建原 P11 `SQLiteAtomicModel` 要求的 `.P11_SIMULATION_ONLY` 标记和 `*.p11-sim.sqlite` 文件。使用原 `FixtureEvidence/FixturePolicy/FixtureWallet` 产生正例和负例，再调用原 `StudyLedger.query()`。这些原件来源和 SHA-256 随 `source_input_receipt.json` 交付。

没有手工把学习数据直接标成到账；也没有把 P11 的独立测试钱包迁入 P17。每次查看学习页只调用 query。契约测试验证查询前后 ledger/wallet 快照、经济策略调用次数均不变，且 P17 钱包原字节保持一致。

## 必测场景与对应入口

| 用例 | 实际实现/断言位置 |
| --- | --- |
| 四类 UI 语义中未知/拒绝/隔离不能冒充到账 | `model_controller.test.mjs` 的 learning status / simulator / self-reported production 组 |
| P11 原状态来源真实执行 | `test_domain_contracts.py::test_p11_query_states_are_from_original_ledger_and_cannot_credit_meta_wallet` |
| 刷新不重复授奖 | `test_learning_read_only_query_does_not_rerun_award` |
| 数据断线仍可查看旧值但禁止提交 | `disconnect keeps last snapshot marked noninteractive` 与浏览器 22 |
| Anki 断线不额外禁止已可用菜单功能 | `Anki disconnected does not block unrelated menu play` |
| APPLIED 模拟持久回执不显示正式“已入账” | 浏览器 17，真实 DOM 文本和原 P11 查询结果对照 |
| 隔离奖励可见且原因可读 | 浏览器 18，实际截图 `P20_Learning_Quarantine.png` |
| 拒绝、补发、对账异常分别可显示 | 浏览器 19 |
| 撤销记录查询不回放奖励 | 原 P11 Undo/query 原字节运行；JS REVERTED 标签测试 |

评分数值和奖励政策没有在 UI 中实现。P08 四键正式权益、真实 Anki 身份与 Undo 能力、P21 持久事务及可信查询均需由各 owner 提供。本文件不把测试值 10 或训练代币数值当正式四键奖励。

## 未执行/未验收

- 真实 Anki Hook → P11 → P17 → P21 → UI 的整链 E2E：`NOT_RUN`。
- 正式“已入账”在当前账号与连续性 fence 下的正例：`BLOCKED`。
- Windows 桌面引擎中的导航、屏幕阅读器、中文缩放：`NOT_RUN`。
- P32 独立自动化、P33 人工、P35 独审：`NOT_RUN`。
- P23 用户流程与 P24/P25/P37 组件、风格、合规受理：`NOT_RUN`。

需要接收的精确端口与验收条件在 `interface_rfcs.json`，不通过 UI 添加“强制到账”或“手工修正余额”按钮解决这些缺项。
