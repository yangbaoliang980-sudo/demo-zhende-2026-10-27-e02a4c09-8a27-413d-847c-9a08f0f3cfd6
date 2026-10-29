# P15｜《言灵旅团》牌堆与出牌候选运行库

**任务：P01 `TASK-02-01`；阶段：S02；版本：`P15-DECK-RUNTIME/0.1.0-isolated`。**

本包交付真实 Python 源码、可执行测试、固定种子向量、非法请求输入、实际运行样例、接口说明及逐文件哈希。P15 负责构筑、抽弃牌、消耗牌、出牌合法性与费用候选。**BattleState 的费用、牌区、效果、HP、revision 和终局只由未修改的 P14 原运行库提交。**

当前为 **隔离实现完成、作者验证通过、正式工程接入 BLOCKED**。最终作者测试实跑 **148 项 PASS、0 FAIL、0 skip**。P32 独测、P33 人工、P35 独审、引擎真机、UI/动画、真实 Anki、P21 存档和整套游戏 E2E 均为 **NOT_RUN**。不能据此释放正式 G2 门禁或宣布跨模块集成。

## 1. 接收后直接复现

Python **3.12**，在本目录运行。以下核心、测试、示例均只依赖标准库，无需安装第三方包。

```bash
python -B tools/verify_delivery.py
python -B tools/author_tests.py
python -B -m deck_runtime
python -B deck_determinism_tests.py
python -B tools/replay_example.py
python -B tools/check_contracts.py
python -B tools/probe_p14_module_identity.py
python -B tools/preflight.py
```

前七项成功退出码为 0。最后的 `preflight.py` 当前应输出 **BLOCKED / exit 3**，因为正式工程映射、真实编队、正式内容与目标环境等输入尚缺。该门禁不是待修复的运行库异常。

也可使用标准 unittest：

```bash
python -B -m unittest discover -s deck_unit_tests -t . -p 'test_*.py' -v
```

可选 `python -B tools/check_contracts.py --jsonschema` 用于第三方 Schema 算法对照。当前 Python 未安装 `jsonschema`，其算法对照为 **NOT_RUN、依赖门禁 BLOCKED、exit 3**；原始 P13 校验器已实际检查 168 条消息，不受该可选依赖影响。

## 2. 本轮实际能力

| 能力 | 实现及边界 |
|---|---|
| 三人编队构筑 | 校验 P13 PartySnapshot；以 slot 排序，按冻结配方产生独立实例；P03 24 个有序编队配方均实测。编队本身由明确标记的作者夹具提供，未冒充真实 P17 输出 |
| 牌实例身份 | 由 battle_id、完整 party SHA、recipe SHA 与序号生成确定性实例 ID；模板 card_id 不变；同一实例恰好处于一个牌区 |
| 初始洗牌与弃牌回流 | P02 xorshift32-v1 + 降序 Fisher–Yates/mod；左端抽牌；保存 initial_seed/state/draw_count；P02 F014 牌序与 RNG 预期直接对照 |
| 抽牌与容量 | 按显式抽牌数和手牌上限生成移动；空 draw 可按政策洗回 discard；exhaust 永不回流；缺牌或手满返回短缺报告，不补卡或计算疲劳伤害 |
| 弃牌与消耗 | END_TURN 显式 KEEP 或 DISCARD_ALL；出牌移到内容指定 discard/exhaust；只有 P14 提交后权威牌区才变化 |
| 出牌验证 | 检查阶段、revision、场次、内容/规则版本、真实手牌实例、角色归属、专属牌归属、存活 actor、全部显式目标、费用、未定义的 DOT 重叠 |
| 费用 | 从冻结内容读取非负安全整数，只返回 energy_delta；拒绝输入中的自报 cost/HP；无折扣或额外平衡公式 |
| 幂等 | request_id 是 P13 command_id 的本地称呼；相同请求的 P15 候选/拒绝证据原字节复用，异指纹碰撞拒绝；成功执行防重由 P14 accepted_commands 负责 |
| 一次提交 | 实测同一次 P14 提交包含费用、移牌和效果；24 次并发相同请求仅提交一次；三个提交前中断点可原请求重试；P14 效果拒绝时费用与牌区一并回滚 |
| ActionIntent | 本地、不可变、引用式验证证据，指向冻结 card/effect IDs；现有 P14 端口只接 DeckPatchCandidate，不向其添加私自定义的字段 |

公共牌归属是实际发现的上游缺项：P03 公共牌模板无 owner，但 P13 CardInstance 与 P14 要求实例有 owner_unit_id。本包强制测试配方显式提供 `[0,0,1,1,2,2]` 公共实例归属槽位，**该数组只用于本包测试，不批准为产品规则**。

