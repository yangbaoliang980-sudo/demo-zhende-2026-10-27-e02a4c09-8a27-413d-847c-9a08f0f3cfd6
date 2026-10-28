# P14｜《言灵旅团》纯逻辑战斗核心交付

**任务：TASK-01-02。交付版本：P14-BATTLE-CORE/0.1.0-isolated。内部 DTO：YLTT-INTERNAL/0.1.0-isolated。**

本包包含可执行的 Python 战斗运行库、作者单元测试、确定性回放、实际事件与快照、不可变终局结果、API 及原始测试证据。P14 是本库唯一的 BattleState／BattleResult 提交者。运行库不是脚本化假响应；P15 牌堆候选和 P16 敌方意图使用明确标记的测试替身。

**当前结论：隔离实现及作者验证已完成；正式工程接入 BLOCKED。** 未取得 P14 的正式工程路径映射、真实 P15／P16 实现和目标引擎环境。没有修改上游工件，没有替用户整合工程，没有 GitHub 写入，没有真实游戏／Anki／存档／UI 联调通过声明。P32 独测、P33 人工、P35 独审均为 **NOT_RUN**。

## 1. 直接运行

使用 Python 3.12，在本包根目录执行。普通运行库、测试、示例及回放只用标准库，不需要游戏引擎或第三方依赖。

```bash
python -B tools/verify_delivery.py

python -B -m unittest discover -s resolution_replay_tests -t . -p 'test_*.py' -v

python -B -m battle_core

python -B tools/replay_file.py examples/demo_replay.json

python -B tools/preflight.py
```

前四条成功时返回 0。最后一条当前应返回 **3 / BLOCKED**，表示正式前置条件不足，不能按程序运行失败或正式通过处理。

单元测试当前发现 **101 项：97 项 PASS、4 项 BLOCKED／skip、0 项 FAIL**。四个 skip 具有明确缺项，不纳入通过数量。详情见 `verification_status.json` 和 `evidence/runs/author_004/`。ZIP 重解压后的复现和导出比对记录在包外 `delivery_receipt.json`，避免对 ZIP 自身形成循环哈希。

## 2. 已实现的核心

| 能力 | 本包实际行为 |
|---|---|
| 开局与阶段 | CREATED → PLAYER_READY → ENEMY_READY → PLAYER_TURN_PENDING → PLAYER_READY；终局／退出／故障闭合 |
| 单一提交 | 费用、牌区、RNG、效果、死亡、终局、回执和事件先在临时副本中计算，校验后一次替换已提交记录 |
| 防重 | 同 ID／同完整命令指纹返回 DUPLICATE_NO_OP；同 ID／不同指纹返回 COMMAND_ID_COLLISION；领域防重先于 revision、阶段和依赖调用 |
| 拒绝不写入 | 非法目标、无牌、旧 revision、错误候选绑定、无效 RNG／牌区、资源下溢等保持全部权威字节不变 |
| 基础效果 | 伤害先盾后血；治疗封顶且不复活；盾遵守显式测试 cap／溢出配置；单层 DOT 按 owner entry 触发 |
| 连击与反应 | effect_index 顺序、显式目标顺序；每次伤害立即死亡；根效果结束后按层级、tier、父事件和稳定单位序处理反应 |
| 胜负 | 反应排空后互斥 WIN／LOSS／DRAW；最后敌人的死亡反击仍能造成 DRAW；只发一次 BATTLE_FINISHED |
| 只读数据 | 复用 P13 原 FrozenMessage：存储规范 bytes，读取 value 得到独立副本；修改显示副本不改权威状态 |
| 随机状态 | initial_seed／state／draw_count 显式保存；实现 xorshift32 及快速跳步验证；洗牌和随机消耗选择仍归 P15 |
| 回放 | 保存初态、规则／内容投影及来源哈希、按序已提交命令与实际候选；重执行比较状态、批次、结果原字节 |
| BOSS 边界预检 | 存活越阈后按图提出阶段；致死、反击全灭和 DOT 终局优先，不发阶段提案、不追加敌行动 |
| 中断与故障 | 三个提交前中断点完全回滚；反应超过 1024 次时丢弃游戏事务，只安全提交 FAULTED；不产生 BattleResult |

