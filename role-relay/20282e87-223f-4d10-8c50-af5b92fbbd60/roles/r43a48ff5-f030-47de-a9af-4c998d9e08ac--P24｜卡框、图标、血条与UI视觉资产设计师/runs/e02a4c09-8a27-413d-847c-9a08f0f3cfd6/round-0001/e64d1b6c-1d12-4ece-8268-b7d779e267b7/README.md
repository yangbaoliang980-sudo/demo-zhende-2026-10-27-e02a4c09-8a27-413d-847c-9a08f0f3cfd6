# P24｜卡框、图标、血条与 UI 视觉资产交付

**P24 的实体资产包已完成，并通过最终 ZIP 解压后的复核。** 本轮交付为 **S03 占位视觉资产**：可编辑图源、透明切图、组件状态图、样例界面、规范和验证工具均已生成。正式风格审定及工程导入仍保留 **BLOCKED / NOT_RUN**。

任务编号：`P24-S03-UI-ASSET-001`
交付版本：`P24-UI-VISUAL/0.1.0-placeholder`
当前状态：**AUTHOR_VISUAL_ASSETS_DELIVERED / S03_PLACEHOLDER / PRODUCTION_INTEGRATION_BLOCKED**

## 一、完整成果下载

| 文件 | 内容 |
| --- | --- |
| **P24_UI_VisualAssets_V0.1.zip** | **完整交付包，5,713,964 字节，436 个实体文件** |
| P24_delivery_receipt.json | 24,347 字节；记录最终 ZIP、清单及 28 项工件的实际大小、SHA-256、包内对应路径，以及最终解压复跑结果 |
| P24_delivery_report.md | 完整交付报告：范围、来源核验、视觉决定、验证结果、阻塞责任与接手方法 |
| README.md | 阅读入口与目录说明 |

最终 ZIP 的 SHA-256：

纯文本

`93362700482dd8628d0e54024df4c10b2667d938afbdfeae5a53054e06429ca9`

已实际完成 **ZIP CRC 检查、436 个包内文件与交付目录逐字节比对、28 项工件与对应 ZIP 成员同名同字节检查**。最终解压目录运行校验前后的文件集合和哈希保持一致。回执位于 ZIP 外，用于绑定最终压缩包，避免循环哈希。

## 二、本轮实际制作的资产

共交付 **105 个可编辑组件 SVG、210 张透明 PNG 切图、7 张可编辑画板和 10 张 PNG 预览**。组件切图提供 **1×、2×** 两种密度。

| 资产类别 | 可编辑组件数 | 本轮覆盖 |
| --- | --- | --- |
| 主要、次要、导航按钮 | 18 | 默认、悬停、按下、禁用、选中、错误 |
| 手牌卡框、敌方信息框 | 12 | 六种基础状态 |
| 卡背 | 2 | 默认、禁用 |
| 透明立绘窗口边框 | 3 | 默认、选中、禁用；保留透明孔 |
| 信息面板 | 4 | 默认、选中、错误、待核对 |
| 生命轨道、生命填充、护盾填充 | 7 | 常规、空值、未知、低生命等适用视觉状态 |
| 费用徽章 | 7 | 六种基础状态及未知 |
| 独立焦点框 | 4 | 按钮、导航、手牌、敌方框 |
| 状态图标 | 48 | **24 种图标**，各含默认与禁用版本 |

**444 行状态矩阵**逐项记录切图、独立叠加层和不适用原因；同时提供 **79 个 P23 原 widget／anchor 条目的视觉映射候选**，保留原状态及来源字段。

### 必交工件与可编辑源文件示例

以下下载件均与 ZIP 内对应文件保持相同名称和原字节。

| 工件 | 用途 |
| --- | --- |
|  | 状态覆盖、资产 ID、叠加方式及不适用原因 |
| ui_visual_export_manifest.json | 105 项资产的源文件、导出、尺寸、alpha、SHA-256、安全区、九宫格、接收方和修改白名单 |
| ui_visual_spec.md | 色板、字体、透明通道、分辨率、命名与组件规范 |
| delivery_manifest.json | 其余 435 个包内文件的逐件记录；清单自身由包外回执绑定 |
| source_input_receipt.json | 31 份直接输入及字体原件的来源与哈希 |
| p30_import_proposal.json | 待 P30 受理的导入参数与字段说明 |
| integration_handoff.md | 下游接收、落位条件、复验与重新渲染方法 |
| placeholder_ui_frame_hand_selected.svg | 可直接编辑的选中手牌框 |
| placeholder_ui_card_back_default.svg | 可直接编辑的卡背 |

