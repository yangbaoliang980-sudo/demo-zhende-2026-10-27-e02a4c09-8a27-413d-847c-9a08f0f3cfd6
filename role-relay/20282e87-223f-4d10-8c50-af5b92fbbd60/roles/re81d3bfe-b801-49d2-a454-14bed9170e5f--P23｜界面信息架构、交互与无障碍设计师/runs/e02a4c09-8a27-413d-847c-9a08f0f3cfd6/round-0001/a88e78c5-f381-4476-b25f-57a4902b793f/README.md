# P23｜界面信息架构、交互与无障碍交付

**已完成可下载的隔离设计资产包，并在最终 ZIP 的新解压目录完成复核：20 项静态检查、9 项负向检查全部通过。**

任务编号：`P23-S03-S06-UX-001`
交付版本：`P23-UX-A11Y/0.1.0-isolated`
当前状态：**AUTHOR_DESIGN_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED**

本轮完成了信息架构、可编辑线框、状态与焦点契约、无障碍和中日文排版规范、可执行静态校验器及交接证据。正式工程接入仍缺 P13 实际路径映射及相关接口受理；程序运行、目标设备、独立验收、真实 Anki/E2E 均按实际情况保留 **BLOCKED / NOT_RUN**。

## 一、完整成果下载

| 文件 | 实际大小 | 内容 |
| --- | --- | --- |
| **P23_UX_Accessibility_V0.1.zip** | **9,705,884 字节** | **172 个实体文件**：设计源文件、预览、契约、规范、校验工具、来源原件、失败记录和交接说明 |
| **P23_delivery_receipt.json** | **22,288 字节** | ZIP 与 **33 个独立导出**的大小和 SHA-256；最终新解压复跑命令、退出码、原始输出及完整性结果 |
| P23_delivery_report.md | 交付报告 | 工作范围、设计决策、输入核验、验证边界及阻塞责任方 |
| README.md | 阅读入口 | 查看线框、复核文件、重新生成和渲染的方法 |

最终 ZIP 的 SHA-256：

纯文本

`6ac0dd8506586f1310addcb5a94c4bae23fb776ab18072b3d93f261dab005b4d`

已实际完成 ZIP CRC 检查、**172 个包内文件与生成目录逐字节比对**、**33 个独立导出与 ZIP 对应文件同名同字节检查**，以及新解压目录运行前后的文件不变性检查。逐件清单记录其余 171 个文件，清单自身与 ZIP 由包外回执绑定，避免循环哈希。

## 二、必交工件

下表中的独立下载文件均与 ZIP 内对应文件保持相同名称和原字节。

| 工件 | 本轮内容 |
| --- | --- |
| ux_anchor_contract.json | **79 个锚点条目**；稳定实例身份、坐标空间、失效降级、权限及 P19 既有载荷兼容 |
| ui_state_map.json | screen_id / widget_id / states / focus_scope / anchor_id 对照 |
|  | **52 个 UI 状态**的输入条件、持续提示、允许操作、焦点与退出条件 |
|  | **52 行**键盘、手柄、鼠标操作及焦点恢复规则 |
| information_architecture.md | 学习状态—角色培养—章节—战斗主路径，覆盖九个已有页面 |
| interaction_spec.md | 选牌、目标确认、结束回合、重复输入、未知操作与奖励异常的交互规范 |
| typography_accessibility_spec.md | 中日文排版、长文本、缺字替代、焦点、对比和非颜色表达 |
| reduced_motion_cases.md | **13 个**减少动效、静音、跳过、锚点缺失与恢复案例 |
|  | **31 项**可度量验收任务，包含执行方、修复 owner、测量方法和证据要求 |
| integration_handoff.md | 下游接收文件、接口边界、正式落位条件及冲突处理 |
| source_input_receipt.json | 固定输入的版本、原路径、归档成员、大小与 SHA-256 |
| delivery_manifest.json | 逐件路径、实际大小、SHA-256、格式/版本、源输入哈希、接收方和修改白名单 |

### 线框与可编辑源文件