P03 八张活动样例、九张牌的配方、抽 5/手牌上限 10/能量 3 等都属于隔离夹具。两张 BUFF/DEBUFF 提议牌保持禁用。多目标、exhaust 和零费能力使用独立 `fixtures/extension_cards.fixture.json` 边界输入测试，不修改 P03 内容或批准新卡。

## 3. 文件入口

| 相对路径 | 内容 |
|---|---|
| `deck_runtime/builder.py` | 纯编队构筑与实例生成 |
| `deck_runtime/deck.py` | 不可变 DeckState、洗牌/抽牌/弃牌/消耗牌区候选 |
| `deck_runtime/rng.py` | 明确 RNG 流、历史校验、固定算法洗牌 |
| `deck_runtime/content.py` | 内容、策略和编队的冻结输入；生产模式闭合 |
| `deck_runtime/planner.py` | 纯验证、DeckPatchCandidate、ActionIntent 与拒绝证据 |
| `deck_runtime/commands.py` | 有界、线程串行的进程内证据缓存，不是提交账本 |
| `deck_runtime/p14_adapter.py` | P14 现有 Python 端口适配、版本/效果绑定与拒绝异常类注入 |
| `deck_patch_schema.json` | P13 DeckPatchCandidate/Move/Rng 原定义的独立投影，未改共享 Schema |
| `invalid_play_cases.json` | 38 个完整非法输入及期望；该文件是夹具，不冒充日志 |
| `card_legality_table.tsv` | P03 十张样例的费用、归属、目标、可用状态、源哈希及测试映射 |
| `deck_determinism_tests.py`、`deck_unit_tests/` | 固定种子、牌区、构筑、验证、并发、防重、回滚、P14 契约测试 |
| `examples/example_requests.json` | 真实运行的 18 个请求、答复、9 份候选证据与提交批次 |
| `examples/p14_recorded_replay.json` | 原 P14 回放格式；运行输入由本次真实 P15 计算 |
| `handoff/P15_API.md` | API、幂等范围、拒绝语义、接线注意事项 |
| `integration_handoff.md` | 下一位接收与正式接入前置条件 |
| `verification_status.json` | 设计、作者测试、契约、真机与独立验收分层状态 |
| `handoff/` | RFC、阻塞、路径请求、接收回执和任务/需求追踪 |
| `evidence/runs/` | 每轮真实命令、退出码、原始 stdout/stderr、运行前源码快照 |
| `evidence/source_input_receipt.json` | 原附件、原 ZIP、固定 GitHub 提交、每份保留输入的实际大小与 SHA-256 |
| `upstream/` | 70 份原字节输入，含 P14 原 ZIP、未修改 P14 源码、P13 codec/Schema、P02/P03 规则内容 |
| `delivery_manifest.sha256.tsv` | 每件文件的路径、大小、SHA、格式/版本、源哈希、接收方及修改白名单 |

## 4. 真实执行结果

作者样例从 CREATED 开始，运行三个玩家回合及固定敌方测试输入。**实际 P15 与原 P14 在隔离测试装配中执行；P17 编队和 P16 敌方输入为夹具。**

| 观测 | 实际值 |
|---|---:|
| 请求数 | 18 |
| P14 提交数 / 最终 revision | 12 |
| 被拒绝请求 / 同 ID 重发 no-op | 3 / 3 |
| ENERGY_SPENT 事件 | 3 |
| 弃牌洗回次数 | 2 |
| RNG 消耗总步数 | 16 |

`tools/replay_example.py` 从原始命令重新调用真实 P15，再交原 P14 计算，逐字节比较答复、候选证据、提交批次和最终状态；不是读取期望候选直接当结果。另由 P14 原 replay 重放已提交候选输入，作为消费端一致性检查。三个独立 PYTHONHASHSEED 进程也重新运行真实 P15，得到相同整段执行摘要。

## 5. 修复与未完成事项

交接时另测 P14 的原包名 `battle_core`，发现 Python 同源码不同模块名会产生不同异常类。旧 P15 适配器硬编码 vendored 异常类，使一次费用不足被 P14 当成内部故障并提交 FAULTED，**未发生扣费，但破坏了非法请求不改变战斗状态的要求**。本轮已在 P15 自有源码修复：装配端必须传入实际 P14 的 `CandidateRejected`。原 FAIL、失败时源码和修复后 PASS 均保留；最后的 148 项测试包含此回归。未修改 P14。

正式映射、真实 P17 编队、正式内容/费用/回合政策、P22 ID、目标引擎/OS、负向候选与 draw-report 正式合同尚缺；见 `handoff/blockers.json`。进程内缓存没有持久化，不能替代 P14 回执或 P21 事务。增减益、自动目标、折扣、复活和敌方 AI 均未擅加。

所有下游记录为 **PREPARED_NOT_ACKNOWLEDGED**。实际路径审批由 P13，规则/内容修订回原 owner，独立复测/审查由 P32/P35；正式源码合并继续由用户指定的 EXT-INTEGRATOR 执行。
