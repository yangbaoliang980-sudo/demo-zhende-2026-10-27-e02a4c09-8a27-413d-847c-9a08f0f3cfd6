# 下一位接收说明｜P15 S02 隔离交付

交付 `P15-DECK-RUNTIME/0.1.0-isolated`，P01 任务 `TASK-02-01`。已收到并核验 P02/P03/P13/P14 固定工件；P14 原 ZIP 为 `a439f32c482117e29586f98350d63a0e2a1ddd7efd4c7578f3cd05a42b4f6068`，对应用户指定提交 `bc2b2daae2a1e784fb136f0a4e32cc84d84d84c6`。完整输入路径/大小/哈希在 `evidence/source_input_receipt.json`。

## 当前可接收内容

P14 可直接在隔离测试装配中接 `deck_runtime.p14_adapter.P14DeckAdapter`，将实际模块的 CandidateRejected 通过 `rejection_type` 传入；不要在 P14 中添加第二套费用计算。构造前会核对规则、效果与 draw-report 数量。纯入口、输入和返回语义见 `handoff/P15_API.md`。

P19 可依据非法案例及错误码展示提示；用户入口只生成 PLAY_CARD/END_TURN 的 P13 BattleCommand。request_id 对应 command_id，重试保持完整原请求。显示端以 P14 已提交快照/批次为准，不能把 P15 候选当成已经扣费、移牌或命中。P15 ActionIntent 是本地引用证据，没有另行获得共享消息生产权限。

P32 可解压后运行 README 的校验、148 项作者用例、固定种子、完整命令重算和原 P14 模块名探针；请自行生成独立日志并记录所测 ZIP/manifest SHA。`evidence/runs/author_003/` 是作者记录，不能继承为 P32 PASS。P35 应审查源输入、原字节未改、异常修复、隔离/正式边界及接收方权限后独立给结论。

P33 可复核 CLI 输入/输出与错误语义；真实 UI、手柄/鼠标、动画、桌面目标环境与 Anki 不在本包人工通过范围。P03/P05/P17/P22/P13 按 `handoff/blockers.json` 和 `interface_rfcs.json` 补其独占工件。

## 正式接入仍阻塞

P13 原映射对三条 P15 规划路径 `runtime/battle/deck/**`、`runtime/battle/card_actions/**`、`tests/deck_unit/**` 均为 `BLOCKED_NOT_MAPPED / write_allowed=false / actual_production_path=null`。本包不改此映射，生产白名单为空。`deck_runtime/` 和 `deck_unit_tests/` 是本次新建隔离交付路径，不是正式实际路径映射。

缺失真实 P17 PartySnapshot 及 owner 回执；当前三席输入来自 P13 形状与 P03 mock 角色的作者夹具。P03 模板、九牌配方、初始/回合抽牌、手牌上限、公共牌实例归属、能量恢复和死亡角色牌政策尚非正式批准。P22 全局 ID/Schema 和真实引擎/OS 未收到；没有借测试数量决定首发规模或零学习日政策。

共享合同还缺负向候选、独立 ActionIntent、构筑输入/建牌初始化以及 requested/drawn/shortfall 等正式字段。当前保留原 DTO，负向使用 P14 原 Python 异常，构筑只交未提交牌区投影，抽牌报告在本地决策证据里；P14 使用匹配的冻结 entry_draw_requested。正式协议需 P13/P14/P03 接收新 RFC。

## 已修复接线缺陷

`P15-DEF-001`：旧 P15 适配器引用 vendored CandidateRejected，在原 P14 包名导入时异常类型不匹配。实测费用不足被误作 INTERNAL_RESOLUTION_ERROR，战斗进入 FAULTED，energy 保持 0。失败记录在 `evidence/runs/adapter_identity_001/`，未删除失败源码。

修复只改 P15：拒绝异常类改为必须由当前 P14 装配端注入。`adapter_identity_002` 已返回 ENERGY_INSUFFICIENT/REJECTED，全部权威字节不变；最终作者测试含此回归且全部通过。P32 复测与 P35 关单仍待执行，未自行代签。

## 包与修改边界

`upstream/` 原件均只读。P14 原 ZIP 另存于 `upstream/archives/`，原 P14 源码在 `upstream/P14/battle_core/`；P13 原 codec/Schema 在 `upstream/P13/`。这些拷贝仅为了可复现测试，不是转移所有权。若发现上游问题，保留双方 base SHA、新证据和 ChangeRequest，不覆盖源文件。

每件文件的 owner、格式、版本、source_input_hashes、recipients 和 modification_whitelist 在 `delivery_manifest.sha256.tsv`。manifest 不含自身哈希，自身与 ZIP 由包外 `delivery_receipt.json` 绑定；独立导出和包内对应文件须原字节相同。全部接收状态都是 PREPARED_NOT_ACKNOWLEDGED。

后续正式源码合并、目标工程装配或发布须由用户指定的 EXT-INTEGRATOR 执行。本轮没有仓库写入、跨模块合并、真实游戏发布或 Anki 联动通过声明。