回合号已按 P02 实际夹具统一：**敌方回合结束时加一，玩家入口沿用已有回合号**。首轮作者误读导致的失败已修复，原日志和失败时源码均保留，没有改 P02 文件或重新定义规则。

## 3. 已运行的完整无渲染示例

`python -B -m battle_core` 实际执行：开局候选抽牌 → 攻击 → 加盾 → 治疗 → 结束回合 → 固定敌方攻击 → 下一玩家回合 → 施加 DOT → 结束回合 → 敌方入口 DOT 致死。

| 观测 | 实际值 |
|---|---:|
| 权威提交数／最终 revision | 10 |
| 逻辑事件总数／last_event_seq | 52 |
| BATTLE_FINISHED 的 seq | 51 |
| 最终结果 | WIN |
| 最终回合号 | 2 |
| P15 脚本候选调用 | 8 |
| P16 脚本意图调用 | 1 |
| 最终敌 HP | 0 |
| 最终第一名角色 HP／盾 | 10／1 |

最后一次敌回合在入口 DOT 后结束，未第二次调用 P16。上述为真实 P14 内存结算，数值和角色／卡 ID 均属隔离样例，不代表正式数值或完整游戏。

`battle_snapshot.json`、`battle_state.json`、`battle_result.json` 是实际运行后的规范 JSON 原字节；没有在文件结尾额外加换行。结果中的 `final_snapshot_sha256` 可以直接与 `battle_snapshot.json` 文件哈希核对。`examples/demo_replay.json` 可直接重放，`examples/demo_execution.json` 保留全部命令、答复及批次。

## 4. 文件入口

| 相对路径 | 用途／责任边界 |
|---|---|
| `battle_core/core.py` | P14 唯一提交、合法命令入口、回执、BattleResult |
| `battle_core/resolver.py` | 一次性临时结算、费用候选应用、效果／反应／终局 |
| `battle_core/model.py` | P14 私有不可变测试内容投影；不是 P22 正式 Schema |
| `battle_core/rng.py` | 显式 xorshift32 状态及候选跃迁验证 |
| `battle_core/replay.py` | 使用记录的输入重执行；不读期望输出生成结果 |
| `battle_core/wire.py` | 引用上游 P13 原 codec／Schema，未修改其字节 |
| `resolution_replay_tests/` | 当前合同边界、29 个 P02 语义场景、P03 8 个效果样例及确定性测试 |
| `examples/fixture_ports.py` | 明确的 P15／P16 脚本替身，不是生产牌堆或 AI |
| `battle_event_samples.json` | 实测示例、DRAW、BOSS 致死、DOT 与种子洗牌候选的批次样本 |
| `battle_result_schema.md` | 结果字段、哈希边界、不可变性及消费限制 |
| `handoff/IC05_API.md` | P15／P16／P19／P29 接线与错误语义 |
| `integration_handoff.md` | 下一位接收说明、环境差异与范围门禁 |
| `handoff/contract_acceptance.json` | P14 对 P13-RFC-001 的隔离接收回执 |
| `handoff/interface_rfcs.json` | 7 项带双方 base SHA 的接口／接入请求 |
| `handoff/path_mapping_request.json` | 给 P13 的实际路径请求；不冒充批准的映射 |
| `handoff/blockers.json` | 具体缺项、责任方与已可独立完成的部分 |
| `upstream/` | 78 份来源原字节／只读依赖及冲突证据；禁止修改 |
| `evidence/source_input_receipt.json` | 每份输入来源、版本、实际大小、SHA-256、父 ZIP 与固定树绑定 |
| `evidence/runs/` | 每次执行的命令、退出码、stdout／stderr、源码 ZIP 与逐件哈希 |
| `delivery_manifest.sha256.tsv` | 全交付文件大小／SHA／版本／来源／接收方／修改白名单 |

## 5. 验证结果的准确范围

