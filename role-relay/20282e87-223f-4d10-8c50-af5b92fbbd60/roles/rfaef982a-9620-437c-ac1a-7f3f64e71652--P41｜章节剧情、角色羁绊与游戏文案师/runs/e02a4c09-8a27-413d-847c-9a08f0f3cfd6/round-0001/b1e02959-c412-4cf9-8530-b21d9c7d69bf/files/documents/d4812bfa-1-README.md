# P41 — S09 剧情授权门禁与交接核验（DEFERRED）

**性质：仅门禁核验交接包，不是剧情开发包。**

- 历史任务书与 V6.0 冻结规则均要求 P41 暂不启动，仅在用户明确批准 S09 剧情范围、P01 出具正式 task ID 后激活。
- 当前转交仅有“直接执行角色职责”的通用要求，原文同时明确 P31/P41/P42/P43 不得无单独授权启动；据此**不能**把该通用要求解释为对 P41 的专门授权。
- 所有转交 ZIP 的实际成员、嵌套 ZIP 的 CRC 与 manifest 已逐件读核；P40 的 30,175 字节原始 ZIP **没有作为本轮附件提供**，仅收到 P40 回执与部分单独手册，故其原始 ZIP SHA 只是上游回执声称，**不是本轮重新计算**。
- GitHub 连接可读取提供的两处仓库元数据；本轮未创建提交、分支、PR、文件或 issue。
- 本包没有 `content/story/**`、`design/lore/**`、`localization/story_strings.tsv`。缺件原因是未授权，不是已经制作却未交付。
- 本包测试是**门禁规则的离线测试**，不等于剧情、Unity、Anki、玩家操作或独立放行测试。

## 实物

`P41_activation_gate.json`：机器可读状态；`gate_review.md`：职责审查与结论；`evidence/source_inventory.tsv`：输入逐件大小及 SHA-256；`evidence/relay_archive_checks.json`：ZIP CRC / manifest 检查；`evidence/blocker_register.tsv`：解除条件与唯一负责方；`evidence/input_inspection.json`：已核实的 ID / 映射 / 上游事实；`tests/verify_activation_gate.py`：门禁校验与状态单测；`tests/validation_log.txt`：实际运行原始输出；`delivery_manifest.json`：本包逐件哈希。

## 启动解除标准

1. 用户明确批准 P41 在 S09 设计/制作**剧情、角色羁绊及关卡文案**，指出范围、预算和是否仅先做独立草案。
2. P01 形成批准的唯一任务 ID 和依赖的固定版本/需求 ID；P13 发出 P41 路径映射与权限，不用 P41 覆盖他岗工程。
3. P04/P07/P22/P23 交付对应稳定角色、关卡、本地化键、文本限制，并记录路径和 SHA-256。
4. 才能生成 `content/story/**`、`localization/story_strings.tsv`、`story_review.md`，随后交 P22/P32/P33/P35 等复核。

本包只能交接给后续核验人；不能作为剧情版本或 S09 PASS 记录。
