# P08｜《言灵旅团》Anki学习收益政策交付

任务ID：`P08-S04-S05-POLICY-001`。交付版：`P08-REWARD-POLICY/0.1.0-proposal`。  
结果：**LOCAL_POLICY_DELIVERED / FORMAL_AWARD_BLOCKED**。

本包交付真实政策文件、四键真值表、补偿数学夹具、下游逻辑用例与实际运行的作者检查证据。没有实现Hook、StudyLedger、钱包或存档，没有真实发奖，也没有跨模块整合。当前用户指令已启动P08政策工作，不以历史激活表代替本次指令。

## 1. 四项主交付

| 路径（相对本包根） | 内容 |
|---|---|
| `spec/anki/reward_semantics/study_policy_draft.md` | 资格层、判断优先级、四键候选、分类资源、时点、跨日、封顶、反刷和关卡边界 |
| `spec/anki/reward_semantics/four_rating_policy_matrix.tsv` | 21类条件×4键，共84行；正式金额UNSET，真实发奖授权false |
| `design/anki_rewards/undo_compensation_options.md` | 未消费/已消费Undo、原族恢复差额、四种补偿候选、人工门槛和精确代数 |
| `design/anki_rewards/quarantine_resolution_policy.md` | 隔离原因、最小影响范围、证据解除、权限及追踪要求 |

31条主规则分别标CONFIRMED/PROPOSAL/PENDING。CONFIRMED仅指原要求中的具体约束，不能解释为实际奖值或生产政策已批准。

## 2. 已作出的候选判断

- 推荐同条件下Again/Hard/Good/Easy获得相同基础向量B；B实际数额待P05核算、P01取得用户批准。Again不能简单视为无效。单次等额不是完整长期反诱导证明。
- 新完成、重复投递、撤销原事实、恢复原事实、替换重答和自然同卡下一次复习分开。来源身份或Undo不可证时暂停相关自动授奖，保留隔离证据。
- 已消费差额先待审，不默认负钱包、不降级、不删道具。若原发10（仅数学夹具）、花7、回收3，恢复原事实的补量为3，不是再给10。
- 日归属不能用收到消息的日期重置。日界、时区、上限、追溯期限均未批准；null不是“无限额”，UNSET不是0。
- 已批准映射返回UNKNOWN走通用资源候选；整个映射合同缺失不能伪装成UNKNOWN回退。
- 学习与关卡来源分域。Anki Undo不删除stage首通键、不自动撤销战斗结果。P07边界回执已形成，正式PolicyRecord门禁未解除。

## 3. 其他可直接消费的文件

| 路径 | 用法 |
|---|---|
| `spec/anki/reward_semantics/policy_registry.json` | 31条主规则与状态、正文位置及源引用 |
| `spec/anki/reward_semantics/policy_record.proposal.json` | 未签署PolicyRecord字段实例；全部正式金额/批准/环境空缺 |
| `spec/anki/reward_semantics/resource_mapping_candidates.tsv` | 八类语义及通用回退；统一凭证或五类材料两种候选，正式ID未注册 |
| `spec/anki/reward_semantics/policy_cases.json` | 58条有前提、操作、期望的逻辑用例，运行均NOT_RUN |
| `spec/anki/reward_semantics/compensation_arithmetic_cases.json` | 12组撤销/恢复闭合状态与1组抵扣分解，均为合成数学夹具 |
| `design/anki_rewards/decisions_pending.tsv` | 沿用DEC-001/002/003/011，另列封顶/日界/类别/保留/长期激励待裁决补充 |
| `design/anki_rewards/interface_rfc.md` | 提交给IC-14/15/16/17/18/19 owner的版本化语义请求 |
| `design/anki_rewards/p07_boundary_response.md` | 对核验后的P07实体文件给出的候选边界回执 |
| `design/anki_rewards/source_input_receipt.json` | 原始ZIP、14份源快照、固定版本、源链、SHA与缺失项 |
| `design/anki_rewards/downstream_handoff.json` | 按接收岗位绑定交付文件及哈希；PREPARED_NOT_ACKNOWLEDGED |
| `design/anki_rewards/delivery_manifest.sha256.tsv` | 每件实际大小、SHA、格式/版本、源哈希、接收人和修改白名单 |
| `design/anki_rewards/verification/` | 只读来源/政策/交付核验脚本及16项校验器作者测试 |

