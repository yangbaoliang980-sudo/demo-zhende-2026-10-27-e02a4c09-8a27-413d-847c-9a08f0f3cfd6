# P09｜日语词性、语法与整句映射交付

**P09 的隔离实体成果已完成，状态为 LOCAL_MAPPING_DELIVERED / REAL_FIELD_CLASSIFICATION_BLOCKED。**

任务 ID：P09-S04-S05-MAP-001
规则版本：P09-POS-MAP/0.1.0-proposal
需求关联：REQ-012；边界关联：REQ-011、REQ-026
接口关联：IC-15、IC-16

本次已完成分类规则、映射数据、人工覆写与回滚格式、可执行参考程序、测试用例和实际运行证据。**真实 Anki 字段观测数为 0，真实发奖数为 0；正式工程写入、真实联动和跨模块整合均未执行。**

## 一、完整交付文件

**完整包：**

包内共 **86 个文件**，ZIP 大小 **5,041,990 字节**，已通过 CRC 检查、重新解压后的逐件哈希核验及映射数据复核。

ZIP 的 SHA-256：

纯文本

`d2418d564772963d1434bc4c3cf03a33c6a7887fdc684814b9bce1a1b0ff702a`

阅读入口：
逐件清单：
外层回执：

### 三份强制成果

| 实体文件 | 包内完整相对路径 | 实际大小 | 完成内容 |
| --- | --- | --- | --- |
|  | content/linguistic/pos_mapping_rules.json | 7,559 字节 | 八类定义、精确标签别名、优先级、复合词性、UNKNOWN 回退和资源用途候选 |
|  | content/linguistic/unknown_fallback_cases.tsv | 7,365 字节 | 47 条回退案例、原因码、通用用途与完整测试输入定位 |
|  | design/linguistic/anki_field_observations.md | 3,396 字节 | 已收到的证据、真实字段不可观察状态、最小采集建议与缺项责任方 |

清单逐件记录了**相对路径、实际大小、完整 SHA-256、格式、版本、源输入哈希、接收人及修改白名单**。清单覆盖包内其余 85 个文件；清单自身和 ZIP 的哈希由外层回执固定。

包内还包含：

| 成果 | 包内路径 |
| --- | --- |
| 类别字典 | content/linguistic/category_dictionary.json |
| P08 资源用途对照表 | content/linguistic/resource_affinity_candidates.tsv |
| 72 条完整分类用例 | content/linguistic/classification_cases.jsonl |
| 24 条带来源标记的合成示例 | content/linguistic/example_entries.synthetic.jsonl |
| 人工覆写与改错日志示例 | content/linguistic/override_log.synthetic.jsonl |
| 输入、输出、覆写日志 Schema 建议 | content/linguistic/schema/ |
| 离线参考程序与命令行入口 | design/linguistic/reference/ |
| 字段协议、分类说明和版本化 RFC | design/linguistic/field_protocol_proposal.md、classification_spec.md、rfc_ic15_ic16.md |
| 下游文件与哈希绑定 | design/linguistic/downstream_handoff.json |

## 二、已经落实的分类行为

### 1. 八类输出与 P08 候选用途保持一致

| 类别 | 本版语义键 | P08 资源用途候选 |
| --- | --- | --- |
| 名词 | NOUN | 守护素材用途 |
| 动词 | VERB | 突击素材用途 |
| 形容词 | I_ADJECTIVE | 支援素材用途 |
| 形容动词 | NA_ADJECTIVE | 支援素材用途 |
| 副词 | ADVERB | 战术素材用途 |
| 语法 | GRAMMAR | 战术素材用途 |
| 整句 | SENTENCE | 通用学习素材用途 |
| 未知 | UNKNOWN | 通用学习素材用途 |

**这些是语义键与用途候选。正式资源 ID、奖励数量及经济模型仍为 null/UNSET，不能解释为零奖励、无限额或已批准的新币种。**

