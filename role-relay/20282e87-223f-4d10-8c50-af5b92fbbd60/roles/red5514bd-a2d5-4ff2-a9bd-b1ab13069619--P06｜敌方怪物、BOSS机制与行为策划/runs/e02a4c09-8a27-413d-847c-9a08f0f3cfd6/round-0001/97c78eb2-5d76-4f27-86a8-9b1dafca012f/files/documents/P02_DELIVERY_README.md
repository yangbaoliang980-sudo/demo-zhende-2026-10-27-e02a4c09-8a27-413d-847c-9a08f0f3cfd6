# P02｜《言灵旅团》S01 独立战斗规则实体交付 v0.1.0-draft

**交付任务** `TASK-01-01`；**作者岗位** P02｜核心战斗状态机与结算规则设计师。

## 一、这是什么（与实际工程的界限）

这是一份**实际存在并已通过本岗静态检查的规则/回放预期资产包**。具体内容是 33 个各含起始 `BattleState` 快照、命令、事件序列及期望结果的 `TEST_ONLY` 夹具，加状态机规范、Mermaid 图、26 段时序、30 项结算顺序、24 项边界真值、示例演算、P13 的 RFC、测试静态验证脚本及 SHA-256 清单。

P02 职责**明确禁止**开发战斗运行时；因此这里没有冒充 P14 独占的战斗源码，更没有假装已经运行游戏、接入 Anki 或集成 UI。状态快照是交接提案，不是 P13 已签署的正式 DTO。动态/契约/真机/E2E/P32/P35 均未运行或尚阻塞。

## 二、文件结构及用途

- `spec/battle/state_machine/battle_state_machine.md`：主规则基线，状态转换、胜败/盾血/DOT/死亡触发/BOSS 全序和技术边界。
- `spec/battle/state_machine/battle_state_machine.mmd`：Mermaid 状态图源文件，可编辑；不含引擎状态实现。
- `spec/battle/state_machine/turn_sequence.tsv`：逐步事件时序，供 P14/测试定位。
- `spec/battle/resolution/effect_priority.tsv`：30 项唯一确定性优先级。
- `spec/battle/resolution/terminal_phase_truth_table.tsv`：24 项重要边界真值，包括双死、BOSS越阈致死、重复动作和抽牌不足。
- `spec/battle/resolution/battle_replay_fixtures.json`：33 份可由 P32 交付给 P14 的回放期望；数值和卡都是 TEST_ONLY。
- `spec/battle/resolution/fixture_index.tsv`：fixture_id→真值行与预期结果索引。
- `spec/battle/resolution/resolution_examples.md`：盾血、Boss 致死、平局、去重、种子洗牌、DOT 演算。
- `spec/battle/resolution/interface_rfc_and_blockers.md`：P13 DTO RFC、P06/P15/P01 待补条件、真实阻塞与变更协议。
- `spec/battle/resolution/validate_spec_fixtures.py`：**仅静态规范/夹具检查**，并非战斗运行时、真实重放执行器或 P32 自动化测试框架。
- `source_input_receipt.tsv`：逐份源输入 SHA、版本、字节和真伪级别，记录独立附件与 ZIP 内文件的差异。
- `downstream_handoff.tsv`：P03/P05/P06/P13/P14/P15/P16/P32/P35/P01 接力待回执记录。
- `P02_static_validation.log`：本岗真实执行的静态检查命令、退出码及 stdout。
- `manifest.sha256.tsv`：实体产物逐件实际 byte-size/SHA-256；清单本身不纳入自身哈希以避免自指。

## 三、如何验证包本身（无游戏运行能力声明）

将压缩包解至独立目录，不要将其直接覆盖现有 GitHub 仓库。Python 3 标准库即可核验静态内容：

```bash
python spec/battle/resolution/validate_spec_fixtures.py
```

若本地也持有原始 P01 ZIP，请加 `--upstream-zip /path/to/P01_S00_V6_完整交接包.zip` 执行 15 项源哈希与 CRC 检查；不带此参数时只检查本 P02 工件。真实执行过的完整命令/退出码在 `P02_static_validation.log`。

**真实独立运行测试建议（交 P32，而非 P02 自评）**：取得 P13 正式 DTO 及 P14 引擎后，对每个 fixture 以同样 starting snapshot/command list/seed 真正调用 P14，比较 `expected.final_state` 和 `expected.logic_events`；对 F001/F019 改变动画开关但校验逻辑完全相同；F029 是多命令命令去重样例。实现字段如因 P13 DTO 确认而变更，先提交版本化映射/RFC 与 old/new 期望，不能静默覆写历史向量。

## 四、上游及真实状态

- P01 完整原 ZIP SHA-256：`139034e2179fbe35c4ac5f3240b0df435b03b9a70f5507263ee97b7e8b022a89`，16 件，CRC 与 15/15 内容哈希均已重新验证。
- V6 GitHub 固定 commit：`8c370d731c323f86ff19642f4cc73f818498f641`；V6 源的 SHA-256 由 P01 上游 manifest 报告，未伪称远端字节本地重新哈希。
- 独立附件 `decisions_pending(1).tsv` 仅 11 字节，不可作为完整决策基线。P01 原 ZIP 内为 3021 字节；`requirements_baseline_v6(1)/(2).txt` 与 `handoff_receipts(1).tsv` 也与原 ZIP 对应物逐字节不一致；此问题已交 P01，原件未改。
- `actual_path_mapping.json` 尚未提交；P02 的路径仅为**独立隔离暂存目录中**未来建议的相对路径，不存在原工程写入授权。GitHub 当前连接只读查看，未改仓库。

## 五、签收及验收分级

- 文档、测试数据、静态格式及财产清单：P02 **已在本地生成并静态自检**；不代表产品/架构签署。
- P13 DTO / 正式路径映射：**BLOCKED**。
- P14 游戏逻辑重放、P32 独立单元/契约测试、真实 Anki/目标机、UI 动画等价 E2E：**NOT_RUN**。
- P35 设计和证据独立审查：**NOT_RUN**。
- 正式集成权限：EXT-INTEGRATOR 尚未由用户委派，P02 无权整合。

如证据或规则冲突，必须保留现有 base SHA、旧/新期望及 case_id，先交 P13 RFC，再由 P14 修改其独占实现，P32 重测，P35 复核；不允许 P02 或其他岗位越权代写。
