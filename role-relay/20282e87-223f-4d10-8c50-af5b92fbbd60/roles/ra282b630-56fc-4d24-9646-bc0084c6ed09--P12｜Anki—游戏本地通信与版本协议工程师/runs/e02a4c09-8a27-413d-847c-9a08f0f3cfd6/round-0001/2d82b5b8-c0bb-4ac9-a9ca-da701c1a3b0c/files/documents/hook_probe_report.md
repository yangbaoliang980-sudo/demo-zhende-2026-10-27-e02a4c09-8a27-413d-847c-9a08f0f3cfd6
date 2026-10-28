# P10｜Anki Hook 探针与来源身份报告

任务：**P10-S04-PROBE-001**。报告版：**P10-PROBE-REPORT/0.1.0**。日期：2026-10-28（UTC+08:00）。关联需求：REQ-011、REQ-025；边界需求：REQ-012、REQ-026。接口：IC-14（owner P12）、IC-15（owner P09）。

**结论：PROBE_REPORT_DELIVERED / S04_TARGET_BLOCKED / QUARANTINED。** 真实复习原始样本为 0，真实 Undo 样本为 0，可支持的目标 Anki 版本集合为空。S05 插件、持久 outbox、安装包与插件单元测试尚未实现/执行。本文及配套检查程序不授权任何事件发奖。

本次用户启动了 P10 的证据核验与可独立推进工作。V6 原文明确要求：事件世代或 Undo 证据缺失时只交探针报告及 QUARANTINED 标志。本包依此交付报告及可执行复核附录，不把附录称为可运行插件，不以占位安装包代替未完成实现。未修改正式工程、Anki 数据库、调度器、游戏账本或 IPC 合同，未进行跨模块整合。

## 1. 已实际核验的输入

两份用户上传 ZIP 已逐成员读取并安全解包，内嵌 ZIP 按完整 SHA-256 去重后递归读取。共 15 个唯一 ZIP、612 个归档文件成员；全部成员 CRC 通过，260 条 relay manifest 的大小/哈希检查通过。260 包含内层封装中的重复交接，不是 260 个独立开发成果。原始上传的附件条数为 103 + 4 = 107。

P09 完整包：5,041,990 字节，SHA-256 `d2418d564772963d1434bc4c3cf03a33c6a7887fdc684814b9bce1a1b0ff702a`。P08 完整包：2,523,333 字节，SHA-256 `c61826ec9af75cbd0a426f13b3f9c40f852f83f69c11093655fb4214419e612f`。另实际逐项复核了 P08/P09 两份内部交付清单，共 146 条，未发现字节漂移。

通过 GitHub 连接重新读取的固定文件树未截断：P09 提交 `6b826ac5c04b96fb84c05a469782d1658b5fc6a0`（541 个树项）；V6 提交 `8c370d731c323f86ff19642f4cc73f818498f641`（170 个树项）。本地 P09 ZIP 与 V6 正文分别重新计算 Git blob SHA-1 和 SHA-256，与固定树记录一致。SHA-1 在此只用于 Git 对象绑定，不替代交付 SHA-256。

| 输入 | 实际状态 | 本岗可使用范围 |
|---|---|---|
| V6 冻结正文、P01 需求与追踪表 | 已读取、已核验字节 | 岗位边界、REQ-011/025、启动与隔离门禁 |
| P08 有效复习草案与 IC-14 RFC | 已读取；proposal | 观察真实完成、来源身份、修正族的语义约束；不是批准的奖额 |
| P09 字段报告和字段协议建议 | 已读取；真实观察数 0 | 后续最小授权字段观察；不是实际牌组字段表 |
| P12 正式跨进程 Schema/ACK 合同 | 未收到 | S05 实现 BLOCKED；不自造正式 Envelope |
| P13 actual_path_mapping、白名单、真实工程 base commit | 未收到 | 正式工程写入 BLOCKED；本包目录只是隔离报告目录 |
| P34 目标 Anki 完整版本/build、OS、测试机 | 未收到 | 目标版 Hook 实测 BLOCKED |
| P38 字段与测试档案授权 | 未收到 | 不读取笔记、卡片、标签、集合或个人路径 |

