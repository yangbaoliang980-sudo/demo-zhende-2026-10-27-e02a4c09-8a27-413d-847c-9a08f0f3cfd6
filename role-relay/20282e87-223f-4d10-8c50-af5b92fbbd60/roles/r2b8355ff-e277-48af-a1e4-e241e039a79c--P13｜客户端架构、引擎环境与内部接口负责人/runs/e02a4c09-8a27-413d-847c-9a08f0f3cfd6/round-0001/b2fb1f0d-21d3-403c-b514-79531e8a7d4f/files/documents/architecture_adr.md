# P13 架构决策记录｜0.1.0-isolated

任务：**P13-S00-ARCH-001**；承接 P01 **TASK-00-02**。日期：2026-10-29（UTC+08）。

本版完成实际输入盘点、隔离路径映射、内部接口与可执行框架。**目标引擎未冻结，正式 S00 Runtime 门禁 BLOCKED。** 作者验证与独立审查分列于 [verification_status.json](verification_status.json)。本文不代表 P32/P35 或外部契约 owner 签收。

## ADR-001：实际工程与运行时

**决定：使用现有 Python 3.12 运行本岗位隔离框架；游戏引擎保持 UNDECIDED。**

三份上传附件及其递归 ZIP 已实际解包。25 个不同 ZIP 的 CRC 通过，1,268 个文件成员已读取字节并建立哈希；484 条转交清单及 P01—P12 包内 642 条交付清单通过。两个指定固定 GitHub 树分别有 170/1,029 条对象记录，均未截断。树记录不等于逐个远端文件内容均已审阅；有本地原字节的条目才建立 Git blob/大小/SHA-256 绑定。[输入回执](source_input_receipt.json)、[盘点](engineering_inventory.tsv)

当前获得的是规则、内容候选、校验器及 P10/P11/P12 隔离 Python 组件。未发现可识别的 Godot/Unity 等游戏工程入口。当前主机为 Linux x86_64，Python 3.12.14、Node v24.22.1；Godot/Godot4/Unity/.NET/Anki 未在当前 PATH 发现。该判断只覆盖已检查文件和本执行主机，不推断用户其他电脑或仓库不存在工程。[原始探针](evidence/runs/environment_probe_001/stdout.log)

Python 可运行的证据不能证明任何游戏引擎可启动。不会把 Node 的存在当作 Electron 桌面方案获批；不会因 P12 是 Python 就决定游戏必须使用 Python。P11/P12 代码应复用，跨语言映射或进程边界由各 owner 评估；原代码保持原字节。

**待决：** P01 的 DEC-005/DEC-006/DEC-012，真实源码根目录/commit、P34 目标机证据及实际引擎探针。Godot、Unity 与现有框架的证据比较及命令见 [engine_runtime_comparison.md](engine_runtime_comparison.md)。没有基于虚构性能或未核验许可证作成本打分。

## ADR-002：路径与所有权

**决定：只有新建 P13 交付根内的 `architecture/**`、`contracts/internal/**`、`runtime/framework/**` 可写。** 包级 README 与交付清单是包装元数据。`architecture/evidence/upstream/**` 是原 owner 的只读副本，不能因父目录属于 P13 而覆盖。

[actual_path_mapping.json](actual_path_mapping.json) 同时保存此次观测的绝对路径、可移植包内路径、授权依据、只读输入，以及真实生产路径的 `null`。它冻结了隔离包的位置，**没有完成真实游戏工程映射**。P12 已交付的 archived 源码可定位和复核；真实宿主修改白名单仍未授予。各岗位规划目录从 V6 原文读取，不在本包创建占位生产目录。

任何新实际工程到达时，先核对固定 commit、目录、文件哈希与原 owner；另出映射版本。`path_guard.py` 用于发现路径越界、上级目录和符号链接误用，是本地协作检查，不是操作系统沙箱或针对恶意同进程代码的安全机制。

V6 的 P29“负责范围”使用 `ui/battle_animation/**`，而“具体交付”又写 `runtime/animation/**`。已保留同一源文件的两个锚点并登记 `P13-CR-001`；真实路径保持未映射，由 P01/P29 澄清，未擅自合并两个目录。[RFC/CR](../contracts/internal/interface_rfcs.json)

