# P25｜《言灵旅团》美术基准与资产审查交付

**任务：P25-PRE-S03-ART-001　版本：P25-ART-BIBLE/0.1.0**  
**美术规范和 P24 占位风格审查已交付；正式单人样本与批量制作 BLOCKED。**

先打开 [P25_review_index.html](P25_review_index.html) 查看图文索引，再读 [P25_delivery_report.md](P25_delivery_report.md)。所有本轮文件都在隔离目录；生产落位仍待 P13 的实际映射。

## 直接使用

- P26：读取 `art_direction/style_bible.md`、`character_brief_template.md`、`layer_export_spec.md`、`crop_profiles.json` 与 `sample_acceptance.tsv`，仅开展一名已指定角色的样本；不从历史占位名字推断正式人设。
- P24：读取 `asset_visual_reviews/P24_review.md`、`P24_asset_reviews.tsv` 和 `P24_RFC04_response.json`。105 项现有组件接受用于 S03 占位视觉；正式版补色彩元数据记录及与正式角色同屏证据。
- P27/P28：读取同一 Bible 和 `asset_visual_reviews/P26_P27_P28_review_status.md`，作品未收到前不填写审美 PASS。
- P30：读取 `layer_export_spec.md`、`crop_profiles.json`、`interface_rfcs.json`。尺寸是审查/制作基准；当前没有已受理的实际引擎导入协议。
- P35：从 `source_input_receipt.json`、`delivery_manifest.json`、`verification_status.json` 和 `asset_visual_reviews/evidence/` 复核。独立审查尚未执行。

## 复验

需要 Python 3.12（本次实际版本见环境记录）和 Pillow。以下输出目录必须尚不存在，且位于包外。

```bash
python -B validation/validate_p25.py --output ../P25_static_check
python -B validation/validate_p25.py --preflight --output ../P25_formal_gate
python -B validation/inspect_sample.py \
  --submission art_direction/sample_submission_template.json \
  --base . --output ../P25_template_gate
```

本固定版本的预期退出码依次是 **0、3、3**。第一个只验证交付完整性和静态规格；后两个因未收到正式样本而保持 BLOCKED。

如需复跑防误放行检查：

```bash
python -B validation/run_negative_checks.py --output ../P25_negative_check
```

它在包外建立可丢弃副本，验证 9 种损坏或错误晋级会被拒绝，预期退出码 0。原包不被改写。

如需重新生成规范图和联系表，另需 Inkscape、fontTools、Node，并使用包内 P24 原始字体文件：

```bash
python -B validation/build_review_visuals.py --output ../P25_render_again
```

重渲染可能因软件/字体版本产生不同字节，不得覆盖本固定版本后沿用旧哈希。先查看实际 PNG，尤其是 105 格切图是否真的显示，再登记新版本。

## 目录边界

`art_direction/` 是 Bible、源文件规范、机器可读色板/裁切及空白模板；`asset_visual_reviews/` 是评审、门禁、实图与证据；`validation/` 是只读复验和包外生成工具。`evidence/upstream/P24/` 保留 P24 原 436 文件，属于证据副本，不计为本轮新绘素材，不允许 P25 改画。

`delivery_manifest.json` 逐件绑定路径、大小、SHA-256、格式、版本、输入哈希、接收方和修改白名单；它自身与最终 ZIP 由包外 `P25_delivery_receipt.json` 绑定，以避免循环哈希。回执不在 ZIP 内。

**空白 ORA、几何比例图和裁切指南均为 TEMPLATE_NOT_ART。正式人物/敌人/特效资产数为 0；P25 不代替画师、不签发行许可，也不宣称游戏已集成。**
