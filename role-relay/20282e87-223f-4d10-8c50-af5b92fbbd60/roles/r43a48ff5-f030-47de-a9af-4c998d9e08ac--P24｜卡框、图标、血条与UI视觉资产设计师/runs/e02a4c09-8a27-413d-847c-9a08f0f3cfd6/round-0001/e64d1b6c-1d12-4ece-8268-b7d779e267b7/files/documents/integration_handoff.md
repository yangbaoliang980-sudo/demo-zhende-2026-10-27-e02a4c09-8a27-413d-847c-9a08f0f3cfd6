# 下游接收与复验

任务P24-S03-UI-ASSET-001；所有资产PLACEHOLDER。先读ui_visual_spec.md与ui_visual_export_manifest.json。

| 接收方 | 直接接收内容 | 必须补齐的动作 |
| --- | --- | --- |
| P25 | SVG、组件状态图、两张P23换肤样例、色板/安全区/字体证据 | 给出固定风格版与逐件意见；本包不自签审美通过 |
| P37 | 新绘图形说明、字体原字节/许可/哈希 | 审核来源和用途；签署独立回执 |
| P22 | asset_id_registration_candidates.tsv、导出命名、source/input hashes | 受理ID与内容引用；不要改写历史ID |
| P30 | ui_visual_export_manifest.json、210张切图、105个源SVG、p30_import_proposal.json | 取得实际引擎与路径后导入，记录格式/尺寸/alpha/九宫格/图集/字体结果 |
| P19/P20 | 原widget锚点对照、状态层、UI预览与文字规范 | 仅在获授权的自身路径实现绑定；素材不提供新业务命令 |
| P28 | 卡背/卡框/费用/状态图标及安全区 | 不覆盖P24图源；需要改图时提编号请求 |
| P32/P35 | 作者验证器、原始证据、来源/交付清单、阻塞表 | 独立复验、审查同版证据；不要把作者PASS转写为独立PASS |
| EXT-INTEGRATOR | 整包与门禁证据 | 只有用户指定后才跨模块整合 |

## 安全落位

P13现有实际路径表没有P24条目；禁止把本包目录名当已授权生产路径。actual_path_request.json为PREPARED_NOT_SUBMITTED。没有执行GitHub写入、引擎导入、业务源码合并。

保留文件名和原字节；若需适配，创建由P30拥有的派生导入记录，绑定原SVG/PNG哈希和import_version，不覆盖P24源。P24自身返工使用新版本。冲突记录双方base SHA和变更请求；拒绝覆盖式合并。

## 只读校验

解压后进入P24_UI_VisualAssets_V0.1，Python需Pillow：

```bash
python -B art/ui/validation/validate_assets.py --output ../P24_check
python -B art/ui/validation/validate_assets.py --preflight --output ../P24_gate
```

输出目录必须尚不存在并位于包外。普通校验预期exit0；正式接入预检本版预期BLOCKED/exit3。`--negative-tests`可复验刻意破坏的样本，只在临时副本中写入。校验失败exit2。不会修改本包或工程。

## 重新渲染现有图源

渲染需要Node+sharp、Python+fontTools、Node内置Brotli（或fontTools已有Brotli）、fontconfig。精确版本见runtime_requirements.json。准备临时字体，然后将当前SVG导出到包外新目录：

```bash
python art/ui/validation/prepare_fonts.py art/ui/source/fonts ../P24_temp_fonts
node art/ui/validation/render_visuals.mjs --root . --output ../P24_render_assets --fonts ../P24_temp_fonts/fonts.conf --mode assets
node art/ui/validation/render_visuals.mjs --root . --output ../P24_render_boards --fonts ../P24_temp_fonts/fonts.conf --mode boards
```

新建组件生成器build_p24.py需要原P23完整包及本次intake原件；它是可选的作者工具，不是普通复验的前置。直接编辑SVG可不运行生成器；修改后必须刷新清单和复验。样例SVG中的底板引用切图快照，改组件后用create_boards.py重建样例。所有脚本是离线设计工具，不是游戏运行UI。
