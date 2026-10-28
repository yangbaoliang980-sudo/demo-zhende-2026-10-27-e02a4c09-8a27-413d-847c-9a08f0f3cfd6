# P09｜日语词性、语法与整句映射交付

**状态：LOCAL_MAPPING_DELIVERED / REAL_FIELD_CLASSIFICATION_BLOCKED。**

任务ID：`P09-S04-S05-MAP-001`。规则版本：`P09-POS-MAP/0.1.0-proposal`。需求：`REQ-012`，兼容边界`REQ-011/026`。IC-15 owner为P09，IC-16 owner为P08。

本包交付8类映射规则、72条分类用例、47条UNKNOWN回退、24条合成示例、5条人工覆写示例、3份Schema建议、离线参考程序及34项作者单元测试。全部日语内容为明确标注的合成示例；未取得真实Anki字段或P13实际路径授权。目录是隔离交付路径，不能直接覆盖正式工程。

## 从哪里开始

| 必交成果 | 包内路径 | 作用 |
|---|---|---|
| 分类规则 | `content/linguistic/pos_mapping_rules.json` | 八类、精确别名、优先级、歧义回退、资源用途候选 |
| UNKNOWN用例 | `content/linguistic/unknown_fallback_cases.tsv` | 47条原因、通用用途及完整fixture定位 |
| 实际字段观察 | `design/linguistic/anki_field_observations.md` | 如实记录0条真实观测及缺失证据 |
| 类别与用途 | `content/linguistic/category_dictionary.json`；`resource_affinity_candidates.tsv` | 语义键、定义、P08候选角色，正式ID及数量未定 |
| 完整测试数据 | `content/linguistic/classification_cases.jsonl`；`example_entries.synthetic.jsonl` | 72条确定性用例、24条可审计示例 |
| 人工更正 | `content/linguistic/override_log.synthetic.jsonl`；`design/linguistic/override_and_rollback.md` | SET/CLEAR/ROLLBACK、快照绑定、追加日志及并发冲突 |
| 可执行参考 | `design/linguistic/reference/pos_mapper.py`；`demo.py` | 标准库离线运行；只接受合成档案，无Anki、钱包或网络操作 |
| 协议与RFC | `design/linguistic/field_protocol_proposal.md`；`rfc_ic15_ic16.md`；`content/linguistic/schema/` | 等待P12/P13/P22接收，尚非正式合同 |

逐件字节数、完整SHA-256、格式/版本、源输入哈希、接收人及修改白名单见包根`delivery_manifest.sha256.tsv`。清单自身与ZIP由包外`P09_delivery_receipt.json`固定，避免自哈希循环。

## 已实现的分类行为

通过字段授权和输入门禁后，依次使用：有效绑定的人工覆写 → 明确类别 → 学习单位 → 词性标签 → UNKNOWN。空白与缺失可跳到下一份明确授权证据；非空未知标签或同级冲突直接UNKNOWN。不存在词尾/长度/中文释义推断。

| 输入情形 | 本版结果 |
|---|---|
| 明确名词、动词、い形容词、な形容词、副词 | 对应单一词性类别 |
| `名詞/動詞`、副词可能等跨类别标签 | UNKNOWN；保留候选集用于人工复核 |
| 语法目标 + 动词标签 | GRAMMAR |
| 整句目标 + 名词/动词 | SENTENCE |
| 单词卡存在Sentence例句字段 | 不因此改成整句 |
| `きれい`没有标签 | UNKNOWN；有明确形动标签才NA_ADJECTIVE |
| 字段不可观察、未授权、空值、格式错误 | UNKNOWN及明确原因；不补采字段 |
| 整个映射合同缺失或非法 | BLOCKED，category=null，没有通用资源分支 |

资源语义原样对齐P08：名词→守护用途，动词→突击用途，两类形容词→支援用途，副词/语法→战术用途，整句/UNKNOWN→通用用途。正式resource_id、数量和经济模型仍未选择，输出始终不授权发奖。改错、撤销覆写及规则回滚都不能制造第二个复习奖励身份。

## 可复现执行

Python 3.10+标准库，从解压后的本目录运行：

```bash
python -B design/linguistic/verification/verify_source_inputs.py
python -B design/linguistic/verification/verify_delivery.py
python -B -m unittest discover -s design/linguistic/verification -p 'test_*.py' -v
python -B design/linguistic/verification/verify_manifest.py
python -B design/linguistic/verification/verify_delivery.py --formal
```

前四项应退出0；最后一项应输出BLOCKED并退出3。原始stdout/stderr、命令、实际退出码、环境与固定输入SHA在`design/linguistic/evidence/author_run_003/`。不要使用`python -O`，也不要覆盖原证据目录。

CLI示例（只演示合成示例，无真实Anki接入）：

```bash
python -B design/linguistic/reference/demo.py --input content/linguistic/example_entries.synthetic.jsonl --rules content/linguistic/pos_mapping_rules.json --rules-sha256 1a99e192b608d158e2daf110bd5a5fd6d328e62184f9ec7038007a70265b87ab --rules-version P09-POS-MAP/0.1.0-proposal --profile content/linguistic/field_profile.synthetic.json
```

## 验证范围

| 层级 | 最终作者结果/当前状态 | 含义 |
|---|---|---|
| 源字节与归档 | PASS | 12个唯一ZIP；153条relay清单项+252条内层TSV清单项；8份消费快照；4份Git blob绑定 |
| 分类与候选数据一致性 | PASS，72/72 | 全为合成固定输入，不是分类准确率 |
| 参考实现作者单元 | PASS，34/34 | 覆写、陈旧快照、模板、哈希/版本、UNKNOWN边界等 |
| 正式前置检查 | BLOCKED，退出3 | 缺真实字段、授权、路径、合同、内容注册、政策及环境 |
| 独立设计/正式Schema审核 | NOT_RUN | P22、P35无独立回执；未运行第三方JSON Schema引擎 |
| 正式契约/真实业务单元 | NOT_RUN | 未接P10/P11/P12/P13/P21真实实现 |
| P32独测/P33人工/目标机/Anki E2E | NOT_RUN | 真实事件观测0，实际发奖0 |

源清单中5份松散manifest副本不具备相对包根，因此未单独作为工程清单执行；其原字节由relay哈希覆盖，完整内层包清单已校验。早期可选依赖探查失败及后续标准库路线记录在`evidence/setup_probe.json`。历史author_run_001/002保留，最终固定源证据以003为准。

## 下一位接手

`design/linguistic/downstream_handoff.json`按P08/P10/P11/P12/P13/P22/P32/P33/P35/P38绑定实际文件和SHA，接收状态都是PREPARED_NOT_ACKNOWLEDGED。

- P08：接收候选映射和UNKNOWN分支；正式奖额/经济模型仍待批准。
- P10：按观察报告提供目标版本、获准字段状态和最小脱敏样本；本包不实现插件。
- P11：消费单一类别与版本快照；保持原事件权益唯一性，不因改标签重奖。
- P22：独立校验字典、用途表和Schema并分配正式ID。
- P12/P13：接收封装/DTO和路径RFC；缺actual_path_mapping前不得写工程。
- P32/P33/P35：按固定本包哈希独立运行相应测试与门禁，不把作者日志改名为独测结果。

缺项和唯一推进owner详见`design/linguistic/blockers.tsv`。字段扩权及收益类别变化需P08/P38/P01；跨模块源码整合仍须用户另行指定EXT-INTEGRATOR。
