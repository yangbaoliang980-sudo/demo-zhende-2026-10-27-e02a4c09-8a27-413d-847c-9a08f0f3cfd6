# P24｜卡框、图标、血条与 UI 视觉资产

**AUTHOR_VISUAL_ASSETS_DELIVERED / S03_PLACEHOLDER / PRODUCTION_INTEGRATION_BLOCKED**

任务：P24-S03-UI-ASSET-001；版本：P24-UI-VISUAL/0.1.0-placeholder。

这是隔离的真实设计资产包，包含105个组件SVG、210张透明PNG、7张可编辑规范/样例画板和10张PNG预览。不存在游戏战斗计算或运行UI实现。

1. 打开 `art/ui/P24_preview_index.html` 浏览预览；该离线索引仅链接本地图片，无网络或业务逻辑。
2. 读取 `art/ui/spec/ui_visual_spec.md`、`ui_asset_state_matrix.tsv` 与 `ui_visual_export_manifest.json`。
3. P30/P32按 `art/ui/spec/integration_handoff.md` 执行静态复验和正式接入预检。
4. 修改SVG时保留字体与透明画布；PNG文字只存在于规范图，组件切图不烘焙业务文字。

P23几何与文字来自已核验固定工件；P25正式风格、P13实际路径、P22命名受理、P30导入协议、P34目标环境、P37许可及P32/P35独立回执未齐。所有资源保持PLACEHOLDER；NOT_RUN不写成PASS。

`delivery_manifest.json`逐件记录全部文件（自身除外）的大小、SHA-256、格式/版本、来源哈希、接收方与修改白名单。包外P24_delivery_receipt.json绑定最终ZIP及该清单，避免循环哈希。独立下载件与ZIP成员同名同字节。
