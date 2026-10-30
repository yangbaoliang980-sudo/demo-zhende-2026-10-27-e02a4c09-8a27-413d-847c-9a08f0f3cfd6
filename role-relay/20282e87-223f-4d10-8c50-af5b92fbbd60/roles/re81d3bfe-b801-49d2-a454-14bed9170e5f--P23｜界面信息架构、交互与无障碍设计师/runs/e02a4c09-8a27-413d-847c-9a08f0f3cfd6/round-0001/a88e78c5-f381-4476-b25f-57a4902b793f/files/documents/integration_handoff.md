# P23 下游接收说明

交付：P23-UX-A11Y/0.1.0-isolated。任务：P23-S03-S06-UX-001。IC-21 owner=P23；IC-23 owner=P29。所有交接条目 PREPARED_NOT_ACKNOWLEDGED，六项 RFC 为 PREPARED_NOT_SUBMITTED；未通过工具给其他人发消息或代签受理。

## 立即可做的工作

先阅读包根 README.md / P23_delivery_report.md，解压后打开 `design/ux/P23_wireframe_review.html`。SVG 是编辑源，PNG 是本次真实渲染结果。图中示例参数与占位区域均非正式内容，不新增 P22 生产 ID。再查机器可读 contract/state/focus 表；不要仅按截图硬编码控制条件。

| 接收岗位 | 接收文件（包内路径） | 需要受理的具体内容 | 本轮边界 |
| --- | --- | --- | --- |
| P19 | design/ux/ux_anchor_contract.json；ui_state_map.json；interaction_state_matrix.tsv；keyboard_focus_matrix.tsv；wireframes/W01–W06、W17 | 战斗锚点、稳定焦点、持久原因、缺失意图降级、真实数值展示；评价回合复核提案 | 未修改 P19 源码；输入资格仍归 P19/P14/P15 |
| P20 | information_architecture.json；interaction_spec.md；learning_status_mapping.json；W07–W15 | 已有九页面的关系、草稿/已保存、未知操作、存档保护、到账证明与技术详情层级 | 未新增正式页面、未接 P21 gateway |
| P24 | wireframes/*.svg；ux_anchor_contract.json；typography_accessibility_spec.md | 文字安全区、卡面区域、控件语义与可达区域 | 本包不含按钮/卡框切图 |
| P25 | accessibility_tokens.json；typography_accessibility_spec.md；字体及许可证 | 低保真候选替换为正式色板/字体/立绘安全区，保留可读约束 | 风格审核 NOT_RUN，不代做角色美术 |
| P28 | IC-21 的 W01/W02 与 anchor 合同 | 内容位置和卡面文字的独立阅读区；禁止依赖飞行轨迹理解作用对象 | 正式素材/动画接入 NOT_RUN |
| P29 | reduced_motion_cases.md；ux_anchor_contract.json；anchor_compatibility.tsv | current rect、缺失 source-card 降级、模式/skip/epoch 规则，P23-RFC-002 | 先受理版本，不能改 P19 封闭 payload |
| P32 | validation/；evidence/；ux_acceptance_tasks.tsv；delivery_manifest.json | 独立重验包、契约静态检查；待真实构建后执行行为/快照/命令数测试 | 本轮只有作者检查；P32 独测 NOT_RUN |
| P33 | UX 任务、W16/W17、键盘矩阵 | 真实玩家可读性、日文文案、目标屏操作与辅助设备 | 作者走查不代玩家试用 |
| P39 | 无障碍规范、静音/少动效案例、UX-B01/A05/A07 | 与正式设备能力对应的无音频、非颜色、读屏验收 | 读屏和手柄真机 NOT_RUN |
| P35 | 全包、包外交付回执、逐件清单、源输入与分层状态 | 独立证据门禁；检查失败保留与未执行项目 | NOT_RUN；无发布结论 |
| P37 | font_provenance.json、fonts/、已收到源证据 | 仅按本包实际字体来源/许可作独立核验 | 未收到正式立绘；素材合规不替代 P25 风格 |

表中短路径相对于 `design/ux/` 或 `design/accessibility/`；以 delivery_manifest.json 的完整 relative_path 为准。接收者不是修改者授权。修改白名单由逐件清单限定。

## 正式落位前的唯一合法路径

P13 需提供真实工程固定提交、P23 的两条 actual_path_mapping、修改白名单与禁改表。当前 actual_production_path=null、write_allowed=false。隔离包内 `design/ux/**` / `design/accessibility/**` 不是实际工程映射；不能因此覆盖同名工程目录。

P01 确认阶段目标和交互提案；P34 提供引擎、OS、构建入口、逻辑/物理分辨率、DPI、输入设备、语言与执行证据。P25 提供正式视觉基线。缺任一相应证据，相关验收 BLOCKED / NOT_RUN。

P19/P20/P29 分别在自己的独占路径实现，不能由 P23 代改。P13 管内部 DTO；P12 管 Anki 跨进程协议；P22 管内容 ID；P21 管物理事务。本包不添加生产 DTO 枚举或存档字段，不含跨模块合并。用户指定的 EXT-INTEGRATOR 最终整合。

## 与现有版本的兼容约束

- P19-HUD/0.1.0-isolated：只读当前 snapshot/context/commit events；“查询本次操作”另走原 command 同 ID 重发，不是只读端口；pending 仅内存，完整页面重载恢复受阻。P23 的 ux.* 是语义设计映射，传给 P29 的既有 units/cards id 保留原 unit/card_instance_id。
- P19-PRESENTATION/0.1.0-proposal：仍为 {id,x,y,width,height}；不暗加 frame_id、epoch、originRect 等字段。现有演出取消语义按上游版本，扩展走 P23-RFC-002。
- P20-META-VIEW/0.1.0-proposal 与 P20-META-INTENT/0.1.0-proposal：保留原请求载荷；amount 不由 UI 指定。当前模拟回执不被重标正式。
- P13-CLIENT-ARCH/0.1.0-isolated / YLTT-INTERNAL/0.1.0-isolated：P23 不改封闭 schema。
- P21_LocalSave_V0.1：承认其隔离 SQLite 查询能力；P20 的外层意图映射和正式接入尚待 P13/P20/P21 受理，不能把 durable=true 或模拟 projection 当全链证明。

## 变更、冲突与恢复

RFC 文件包含真实上游 base SHA-256、提案版本、acceptance 和 ChangeRequest；P23 新版本以 delivery_manifest.json 的 SHA-256 绑定。发生冲突时保留双方 base/source 字节和变更说明，禁止覆盖式合并。修改 P23 设计须重算引用、焦点和线框检查；修改其他 owner 的证据副本属于破坏来源，禁止直接修补。

同一问题连续两轮无新证据，交 P01 进行范围/方案裁决；本轮记录的浏览器失败分别增加了上下文、字体加载和符号覆盖的新证据，已修正作者工具，未转成运行通过的假记录。

最先可接手的工作是 P32 复核设计包和 P35 审查证据；实际产品行为、Anki 联动、真机与整游戏 E2E 保留 NOT_RUN。