## ADR-003：领域层、候选层与物理提交

| 数据/能力 | 唯一业务或提交 owner | 可依赖的上游 | 其他岗位的界限 |
|---|---|---|---|
| BattleState、战斗费用、牌区、revision/seq、BattleResult | P14 | P02 规则、P15 候选、P16 意图、P22 内容版本 | P15/P16/P19/P29 不写权威状态 |
| 抽牌、牌区与费用候选 | P15 | 只读快照、P03/P05 数据 | 返回 DeckPatchCandidate；不自行扣费 |
| EnemyIntent、PhaseProposal | P16 | P06 行为定义、只读快照 | 不直接写 HP/phase |
| StudyLedger 资格/修正族/隔离 | P11 | P08 已批政策、P10 事实、P12 传输 | 不替 P17 算钱包，不替 P21 落盘 |
| Wallet、Party、Character 业务 | P17 | P04/P05 规则、P11/P18 权益请求 | 唯一计算可用/预留/消费候选 |
| StageProgress、首通/重复领取业务键 | P18 | 可信 P14 BattleResult、P07 规则 | 不制造战斗结果，不占用学习身份 |
| 游戏物理存档、原子性、备份、迁移、恢复 | P21 | 各领域不可变候选 | 不重新决定奖励资格或奖额 |
| HUD 绑定与最终显示 | P19 | P14 权威快照 | P29 仅通过公开显示适配器 |
| 动画播放与临时显示插值 | P29 | 已提交事件、P19 显示租约 | 不通过命中帧结算伤害 |

P14 的“提交”指单场战斗权威状态的原子替换；若以后保存战斗进度，游戏文件/数据库的物理写入仍由 P21 完成，不能因此出现第二套费用业务逻辑。P17 的 WalletDelta 是业务候选，P21 只执行经核验的事务和并发约束，不能自行绕过 P17 加减余额。

`StudyLedger + Wallet`、`StageProgress + Wallet`、`Character + Wallet` 应由 P21 一次性提交。没有生产原子合同就不得“先扣钱后补盘”。本包只给形状和端口提案，没有实现这些业务或存储。

IC owner 维持 V6：**IC-02=P13、IC-05=P14、IC-08=P13、IC-19=P21、IC-25=P32**。P13 拥有共享 DTO 形状，不因此取得 IC-05/19 的业务合同批准权。[V6 原文](evidence/upstream/P12/sources/baseline/v6_freeze.txt)

## ADR-004：版本、整数与确定性

**决定：隔离契约版本 `YLTT-INTERNAL/0.1.0-isolated` 精确匹配；对象封闭，未知字段和版本拒绝。**

采用 UTF-8 JSON、ASCII Schema 键、数组原序、键排序、无多余空白、整数十进制和 SHA-256。禁止浮点、NaN/Infinity、重复键、BOM、孤立 surrogate、控制字符与不安全整数。线上的数值范围为 `[-(2^53-1), 2^53-1]`，字段再施加非负等约束；bool 不视为整数。

P02 请求明确 64-bit/序列化。本版选择 **目标实现使用检查溢出的整数运算，跨语言 JSON 接口限制为安全整数范围**；不直接输出整个 int64 范围，以免 JavaScript 数字丢精度。若后续确需超过此范围，提交新版本 RFC，选择十进制字符串表示并提供跨语言向量，不能静默放宽。此为技术接口边界，不是卡牌数值/经济上限审批。

P02 提议的 `xorshift32-v1` 被记录为隔离 RNG 状态形状与回放标识；P13 未写洗牌或战斗随机算法，P14/P15 的实现测试仍 NOT_RUN。不得把主线程帧率、动画状态、系统时间或 Anki 消息到达顺序加入战斗随机性。[P02 规则](evidence/upstream/P02/spec/battle/state_machine/battle_state_machine.md)

