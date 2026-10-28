# 《言灵旅团》产品范围与验收规格（P01 PRD v0.1）

**状态**：产品方向基线就绪，数量与重要奖励政策未批准；真实游戏/Anki运行 `NOT_RUN`。承接 `requirements_baseline_v6.txt` 与 `requirements_traceability.tsv`；所有条目以需求ID及原话为准。

## 体验闭环
玩家以二次元角色为主要视觉资产；在三人编队下进行回合制卡牌战斗，对怪物卡面使用攻击、防御、治疗、增益等效果；每次权威BattleState结算驱动敌人卡面轻动画、伤害数字与血条变化。通过章节推进和Boss挑战获取角色成长收益；Anki真实桌面端复习事件额外驱动学习资源。不得修改Anki调度。用户未决定零学习日资源机制，不应将卡牌体验完全建立在未经裁决的积分门槛上。

## 当前开发增量（已确认优先顺序，非已完成）
S00有P01需求/问题追踪，P13工程核验和路径owner映射、P22最小内容ID与schema、P34环境、P32验证、P35独立审查。S01先执行纯逻辑确定性核心；S02抽牌/出牌/牌堆、角色骨架和P14唯一费用提交；PRE-S03先确认原创立绘质量；S03完成可独立实测的战斗HUD/敌人意图/卡牌对撞与受击反馈。高质量一人原画样本不等于最终完整角色数量。

## S08完整桌面MVP闭环（后续目标）
在必要的S04–S07能力通过后，且用户任命EXT-INTEGRATOR提供固定集成提交，方能由P36制作双端固定RC，由P32/P33/P34/P35/P37/P38在同RC执行门禁。真实Anki四键/Undo身份、学习账本事务、编队养成、持久存档、章节Boss及首通防重复必须提供原始证据。没有外部整合人和双端E2E就不能称完成。

## 本版明确不冻结
初始角色/普通怪/Boss/卡牌建议规模（3/3/1/20–30）；引擎与具体Windows/其他系统；Anki版本；四键具体奖额、撤销已消费权益的债务/抵扣；无学习日基础行动；装备/稀有度；公开发行/收费；最终整合者身份。见DEC-001–DEC-012。

## 非功能性与验收证据
每个程序任务要有真实源、入口、构建/测试命令、退出码、日志SHA、固定输入；每个正式美术资产应有可编辑源和导出及权利验证；每个跨岗接口需要带契约版、DTO/ID owner、接收回执。单独组件、Mock、静态核验分别报告；P35独立Gate不得作者代签。发生两个连续返工周期而无新增证据，升级P01仲裁，不能自判成功。

## 追踪入口
源证据表 `planning/handoffs/source_evidence.tsv`，41需求 `spec/product/requirements_traceability.tsv`，范围 `spec/product/scope_matrix.tsv`，26问题+阻塞 `planning/handoffs/gate_issues.tsv`，全岗激活 `planning/handoffs/role_activation_register.tsv`，未决策与ADR `planning/decisions/`。
