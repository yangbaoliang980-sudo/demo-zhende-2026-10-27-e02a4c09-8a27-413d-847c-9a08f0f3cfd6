# P16 交接：隔离运行库与正式接入条件

任务 `P16-S03-AI-001`；版本 `P16-ENEMY-AI/0.1.0-isolated`。接收状态为 **PREPARED_NOT_ACKNOWLEDGED**。本文件是可执行成果的接线说明，不代表已批准跨模块合并。

## 1. 接收者先运行

在新目录解压整个包。Python 3.12 标准库即可运行；保留 `upstream/` 的原始目录结构，本次导入明确依赖其原 P13 codec/validator 和 P14 纯 RNG、单槽契约运行库。单独下载 `planner.py` 不能替代完整依赖包。

```bash
python -B tools/verify_delivery.py
python -B tools/author_tests.py
python -B tools/replay_fixtures.py
python -B tools/check_contracts.py
python -B -m enemy_ai
python -B tools/replay_demo.py
python -B tools/preflight.py
```

前六条预期退出 0；正式前置检查退出 3 / BLOCKED 是当前已知状态。不要把最后一条转换成生产 PASS。包内 `verification_status.json` 记录作者执行结果，包外 `delivery_receipt.json` 记录最终 ZIP 的新目录复跑结果。

## 2. P14：已可用的单行动槽端口

读取 `enemy_ai/p14_adapter.py` 与 `examples/p14_fixture.py`。适配器实现原 `EnemyPlanner.propose(snapshot)`，只允许 `scope='ONE_SLOT_CONTRACT_TEST_ONLY'`。将实际装配模块的 `CandidateRejected` 类传入，避免同文件以不同模块名导入后的异常类型不一致。

先用可信快照和明确行为扩展生成 `publish_intent` 结果；在 P14 已完成入口 DOT/反应/终局处理后，适配器调用 `resolve_intent` 并返回原 EnemyIntent。P14 仍从自己的受信 Action 配置取得伤害值，计算护盾、HP、死亡、事件和 revision，执行权威提交。

运行库不缓存“执行成功”，不推进已提交循环、不落盘。P14 当前没有 BehaviorCandidate/Announcement 受理字段，所以这个端口不能被当作多回合生产适配器。样例中的 P15 牌区请求与 P17 三人编队都是明确测试夹具，没有调用 P15 正式构筑流程或真实角色存档。

## 3. P14/P13：必须先受理的合同事项

`handoff/interface_rfcs.json` 保存 6 项版本化 RFC，每项绑定实际 base 文件 SHA。RFC 只随交付包准备，尚未发送、批准或替对方提交修改。

首先冻结行为/预告快照及候选原子受理。冻结记录必须属于权威战斗状态，绑定场次、敌方实例、槽位、规则/内容/图版本及阶段代次。P16 候选只提议行为字段，不提议 HP 或 phase 写入；候选的 `commit_condition` 要由 P14 真实结果决定。

阶段受理要在 P14 的根效果和合法反应排空后执行。80→30 的 P2/P3 提议须同批受理；只增加一次 phase_epoch、安排一次 ENTRY_WAIT、取消旧蓄力一次，不能每条提议各赠送一次行动。重复 proposal_id、阶段历史、根事务身份需要 P14 回执支持。当前 `inspect_phase_proposal` 明确拒绝此功能，测试证实其阻塞。

另有已复现的群攻目标基数缺口。原目标 3 人变为有效 2 人时，P16 返回只含原名单幸存目标的 EnemyIntent，但 P14 固定 `target_count=3` 跳过整次攻击。修复 owner 为 P14，DTO 如改变由 P13 出版新合同。不能通过加入失效目标、改成单体技能或隐性重选规避。

安全跳过原因目前在 P16 本地 view；原 P14 将 P06 SKIP 技能作为零效果 Action 处理，不保证发出 `ENEMY_ACTION_SKIPPED`。P19 正式消费前需新合同明确事件语义。新增 targetable、多敌队列和召唤也需要各 owner 的版本化输入，当前没有默认获批。

## 4. P19/P27：只读表现数据

读取 `P16_API.md`、`examples/demo_execution.json`、`intent_replay_fixtures.json`。视图包含意图字典 ID、目标列表、基础数值、段数、后续释放基础伤害、phase/epoch 和偏差原因。

`BASE_DAMAGE_NOT_HP_LOSS` 表示提示的内容数值：例子中预告 8，实际护盾吸收 4、扣血 4。伤害数字、HP 和护盾动画应读取 P14 已提交事件。P16 不操作特效层，不把图片加载/动画播放完成当作业务条件。

`next_forecast` 为条件性循环后继，目标为 null。它不构成已锁定的下一回合预告。正式下一预告应在 P14 接受本回合后，使用新权威快照再生成。逻辑阶段图缺失和缺美术图片必须分开处理；前者只返回降级建议，后者不能改变 AI。

## 5. P32/P33/P35：证据与独立验收

作者完整测试 182 项，其中原 P06 89 条真值表仅 86 条完成 P16 字段投影验证，另外 3 条 BLOCKED。投影记录逐项列出已检查字段和未验证的 P14 提交/UI 等字段。不要将 86 条投影解释为 86 条完整战斗 E2E。

真实 P14 契约测试 18 项同时包括正常伤害、防重、回滚和对已知不支持行为的反例断言。`test_existing_p14_cannot_execute_partial_sweep` 的测试 PASS 表示成功复现当前限制，产品群攻接入仍 BLOCKED。

P16-DEF-001 和 P16-DEF-002 均保留失败时源码 ZIP、原 stderr、修复后完整回归。两项作者已修复，P32 复测与 P35 关单仍 NOT_RUN。P33 真机/UI/动画操作当前未执行；P35 不得根据作者自检替代独审。

输入来源、固定提交、原附件与 ZIP、逐文件 SHA 在 `evidence/source_input_receipt.json`。本轮结束时重新读取了 4 个上传附件、61 个唯一 ZIP、3912 个展开成员及 88 个保留上游文件，未发现改变。GitHub 固定来源匹配证据另见 `evidence/github_fixed_source_verification.json`。

## 6. 正式工程与冲突处理

P13 原映射仍为 null / write_allowed=false。`handoff/actual_path_request.json` 保留原条目，本包没有自行把隔离路径批准成真实路径。生产修改白名单为空。P01 的原任务登记没有 P16 独立行，本地任务 ID 来自本次用户明确启动，仅关联 P19 `TASK-03-01` 作为依赖支持。

得到用户指定 EXT-INTEGRATOR 及 P13 真实路径授权后，整合者先比较本包记录的 base SHA 与当前工程。若不一致，保存双方 base SHA 并提出 ChangeRequest；不得覆盖式合并。所有 P06/P13/P14 输入保持只读，修复返回原 owner。协议变更需要原 owner 新版本与新证据，重复两轮返工无新证据再交 P01 裁决。

S07 正式激活、正式内容规模、召唤和额外机制均待 P01/P06 按范围处理。本包只完成已有配置的可独立验证 P16 行为，不代表整款游戏、Anki 联动或桌面发布完成。
