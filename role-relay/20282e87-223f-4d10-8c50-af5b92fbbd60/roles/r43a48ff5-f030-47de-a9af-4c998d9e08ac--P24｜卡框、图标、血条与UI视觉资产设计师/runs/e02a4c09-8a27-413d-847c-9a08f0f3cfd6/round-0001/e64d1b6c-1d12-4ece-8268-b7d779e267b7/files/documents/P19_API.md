# P19 HUD API / 0.1.0-isolated

接收人：P13、P14、P15、P16、P23、P29、P32、P39。共享战斗 DTO 原版本：`YLTT-INTERNAL/0.1.0-isolated`。本地只读显示扩展：`P19-HUD-FRAME/0.1.0-proposal`、`P19-HUD-CONTEXT/0.1.0-proposal`，均 **PREPARED_NOT_ACCEPTED**。

## 1. 组件装配

```javascript
const guard = createWireGuard(originalP13Schema);
const hud = new HudController({
  port, guard, mode: 'isolated',
  presentation: new PresentationBridge({driver: null})
});
const mounted = mountHud(hud);
await hud.refresh();
```

`mode` 目前只接受 `isolated`；传入生产模式会抛出 `PRODUCTION_CONTRACT_UNBOUND`。所有权仍由真实宿主维护；同进程 JavaScript/Python 不是安全沙箱。

## 2. 依赖端口

| 方法 | 输入 | 输出 | 要求 |
| --- | --- | --- | --- |
| `port.read()` | 无 | Promise&lt;Frame&gt; | 来自 owner 的一致读取；UI 不拼接多个时刻的终态 |
| `port.submit(command)` | 原 P13 BattleCommand | Promise&lt;BattleReply&gt; | UI 仅 PLAY_CARD/END_TURN；P15 校验，P14 提交 |

当前 `FixtureHttpPort` 使用 `/api/frame` 与 `/api/command`；它明确只用于测试台。正式桥接不可假设这两个 HTTP 路径已经获准。测试台只监听 127.0.0.1，校验 Host、Origin、短期测试 token，关闭 CORS，消息限定 1 MiB；退出后没有持久状态。token 仅控制本地测试请求，不是正式账号鉴权方案。

## 3. Frame

Frame 具有 `format`、`snapshot`、`context`；测试台还提供 `recent_batches` 与来源 `scope`。snapshot 必须是未经增字段的原 `BattleSnapshot`。context 可为 null。`recent_batches` 是原 `BattleCommitBatch` 的历史副本，只用于可读记录，不能改变 HP/费用/牌堆。

快照读取后执行原 schema 形状检查与 UI 边界检查：安全整数、HP 不超过 max、单位/阵位唯一、卡实例与牌区完整分区、角色所有者存在、状态和 Boss 引用存在、phase/outcome 对应。接收对象深复制并冻结。相同 battle 的较低 revision 丢弃；同 revision 不同内容触发冲突；last_event_seq 不得倒退。业务胜负/伤害/费用规则不在这些检查中重算。

JSON 传输使用 `parseWireJson`：拒绝重复键（包括转义后同名键）、小数/指数数字、越界整数、控制字符、未闭合文本、过深或过大内容。规范化 JSON 对照原 P13 Python 实测哈希一致。哈希用于字节绑定，不构成身份认证。

## 4. 本地 Context 提案

```
format = P19-HUD-CONTEXT/0.1.0-proposal
source_kind = ISOLATED_FIXTURE_ONLY
battle_id / revision / snapshot_sha256 = 当前原快照精确绑定
cards = 只读卡牌显示信息数组
intents = 明确来源的测试/候选意图数组
unit_labels = 可选的显示名称数组
```

cards 每项：`instance_id`、`actor_id`、`name`、`category`、`cost`、`description`、`enabled`、`reason_code`、`allowed_target_sets`。名称/描述/费用只展示，不能用于再次计算扣费；可用性和合法目标来自 owner 端口。当前作者 fixture 对每个候选目标组调用原 P15 `plan`，不在 UI 重写规则。多目标命令使用 owner 给定目标组的顺序，点击顺序不改写该顺序。

intents 每项：`actor_id`、`expected_revision`、`target_ids`、`provenance`、`label`、`skill_id`、`base_amount`、`hit_count`、`damage_label`。当前只接受 `SCRIPTED_TEST_ONLY` 或 `P16_PREVIEW_CANDIDATE_ONLY`；不接受冒充已提交状态的来源。`damage_label` 必须为 `BASE_DAMAGE_NOT_HP_LOSS`。正式意图提交端口仍缺失，不能从 UI 把候选升级为权威。

`unit_labels` 仅为可选文本，不决定单位身份或业务；缺少时显示原 unit_id。所有显示文本通过 DOM `textContent` 写入，不拼接 HTML。

上下文错 battle、错 revision、错 hash、缺目标/引用或版本不符时，P19 丢弃整个上下文：HP 等合法 snapshot 字段继续刷新；手牌显示 ID/待同步；旧意图消失；出牌选择锁定。END_TURN 可在合法 PLAYER_READY 快照且无其他输入锁时请求，由 P14 最终判断。

## 5. 用户输入与响应

界面不发送 `SYSTEM_START`、`SYSTEM_ENEMY_ACTION`、`SYSTEM_ENTER_PLAYER_TURN`、ABORT；后者也没有本轮 UX 授权。测试台对系统命令执行 HTTP 400 负例，原核心不变化。

每次新的合法用户动作生成 `p19:<UUID>`，带当前 expected_revision。发送前同步设置 pending，防止同一事件循环中的第二次点击。默认同 revision、同 kind/payload 的短时重复输入窗口为 350 ms。这个值是本地输入保护，最终幂等依赖 P14。

处理 COMMITTED 时必须匹配 battle_id、command_id、previous_revision、snapshot revision 和 observed_revision。先绑定完整 snapshot，随后再通知 P29；无任何乐观扣费/扣血。再做一致 read 以获取宿主后续系统批次。DUPLICATE_NO_OP 不重播效果，不推算数值；同样获取最新 snapshot。

REJECTED 显示 owner 错误码并刷新。传输超时（默认 8 s）或无法证明最新状态则保留**原完整命令**为 UNKNOWN，停止新出牌/结束回合。用户点击“查询本次操作”时，仅重发同一 command_id/expected_revision/payload；不会新建请求。连续点击查询也只发一份在途请求。生产恢复端口及持久去重保留期限需要 P13/P14/P21 确认，浏览器重载不恢复未决 command，不能把本地内存当持久幂等账本。

## 6. 生命周期

进入后台立刻锁输入、清选择、取消旧表现。恢复后重新读取快照，成功前不允许操作；未决 UNKNOWN 命令仍需同 ID 查询。多个 read 的旧响应不会覆盖较新的读取。dispose 增加代次，使旧异步回调失效。

P29 缺失、异常、卡住、跳过、seq 丢失都不参与解锁或结算。详细规则见 `presentation_adapter_spec.md`。现有浏览器只验证本地组件；目标 Windows 的真实后台/最小化及引擎生命周期需 P33 实机验收。

## 7. 容量和适用范围

P13 schema 的消息/集合边界保留；UI 请求历史当前最多 4096 个本地 ID，满后拒绝新请求，不能通过删 ID 获得第二次机会。可读日志显示最近 80 条。两者都不是正式存档策略。目标分辨率与锚点待 P23 接收；本轮检查 1440×1000、1280×800、960×720，另以 390 宽度检查溢出，不构成移动平台移植。
