# P09 分类规则与确定性边界

任务 `P09-S04-S05-MAP-001`；规则 `P09-POS-MAP/0.1.0-proposal`；需求 `REQ-012`；契约 `IC-15`（P09 owner）及 `IC-16`（P08 owner）。本版为隔离候选数据和作者参考实现；不是正式资源配置。

## 分类对象与标准

本项目只有八个输出语义键：`NOUN / VERB / I_ADJECTIVE / NA_ADJECTIVE / ADVERB / GRAMMAR / SENTENCE / UNKNOWN`。前五项是词性归并，GRAMMAR、SENTENCE是学习目标单位，UNKNOWN是回退。不能把“语法”当作一个语言学词性，也不能把同一条里的名词、动词分别计成多次复习或多笔权益。

`category_dictionary.json`给出定义和合成例子。语义键尚非P22正式ID。国立国语研究所的UniDic说明形状词与学校文法的形容动词词干相对应，并保留“可能性”复合标签；本项目因此将明确的形状词标签兼容到NA_ADJECTIVE，而将跨类别可能性保留为歧义。此归并是P09工程选择，不宣称运行了UniDic分词器。来源：[UniDic用语集](https://clrd.ninjal.ac.jp/unidic/glossary.html)。

## 完整判定顺序

1. **映射合同门禁。** 文件/版本缺失、哈希不符、规则结构非法或被内存改动：BLOCKED，category=null，resource_role=null。不能包装成已有UNKNOWN合同。候选包无正式发奖权限。
2. **字段授权与输入门禁。** 校验字段档案、模板作用域、版本、对象形状和字段白名单。先看字段名，拒绝未列入白名单的载荷；不读取或输出这些值。不可读状态不允许夹带字段正文。参考实现只接受合成来源；真实来源返回UNKNOWN并标记REAL_PROFILE_NOT_VALIDATED。
3. **有效人工覆写。** 必须绑定当前scope、subject、profile版本/哈希、观察快照哈希、mapping版本/哈希，并通过追加日志重放；可明确设UNKNOWN。损坏覆写日志返回UNKNOWN，不能偷偷忽略损坏记录。
4. **明确类别。** 逻辑category_label只有一个已识别类别时采用；优先于学习单位和词性。显式UNKNOWN、非空未知标签或冲突标签是终止结果，不跌回下层“找一个可用答案”。
5. **学习单位。** GRAMMAR、SENTENCE明确胜过句内词性。WORD转到词性层；MIXED转UNKNOWN。GRAMMAR/SENTENCE同时声明则UNKNOWN。
6. **词性。** 只对精确白名单标签/已枚举复合标签求类别集合。集合为单一词性则分类；跨类别、含未知token、助词/助动词等范围外标签则UNKNOWN。
7. **无可用证据。** 缺失、null、空白、不可观察、读失败、未授权，各有reason_code，均为UNKNOWN。可选上层字段缺失或空白时，可继续使用下一层已授权的明确标签；这不是从缺失字段猜内容。

高优先级明确声明是档案约定的决策依据；下层标签不参与再次投票。这样的处理能让“学习整句，但句内有名词和动词”的条目得到一个稳定结果。若上游不愿接受这一优先级，应走RFC并创建新规则版本。

## 标签规范化

只规范化分类标签，不改原词条、Anki内容或源证据字节。512字符是本参考实现的输入边界；不截断后继续判断。NFKC后去首尾空白、压缩行内空白并casefold。换行仍保留作分隔符。

允许无属性的b/strong/i/em/span包装，以及无属性div/p/br分隔。脚本、样式、图片、音频、ruby、属性、注释、非配对标签及控制字符拒绝分类。不会加载媒体、解释脚本或从图片识字。`&nbsp;`归空白。HTML规范化不是通用Anki HTML渲染器，也不声称所有合法字段HTML都能识别。

分隔符为`/ ; | , 、 ・ ； ，`及换行。`名詞/noun`去重后只有NOUN；`名詞/動詞`是UNKNOWN；`名詞/other`不能丢掉other后归名词。`adj`不够区分两类形容词，因此UNKNOWN。短别名如n/v只有在专用标签字段完整匹配才生效。

不使用词尾、字符串长度、汉字比例、中文释义、牌组名或“含例句字段”作为推断依据。`きれい`、`嫌い`没有词性标签时未知；明确形容动词标签时才为NA_ADJECTIVE。句号不是整句证据；`Sentence`例句字段存在不改变学习目标。

## 多义与混合

同一词的多个义项若明确共享一个词性，可保留该词性，不尝试选择义项。跨词性多义为UNKNOWN，等待绑定当前快照的人工覆写。UniDic“名詞-普通名詞-副詞可能”等枚举标签不会被字符串前缀压成NOUN。词性相同的重复标签合并；明确MIXED条目整体UNKNOWN，不拆成多个收益。未知的多项目形式也不会被自动分词。

语法说明常伴随例句：只有语法学习目标标签时归GRAMMAR；整句学习目标归SENTENCE；没有目标声明就不能凭自然语言文本推断。子字段、词义和语法的进一步消歧均留给用户修正或后续经批准版本。

## 资源边界

严格复用P08候选：NOUN→GUARD_MATERIAL；VERB→ATTACK_MATERIAL；两类形容词→SUPPORT_MATERIAL；ADVERB与GRAMMAR→TACTIC_MATERIAL；SENTENCE和UNKNOWN→GENERAL_MATERIAL。此处是用途候选。正式resource_id、数量和经济模型全部UNSET/null；未选择“统一学习凭证”还是“五种材料”。

只有之后获批、版本固定的映射返回UNKNOWN，P11才可依据其获批政策走通用分支。本包结果始终production_award_authorized=false。分类改错与规则回滚不制造新复习身份，不重复授予旧事件权益，不修改战斗能量；历史差额交P08/P11/P17/P21。
