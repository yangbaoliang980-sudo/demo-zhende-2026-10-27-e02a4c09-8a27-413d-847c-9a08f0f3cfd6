# P03｜《言灵旅团》S01—S02 卡牌内容与三人卡组规则

**版本** `P03-CARDS-0.1.0-draft`；**本地任务标识** `TASK-P03-S01-S02-LOCAL-001`（P01尚未为本岗在所提供 task_register 版本确认正式任务编号）；**生产岗位** P03；**状态** `LOCAL_CONTENT_DELIVERED / FULL_CONTRACT_BLOCKED / P32_P35_NOT_RUN`。

本包是本岗实际生成的内容候选和可执行的离线静态校验脚本，不是单纯计划；同样不是可运行游戏、P15牌堆实现或真实Anki联动。绝不包含正式游戏引擎源码修改、战斗写事务、抽牌/费用扣减代码、P22 Schema修改和其他岗位路径。

## 正式实体文件

- `content/cards/card_catalog.json` — 3张S01基础牌，S02第四类DOT，4张mock角色槽专属牌，以及2张禁用的BUFF/DEBUFF提议牌；全部TEST_ONLY且数值P05未批准。
- `design/cards/party_deck_rules.md` — 三人合成卡组、手牌/弃牌/洗牌界限、案例与不确定政策。
- `content/cards/card_effect_examples.json` — 攻击/盾/治疗/DOT整数样例、增益/减益未实施示例。
- `content/cards/card_choice_cases.tsv` — 固定初始状态的多个合法出牌分支和非法条件；非P14真实战斗命令日志。
- `content/cards/choice_scenarios.json` — 与案例配套的初始场景数据。
- `content/cards/card_dictionary.tsv`、`content/cards/character_card_pool.tsv` — 卡牌词典和专属关联。
- `content/cards/deck_build_fixtures.json` — 4P3=24个mock三人编队实例构筑期望。
- `design/cards/card_keywords.md`、`design/cards/card_effect_event_map.tsv`、`design/cards/interface_rfc_blockers.md` — 关键词、只读事件表现映射、RFC/缺证据清单。
- `content/cards/validate_card_content.py` — P03本岗数据**静态**校验与反例注入脚本（不实现 P15/P14）。
- `source_input_receipt.tsv`、`downstream_handoff.tsv`、`P03_static_validation.log`、`manifest.sha256.tsv` — 实际输入来源、交接与校验记录及逐文件大小/哈希。

## 真实执行的可复核静态校验

在本包根目录执行：

```bash
python content/cards/validate_card_content.py
```

如果同时持有 P01/P02 原始ZIP，可追加：

```bash
python content/cards/validate_card_content.py --p01 "<P01完整ZIP路径>" --p02 "<P02完整ZIP路径>"
```

校验会检查全部本地卡/effect/skill/mock character引用、选择场景、24个有序队伍、样例整数关系，并对故意注入的重复ID/悬空引用/非法费用等坏输入要求正确拒绝。实际运行stdout/退出码保存在日志；它绝不调用P14实际引擎，也不能代替P22全局 ID/Schema linter或P32独立验收。

## 输入证据及影响限制

P01完整ZIP SHA-256 `139034e2179fbe35c4ac5f3240b0df435b03b9a70f5507263ee97b7e8b022a89`；P02完整ZIP SHA-256 `969c7e7688f795aaea80abddc0c4ed949f5f6b9d8588c2e787a0f9da1fb06501`。均经本次ZIP CRC和成员manifest哈希核验。固定V6提交 `8c370d731c323f86ff19642f4cc73f818498f641` 通过GitHub连接只读核对，但远端文本内容未在本地重新SHA256，不能把git blob SHA冒充SHA-256。

单独附件 `decisions_pending(2).tsv`/`effect_priority(1).tsv`只有11字节；使用独立 ZIP 内完整文件、未对原附件修复/重写。具体逐文件哈希在 `source_input_receipt.tsv`。

正式项目 `actual_path_mapping.json`、目标机/引擎、P22注册表、P04角色模型、P05数值、P08学习政策缺失，因此本包路径只是**可审查隔离工件**，不得直接映射为工程中已存在相同文件。只交由P05/P13/P15/P22/P24/P32/P35审查签收，独立审查未发生。

## 验收分级

| 项 | 状态 |
| --- | --- |
| 实体文件生产/本岗静态内容校验 | 详见真实 `P03_static_validation.log` |
| 4P3编队构筑、0本地悬空/重复引用 | 详见本岗静态校验，**仅MOCK集合** |
| P22全域ID/正式Schema | BLOCKED/NOT_RUN |
| P04角色、P05费用数值、P08零学习日政策 | BLOCKED |
| P13 DTO与 actual_path_mapping | BLOCKED |
| P15牌堆真实单元/契约，P14战斗执行 | NOT_RUN |
| P32独立自动化，P35独立门禁 | NOT_RUN |
| 目标机、真实 Anki、UI、E2E、正式集成 | NOT_RUN |

修改白名单：仅 `design/cards/**`、`content/cards/**`，且须经P13路径映射与所有权授权方可转入真实工程；根部交接日志/manifest是独立包的元数据，不是工程白名单请求。
