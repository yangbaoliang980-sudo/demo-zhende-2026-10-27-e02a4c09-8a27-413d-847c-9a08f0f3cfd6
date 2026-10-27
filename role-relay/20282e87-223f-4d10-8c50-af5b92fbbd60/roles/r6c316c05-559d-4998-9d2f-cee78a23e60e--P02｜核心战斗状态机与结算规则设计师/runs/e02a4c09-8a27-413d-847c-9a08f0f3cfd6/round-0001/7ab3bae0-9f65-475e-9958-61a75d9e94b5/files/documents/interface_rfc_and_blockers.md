# P02 接口提案 / 阻塞及变更移交单（不代表 P13 已批准）

## 实际阻塞

| case_id | 状态 | 问题 | 唯一负责人 | 本次可独立继续的部分 | 解除证据 |
|---|---|---|---|---|---|
| P02-BLK-01 | BLOCKED | 尚无 P13 `actual_path_mapping.json` 与 `engineering_inventory.tsv` 的实际合格版本 | P13 | 暂存规则、回放向量与只读校验 | P13 有效版本、真实绝对/相对映射、所有权及来源提交哈希 |
| P02-BLK-02 | BLOCKED | P13 `BattleState/Command/LogicEvent/DeckPatch` DTO、version、revision 与 CAS 语义未签 | P13 | 生成 TEST_ONLY 接口形状和事件顺序 | P13 版本化 DTO、schema、P14 消费确认 |
| P02-BLK-03 | BLOCKED | P03/P05/P15 卡牌费用、回合资源、抽弃牌和洗牌未批准 | P03/P05/P15，产品政策交 P01 | 以 mock policy 填充回放 | 各 owner 提供批准的参数、DeckPatch 和接口测试 |
| P02-BLK-04 | BLOCKED | P06 BOSS phase graph/阈值和敌方意图未提交 | P06 | 验证不提前胜利、致死优先、阈值提案的抽象规则 | P06 带内容版本的图与边界用例 |
| P02-BLK-05 | BLOCKED | P32/P35 尚未独立执行回放和规范验收 | P32/P35 | P02 仅能静态自验，不能代签 | P32 原始运行日志+同输入多次重放差异、P35 Gate |
| P02-BLK-06 | BLOCKED | 目标引擎/OS/Anki 真机和集成角色未签 | P13/P34/P01/USER | 所有纯逻辑规则与异常策略设计 | 真实工程/环境证据与授权，非此岗位负责 |
| P02-BLK-07 | BLOCKED | `decisions_pending(1).tsv` 单独附件只有 11 字节，P01 ZIP 内版本 3021 字节；`handoff_receipts` 与 `requirements_baseline` 独立附件亦与ZIP不一致 | P01 | 以原ZIP manifest验证且明确来源的版本进行隔离设计 | P01 明确 authoritative revision/修正上游独立下载；不可由P02覆盖上游 |

## 提交 P13 的 RFC-IC-02-001（PROPOSED / NOT_ACCEPTED）

- base SHA：`P01-S00-V0.1 ZIP = 139034e2179fbe35c4ac5f3240b0df435b03b9a70f5507263ee97b7e8b022a89`；GitHub fixed commit `8c370d731c323f86ff19642f4cc73f818498f641`；**未取得 P13 DTO base SHA，故不得伪造 old-version diff**。
- requested interface version: `BattleDTO/0.1.0-proposal`; compat owner P13。
- fields requested: battle_id, revision, phase, turn_number, energy, combatants hp/max_hp/shield/statuses/unit slots, zones instance_ids, command receipts with canonical fingerprints, seed+rng_state+draw_count, terminal_outcome, boss phase proposals, deterministic event seq.
- transaction/request: `PLAY_CARD`, `END_TURN`, `SYSTEM_START`, `SYSTEM_ENEMY_ACTION`, `SYSTEM_ENTER_PLAYER_TURN`, `ABORT`; each with unique command_id and expected_revision; commands serial within battle.
- semantic rejection codes: `TARGET_INVALID`, `PHASE_INVALID`, `REVISION_CONFLICT`, `CARD_NOT_IN_HAND`, `ENERGY_INSUFFICIENT`, `COMMAND_ID_COLLISION`, `DUPLICATE_NO_OP`, `ALREADY_CLOSED`, `INVALID_CONTENT`, `INVALID_ARGUMENT`.
- event fields: `{seq,type,...details}`; `DAMAGE_APPLIED` must expose raw/absorbed/hp_loss/overkill; `BATTLE_FINISHED` one result among WIN/LOSS/DRAW; `BOSS_PHASE_PROPOSED` only alive boss after reactions; `COMMAND_COMMITTED` last event.
- deterministic PRNG: `xorshift32-v1`, numeric representation uint32, shuffle algorithm/next card semantics; **subject to P13/P15 signed acceptance**.
- interface conflict handling: if P13 finds existing DTO differ, register `RFC-IC-02-001` against their signed base SHA and new/old expected sample output, do not overwrite; P14 implementation awaits resulting contract version.

## 交 P01 的 PolicyDecision 请求（NOT_APPROVED）

- DEC-003：零学习日是否拥有基础行动/资源，只对产出政策有影响；不可用 P02 mock `energy=3` 当用户已批准。
- 回合限制/每回合时长、失败或平局的奖励/惩罚：当前用户未给，P02 不自行冻结。
- BOSS 设计硬数量、实际HP阈值/状态：P06/P05 准备、P01按影响范围及用户偏好升级。
- DEC-004：三个初始角色/三怪一BOSS/20-30牌仅建议，夹具固定三人上阵不能推断起始角色收藏数量。

## 接收与复工

P03/P05/P06 消费排序规范定义内容提案；P13 据 RFC 决定 DTO 版本；P14 独占 runtime 写入；P15 返回候选不扣费；P16 等只消费事件；P32 对每个 fixture 的事件全序与结果进行实际测试；P35审查。下游接收为 `PREPARED_NOT_ACKNOWLEDGED`，未实际签收。若 fixture 预期变化：登记 case_id，保留 old/new_expected JSON、旧规则与接口 SHA，先 P13 评估 DTO，后 P14 修改实现并 P32 重跑；不得直接删旧案例。同一问题连续两轮无新证据升级 P01。