缺失结论仅覆盖本次附件和上述两个固定项目树，不推断用户其他仓库或电脑不存在这些资料。完整原字节快照、归档成员链、来源版本、SHA-256 在 `source_input_receipt.json`；原始检查证据在 `evidence/intake/`。没有对无关战斗、美术等模块作功能验收。

## 2. 实际执行环境与证据等级

报告检查在 Linux、Python 3.12.14 下运行。仅检查当前 Python 的模块可发现性和 PATH：未发现 `anki`、`aqt` 或 Anki 可执行入口。没有启动 GUI，也未扫描个人 Anki 配置目录。这是执行宿主的检查结果，不是用户目标机环境。

`anki_hook_probe.py preflight` 的原始输出被保存为 `probe_log_redacted.txt`，记录类型明确为 `ENVIRONMENT_AND_INPUT_PREFLIGHT_NOT_REVIEW_LOG`。该文件不含卡片样例，也不是“脱敏后剩下空记录”的真实复习日志。未采集个人字段，无需用伪造记录填充。

| 层级 | 当前结果 | 证明边界 |
|---|---|---|
| 上传 ZIP、relay 清单及 P08/P09 内部清单 | PASS | 文件完整性，不是功能通过 |
| 固定 Git blob 绑定 | PASS | P09 包/V6 原文来源对应，不是目标 Anki 环境 |
| 官方固定源码静态提取 | PASS | 仅源码中的 Hook 声明与参数 |
| 报告检查器作者单元测试 | PASS，18/18 | 防止完整性错误和错误升级证据，不是插件单测 |
| 目标版真实四键/Undo/redo/备份 | NOT_RUN，前置 BLOCKED | 没有可声明支持的事件 |
| 插件 outbox 单元/离线重试/停用回归 | NOT_RUN，实施 BLOCKED | 没有把检查器测试替充 outbox 测试 |
| 正式契约、目标机、E2E | NOT_RUN | 未连接 P11/P12/P21 或真实 Anki |
| P32 独测、P33 人工、P34 兼容、P35 独审、P38 权限审核 | NOT_RUN | 本岗未替这些岗位签字 |

最终作者命令、stdout、stderr、退出码及执行前输入哈希见 `evidence/author_run_002/`。前置检查退出 3 是真实 BLOCKED；“按预期阻塞”不代表前置门禁 PASS。

## 3. 官方源码静态观察：限定到一个固定提交

