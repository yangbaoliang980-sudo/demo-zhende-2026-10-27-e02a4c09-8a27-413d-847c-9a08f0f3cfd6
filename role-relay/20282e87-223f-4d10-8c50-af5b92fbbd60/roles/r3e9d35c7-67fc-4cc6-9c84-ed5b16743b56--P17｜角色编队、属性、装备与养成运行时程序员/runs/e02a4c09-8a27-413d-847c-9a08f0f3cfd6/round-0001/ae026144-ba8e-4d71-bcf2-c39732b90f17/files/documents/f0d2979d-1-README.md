# P17｜角色、编队、成长与共享钱包隔离运行库

任务：`P17-S05-S06-S07-META-001`  
版本：`P17-META/0.1.0-isolated`  
状态：`ISOLATED_RUNTIME_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED`

本包交付实际 Python 源码、原始上游配置、可执行测试、只读编队导出、钱包候选契约和执行证据。运行时只生成不可变候选，不拥有物理存档端口。当前缺少 P21 实现及 P13 对 P17 的正式路径授权，因此不能称为正式 S05/S06/S07 接入或桌面游戏完成。

## 实际完成的功能

| 功能 | 行为与范围 |
| --- | --- |
| 角色获取 | 从外部已解析授权引用读取授予内容；未知角色、重复权益、重复角色、跨账号输入拒绝；不自动补发免费角色 |
| 三人编队 | 恰好三个已拥有、已定义且互不相同的角色；保持槽位顺序；不强制攻击／防御／治疗各一 |
| 经验与等级 | 使用 P04 原始累计 XP 门槛和逐级训练代币费用；一次 +1；XP 不扣减、不自动升级 |
| 技能成长 | 使用 P04 原始角色等级条件与 rank 消耗；仅改变养成数据，不自行修改卡牌伤害／治疗／护盾 |
| 装备 | 默认按 P04 关闭。显式测试配置验证获取、装卸、槽位、职业／等级条件、跨角色重复实例和属性复算；测试配置不是 DEC-009 批复 |
| 派生属性 | 按 P04 整数公式计算 HP／攻击／防御／支援；显式装备测试模式叠加测试加成 |
| 共享钱包 | 来源逐笔登记、可用／预留分离、消费、预留释放／兑现、源分摊与守恒；余额不为负 |
| 权益防重 | 学习按来源／集合谱系／受益人／复习家族；首通按账号／章节／关卡；重复掉落另外绑定 battle_id；政策或投递 ID 不重置唯一性 |
| 学习撤销 | 外部 P11 撤销授权下，隔离测试可撤销完整未消费来源；已消费或已预留时返回 BLOCKED，不制造负债或用其他来源填补 |
| 并发与提交边界 | request_id 指纹、领域／钱包 revision、内容哈希、store instance 和 continuity 绑定；P21 应在锁／CAS 内调用重新计算验证 |
| 重新载入 | 从调用者提供的字节、预期哈希及连续性信息重建；验证守恒、来源、拥有权、成长支付与幂等记录；不自行读写游戏存档 |

装备数值、示例 P11/P18 资格与 P21 内存事务模型均有独立测试标记。正式奖励金额、已消费撤销政策、无学习日保底政策、免费角色／起始牌及内容规模未在本包批准。

## 快速运行

完整解压 `P17_CharacterPartyWallet_V0.1.zip`，进入同名根目录。已实测环境为 Linux + Python 3.12.14；使用标准库及包内未修改的 P13 校验器，不需要安装依赖。

```bash
python -B tools/verify_delivery.py
python -B tools/author_tests.py
python -B tools/check_contracts.py
python -B -m character_party_runtime
python -B tools/replay_demo.py
python -B tools/check_determinism.py
python -B tools/preflight.py
```

前六条用于已交付隔离成果。最后一条预期以 **exit 3 / BLOCKED** 结束，列出真实工程接入缺项；不能把它修改为 exit 0 作为放行方式。Windows 的 `python` 命令可使用同样参数，但目标 Windows 实测仍为 NOT_RUN。

## 可复算示例

示例实际执行了 P04 原 `character_lifecycle_fixtures.json`：空状态→三个唯一角色授予→15 训练代币→三个 XP 授予→编队→升级→重新解码。11 个模拟事务之后：

