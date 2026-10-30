# P20 显示与操作端口提案

`P20-META-VIEW/0.1.0-proposal` / `P20-META-INTENT/0.1.0-proposal`  
关联 `IC-10 / IC-13 / IC-21`；状态 `PREPARED_NOT_ACCEPTED`。

原 P13 DTO、P17/P18/P11 文件全部保留原字节。本文件定义本隔离界面所需的组合显示层，不修改原内部 DTO，也不表示契约 owner 已经批准。

## 1. 对象与目录

`ui/meta/model.mjs` 校验并冻结只读视图；`controller.mjs` 管理页面、草稿、未决请求与重入；`renderer.mjs` 仅渲染字段与可操作性；`port.mjs` 实现本地 HTTP 提案；`app.mjs` 绑定浏览器生命周期和 DOM 事件。

`tests/meta_ui_unit/support/fixture_host.py` 是唯一的测试组合根，调用原领域代码并用明确的内存发布器代替 P21。正式工程不得把这一文件或上游 `tests/support/` 作为生产存档实现。P20 没有生产写入适配器。

## 2. 只读视图

端口 `read() -> Promise<View>`；HTTP 验证台为 `GET /api/view`。结构示例为 `tests/meta_ui_unit/fixtures/demo.json`，其内容由原代码实际执行生成。

| 字段 | 规则 |
| --- | --- |
| schema_version | 必须是当前 P20 显示提案版本 |
| mode | 本包只允许 UNBOUND / FIXTURE；不能由响应开启生产模式 |
| sequence | 同一会话单调视图序列；同序列不同内容拒绝 |
| identity | profile_id / store_instance / continuity_ref / session_id |
| revisions | meta / wallet / stage 的非负安全整数 |
| source_hashes | 原 meta/stage 快照和两套内容组合哈希 |
| save | 未修改形状的 P13 SaveStatusView |
| wallet | 原 P17 输出的 P13 WalletSnapshot；缺失为 null，不伪装零 |
| characters | P17 已拥有角色进度、属性、源 revision/哈希；P04 测试名称；升级资格/配置费用与装备资格 |
| party | 原提交顺序及完整性，只读；局部草稿另存 |
| stage_progress | 原 `P18-PROGRESS-VIEW/0.1.0-proposal`，保留 review/quarantine/consumed 字段 |
| stage_details | 与进度一一对应的显示资料、P18 预检资格、只读首通预览 |
| learning | connection、pending_count、原 P11 query outcome；不附带可操作奖励数额 |
| settlement | 返回结果的引用、P18 处理决策、可领取性、测试回执或 null |
| capabilities | 测试写入口与装备开关；UNBOUND 不允许写 |

交付包含实际字段验证和反例测试：安全整数、钱包账号/版本、角色源快照、三席唯一性、关卡目录一致性、旧 revision、同序列冲突、解锁按钮与领域状态冲突。SHA-256 只用于绑定字节，不能把调用者输入变成权威证据。生产组合根的来源认证和一致读取仍由 P13/P21 定义。

## 3. 操作意图

`submit(intent) -> Promise<Reply>`；HTTP 为 `POST /api/command`。所有意图严格包含：

```json
{
  "schema_version": "P20-META-INTENT/0.1.0-proposal",
  "request_id": "p20.unique-operation-id",
  "binding": {
    "identity": "原视图 identity 对象",
    "revisions": "原视图 revisions 对象",
    "source_hashes": "原视图 source_hashes 对象"
  },
  "kind": "LEVEL_UP",
  "payload": {
    "character_id": "MOCK_P04_CHAR_001",
    "from_rank": 1,
    "to_rank": 2
  }
}
```

上例中的三段字符串是字段说明，不是可发送 JSON。实际可运行消息见契约测试、浏览器 trace 与生成夹具。UI 不发送金额、等级后态、解锁列表、任意奖励凭证或客户端 BattleResult。

| kind | payload 精确字段 | 原领域调用 |
| --- | --- | --- |
| SET_PARTY | ordered_character_ids | P17 command / MetaPlanner.plan / validate_for_commit |
| LEVEL_UP | character_id, from_rank, to_rank | P17 同名命令，费用由 Catalog/规则取得 |
| SET_EQUIPMENT | character_id, items | P17 同名命令；实例唯一、等级、slot、开关由 P17 校验 |
| ENTER_STAGE | stage_id | 受信任协调层取得 entry_ref/battle_id/seed，再调用 P18 ENTER |
| CLAIM_STAGE_REWARD | battle_id | 受信任协调层解析原终局，再调用 P18 SETTLE 与联合候选 |

当前测试组合根中入场及终局证据来自原 P18 `FixtureAuthority`，全部是合成夹具。真实 `resolve_entry/resolve_battle`、P14 battle 生命周期和 P19 场景切换均为正式接入阻塞。

## 4. 候选、回复与查询

P17/P18 的 `CANDIDATE` 不能作为 UI 成功回复。测试端必须调用原 `validate_for_commit` 或 `validate_atomic`，完成内存发布后才能返回 `COMMITTED_SIMULATION`，且固定 `durable=false`。

回复绑定原 `request_id` 与规范意图 SHA-256，并带当前视图。允许状态是 `COMMITTED_SIMULATION / DUPLICATE_NO_OP / REJECTED / BLOCKED / UNKNOWN`；原 ID/hash 不匹配、声称 durable=true、存储实例不符、过旧视图或未知状态均保留未决请求。

`lookup(original_intent)` 为只读；HTTP 为 `POST /api/lookup`。它需要完整原意图来核验 ID、载荷与 fence，不重新计划或提交。重发同 ID 修改 payload 返回碰撞，重新生成 ID 不得用于绕过未知结果。当前测试端回执只在内存内保留，跨服务重启的正式保留策略未定义。

## 5. 学习“已入账”的正式接入条件

原 P11 `Outcome` 的 APPLIED、receipt.durable 和 origin 是不同维度。P11 测试 SQLite 会产生 `durable=true` 但 `origin=P21_SIMULATOR` 的回执；本 UI 明确只显示“测试记录已处理”。

当前 `learningLabel()` 对自报 P21_PRODUCTION 也不会直接显示“已入账”。正式该分支需要 P11/P13/P21 接受并实现：账号/collection scope、inbox、原事务、store instance、continuity、高水位和当前钱包可用数额的一致读取/提交查询，以及可信 composition root 的绑定。相关 RFC 已准备但未提交。本轮不把这条缺失链标为通过。

## 6. 不可损失的恢复数据

浏览器仅保存导航与 `PENDING` 意图，没有钱包或账本副本。恢复记录写失败则不发请求；清除失败则继续 UNKNOWN；坏 JSON 或 hash 不符不静默丢弃。重新读取时旧数据可被忽略，较高视图序列也不能掩盖 meta/wallet/stage revision 倒退。

页面从后台恢复会先同步，完成前暂停变更。操作响应不能把用户强制带回刚离开的页面。HTML 输出全部转义动态文本，领域对象不会暴露可变 DOM 引用。

## 7. 责任和验收

P13 接受 DTO/显示组合和路由；P17 接受角色/钱包字段及操作映射；P18 接受关卡/结算映射；P11/P12/P21 接受学习和恢复证明；P23 接收用户流程；P32/P33 测试，P35 独审；用户指定的 EXT-INTEGRATOR 实施接线。任何版本或字段更改均记录 base SHA 与 ChangeRequest，不能覆盖源文件。