完整包提供 **18 张 SVG 源文件和 18 张 PNG 预览**，位于包内 design/ux/wireframes/。解压完整 ZIP 后，可打开 design/ux/P23_wireframe_review.html 浏览全部设计。

覆盖内容包括：

- 战斗可操作、目标确认、原操作待确认、意图缺失、权威终局、结束回合复核。
- 营地、编队草稿、升级确认、升级未知、章节冻结、奖励待确认、学习隔离。
- 角色入口、出战交接、中文/日文排版与大字布局提案。

以下是战斗目标确认线框。图中的数字、名称和卡面区域均明确标为设计夹具：

可单独下载：战斗可编辑 SVG（附件：W02_Battle_Target.svg）、、学习隔离 SVG（附件：W10_Learning_Quarantine.svg）、。

## 三、已经落实的关键交互决策

**1. 敌方意图在关闭特效后仍可读。**
敌人卡面保留生命条、生命当前值/最大值和护盾；意图常驻显示行动、目标、基础值×次数及候选/未知标签。实际生命减少与护盾吸收进入独立结算记录，避免把卡面基础值写成真实掉血。

**2. 选牌、选目标与提交分开。**
选择阶段不产生业务命令，最终确认才提交。目标变化、死亡或版本变化后，不自动改选另一个对象并出牌。禁用牌保留完整原因的可达入口。结束回合前的行内复核已形成线框，状态为等待 P01/P19 受理的交互提案。

**3. 战斗查证与只读查询分别绑定。**
核对 P19 API 和控制器后，契约明确：战斗页“查询本次操作”会**重发相同 command_id / expected_revision / payload 的原命令**，依赖核心防重；它不是只读请求。P19 当前未决命令仅保存在内存，完整页面重载后的持久恢复仍受阻。P20 原意图查询与学习记录查询按各自接口单独定义。

**4. 学习连接、记录处理、奖励到账分别展示。**
连接可用、收到消息、模拟 APPLIED、隔离记录均不能直接转成“正式奖励已入账”。学习异常页保留原因和下一步；技术编号放入详情层。隔离状态不使用作弊、惩罚或要求改变 Anki 评分的文案。

**5. 焦点与选中状态有独立表达。**
同页不同控件使用不同固定锚点；动态手牌按实例 ID 保留焦点。目标选中标记和当前输入焦点分别呈现。鼠标流程不要求拖拽，键盘与手柄规则包含禁用原因、对象移除、窗口恢复和设备断连。