| 角色 | 等级 | 累计 XP | HP／攻击／防御／支援 |
| --- | ---: | ---: | --- |
| MOCK_P04_CHAR_001 | 2 | 10 | 108／21／6／4 |
| MOCK_P04_CHAR_002 | 3 | 25 | 168／10／23／6 |
| MOCK_P04_CHAR_003 | 1 | 10 | 108／7／7／17 |

余额为 `15 − 4 − 4 − 6 = 1`。每一步完整请求、证据夹具、不可变候选、P13 投影和内存模型回执均在 `examples/lifecycle_execution.json`。重新载入后重试原请求返回 DUPLICATE_NO_OP。回执始终标记 `durable=false`。

## 阅读入口与实体路径

| 路径 | 用途 |
| --- | --- |
| `character_party_runtime/` | 公共 API、输入适配、状态验证、候选调度；没有正式存档实现 |
| `runtime/meta/wallet/rules.py` | P17 共享钱包业务及来源分摊 |
| `runtime/meta/characters/rules.py` | 获取、XP、等级、技能、装备与属性 |
| `runtime/meta/party/projection.py` | 编队合法性、完整战斗导出和原 P13 DTO 投影 |
| `wallet_delta_contract.json` | P13 原 WalletDeltaCandidate 定义的独立 Schema 投影 |
| `wallet_concurrency_tests.py` | 真实线程争用测试；受测提交端明确是内存模型 |
| `tests/character_unit/` | 作者测试；P32 独测另行执行 |
| `tests/support/` | 明确隔离的 P11/P18 输入夹具和 P21 内存边界模型 |
| `P17_API.md` | 调用、数据、错误、唯一性与事务语义 |
| `integration_handoff.md` | 下一位接收和正式接入要求 |
| `verification_status.json` | 作者、独测、契约、真机、E2E 分层状态 |
| `blockers.json`、`interface_rfcs.json` | 精确缺项、责任方、base SHA 和待审提案 |
| `source_input_receipt.json`、`sources/` | 来源固定版本及未修改原件 |
| `evidence/runs/` | 每次实际执行日志、退出码、执行源码副本，含失败记录 |
| `delivery_manifest.sha256.tsv` | 逐文件大小、SHA、版本、源哈希、接收人和修改白名单 |

## 原始材料与复用

本轮展开并核验了 5 个上传 ZIP、48 个外层附件、73 个去重 ZIP 和 5069 个展开成员。716 条转交 manifest 记录及 527 条选定上游 SHA 清单记录均按实际字节检查。这里的数量分别描述外层转交、内层归档和展开文件，不能相加当作不同成果数。

V6.0 岗位仓库固定提交为 `8c370d731c323f86ff19642f4cc73f818498f641`；P16 转交固定提交为 `52f17647daf8de567e9ed08428ec550588943bd6`。GitHub 树读取及本地 Git blob 匹配保存在 `evidence/intake/`。P04 原件是配置与校验器，并非已存在的 P17 运行库，因此本包复用其内容和公式，未另造一套成长数值。

P13 的 `actual_path_mapping.json` 对 P17 四条正式路径仍为 `actual_production_path=null`、`write_allowed=false`。本包目录仅是本次授权的隔离交付布局，不能作为覆写真实工程的授权。

## 明确的接入限制

P11 原 `WalletPort.compute(RewardIntent, wallet_snapshot)` 与本包 `EvidencePort`、来源批次模型之间尚无批准的无损适配；原 `source_after` 的会计结构不能被 P13 的简化投影替代。正式学习资格、四键奖励与撤销政策仍归 P11/P08/P01。

P13 的 `EntityStats` 尚不包含 support、技能、装备及 P03 别名。本包同时交完整 `PartyBattleExport` 与兼容原形状的 `PartySnapshot`，没有把这些字段偷偷塞进旧 DTO。P15/P14 的战斗消费和伤害规则保持其各自所有权，接线须经 P13 契约处理。

正式 P21 存档原子性、断电恢复、备份回退、目标引擎、Windows、真实 Anki、整游戏 E2E、P32、P33、P35 均未在本轮验收。修改生产开关或持久化自报字段不能补齐这些证据。

跨模块整合仍交由用户后续指定的 EXT-INTEGRATOR。本包只准备交接，不代签下游接收或独立放行。
