# 结算演算实例（仅 TEST_ONLY，不构成正式数值）

规则版本：`P02-BATTLE-0.1.0-draft`。详细原始快照、命令及**全部期望事件**在 `battle_replay_fixtures.json` 中；本文件供实现/测试人员人工审查。

## A. 护盾先于HP

E1 初始 `HP=12/12, Shield=5`，卡牌逻辑伤害 amount=8，出牌资源 3/3，测试牌费 1。

先合法性检查→P14 缓冲 `ENERGY_SPENT(3→2)` 与 `CARD_MOVED(hand→discard)`→伤害 `absorbed=min(5,8)=5`→`hp_loss=min(12,8-5)=3`→敌人变为 `HP=9,Shield=0`→敌人仍存活→双方仍存活无终局→revision +1。动画若显示数字 8，可以同时标注护盾消耗 5、生命消耗 3，但绝不重算伤害。

## B. 越过BOSS阶段阈值且同时致死

**测试局部阈值**：B1 `maxHP=20`、phase1→phase2 的临界 `hp≤10`，阈值属 P06 未签核的测试注入，不是正式数值。B1 初始 HP=12，受到 12 点伤害→HP=0→`UNIT_DIED(B1)`→根效果与死亡反应队列排空→无敌人存活且玩家存活→`BATTLE_FINISHED(WIN)`。**不得**出现 `BOSS_PHASE_PROPOSED` 或阶段切换；如 HP 从 12→8 而且双方存活，则应出现且仅出现一次 `BOSS_PHASE_PROPOSED(phase2)`。

## C. 同归于尽

P1 是仅有存活英雄 HP=4，E1 是仅有存活敌人 HP=5。P1 打出可造成 5 伤害的 TEST_ONLY 卡，使 E1 死亡；E1 的测试专用 `ON_DEATH_RETALIATE` 已注册对杀死它的英雄造成 4 点伤害，死亡后该触发仍合法。根效果处理 E1 死亡并排入 reaction，随后 reaction 击杀 P1。队列排空后双方 live count 均零→仅一个 `BATTLE_FINISHED(DRAW)`。提前发 `WIN` 违反本规则。

## D. 无目标和重复点卡

初始手牌有实例 C1，energy=3；若向不存在的 E99 出牌，返回 `TARGET_INVALID`，revision/energy/hand/seen_commands 均原样不动，**无权威事件**。如首次合法 C1 出牌使用命令 ID X，energy 从 3→2、C1 进入 discard 且 revision=1；重新发送同一个 ID、相同 payload（包括 expected_revision=0）返回 `DUPLICATE_NO_OP`，仍保持 revision=1 和 energy=2。新 ID 再试打 C1 返回 `CARD_NOT_IN_HAND`。

## E. 抽牌耗尽与可复现洗牌

P15 需为回合入口提供已批准的 `draw_target`/`shuffle` 规则。`TEST_ONLY` 中抽牌请求 2 张，而 draw/discard 全空，发一个 `DRAW_SHORTFALL(requested=2,drawn=0)`，无生成牌、无疲劳扣血；结果回到 PLAYER_READY。

另一个 `TEST_ONLY` 测试 discard=`[C1,C2,C3]` 且 draw 空，允许 recycle 后洗牌。seed=1，xorshift32 前两次输出分别 270369 和 67634689；Fisher-Yates i=2 j=0、i=1 j=1，重建 draw=`[C3,C2,C1]`，抽 1 张 C3，剩余 draw=`[C2,C1]`；random.draw_count 从 0→2。

## F. DOT与行动交错

玩家回合入口先处理 P1 身上的 DOT，再根据死亡反应清队列及判断胜负，**然后**才可以刷新资源/补牌。如果该 DOT 导致最后存活的我方单位死亡且敌人未死，立即 `LOSS`，不发生同次回合的 draw 或 `PLAYER_TURN_STARTED`。反向如敌人回合入口的 DOT 击杀最后敌人，立即 WIN，不再选择敌方目标。

## G. 连锁回环保护

反应排序：tier→根事件序号→来源固定槽位→effect_index→trigger_id，宽度优先。已执行 trigger instance 本命令内不可再次执行；对真正持续产生**新**触发ID的非法循环采用 1024 次事务安全限幅，溢出不提交任何中间 HP/资源状态，记 FAULTED、无终局奖励。该 1024 不是玩家回合或关卡的玩法上限。