| 层级 | 状态 | 说明 |
|---|---|---|
| P14 作者单元／回放 | PASS：97；BLOCKED：4 | 101 项发现，当前无 FAIL；含并发 24 次相同请求仅一次提交 |
| P02 旧格式场景 | 29 个语义投影 PASS，4 个 BLOCKED | 不是 33 个原格式逐字节通过 |
| P03 效果样例 | 8 个已启用效果实际执行 PASS | 两张 BUFF／DEBUFF 提议牌未启用 |
| 当前 P13 原校验器 | 作者合同边界 PASS | 命令、候选、状态、快照、答复、事件、批次、结果均走原校验器 |
| 第三方 JSON Schema 算法对照 | BLOCKED／NOT_RUN | `jsonschema==4.25.1` 不在当前环境；下载遇网络权限限制；第一次启动失败原日志保留 |
| 独立进程确定性 | PASS | 3 个 PYTHONHASHSEED 进程的 demo 输出摘要相同 |
| 原始输入未改 | PASS | 3 个上传附件、1,788 个展开成员逐字节哈希复核；586 条转交清单、281 条相关原交付清单通过 |
| 作者设计复核 | COMPLETED | 不是 P35 独立设计审核 |
| 正式路径／真实 P15、P16／目标环境 | BLOCKED | 详见实际缺项，不推断其他位置不存在工程 |
| P32 独测、P33 人工、P35 独审 | NOT_RUN | 未代签 |
| 引擎画面、真实动画、Anki、P21、E2E、跨模块整合／发布 | NOT_RUN | 本包没有执行这些验证 |

可选的算法对照入口为 `python -B tools/check_contracts.py`，缺依赖返回 3。它不是运行库必需依赖，不应为运行本包安装额外包。若测试负责人需要该项，在可用环境按 `requirements-dev.txt` 安装后执行即可。

## 6. 接口差异与尚未实现的范围

**P02 与 P13 事件格式不同。** P13 缺少若干 P02 中间过程事件；护盾、状态等也采用不同事件名／字段。本包完全保留 P13 冻结 Schema，以明确投影验证 P02 状态和能表达的事件；缺少的过程不能伪称已获正式兼容批准。映射明细见 `handoff/p02_projection_contract.md`。

**四个旧历史回执不能直接迁移。** F010／F011／F021／F028 只有旧规范下的 command SHA，缺完整旧请求和新回执范围。测试显式 skip／BLOCKED，未生成假的迁移 SHA。当前 P13 下的重复、碰撞、旧 revision 和新 ID 再打已弃牌等，使用真实提交历史独立实测。

**正式 P15／P16 未收到。** P14 没有实现抽牌算法、费用计算或敌方 AI。单 EnemyIntent 可执行；多存活敌人的行动批次合同未给出时拒绝 `ENEMY_BATCH_CONTRACT_UNBOUND`。这不改变首版怪物种类数量，P01 的候选规模仍未冻结。

**S07 阶段提交未接通。** 已做致死／存活阈值预检；当前 DTO 缺正式阶段命令和 epoch／行动槽状态，`inspect_phase_proposal()` 只校验后返回未绑定。有待提交阶段时不继续旧敌方行动。不能宣称完整 BOSS 多阶段机制完成。

**仅支持已明确规则。** BUFF／DEBUFF、DOT 重复叠层、正式盾上限、生产数值与正式内容 ID 仍待原 owner。测试 cap=40 仅验证 P05 候选的显式 CLAMP／REJECT 两种配置，不批准产品策略。

## 7. 修改和接收边界

P13 原 `actual_path_mapping.json` 对 P14 的 `runtime/battle/core/**` 和 `tests/battle_core_unit/**` 都标记 `BLOCKED_NOT_MAPPED / write_allowed=false`。本包未创建这两个真实工程目录，只在用户允许的新隔离交付目录中产生 `battle_core/` 与 `resolution_replay_tests/`。生产写入清单为空。

下游可以直接核验本包并运行测试。P15 先接 `handoff/IC05_API.md` 的纯候选接口，P16 接单意图及阶段阻塞说明；P19／P29 使用已提交 Batch 和 Snapshot；P32／P35 以固定交付哈希复测和审查。所有接收记录均为 **PREPARED_NOT_ACKNOWLEDGED**，没有通过工具向他人发送消息。工程最终合并仍交用户指定的 EXT-INTEGRATOR。