## 三、实际视觉预览

### 战斗目标确认样例

这张样例使用实际导出的组件切图，依据 **P23 最终 W02 线框**制作。控制矩形和游戏区文案保持原有含义；名称、数值与卡面区域均为设计夹具。

### 组件状态图

其他预览可直接下载：

完整解压后，打开包内 art/ui/P24_preview_index.html，可以浏览全部画板和逐件组件索引。

## 四、已经落实的视觉规则

**焦点与选中分开。** 选中使用金色边框、勾号及界面文字；当前输入焦点使用独立冰蓝外框，两者能够同时显示。禁用状态保留虚线或斜杠，原因文字由 P19／P20 持续显示。

**业务文字与切图分开。** 生命、费用、目标、错误原因、奖励处理状态没有烘焙进组件 PNG。生命填充从左裁切；零生命不绘制填充；未知生命使用独立图纹和明确文字。P24 没有定义低生命阈值或参与战斗计算。

**学习状态保持三层区分。** 学习样例保留连接、记录处理、钱包证明三个区域。“连接可用”和“记录待核对”不会被视觉素材表达成奖励已到账。

**安全区与缩放有明确数据。** 手牌框采用 236×174，敌方信息框采用 350×196，立绘窗口采用 78×92；文本区、状态标记保留区、透明孔与九宫格边界均写入清单。P23 的 1280×856 是含审查标注的画板，实际界面区仍为 (0,48,1280,720)。

色彩检查采用普通文字 **4.5:1**、必要组件及状态边界 **3:1** 的候选目标；这些指标用于本包静态检查，没有宣称整游戏通过无障碍认证。[W3C](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html?utm_source=chatgpt.com)

## 五、实际验证结果

| 验证层级 | 实际结果 | 证明范围 |
| --- | --- | --- |
| **最终解压包静态检查** | **18/18 PASS** | ID、尺寸、alpha、SVG 结构、状态、哈希、清单、锚点与所有权边界 |
| **负向检查** | **9/9 按预期拒绝** | 重复 ID、丢失 alpha、错误尺寸、缺失状态、路径逃逸、占位冒升、无效九宫格、篡改字节、低对比 |
| 组件 PNG 实际渲染 | **210/210 PASS** | 源 SVG 实际导出 |
| 画板 PNG 实际渲染 | **10/10 PASS** | 七张画板及额外三种排版密度 |
| 文字边界检查 | **305 个节点，未发现越界或明显文字重叠** | Inkscape 实际边界测量 |
| 展示文本字体覆盖 | **缺字 0** | 当前展示字串及回退字体集合 |
| 实色对比检查 | **37/37 PASS** | 所检文字最低约 **6.589:1**；关键边界最低约 **3.879:1** |
| 九宫格检查 | **82/82 PASS** | 候选尺寸下四角像素保持不变 |
| 立绘窗口透明孔 | **6/6 PASS** | 三种状态 × 两种密度，孔内 alpha 均为 0 |
| 正式接入预检 | **BLOCKED，exit 3** | 路径、风格、导入与目标环境等前提不足 |
| P25／P37／P30 独立审核及导入 | **NOT_RUN** | 未代签审核或导入通过 |
| 游戏单元、运行契约、目标设备、真实 Anki／E2E | **NOT_RUN** | 静态资产验证未替代程序运行 |
| P32 独测、P35 工程放行 | **NOT_RUN** | 等待独立岗位执行 |

原始结果见 visual_qa_results.json、validation_results.json 和 negative_results.json。**最终 ZIP 新解压后的复跑结果以包外交付回执为准。**

100%／125%／150%／200% 已实际生成不同像素密度的静态排版图；目标系统 DPI、游戏内文字放大重排和真实显示设备尚未测试。

## 六、上游核验与正式接入缺口