**6. 排版与减少动效有明确验收目标。**
正文 18、关键文字 20 逻辑像素，44×44 命中区均为本岗候选指标；目标屏尚未冻结。规范参考 WCAG 2.2 与 W3C 中日文排版资料，实际字号、缩放、辅助技术和玩家理解效果仍需目标环境验收。[w3.org](https://www.w3.org/TR/WCAG22/?utm_source=chatgpt.com)

## 四、实际验证结果

以下以**最终 ZIP 新解压目录复跑**为准；重复执行不累计为新增覆盖。

| 验证层级 | 实际结果 | 证明范围 |
| --- | --- | --- |
| 作者静态设计与文件完整性检查 | **20/20 PASS** | 来源字节、锚点、状态、焦点、查询语义、引用、规范与清单 |
| 负向检查 | **9/9 按预期拒绝** | 重复锚点、越权写入、身份改写、错误到账标签、焦点断链、缺失异常态、路径越界、错误只读标记等 |
| 静态线框渲染 | **18/18 PASS** | Chromium 实际渲染；717 个文字节点的画板边界检查无越界 |
| 候选对比色检查 | **6/6 PASS** | 本包低保真实色 token；未代替正式美术色板验收 |
| 字体覆盖检查 | **普通夹具无意外缺字** | 两个刻意缺字用例保留明确替代，原始 UTF-8 未改写 |
| 设计生成器复跑 | **字节一致** | SVG、目录与离线浏览文件 |
| ZIP、包内文件和独立导出 | **PASS** | 172 个包内文件、33 个独立导出 |
| 正式接入预检 | **BLOCKED，exit 3** | 路径、环境及接口受理条件不足 |
| 游戏单元/运行契约/目标设备测试 | **NOT_RUN** | 未用设计校验替代 |
| P32、P33、P35 独立验收 | **NOT_RUN** | 未代签 |
| P25 风格、P37 合规 | **NOT_RUN** | 字体原件与许可已附，独立审核待执行 |
| 真实 Anki、正式奖励入账、整游戏 E2E | **NOT_RUN** | 未执行 |

本轮实际处理 **15 个上传件、121 个去重归档、9,939 个成员和 839 条 relay 校验记录**，保留了 **56 份相关来源原件**。同时保留作者渲染失败记录，以及字号、连接一致性、锚点、字体、焦点和战斗查询语义的修正前证据。详见 author_walkthrough.md 和 verification_status.json。

## 五、正式接入仍需补齐的条件

| 责任方 | 需要补齐的证据 |
| --- | --- |
| **P13** | 真实工程固定提交、P23 两条实际路径映射和写入白名单；权威意图视图；原操作恢复及 P20/P21 正式适配受理 |
| **P01** | 阶段范围、结束回合复核等提案决定；MVP 数量及未决奖励政策 |
| **P34** | 引擎、目标 OS、构建入口、分辨率/DPI、语言和输入设备的执行证据 |
| **P25** | 固定版本的正式视觉基础、字体/色板与立绘安全区 |
| **P29** | IC-23 锚点与表现模式的版本受理 |
| **P32 / P33 / P35 等** | 独立复测、玩家/双语/设备验收及证据门禁 |
| **用户指定的 EXT-INTEGRATOR** | 获授权后的跨模块整合 |

六项 RFC 已准备，状态均为 PREPARED_NOT_SUBMITTED；接收条目为 PREPARED_NOT_ACKNOWLEDGED。具体版本与 base SHA 见 interface_rfcs.json，缺项和跟进 owner 见 blocker_register.json。

## 六、下一位直接复核

完整解压后进入 P23_UX_Accessibility_V0.1：

Bash

```
python -B design/ux/validation/validate_design.py \
  --output ../P23_independent_check
```

预期退出码为 **0**。该命令校验设计文件与交付完整性。

查看正式接入门禁：

Bash

```
python -B design/ux/validation/validate_design.py \
  --preflight \
  --output ../P23_production_preflight
```

当前包预期返回 **BLOCKED，退出码 3**。输出目录须尚不存在，并位于包外。

**下一接收方可立即使用本包开展 P19/P20 的设计实施评审、P24/P25/P29 的资产与接口受理，以及 P32/P35 的独立静态复核和证据审查。**

---

## 本次归档的原始文件

- [P23_UX_Accessibility_V0.1.zip](files/archives/P23_UX_Accessibility_V0.1.zip)
- [P23_delivery_report.md](files/documents/P23_delivery_report.md)
- [delivery_manifest.json](files/data/delivery_manifest.json)
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
- [blocker_register.json](files/data/blocker_register.json)
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
- [integration_handoff.md](files/documents/integration_handoff.md)
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
- [source_input_receipt.json](files/data/source_input_receipt.json)
- [verification_status.json](files/data/verification_status.json)
- [P23_delivery_receipt.json](files/data/P23_delivery_receipt.json)
- [README.md](files/documents/README.md)
- [actual_path_request.json](files/data/actual_path_request.json)
- [interface_rfcs.json](files/data/interface_rfcs.json)
- [ux_anchor_contract.json](files/data/ux_anchor_contract.json)
- [ui_state_map.json](files/data/ui_state_map.json)
- [interaction_spec.md](files/documents/interaction_spec.md)
- [W01_Battle_Ready.png](files/images/W01_Battle_Ready.png)
- [W02_Battle_Target.png](files/images/W02_Battle_Target.png)
- [W10_Learning_Quarantine.png](files/images/W10_Learning_Quarantine.png)
- [W01_Battle_Ready.svg](files/images/W01_Battle_Ready.svg)
- [W02_Battle_Target.svg](files/images/W02_Battle_Target.svg)
- [W10_Learning_Quarantine.svg](files/images/W10_Learning_Quarantine.svg)

