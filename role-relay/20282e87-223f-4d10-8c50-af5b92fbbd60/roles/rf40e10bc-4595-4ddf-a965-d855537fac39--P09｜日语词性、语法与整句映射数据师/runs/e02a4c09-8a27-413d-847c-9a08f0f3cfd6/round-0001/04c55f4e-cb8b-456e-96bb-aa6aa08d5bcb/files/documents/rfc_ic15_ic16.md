# P09 接口提案与 P08 回执

任务：P09-S04-S05-MAP-001。版本：0.1.0-proposal。所有接收状态PREPARED_NOT_ACKNOWLEDGED；没有向其他岗位发送消息、改写上游或宣告接收通过。

| RFC | owner与接收人 | 提案与范围 | 正式base |
|---|---|---|---|
| P09-RFC-015-001 | P09；P10/P11/P22/P32 | 八类枚举、字段可见性、确定优先级、UNKNOWN与缺合同区分、单对象人工覆写 | 未取得；base_sha256=null |
| P09-RFC-016-001 | P08；P05/P11/P17/P22 | 接收其八类候选用途；正式资源ID/数量/经济模型不变更，标签纠错不重奖 | SRC-P08-POLICY与SRC-P08-RESOURCES哈希见source_input_receipt.json |
| P09-RFC-TRANSPORT-001 | P12；P10/P11 | 建议字段观察与分类结果封装；只读最小字段；不新增身份假设 | 未取得；base_sha256=null |
| P09-RFC-DTO-PATH-001 | P13；P22 | 接收语义DTO及actual_path_mapping请求；不存在路径授权前不得整合 | 未取得；base_sha256=null |
| P09-RFC-CONTENT-001 | P22；P08/P11/P32 | 校验八类键、候选资源引用、规则hash、schema版本及fixtures；分配正式ID | 未取得；base_sha256=null |

## 对 P08-RFC-015-001 的本岗响应

已提供固定哈希规则、47条UNKNOWN案例、观察报告、类别字典、72条分类用例、5条覆写示例及可运行验证。接收P08“已有映射返回UNKNOWN”与“缺整个映射”的区分，也接收分类纠错不能重奖的边界。

P08-BLK-02只能由“未交候选映射”更新为“候选已交、正式映射仍受门禁阻塞”；本岗不修改P08的formal_prerequisites.json或签署正式政策。真实字段可见性、正式resource_id、奖励数量、真实合同和独立回执仍未取得。

## P22接收建议

请核对category_dictionary与rules的一致性、八类覆盖、UNKNOWN和SENTENCE稳定GENERAL_MATERIAL、形容动词不另增币种、资源候选与P08逐行一致、候选键未冒充正式ID、aliases无冲突、Schema可用性、manifest与source哈希，以及字段缺失/双词性/语法整句/覆写回滚的期望结果。P22独立JSON Schema引擎验证尚未运行，不能把P09手写参考输入检查升级为其验收。

任何采集新敏感字段、增加新类别或经济种类的建议先报P08/P38/P01。跨模块源码整合交用户指定EXT-INTEGRATOR；本包只提供隔离可复现候选。