## 4. 已执行与未执行

| 层级 | 本次结果 | 范围 |
|---|---|---|
| 来源ZIP CRC与逐层清单 | PASS | 10个唯一ZIP、296条清单项；含重复封装层，不是296个唯一源文件 |
| 消费源快照字节/来源绑定 | PASS | 14份；其中2份核对Git blob，其余核对原始ZIP成员链 |
| 规则/矩阵/引用静态检查 | PASS | 31条规则、84行矩阵，正式值未冒充批准 |
| 数学等式检查 | PASS | 13个合成示例；没有执行真钱包事务 |
| 校验器作者测试 | PASS，16/16 | 含Easy差额、缺Again、假批准、负数、来源篡改、补全奖等拒绝测试 |
| 正式前置检查 | BLOCKED，退出码3 | 检查交付证据缺项，不是机器探针；不将BLOCKED改写为运行PASS |
| 独立设计审核/P35 SPEC | NOT_RUN | 无独立回执 |
| P11/P17/P21业务单元 | NOT_RUN | 无实际实现固定提交 |
| P12/P11/P21正式契约/并发/崩溃恢复 | NOT_RUN | 58条逻辑用例未接入运行适配 |
| P32独测、P33人工、P34真机、真实Anki E2E | NOT_RUN | 没有目标机/联动运行证据 |
| 正式工程写入/跨模块合并 | BLOCKED | P13路径授权及用户指定整合者未取得 |

原始命令、stdout、stderr、退出码和SHA见`design/anki_rewards/evidence/author_run_001/run_receipt.json`。校验器的16项作者测试不代表学习账本通过16项测试。实际真实学习事件观测数=0，真实发奖数=0。

## 5. 离线复核

在解压后的本包根目录执行，Python3.10+、仅标准库，无网络、无Anki、无引擎依赖：

```bash
python -B design/anki_rewards/verification/verify_sources.py
python -B design/anki_rewards/verification/verify_policy_artifacts.py
python -B -m unittest discover -s design/anki_rewards/verification -p 'test_*.py' -v
python -B design/anki_rewards/verification/verify_manifest.py
python -B design/anki_rewards/verification/verify_policy_artifacts.py --formal
```

前四项期望退出0，最后一项期望明确输出BLOCKED并退出3。前三类结果只证明源/文件/数学检查，不证明目标程序实现。`-B`防止在交付目录产生缓存文件。

需要保存新检查日志时，在独立副本运行`python -B design/anki_rewards/verification/run_author_checks.py`。它新增author_run目录，故该副本不再与原包逐件清单完全一致；新增证据应作为新的交付版本保存，不覆盖本次冻结记录。最终包的ZIP与清单自身哈希在外层`P08_delivery_receipt.json`固定，避免清单自哈希循环。

## 6. 下游接收与仍需补齐的条件

P09可据规则设计映射与UNKNOWN回退；P10可据资格与因果要求执行目标版探针；P11/P12/P17/P21可据候选设计与58条逻辑用例准备各自实现，不能以本草案真实发奖；P32/P35可独立复算本包并分级验收。

正式启用仍缺：P01用户PolicyRecord；P09真实映射；P10身份/Undo/redo/备份能力；P05正式预算；P13实际路径、固定工程和DTO；P12正式协议；P17来源分摊；P21原子事务/恢复；P22正式ID；P34目标环境；独立测试/门禁与EXT-INTEGRATOR授权。每项具体材料、版本缺失与责任方在`formal_prerequisites.json`列明。

P08实际写入只在本隔离包的`spec/anki/reward_semantics/**`、`design/anki_rewards/**`，根README是包级元数据。上游字节快照只读；`path_mapping_request.json`只是申请，actual_paths=null、真实工程白名单为空。没有覆盖任何上游工程或替其他岗位实现代码。