参考仓库为 [ankitects/anki](https://github.com/ankitects/anki)，固定提交 `d87cb22bf337c52257376f3abcec09c03a255ed4`。该提交 `.version` 的原字节是 `26.09.3`。**这是公开源码参考，既不是用户指定的目标版本，也不是本次已安装运行的版本。** 不据此推荐升级或宣布版本兼容。

源码按原字节保存于 `sources/anki_reference/`，来源路径、文件 SHA-256 与 Git blob SHA-1 在 `reference_inputs.json`。保留官方版权头及 LICENSE。这些只读参考代码不属于本岗原创插件实现，不应复制进正式插件目录。

| 观察点 | 此固定源码实际内容 | 对 P10 的限制 |
|---|---|---|
| 复习完成通知 | `reviewer_did_answer_card(reviewer, card, ease)`，ease 类型为 Literal[1,2,3,4] | 参数中没有直接声明原生复习唯一键或撤销目标；不能仅凭 card 对象生成权益身份 |
| 评分映射 | `V3CardInfo.rating_from_ease` 中 1→Again、2→Hard、3→Good、其他分支→Easy；调用输入另受 Literal 类型声明约束 | 仅记录这一提交的映射，目标版本仍须四键逐项实测，不自行接收未知评分 |
| 完成回调位置 | `reviewer.py` 的 `answer_card(...).success(after_answer)` 进入 `_after_answering` 后触发 did_answer | 按源码可定位成功路径；未证明此目标环境的落盘时点、崩溃可恢复性或所有回答入口覆盖 |
| 前置评分过滤器 | `reviewer_will_answer_card` 可以影响是否回答及 ease | 本岗不注册可改变评分/调度的过滤器，不把它当完成证据 |
| Undo 通知 | 生成器声明 `state_did_undo(changes: OpChangesAfterUndo)`；官方 operations/collection.py 的 Undo 成功回调触发它 | 存在观察入口，但原复习目标、连续 Undo、非复习 Undo 与跨重启身份仍未实测 |
| Undo 返回结构 | collection.proto 的 OpChangesAfterUndo 声明 changes、operation、reverted_to_timestamp、new_status、counter；UndoStatus 声明 undo、redo、last_step | 字段存在不证明其跨重启/备份稳定，不把 counter/last_step/时间戳单独冻结成事件 ID |
| redo 路径 | 此提交 operations/collection.py 的 redo 成功回调显示提示；同一 Hook 生成器没有 `state_did_redo` / `state_did_revert` 声明 | 不虚构专用 redo Hook；通用操作通知是否足以可靠关联仍是未验证能力 |
| 通用操作通知 | operations/__init__.py 将结果提取为 changes，再调用 `operation_did_execute(changes, initiator)` | 不能把它的参数假装成完整 OpChangesAfterUndo；普通编辑/reset 也不能一律当复习完成或 Undo |
| 菜单状态通知 | `undo_state_did_change(info)` 的 UndoActionsInfo 包含 can_undo/can_redo、文本、show_redo | 菜单文案/可用状态不是稳定的复习关联凭证，不按本地化文案猜目标 |
| 备份/加载通知 | 可找到 backup_did_complete、collection_did_load、profile_did_open 及临时关闭相关声明 | 不能仅凭这些通知推导备份谱系、新世代、历史消费水位或自动恢复授权 |

观察依据是 `qt/tools/genhooks_gui.py`、`qt/aqt/reviewer.py`、`qt/aqt/operations/collection.py`、`qt/aqt/operations/__init__.py`、`qt/aqt/main.py`、`qt/aqt/undo.py`、`pylib/anki/collection.py` 和 `proto/anki/collection.proto`。配套脚本通过 AST 读取声明，不导入或运行这些文件。上述“未声明”只描述本次参考文件，不等于断言所有 Anki 版本都不支持某能力。

版本差异验证为 NOT_RUN：尚无用户目标版本与运行样本可比较。升级、降级或发行包补丁差异需新回执，不能把本次 main 分支快照当作兼容范围。

## 4. 身份与 outbox 的关键工程边界

P08 已要求区分真实复习事实、投递身份、修正族和权益身份。P09 的 scope_ref/subject_ref 用于分类，也不等于复习事件唯一键。此轮没有冻结任何新的来源身份构造策略。

`card_id` 标识卡片；同卡正常下一次复习应可与前一次区分。同卡在 Undo 后再次回答，却不足以单独证明是 redo、替换原事实或新的正常复习。`card_id + rating`、`card_id + 毫秒时间`、每次启动生成 UUID、回调本地序号、协议版本、映射版本或游戏存档 ID，均不能自行获得业务防重与备份谱系证明。

即使目标版能观察某个 revlog 标识，也须证明它与这次成功完成的关联、跨集合/克隆/旧备份/重装行为，以及 Undo/redo 对它的影响。当前未读数据库，不以“查最后一行”推断目标事件，不补造 collection epoch。缺这些证据时 `source_generation`、`review_event_identity`、`undo_target_association` 均为 UNVERIFIED。

**持久 outbox 不能自动消除捕获窗口。** Anki 原生提交、GUI 回调、插件自身持久化是不同步骤；若崩溃发生在提交之后、插件入队之前，重试尚未入队的记录并不能恢复它。下一版必须证明目标版官方只读能力足以识别缺口并恢复来源，或诚实报告不能无损补采、隔离受影响范围。禁止为实现所谓原子入队而修改 Anki SQLite 或调度器。

已入队事件将来应持久保留最初来源证据和身份，重试不得重新造“新复习”；ACK 的处理必须消费 P12 批准合同。不能把 ACK_QUARANTINED 显示为到账，不能在未知 ACK、超时或连接失败时擅自删记录。本轮没有 ACK、IPC 或队列实现，因此不声称上述可靠性已实现。

## 5. 最小采集与脱敏边界

本轮实际采集用户学习字段数为 0。下表只列待 P38/P12/P08/P01 评审的观察需求，不是新增的获批字段或正式传输 Schema。相应版本化提案见 `rfc_ic14_ic15.md`。

| 信息组 | 观察目的 | 当前处理 |
|---|---|---|
| 完整 Anki 版本/build、OS、采集器版本、能力回执哈希 | 绑定运行证据适用范围 | 目标环境未收到 |
| 实际 Hook 名称、参数形状、实际评分值与确认语义 | 验证完成路径与四评分 | 无真实日志；不把显示答案当完成 |
| 经证明的来源作用域、每次完成身份及世代证据 | 复习事实与重复投递区分 | 全部 UNVERIFIED，不选择身份算法 |
| 原完成关联、Undo/redo/替换重答证据 | 修正族与撤销正确性 | 关联缺失时隔离，不猜前一条 |
| 获准 note type/template 作用域与最小类别/词性标签状态 | 交给 P09 分类 | 不假设 Front/Back、GameCategory 或“品詞”真实存在 |
| 本地投递序号、重试状态、不可变来源快照摘要 | 未来队列可靠性 | 仅技术投递元数据候选；不得变成复习唯一键 |

默认不读取词条正文、整句、答案 HTML、全部标签、媒体、牌组名称、账号、集合绝对路径或整库导出。存在一个获准且足够明确的类别标签时，不扩大到 P09 合成示例的五个字段。P09 定义的 READABLE/MISSING/UNOBSERVABLE/READ_ERROR/NOT_AUTHORIZED 语义可以供下一版接收评审；任何实际字段都需绑定目标版、授权范围与快照。UNKNOWN 分类不能修复未授权或不可信的来源事件。

分享日志前应按获批方案保持同卡/同事件/Undo 目标的可比较关系，同时去除正文与本机身份信息。简单哈希不自动等于匿名化，密钥或原始映射不得和公开样例同时交付。当前尚无真实样本可进行这一验证。

## 6. 真实验证的精确缺口

`sample_inventory.json` 已记录 14 项真实场景的 NOT_RUN 状态，raw_samples 为空；它是样本索引和缺口记录，不是“已有样例”的替代品。范围包括四评分、复习/非复习 Undo、redo、正常同卡复习、Undo 后改评分重答、备份恢复、提交到入队的崩溃窗口、离线重启重试、禁用回归与卸载。

目标机运行时，每条样本必须绑定完整目标版号、OS、获准测试档案、授权哈希、采集方法、真实顺序、期望与实际行为、脱敏原始日志哈希。先区分以下实际可观察情况，再提出任何身份策略：

- 四个评分分别完成，不要求靠修改调度器强制得到同卡。
- 同卡正常再出现，与 Undo 后重答分开记录；redo 与重新按评分键分开记录。
- Undo 混入编辑等非复习操作时，证明不会撤错最近一次学习事件。
- 使用 Anki 官方备份/恢复路径验证历史回退；不直接编辑 SQLite。测试档案与数据留存需先获授权。
- 分别验证“已经入队后离线重启”和“提交后尚未入队就退出”；两者的可靠性结论不得合并。
- 插件禁用、未知目标版本、采集异常及队列存储错误时，真实验证 Anki 自身的学习流程不受损。没有运行就不能写 PASS。

此处是现有职责的验收缺口说明，不新增角色、不代替 P32/P33 执行，也不把未来命令写进本次原始运行日志。

## 7. 降级与交接

当前一律 `production_award_authorized=false`；不生成 IPC 学习事件，不安装插件，不查询/修改钱包，不伪造撤销。QUARANTINED 是本岗能力门禁标志，**不是 P11 已持久接收事件的 ACK_QUARANTINED**。当前连待隔离的真实事件也没有。

P11 接收零样本、UNVERIFIED 身份及禁止发奖结论；P12 接收固定源码观察与 IC-14 语义提案；P09 接收“仍无真实字段”的回执；P34 接收目标环境缺项；P32/P33 接收源码、作者原始证据及 NOT_RUN 场景；P35 接收完整性和分级状态；P36 接收不可安装、不可发布的交付描述。P13/P38/P08/P01 处理各自的路径、授权、政策和版本接收项。逐件绑定在 `downstream_handoff.json`。

所有下游接收状态为 PREPARED_NOT_ACKNOWLEDGED，没有代签。没有发消息、提交 PR、推送 GitHub 或宣布整合成功。未来取得新输入时，由 P10 记录旧/新 SHA 和 ChangeRequest 后提交新版本；保留本版 NOT_RUN 与原始记录，不把本包布尔标志改成 true 冒充解禁。