“语法”和“整句”被定义为学习目标类别。对 UniDic 的“形状词”称呼提供了兼容别名；跨类别的“可能性”标签则保留歧义，不据此猜当前用法。该处理参考了国立国语研究所对形状词和可能性词性体系的说明。[clrd.ninjal.ac.jp](https://clrd.ninjal.ac.jp/unidic/glossary.html?utm_source=chatgpt.com)

### 2. 判定顺序已经写入数据和程序

通过输入与授权检查后，优先级为：

**有效人工覆写 → 明确类别标签 → 学习单位类型 → 词性标签 → UNKNOWN。**

具体边界如下：

| 输入情况 | 确定处理 |
| --- | --- |
| 名詞 / noun | 两个别名归为同一类别，输出 NOUN |
| 名詞 / 動詞 | 输出 UNKNOWN，保留候选类别供人工复核 |
| 名詞-普通名詞-副詞可能 | 输出 UNKNOWN，不只取“名词”前缀 |
| 明确语法目标，同时有动词标签 | 输出 GRAMMAR |
| 明确整句目标，同时有名词和动词 | 输出 SENTENCE |
| 单词卡带有例句字段 | 不因例句存在而改成整句 |
| きれい 没有类别或词性标签 | 输出 UNKNOWN |
| きれい 有明确形容动词标签 | 输出 NA_ADJECTIVE |
| 字段缺失、空值、不可观察、读取失败 | 输出 UNKNOWN，区分原因码 |
| 高优先级非空标签无法识别或互相冲突 | 直接 UNKNOWN，不向下寻找一个看似可用的答案 |

**参考程序不凭词尾、字符串长度、中文释义或句号推断类别，也不调用网络分类服务。**

### 3. 保留了 P08 要求的关键区别

这两个状态没有混在一起：

- **已有映射规则返回 UNKNOWN**：给出通用资源的语义候选；实际发奖仍须满足获批政策及其他门禁。
- **整个映射合同缺失、版本错误或规则非法**：输出 BLOCKED，category=null，不提供资源分支。

本包所有分类结果均保持：

JSON

```
{
  "formal_resource_id": null,
  "quantity": null,
  "production_award_authorized": false,
  "reward_effect": "NONE_PREVIEW_ONLY"
}
```

## 三、人工改错与回滚已提供可执行验证

覆写绑定到**分类对象、模板作用域、字段档案哈希、观察快照哈希、规则版本和规则哈希**。字段内容或模板改变后，旧覆写不会自动套用。

日志采用追加方式，支持：

| 操作 | 行为 |
| --- | --- |
| SET | 设置一个明确类别，包括 UNKNOWN |
| CLEAR | 取消当前人工覆盖，恢复按规则判定，保留历史 |
| ROLLBACK | 追加新记录，恢复同一绑定下某条历史记录的结果 |

包内五条合成日志实际验证了：

**双词性项 → 人工设为名词 → 改为动词 → 回滚到名词 → 清除覆写后回到 UNKNOWN → 人工明确 UNKNOWN。**

另已验证哈希篡改、陈旧快照、模板变化、并发修改冲突、跨对象回滚及无时区时间戳的拒绝行为。

规则文件也提供了**合成旧版本回滚测试**，但没有把这个夹具声称为真实历史版本。实际已批准映射版本的回滚仍为 NOT_RUN。所有分类纠错和回滚都不生成新的复习事件身份，不执行钱包变更，不使旧事件重新获奖。

## 四、上游证据与实际验证结果

本次实际解包并核验了上传附件及内嵌 ZIP，读取了 P08 奖励草案、资源候选、RFC、P01 需求映射和 V6 相关职责正文。

其中：

- P08 完整包为 **2,523,333 字节**，SHA-256 与交接声明的 c61826ec…19e612f 一致。
- P08 包及相关文件的 Git blob 与固定提交 021008f602b13cba62a15bc317cb5074e2086a74 的指定交接目录一致。
- V6 原文与固定提交 8c370d731c323f86ff19642f4cc73f818498f641 的文件树一致。
- **未发现真实 Anki 字段样本、字段读取授权或 P13 的 actual_path_mapping.json。**

完整来源路径、版本、SHA-256 和 ZIP 成员链已写入包内 design/linguistic/source_input_receipt.json。

### 验证分级

| 验证层级 | 本次结果 | 证明范围 |
| --- | --- | --- |
| 源归档与清单核验 | **PASS** | 12 个唯一 ZIP；153 条 relay 清单项和 252 条内层 TSV 清单项，含封装层重复项 |
| 消费源快照与 Git blob 绑定 | **PASS** | 8 份消费快照、4 份 Git blob 绑定 |
| 分类数据与 P08 用途一致性 | **PASS，72/72** | 合成固定输入的预期行为 |
| 参考实现作者单元测试 | **PASS，34/34** | 输入边界、覆写、回滚、版本及哈希绑定等 |
| 命令行示例 | **PASS，24 条输出** | 合成示例通过实际 CLI 入口运行 |
| ZIP 重新解压与逐件哈希 | **PASS** | 最终交付字节及静态映射数据 |
| 正式前置检查 | **BLOCKED，退出码 3** | 缺真实字段、授权、路径、合同、政策及环境 |
| P22 独立 Schema 引擎校验 | **NOT_RUN** | 无独立执行回执 |
| P32 独测、正式契约、真实业务单元 | **NOT_RUN** | 未接入对应正式实现 |
| P33 人工、目标机、真实 Anki E2E | **NOT_RUN** | 无真实运行证据 |
| P35 独立分级门禁 | **NOT_RUN** | 无独立验收回执 |

72 条分类数据也被单元测试调用，**不能将两种入口相加宣称为 144 条独立案例**。这些结果也不构成真实牌组的自动分类准确率。

早期可选 jsonschema 依赖探查曾失败，已保留明确标注的错误记录；后续参考程序和测试使用 Python 标准库运行，未把第三方 Schema 引擎校验写成通过。

最终作者证据位于：

纯文本

`design/linguistic/evidence/author_run_003/`

包含实际命令、stdout、stderr、退出码、环境和执行前固定的 **36 份输入文件哈希**。打包时再次核对这些输入未发生漂移。

## 五、下一位可以直接接手的内容

downstream_handoff.json 已为接收岗位绑定 **46 条文件交接记录**，接收状态统一为 PREPARED_NOT_ACKNOWLEDGED。

| 接收方 | 可直接接收 | 仍需补齐 |
| --- | --- | --- |
| P08 | 八类映射、UNKNOWN 分支、资源用途对照、改错不重奖边界 | 正式政策接收与批准 |
| P10 | 字段观察报告、最小字段建议、输入格式样例 | 目标版获准字段、脱敏样本和可观察证据 |
| P11 | 单一类别输出、规则与快照绑定、覆写语义 | 正式账本合同与真实实现接入 |
| P22 | 类别字典、映射表、Schema 建议、完整用例 | 独立校验、正式内容 ID 与 Schema 注册 |
| P12／P13 | 传输、DTO 与路径 RFC | 正式合同、实际路径映射及写入白名单 |
| P32／P33／P35 | 固定输入、参考源码、复现命令和作者原始证据 | 各自独立执行及门禁回执 |

解压后，在包根运行：

Bash

```
python -B design/linguistic/verification/verify_source_inputs.py
python -B design/linguistic/verification/verify_delivery.py
python -B -m unittest discover -s design/linguistic/verification -p 'test_*.py' -v
python -B design/linguistic/verification/verify_manifest.py
python -B design/linguistic/verification/verify_delivery.py --formal
```

前四项应退出 0；最后一项应明确返回 BLOCKED 并退出 3。**这份交付可以用于下游候选实现和独立验证，尚不能用于真实发奖或直接覆盖正式工程。**

## 保存状态

**上述文件已经生成，可通过本次会话的链接下载；持久保存尚未完成。**

自动审批拒绝了将完整包及六份配套文件保存到目标文件区的操作。审核给出的理由是：文件包含项目资料，尚未确认这些具体文件向该目的地传输的明确授权及目的地可信性。此次没有完成上传，拒绝后也没有改用其他途径上传。

若要继续完成保存，需要你明确授权：

> 允许将本次 P09 完整交付包，以及 README、三份强制成果、交付回执和逐件清单，保存到我的 ChatGPT 文件区。