# P19 → P29 公开 presentation_adapter

版本：`P19-PRESENTATION/0.1.0-proposal`  
共享事件：原 P13 `BattleCommitBatch` / `BattleEvent`  
状态：**实现了 P19 桥及无驱动回退；P29 接收、真实动效执行 NOT_RUN**

## 所有权

P19 负责手牌、HP/护盾、费用、意图、回合按钮、输入状态和错误信息的最终绑定。HP/护盾/费用/牌数只读取 `BattleSnapshot`。P29 不取得 UI controller、命令端口、可变领域状态或业务控件 DOM 引用。

P29 只接收冻结事件副本与数字坐标，负责未来独立 overlay 上的卡牌运动/撞击/震动/闪白/伤害数字。不得写入 HP 标签、血条宽度、费用、手牌数量、按钮 enabled 或敌意图。关闭表现时这些字段仍完整可见。

## 接口

```javascript
const driver = {
  present(envelope) { /* Promise<void>，仅表现 */ },
  cancel(reason, epoch) { /* 同步或 Promise<void>，清理旧 overlay */ }
};
const bridge = new PresentationBridge({driver, anchors, onStatus});
bridge.setMode('normal');
// 此时 P19 已经完成 snapshot 的原子视图绑定。
void bridge.present(batch, previousEventSeq, authoritativeFinalSnapshot);
```

envelope 的字段：`version`、`epoch`、`battle_id`、`revision`、`last_event_seq`、`mode`、`events`、`anchors`。events 是原事件的深复制、深冻结数组。anchors 含 `units[]` / `cards[]`，每项只有 `id,x,y,width,height`，坐标来自已布局元素的 viewport 矩形并取整。锚点名称/坐标方案仍需 P23 设计受理。

不包含 snapshot 对象、owner 能力、DOM 节点或 UI 修改回调。此约束防止正常协作者误写，**不宣称能沙箱隔离恶意同进程 JavaScript**。

## 顺序、跳过与失败

| 事件 | P19 行为 | P29 必须遵守 |
| --- | --- | --- |
| 新完整 snapshot 到达 | 先更新终态；清除旧选择/上下文 | 不等待动画才允许 HUD 更新 |
| seq 连续且有驱动 | 发送冻结表现包 | 使用包内实际伤害事件，不能以基础攻击值推算掉血 |
| seq 丢失、重复、错 revision/battle/command | `SEQUENCE_GAP_SNAP_TO_FINAL`，取消表现 | 清 overlay；不可倒推或补写逻辑事件 |
| 关闭/减少动态 | 静态终态，`present` 不执行 | 不要求声音或屏幕震动传达关键状态 |
| fast | 只把 mode=fast 交给 P29 | 只能改变表现时长，不能影响逻辑调度或结果 |
| 跳过/后台/刷新/销毁 | 增加 epoch 并 cancel | 旧 epoch 的计时器/回调必须自行结束 |
| present 抛错 | 取消并保持静态终态 | 不重试伤害或出牌 |
| present 永不返回 | 不阻塞输入或快照接收 | 后续 cancel 必须清理自身任务 |

bridge 从不 await 动画来解锁输入。异步完成时只允许与当前 epoch 相同的状态通知；旧完成不会覆盖新的 cancel 状态。P29 还必须在自身控制器执行 epoch 检查，因为桥无法撤销已经泄漏到外部的恶意/错误 DOM 写入。

## 测试证据与边界

`tests/battle_ui_unit/presentation.test.mjs` 实测：无驱动、四个模式、丢 seq、重复 seq、旧 revision、抛错、永不完成、跳过、旧回调和参数冻结。真实浏览器实测静态终态及模式切换不改变核心状态。没有 P29 真实控制器，因此没有把 test driver 结果写成动画集成 PASS。

需 P29 回交：具体版本的 driver 实现、取消/旧 epoch 清理证据、锚点接收、可用资源列表及独立测试。需 P13/P14 回交：正式原子提交事件分发与当前快照一致读取端口。RFC 详见 `interface_rfcs.json`。
