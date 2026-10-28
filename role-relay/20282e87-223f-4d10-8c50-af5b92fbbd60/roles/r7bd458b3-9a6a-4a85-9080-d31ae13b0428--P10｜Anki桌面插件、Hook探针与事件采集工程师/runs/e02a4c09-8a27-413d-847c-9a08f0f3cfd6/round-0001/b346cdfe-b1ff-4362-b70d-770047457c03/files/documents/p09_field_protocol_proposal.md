# 字段协议建议：P09-FIELD-OBS/0.1.0-proposal

状态：PROPOSAL / PREPARED_NOT_ACKNOWLEDGED。IC-15语义owner=P09；跨进程封装=P12；内部DTO=P13；正式内容ID与Schema=P22。三个JSON Schema均为隔离建议文件，未写入其他岗位目录。

## 输入的最小语义

| 逻辑项 | 合成档案示范 | 分类用途及边界 |
|---|---|---|
| category_label | GameCategory | 可明确指定八类之一，最高自动优先级；不是实际字段承诺 |
| unit_kind | StudyUnit | WORD/GRAMMAR/SENTENCE/MIXED/UNKNOWN；避免把例句和学习目标混同 |
| pos_label | 品詞 | 明确词性标签，精确白名单匹配 |
| lemma | Expression | 可选人工说明；自动分类不依赖正文 |
| context | Sentence | 可选人工说明；存在本身不能判整句 |

最小可用输入只需一个可授权、可观察且足够明确的分类标签，不要求同时读取五个字段。不添加Anki字段、不改名、不写回笔记。实际字段命名、note type和card template经P10观察后绑定；不能仅根据字段名碰巧相同或字段下标猜用途。字段重命名、模板变化、授权撤回需要新档案和新哈希。

输入包含schema_version、source_kind、profile_id、scope_ref、subject_ref、fields。scope_ref由上游提供不透明的来源/笔记类型/卡模板作用域；subject_ref由上游提供当前分类对象标识。**二者不是复习事件唯一键**，也不声明Anki原生一定能直接给出这些字段。一个笔记生成不同模板卡片时，档案应能区分学习目标。具体身份格式由P10/P12证明后冻结。

每个获准字段为`{"state":"READABLE","value":"名詞"}`或`{"state":"UNOBSERVABLE"}`等。不可观察、未授权和读取失败不可夹带正文。READABLE允许null表示实际为空；字段缺失表示未提供。不透明字段和未知键不许自动复制到日志。

本包schema允许描述ANKI_OBSERVED来源，参考程序主动拒绝该来源；此差异是能力门禁，不是对真实协议已支持的承诺。真实profile尚不存在，正式字段授权也尚不存在。参考程序只接受该synthetic档案的syn:标识，用于本包测试。

## 输出及可复现绑定

输出固定规则版本与原文件SHA、字段档案ID/SHA、规范化JSON观察快照SHA、scope_ref和subject_ref、唯一category、reason_code、selected_tier、候选集合、人工事件ID以及warnings。只输出语义候选resource_role；formal_resource_id和quantity为null，production_award_authorized=false，reward_effect=NONE_PREVIEW_ONLY。

UNKNOWN是合法语义分类；BLOCKED_MISSING_MAPPING使用category=null且无资源分支。授权/格式异常在本参考程序输出UNKNOWN和异常reason_code，但这不是授权P11发奖：P11必须先独立通过来源与政策门禁。明确READ_ERROR、未授权等与单纯词性不明不能在账本资格中合并。

快照序列化：UTF-8，无BOM；JSON对象按key排序，分隔符为`,`和`:`，ensure_ascii=false，不接受NaN/Infinity及重复键。profile与input各自计算SHA-256；映射SHA是文件原字节SHA。历史输入快照是复现键，不能成为可绕过业务唯一性的“新奖励键”。实际数据中的低熵内容哈希不等于匿名化，日志分享范围仍由P38决定。

## 规范化及上游职责

允许的标签HTML子集、长度及分隔符见classification_spec.md。本包没有导入anki/aqt，也没有读数据库或网络请求。P10只采集经批准的最小字段；P12验证传输可信性和版本；P13接内部DTO；P22接语义键和正式内容ID；P11绑定原学习事件和映射快照。事件身份、四键编码、Undo、时区、钱包事务均不由P09增加字段假设。

不存在正式字段的观察回执时，现实映射为BLOCKED/NOT_RUN。需要扩展范围、加敏感字段或改变收益类别时，先交P08/P38/P01；不得在适配器中偷偷回落到全note、全deck或模型推断。