两份 relay ZIP 中的 **140 条原文件记录**已按大小和 SHA-256 核验；P23 完整 ZIP 已实际解包，**171 个清单成员哈希匹配**。通过 GitHub 固定树与本地 Git blob SHA 对照，**151 个 P23 包内文件匹配到固定树条目**。

本轮依据的固定提交为：

- 职责仓库：`8c370d731c323f86ff19642f4cc73f818498f641`
- 上游交接：`bc9aec3a300e1a39aafb3303754a00b8004bbde5`

正式接入仍需补齐：

| 责任方 | 缺失证据与下一步 |
| --- | --- |
| **P13** | P24 实际路径映射、真实工程固定提交及写入白名单；现有映射没有 P24 条目 |
| **P25** | 固定 Art Bible、正式色板／字体及立绘安全区审定；本批保持 PLACEHOLDER |
| **P22** | 候选资产 ID、导出命名和内容引用受理 |
| **P30** | IC-22 实际导入协议、引擎版本、`import_version`、图集与字体导入结果 |
| **P34** | 目标 OS、引擎、分辨率和 DPI 执行证据 |
| **P37** | 原创图形及随附字体来源／许可的独立审查回执 |
| **P32／P35** | 同版独立复测及工程放行证据 |

详细记录见 blocker_register.json。六份 RFC 已准备，状态均为 PREPARED_NOT_SUBMITTED。

## 七、下一位直接复验

解压完整 ZIP，进入 P24_UI_VisualAssets_V0.1 后执行：

Bash

`python -B art/ui/validation/validate_assets.py \
  --output ../P24_check`

预期退出码：**0**。

检查正式接入门禁：

Bash

`python -B art/ui/validation/validate_assets.py \
  --preflight \
  --output ../P24_gate`

本版预期结果：**BLOCKED，退出码 3**。输出目录必须尚不存在，并位于包外。

**下一接收方可直接使用本包开展 P25 风格审查、P37 来源许可复核、P30 格式与导入受理，以及 P19／P20／P28 的资产接收。** 本轮没有覆盖真实工程，没有改动战斗或交互程序，也没有执行跨模块整合。

---

## 本次归档的原始文件

