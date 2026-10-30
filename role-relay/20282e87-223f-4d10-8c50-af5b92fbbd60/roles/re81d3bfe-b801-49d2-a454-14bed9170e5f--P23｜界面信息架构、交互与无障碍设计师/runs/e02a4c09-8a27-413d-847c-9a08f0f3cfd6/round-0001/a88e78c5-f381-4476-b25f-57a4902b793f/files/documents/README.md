# P23｜界面信息架构、交互与无障碍交付

**交付版本：P23-UX-A11Y/0.1.0-isolated。任务：P23-S03-S06-UX-001。**

这是一份可编辑、可独立校验的 P23 设计资产包。优先完成 S03 战斗信息与交互，同时对齐已收到的 P20 元界面异常态；S08 仅提供待执行验收任务。没有修改 P19/P20/P29 或其他岗位工程，没有运行或整合整游戏。

P19 战斗“查询本次操作”沿用原接口的同 ID 原命令重发，与 P20/学习只读查询分开；P19 当前内存 pending 不支持完整页面重载恢复。

正式路径未获 P13 映射：`actual_path_request.json` 的 production_write_authorized=false。正式工程接入为 BLOCKED；独立测试、真机、玩家试用、真实 Anki/E2E 均 NOT_RUN。

## 阅读与文件入口

完整解压后，用桌面浏览器打开 **design/ux/P23_wireframe_review.html**。其中按钮是静态设计图，只有目录和 SVG 链接是真实导航，不能测试游戏输入或学习收益。SVG 为可编辑源，PNG 为作者实际 Chromium 渲染预览。随包字体用于离线一致预览。

| 实体文件/目录 | 内容 |
| --- | --- |
| design/ux/wireframes/ | 18 张低保真 SVG 与同名 PNG；已有页面、异常态及排版板 |
| design/ux/ux_anchor_contract.json | 79 个语义锚点模板/固定锚点、坐标、身份、权限和兼容边界 |
| design/ux/ui_state_map.json | screen_id、widget_id、states、focus_scope、anchor_id 对照 |
| design/ux/interaction_state_matrix.tsv | 52 个 UI 状态，原始 owner 条件、提示、操作、焦点和退出条件 |
| design/ux/keyboard_focus_matrix.tsv | 52 行焦点/键盘/手柄/鼠标操作矩阵，真实设备结果 NOT_RUN |
| design/ux/information_architecture.md / .json | 学习—角色—章节—战斗主路径与九个既有页面 |
| design/ux/interaction_spec.md | 选牌/目标/回合、重复输入、未知恢复、角色与奖励的交互规则 |
| design/accessibility/typography_accessibility_spec.md | 中文/日文排版、字体回退、焦点、对比、非颜色表达 |
| design/accessibility/reduced_motion_cases.md | 13 个减少动效、静音、跳过、缺失锚点案例；运行均 NOT_RUN |
| design/accessibility/ux_acceptance_tasks.tsv | 31 项可度量下游验收任务，含独立证据门禁 |
| design/ux/validation/ | 标准库静态校验器、可选渲染/字体检查/线框生成器 |
| design/ux/evidence/ | 原始渲染结果、失败记录、来源原件、作者检查与环境 |
| source_input_receipt.json / delivery_manifest.json | 固定输入与逐件大小/SHA-256/版本/接收人/修改白名单 |
| interface_rfcs.json / design/ux/integration_handoff.md | 六项未提交 RFC、版本冲突边界和下游接收说明 |

线框参数、角色/卡牌名称和数量都是设计夹具。三席编队是已确认方向；首发角色数、卡牌数和怪物数仍由 P01 决定。1280×720 是候选逻辑画布，不是已批准目标屏；PNG 的上下标注使文件高度为 856。

## 立即复核（Python 3.10+，无需第三方库）

进入解压后的 P23_UX_Accessibility_V0.1 目录：

```bash
python -B design/ux/validation/validate_design.py --output ../P23_independent_check
```

输出目录必须尚不存在且位于包外。正常退出码 0 只代表**设计文件与完整性校验**。它不运行 P19/P20，不会证明战斗、事务、真实 Anki 或玩家易用性通过。

查看正式接入阻塞：

```bash
python -B design/ux/validation/validate_design.py --preflight --output ../P23_production_preflight
```

当前包预期退出码 **3 / BLOCKED**。不能删掉阻塞记录或改成生产授权来取得“通过”。

## 可选的设计维护与重新渲染

SVG 可以直接在矢量编辑器或文本编辑器修改。若希望从本包布局源重新生成 SVG/目录/HTML，先准备 Pillow、fontTools[woff]，再运行：

```bash
python -B design/ux/validation/generate_wireframes.py --write
python -B design/ux/validation/verify_glyphs.py --output ../P23_glyph_check.json
```

`--write` 仅写本隔离包 P23 设计文件；不适用于真实工程。改动后需更新版本/契约/目录、重新渲染、校验并重新打包。旧清单和旧渲染哈希不会再匹配，这是正常的版本保护。

本包提供 Playwright 渲染器，运行环境需自行安装 Node 与 Playwright 及浏览器。可用 `P23_PLAYWRIGHT_MODULE` 指定 Playwright 包位置，`P23_BROWSER_EXECUTABLE` 指定浏览器；不附大体积浏览器二进制或 node_modules。

```bash
node design/ux/validation/render_wireframes.mjs --output ../P23_render_check
```

该命令只读原图，在包外生成 PNG 与 render_results.json；加 `--publish-previews` 才更新本包预览。只允许 file/data 请求。作者使用的精确环境和浏览器版本在 evidence/environment_observed.json；依赖记录见 validation/runtime_requirements.json。字体与渲染检查不会运行游戏。

## 接收与验收边界

P19/P20 接收交互与状态绑定，P24/P25 接收布局及视觉约束，P29 接收锚点与减少动效，P28/P39 按 IC-21 和无障碍要求接收。P32 独测、P33 用户/双语试用、P35 独审、P37 字体/素材合规分别独立执行。P13 实际路径和用户指定 EXT-INTEGRATOR 到位前不得跨模块落位/合并。

详细状态、已修正问题、来源证据与正式接入缺项见 P23_delivery_report.md、author_walkthrough.md、blocker_register.json。ZIP、单独导出与包内同名原字节关系由包外 P23_delivery_receipt.json 绑定。
