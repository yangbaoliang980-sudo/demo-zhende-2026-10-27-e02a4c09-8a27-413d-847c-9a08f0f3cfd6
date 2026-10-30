# P22 下游交接说明

交付版本：P22-CONTENT/0.1.0-isolated；任务 P22-S00-S02-CONTENT-001。本说明是可复现组件的接收说明，不构成生产路径授权或已完成跨模块集成的声明。

## 直接接手

接收完整 ZIP，先核对外部 `P22_delivery_receipt.json` 的 ZIP 哈希，再执行 `verify_delivery.py` 和 `reproduce.py`。`delivery_manifest.json` 记录包内除自身以外的全部文件；清单自身及 ZIP 由包外回执绑定，避免循环哈希。

依赖固定于 requirements.txt。库入口为 `p22_content.pipeline.validate(root, profile)`，返回结构与引用状态、详细问题、注册表、引用和内容清单；`output_files(report)` 返回确定字节。调用者不得将候选 exit 0 转为 production gate PASS；正式资产与未知版本仍应按阻塞处理。

| 接收方 | 交接文件/接口 | 下一步边界 |
| --- | --- | --- |
| P03 | card/effect Schema、P03 compat、注册/引用报告 | 在 P03 自有路径修复或提交新版卡牌与镜像；P22 不代改卡牌 |
| P04 | character Schema、P04 compat、完整来源表及 source_variants | 确认样例与 P03 槽位兼容关系，保留双方 ID；处理历史坏独立导出 |
| P06 | enemy/phase Schema、P06 compat、阶段/状态引用报告 | 接收 Boss 绑定与行动循环静态约束；游戏执行由原程序 owner 负责 |
| P07 | stage Schema、P07 compat、canonical 和 DAG 报告 | 保持首通身份，提交关卡/奖励新版本；P22 不发奖 |
| P09 | linguistic_category、P09 compat、缺正式绑定报告 | 补分类/资源正式映射及固定外部文档来源；不把候选数量当真实收益 |
| P13 | actual_path_request、RFC、固定注册与Schema版本 | 提供真实仓库/base commit、三条路径白名单、目标引擎/OS和接口受理 |
| P30 | asset/asset_catalog Schema、资源请求与 RFC-IC22 | 提供目录契约、实际素材和源文件字节、许可/风格回执；当前资产数 0 |
| P21 | id_migration_map、content_migration_plan | 保持内容与物理存档版本分离；已发行 ID 变更必须走其迁移/事务流程 |
| P32 | 全部源码、tests、fixtures、author_final、failures | 独立复跑 109 项、核对遗漏及目标平台；作者测试不代签 |
| P33 | CLI 使用与环境/门禁记录 | 获得真实目标环境后做人工验收；本轮未执行 |
| P35 | source_input_receipt、delivery_manifest、失败/复测和状态表 | 独立核验来源、所有权、资产和证据边界 |
| P36 | 内容清单、资源清单、版本和逐件交付清单 | 评估后续打包/发布兼容；本包不能直接作为正式发布内容 |

全部接收条目为 `PREPARED_NOT_ACKNOWLEDGED`。所有 RFC 为 `PREPARED_NOT_SUBMITTED`。本轮没有向岗位或第三方发送消息、开 PR、推送分支或代签批准。

## 正式接入缺项

| 缺项 | 责任方 | 需要的证据 |
| --- | --- | --- |
| 生产路径及目标环境 | P13/P34 | 实际工程固定提交、三条映射、授权白名单、引擎/OS/构建入口和执行探针 |
| 内容生产提升和 MVP 数量 | P01 与原内容 owner | 明确需求版本、批准范围和数据版本；不能从候选数量推断 |
| 正式素材与目录 | P30，素材 owner P26/P27；验收 P25/P37 | 实际文件、源文件、许可、风格与资源注册回执 |
| 正式词性与资源绑定 | P09/P08/P22，范围批准 P01 | 分类语义、数量/资源契约、正式 ID 注册及固定来源 |
| 已发行 ID 历史 | P13/P21/P01 | 旧注册表、批准迁移、canonical 身份保存要求；未收到则不编造 |
| 独立门禁 | P32/P33/P35 | 独测/目标机人工/证据独审的实际结果 |
| 跨模块整合 | 用户指定 EXT-INTEGRATOR | 用户明确授权及接收工程；P22 不执行 |

修改白名单仅覆盖本交付包的 P22 Schema、工具、清单及本岗交付说明。`evidence/upstream/**`、`evidence/support/**` 和所有原始失败/输入证据禁止原位编辑。需修正证据时追加新记录并保留旧字节。实际工程未映射，不获写权限。

## 冲突恢复

来源冲突时保留两个 base SHA、各自固定成员来源和 ChangeRequest，不覆盖式合并。P04 6 字节历史导出与完整原包成员已按此保留。静态检测出内容错误由原内容 owner 修复；P22 校验器缺陷由 P22 修复、P32 复测、P35 审查。同一问题连续两轮返工而无新证据时升级 P01。