- [P23_UX_Accessibility_V0.1.zip](files/archives/P23_UX_Accessibility_V0.1.zip)
- [P23_delivery_report.md](files/documents/P23_delivery_report.md)
- [accessibility_tokens.json](files/data/accessibility_tokens.json)
- [external_references.json](files/data/external_references.json)
- [font_provenance.json](files/data/font_provenance.json)
- [DejaVuSans.ttf](files/other/DejaVuSans.ttf)
- [DejaVu_LICENSE.txt](files/documents/DejaVu_LICENSE.txt)
- [NotoJP_LICENSE.txt](files/documents/NotoJP_LICENSE.txt)
- [NotoJP_package.json](files/data/NotoJP_package.json)
- [NotoSC_LICENSE.txt](files/documents/NotoSC_LICENSE.txt)
- [noto-sans-jp-japanese-400-normal.woff2](files/other/noto-sans-jp-japanese-400-normal.woff2)
- [noto-sans-sc-chinese-simplified-400-normal.woff2](files/other/noto-sans-sc-chinese-simplified-400-normal.woff2)
- [reduced_motion_cases.md](files/documents/reduced_motion_cases.md)
- [typography_accessibility_spec.md](files/documents/typography_accessibility_spec.md)
- [typography_test_strings.json](files/data/typography_test_strings.json)
- [ux_acceptance_tasks.tsv](files/data/ux_acceptance_tasks.tsv)
- [P23_wireframe_review.html](files/code/P23_wireframe_review.html)
- [anchor_compatibility.tsv](files/data/anchor_compatibility.tsv)
- [author_walkthrough.md](files/documents/author_walkthrough.md)
- [defect_log.json](files/data/defect_log.json)
- [P23_wireframe_contact_sheet.png](files/images/P23_wireframe_contact_sheet.png)
- [W01_before_review.png](files/images/W01_before_review.png)
- [glyph_failure.json](files/data/glyph_failure.json)
- [verify_glyphs_before.py](files/code/verify_glyphs_before.py)
- [browser_registry.json](files/data/browser_registry.json)
- [dependency_integrity.json](files/data/dependency_integrity.json)
- [environment_observed.json](files/data/environment_observed.json)
- [font_registry.json](files/data/font_registry.json)
- [generator_reproduction.json](files/data/generator_reproduction.json)
- [glyph_coverage.json](files/data/glyph_coverage.json)
- [intake_relay_checks.tsv](files/data/intake_relay_checks.tsv)
- [p22_tree_evidence.json](files/data/p22_tree_evidence.json)
- [preflight.json](files/data/preflight.json)
- [render_environment_001.json](files/data/render_environment_001.json)
- [render_environment_002.json](files/data/render_environment_002.json)
- [render_environment_003.json](files/data/render_environment_003.json)
- [render_environment_004.json](files/data/render_environment_004.json)
- [render_results.json](files/data/render_results.json)
- [roles_tree_evidence.json](files/data/roles_tree_evidence.json)
- [upload_git_matches.json](files/data/upload_git_matches.json)
- [requirements_baseline_v6.txt](files/documents/requirements_baseline_v6.txt)
- [decisions_pending.tsv](files/data/decisions_pending.tsv)
- [prd_scope_v0.md](files/documents/prd_scope_v0.md)
- [battle_state_machine.md](files/documents/battle_state_machine.md)
- [turn_sequence.tsv](files/data/turn_sequence.tsv)
- [terminal_phase_truth_table.tsv](files/data/terminal_phase_truth_table.tsv)
- [study_policy_draft.md](files/documents/study_policy_draft.md)
- [quarantine_resolution_policy.md](files/documents/quarantine_resolution_policy.md)
- [undo_compensation_options.md](files/documents/undo_compensation_options.md)
- [internal_api_contracts.json](files/data/internal_api_contracts.json)
- [internal_dto.schema.json](files/data/internal_dto.schema.json)
- [target_environment_requirements.json](files/data/target_environment_requirements.json)
- [actual_path_mapping.json](files/data/actual_path_mapping.json)
- [contract_semantics.md](files/documents/contract_semantics.md)
- [presentation_adapter_spec.md](files/documents/presentation_adapter_spec.md)
- [P19_API.md](files/documents/P19_API.md)
- [battle_hud_state_binding.json](files/data/battle_hud_state_binding.json)
- [hud_controller.mjs](files/other/hud_controller.mjs)
- [battle.css](files/code/battle.css)
- [index.html](files/code/index.html)
- [hud_renderer.mjs](files/other/hud_renderer.mjs)
- [P19_HUD_1280.png](files/images/P19_HUD_1280.png)
- [control_state_table.tsv](files/data/control_state_table.tsv)
- [P20_API.md](files/documents/P20_API.md)
- [domain_api_mapping.json](files/data/domain_api_mapping.json)
- [controller.mjs](files/other/controller.mjs)
- [styles.css](files/code/styles.css)
- [party_menu_flow.md](files/documents/party_menu_flow.md)
- [learning_status_ui_tests.md](files/documents/learning_status_ui_tests.md)
- [model.mjs](files/other/model.mjs)
- [renderer.mjs](files/other/renderer.mjs)
- [P20_Chapters_1280.png](files/images/P20_Chapters_1280.png)
- [P20_Growth_1280.png](files/images/P20_Growth_1280.png)
- [P20_Learning_Quarantine.png](files/images/P20_Learning_Quarantine.png)
- [P20_Menu_1280.png](files/images/P20_Menu_1280.png)
- [P20_Menu_390.png](files/images/P20_Menu_390.png)
- [P20_Migration_Failed.png](files/images/P20_Migration_Failed.png)
- [P20_Party_1280.png](files/images/P20_Party_1280.png)
- [P20_Restart_Pending.png](files/images/P20_Restart_Pending.png)
- [P20_Settlement_1280.png](files/images/P20_Settlement_1280.png)
- [P21_API.md](files/documents/P21_API.md)
- [P20_recovery_response.md](files/documents/P20_recovery_response.md)
- [missing_bindings.tsv](files/data/missing_bindings.tsv)
- [id_policy.json](files/data/id_policy.json)
- [content_id_registry.tsv](files/data/content_id_registry.tsv)
- [content_schema_spec.md](files/documents/content_schema_spec.md)
- [第六轮_27项接口契约冻结修订V6.0.json](files/data/%E7%AC%AC%E5%85%AD%E8%BD%AE_27%E9%A1%B9%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6%E5%86%BB%E7%BB%93%E4%BF%AE%E8%AE%A2V6.0.json)
- [第六轮_游戏研发岗位体系最终冻结版V6.0.txt](files/documents/%E7%AC%AC%E5%85%AD%E8%BD%AE_%E6%B8%B8%E6%88%8F%E7%A0%94%E5%8F%91%E5%B2%97%E4%BD%8D%E4%BD%93%E7%B3%BB%E6%9C%80%E7%BB%88%E5%86%BB%E7%BB%93%E7%89%88V6.0.txt)
- [第六轮_92项职责冻结映射V6.0.tsv](files/data/%E7%AC%AC%E5%85%AD%E8%BD%AE_92%E9%A1%B9%E8%81%8C%E8%B4%A3%E5%86%BB%E7%BB%93%E6%98%A0%E5%B0%84V6.0.tsv)
- [第六轮_全部岗位职责_可复制版V6.0.txt](files/documents/%E7%AC%AC%E5%85%AD%E8%BD%AE_%E5%85%A8%E9%83%A8%E5%B2%97%E4%BD%8D%E8%81%8C%E8%B4%A3_%E5%8F%AF%E5%A4%8D%E5%88%B6%E7%89%88V6.0.txt)
- [v6_git_matches.json](files/data/v6_git_matches.json)
- [focus_graph.json](files/data/focus_graph.json)
- [information_architecture.json](files/data/information_architecture.json)
- [information_architecture.md](files/documents/information_architecture.md)
- [interaction_state_matrix.tsv](files/data/interaction_state_matrix.tsv)
- [keyboard_focus_matrix.tsv](files/data/keyboard_focus_matrix.tsv)
- [learning_status_mapping.json](files/data/learning_status_mapping.json)
- [readonly_upstream_review.tsv](files/data/readonly_upstream_review.tsv)
- [generate_wireframes.py](files/code/generate_wireframes.py)
- [render_wireframes.mjs](files/other/render_wireframes.mjs)
- [runtime_requirements.json](files/data/runtime_requirements.json)
- [validate_design.py](files/code/validate_design.py)
- [verify_glyphs.py](files/code/verify_glyphs.py)
- [wireframe_catalog.json](files/data/wireframe_catalog.json)
- [W00_Information_Architecture.png](files/images/W00_Information_Architecture.png)
- [W00_Information_Architecture.svg](files/images/W00_Information_Architecture.svg)
- [W03_Battle_Unknown.png](files/images/W03_Battle_Unknown.png)
- [W03_Battle_Unknown.svg](files/images/W03_Battle_Unknown.svg)
- [W04_Battle_Intent_Missing.png](files/images/W04_Battle_Intent_Missing.png)
- [W04_Battle_Intent_Missing.svg](files/images/W04_Battle_Intent_Missing.svg)
- [W05_Battle_Result.png](files/images/W05_Battle_Result.png)
- [W05_Battle_Result.svg](files/images/W05_Battle_Result.svg)
- [W06_Battle_End_Review.png](files/images/W06_Battle_End_Review.png)
- [W06_Battle_End_Review.svg](files/images/W06_Battle_End_Review.svg)
- [W07_Camp.png](files/images/W07_Camp.png)
- [W07_Camp.svg](files/images/W07_Camp.svg)
- [W08_Party_Draft.png](files/images/W08_Party_Draft.png)
- [W08_Party_Draft.svg](files/images/W08_Party_Draft.svg)
- [W09_Growth_Confirm.png](files/images/W09_Growth_Confirm.png)
- [W09_Growth_Confirm.svg](files/images/W09_Growth_Confirm.svg)
- [W11_Growth_Pending.png](files/images/W11_Growth_Pending.png)
- [W11_Growth_Pending.svg](files/images/W11_Growth_Pending.svg)
- [W12_Chapters.png](files/images/W12_Chapters.png)
- [W12_Chapters.svg](files/images/W12_Chapters.svg)
- [W13_Settlement_Pending.png](files/images/W13_Settlement_Pending.png)
- [W13_Settlement_Pending.svg](files/images/W13_Settlement_Pending.svg)
- [W14_Characters.png](files/images/W14_Characters.png)
- [W14_Characters.svg](files/images/W14_Characters.svg)
- [W15_Handoff.png](files/images/W15_Handoff.png)
- [W15_Handoff.svg](files/images/W15_Handoff.svg)
- [W16_Typography.png](files/images/W16_Typography.png)
- [W16_Typography.svg](files/images/W16_Typography.svg)
- [W17_Battle_Large_Text.png](files/images/W17_Battle_Large_Text.png)
- [W17_Battle_Large_Text.svg](files/images/W17_Battle_Large_Text.svg)
- [P23_delivery_receipt.json](files/data/P23_delivery_receipt.json)
- [ux_anchor_contract.json](files/data/ux_anchor_contract.json)
- [ui_state_map.json](files/data/ui_state_map.json)
- [interaction_spec.md](files/documents/interaction_spec.md)
- [W01_Battle_Ready.png](files/images/W01_Battle_Ready.png)
- [W02_Battle_Target.png](files/images/W02_Battle_Target.png)
- [W10_Learning_Quarantine.png](files/images/W10_Learning_Quarantine.png)
- [W01_Battle_Ready.svg](files/images/W01_Battle_Ready.svg)
- [W02_Battle_Target.svg](files/images/W02_Battle_Target.svg)
- [W10_Learning_Quarantine.svg](files/images/W10_Learning_Quarantine.svg)
- [P24_UI_VisualAssets_V0.1.zip](files/archives/P24_UI_VisualAssets_V0.1.zip)
- [e1cb8b71-1-README.md](files/documents/e1cb8b71-1-README.md)
- [ui_visual_export_manifest.json](files/data/ui_visual_export_manifest.json)
- [placeholder_ui_frame_hand_selected.svg](files/images/placeholder_ui_frame_hand_selected.svg)
- [placeholder_ui_card_back_default.svg](files/images/placeholder_ui_card_back_default.svg)
- [P24_Learning_Quarantine_1280.png](files/images/P24_Learning_Quarantine_1280.png)
- [P24_Geometry_SafeAreas.png](files/images/P24_Geometry_SafeAreas.png)
- [P24_Typography_Scale.png](files/images/P24_Typography_Scale.png)
- [visual_qa_results.json](files/data/visual_qa_results.json)
- [validation_results.json](files/data/validation_results.json)
- [5c4a57cc-1-blocker_register.json](files/data/5c4a57cc-1-blocker_register.json)
- [P24_delivery_receipt.json](files/data/P24_delivery_receipt.json)
- [P24_delivery_report.md](files/documents/P24_delivery_report.md)
- [ui_asset_state_matrix.tsv](files/data/ui_asset_state_matrix.tsv)
- [delivery_manifest.json](files/data/delivery_manifest.json)
- [source_input_receipt.json](files/data/source_input_receipt.json)
- [verification_status.json](files/data/verification_status.json)
- [interface_rfcs.json](files/data/interface_rfcs.json)
- [actual_path_request.json](files/data/actual_path_request.json)
- [ui_visual_spec.md](files/documents/ui_visual_spec.md)
- [integration_handoff.md](files/documents/integration_handoff.md)
- [p30_import_proposal.json](files/data/p30_import_proposal.json)
- [p23_asset_binding_candidates.json](files/data/p23_asset_binding_candidates.json)
- [asset_id_registration_candidates.tsv](files/data/asset_id_registration_candidates.tsv)
- [P24_preview_index.html](files/code/P24_preview_index.html)
- [P24_Component_States.png](files/images/P24_Component_States.png)
- [P24_Icons_Cost.png](files/images/P24_Icons_Cost.png)
- [P24_Battle_Target_1280.png](files/images/P24_Battle_Target_1280.png)
- [P24_Alpha_NineSlice.png](files/images/P24_Alpha_NineSlice.png)
- [negative_results.json](files/data/negative_results.json)