相同 battle_id/command_id 的已接受命令应先检查规范指纹，再检查 expected_revision；相同指纹重复不产生新提交或新事件，冲突指纹拒绝。此由 P14 实现；本包的线程邮箱不做第二套去重数据库。[契约语义](../contracts/internal/contract_semantics.md)

## ADR-005：宿主线程与背压

网络/本机 IPC I/O 放在 P12 的工作侧；解析后的不可变消息通过有限容量队列进入确定的领域执行线程。P14 按 battle_id 串行提交，跨线程传递不共享可变对象。游戏主线程接收只读提交批次并负责界面，禁止工作线程直接操作引擎节点。Godot 官方文档明确活动场景树不能任意跨线程交互；具体目标引擎的调度适配仍须实测。[Godot 线程文档](https://docs.godotengine.org/en/stable/tutorials/performance/thread_safe_apis.html)

本包 `CommandMailbox` 已实际测试工作线程入队、所属线程 drain、队列满、close 后已有请求继续 drain、域调用异常和返回作用域错误。它只证明通用宿主边界。**QUEUED_NOT_COMMITTED 不是 ACK_APPLIED。** 领域调用可能在提交后抛错，邮箱只返回 OUTCOME_UNKNOWN，不假装业务拒绝或奖励成功。

队列容量 64 和单次 drain 默认 16 是隔离框架工作预算，不是目标机性能指标或用户玩法限制。容量可配置但有结构界限。真实 P12 ingress 不在本轮接到该邮箱，也没有把此队列替代其耐久 outbox。

## ADR-006：显示与动画

`BattleCommitBatch` 将同一 revision 的权威快照和完整连续事件一起发布；事务失败不发布缓冲事件。批次首事件 COMMAND_ACCEPTED、末事件 COMMAND_COMMITTED；P19 根据最终快照绑定数值。P29 只做临时插值与表现，损伤数字来自 P14 事件，不从 HP 差值反推新的结算。

`BattleStreamGuard` 校验 battle_id/revision/seq；同批重复不再接受，缺口或冲突请求新快照，不部分应用坏批次。取消、跳过、掉事件、后台恢复和新战斗切换均不得改变 BattleState。实际 P19/P29 控件、租约与动画实现仍 NOT_RUN；本包只提供接口与 Spy 测试。[视图适配合同](../contracts/internal/presentation_adapter_spec.md)

## ADR-007：P12 的结构耦合与正式放行

已读到 P12 `bridge.py` 中 `_row()`、`_verified()` 对 `snapshot.ledger['inbox']`、`families`、`last_commit` 等 P11 内部结构的访问。当前原始隔离测试可复现，但这些内部字段不应成为无版本的正式 UI/传输 API。

给出 `StudyStatusQuery/StudyStatusView` 和 `StudyResultReader` 作为只读投影提案，并以 `CommitProofView` 绑定 P21 的实例、水位、连续性和事务引用。投影的创建由 P11/P21 负责，P12 由原 owner 修改自己的 bridge。P13 没有改写上述源码或重写其 wire 协议。Schema 验证通过也不证明真实来源或耐久提交。

`UNKNOWN` 与连续性已证明的 `NOT_FOUND/ABSENT` 分开；`REVERTED` 不映射为新增授奖；`QUARANTINED` 不显示到账；待对账可能已有部分经济变化，不能写“毫无变更”。这些边界继承 P08/P11/P12 的实际工件。[P12 原交接](evidence/upstream/P12/INTEGRATION.md)、[P08 语义](evidence/upstream/P08/spec/anki/reward_semantics/study_policy_draft.md)

## 取舍与门禁

当前选择减少了重复实现：P13 交付可执行通用框架，P11/P12 保持原字节，P14—P21 的业务仍由原 owner 交付。代价是没有可点击的战斗游戏、没有目标引擎构建，也没有真实 Anki 联动。下一位可直接复现作者测试、使用固定 DTO 和隔离端口，不应把这些结果升级为 S03 完整竖切或 S08 集成完成。

所有尚缺工件及唯一推进 owner 见 [blockers.json](blockers.json)。跨模块整合仍等待用户指定 EXT-INTEGRATOR；P35 独立门禁仍 NOT_RUN。
