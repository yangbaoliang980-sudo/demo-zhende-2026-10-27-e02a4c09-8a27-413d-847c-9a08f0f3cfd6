# P19 / P29 公开显示适配器｜P13 IC-08 隔离版

接口形状归 P13；HUD 控件、最终数值绑定与租约校验实现归 P19；动画时间轴、播放/跳过/加速归 P29。P23 的布局/锚点及减少动态效果规范仍需原 owner 提供。本文件没有实现 UI 或动画。

## 输入与唯一事实来源

P14 的已提交 BattleSnapshot 是最终数值事实来源，BattleCommitBatch 提供该 revision 的连续事件及同次快照。P19 不等动画完成才确认权威值，P29 不把碰撞时点反馈为“现在扣血”。纯表现逻辑只改变临时显示层。

`ports.py` 中的 PresentationAdapter 是 P19 实现并向 P29 公开的五个方法：

| 方法 | 调用者/实现者 | 语义 |
|---|---|---|
| `reconcile(snapshot)` | 宿主/P19 → P19 | 验证 battle/revision/seq 后绑定最新最终快照；取消被覆盖的显示租约 |
| `begin(batch) -> lease_id` | P29 → P19 | 只为已由可信 P14 通道接收的提交批次建立临时显示权限；返回不透明、绑定 battle/revision/seq 的租约 |
| `display_bars(lease_id, unit_id, hp, shield)` | P29 → P19 | 只写该单位的临时血条/盾显示；值来自对应真实事件与插值；不修改最终绑定或 BattleState |
| `finish(lease_id)` | P29 → P19 | 结束表现并归位到 P19 当前最新快照；不是盲目归位到旧批次快照 |
| `cancel(lease_id)` | P29/宿主 → P19 | 可重复取消；清除临时层并归最新状态；没有领域回调 |

这不是由 JSON 自报 lease_id 就获得权限。P19 必须校验租约存在、battle_id、revision、合法锚点/单位及是否已过期；切战斗、较新快照、后台恢复、资源加载失败或取消都会失效旧租约。过期动画不能把新 HP 覆盖成旧 HP。具体租约实现及并发 UI 测试属于 P19/P29，**本轮 NOT_RUN**。

## 事件缺口与重复

P13 提供的 BattleStreamGuard 是只读传输顺序守卫，其缓存是快照副本，不是第二个 BattleState。它实际验证整批结构、当前 revision+1、当前 seq+1 和同一 battle；完全重复的最后一批返回 DUPLICATE；更旧数据返回 STALE 或请求重同步；任意缺口/冲突返回 NEED_SNAPSHOT，不部分应用。

遇到 NEED_SNAPSHOT，宿主调用 P14 只读 snapshot 端口，P19 reconcile 后再交下一完整批次。不能只更新本地 seq 跳过逻辑事件，也不能从动画残余值构造新战斗快照。引擎主线程调用守卫；当前实现没有被描述为多消费者并发安全。

## 呈现数据绑定

最终 HP/盾/费用/手牌/意图来自 snapshot。伤害数字来自 P14 的 DAMAGE_APPLIED 字段 raw/absorbed/hp_loss/overkill；它们在数据模型中有分别的含义，不能把 raw 当作实际扣 HP。HEAL_APPLIED、SHIELD_CHANGED、UNIT_DIED、BOSS_PHASE_* 等只供表现；缺正式素材时可降级到 P19 的文字/静态状态，不能借此把占位素材称正式美术。

后续 P19/P29 必测：无动画与动画开关同一权威输入；取消后最新快照归位；重复批次；缺 seq；同 revision 不同快照；旧战斗事件；新快照与旧动画同时到达；无音频可读；资源加载失败。作者 Spy 测试只证明接口没有调用战斗写入入口，不能替代以上真实 UI/动画测试。
