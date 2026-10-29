# P18｜关卡进度、解锁与首通奖励运行库

**真实隔离源码与作者验证已交付；正式工程接入仍为 BLOCKED。**

任务编号：`P18-S07-STAGES-001`；版本：`P18-STAGES/0.1.0-isolated`；状态：`ISOLATED_RUNTIME_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED`。

本包直接使用收到的 P07 章节/解锁/奖励原件、P05 预算、P13 codec/DTO、P14 核心和 P17 钱包/养成模块。所有上游副本只读，未修改真实工程。P13 三条 P18 正式路径均为 null / write_allowed=false；P21 真实持久事务接口未收到，跨模块接入留给用户指定 EXT-INTEGRATOR。

## 已实现

关卡选择与进入资格；三人入场参数快照；权威终局消费；失败/退出重试；稳定存档 scope + stage 首通键；重复战斗与终局防重；一次性/重复奖励候选；与 P17 钱包和 XP 的联合候选；解锁与章节完成投影；撤销/对账隔离；备份连续性检查；提交前重算；原 P13 DTO 投影。

首通键不含 battle_id、内容版本、章节或存档文件名。相同 stage 的两场不同战斗获胜只有一次首通。旧终局、非法关卡、伪造结果和重复领奖不会修改 Wallet。重复奖励默认关闭，正金额 repeat 仅在合成测试 Catalog 中验证机制。

P18 运行时不产生 BattleResult，不计算 P17 钱包/成长规则，不写磁盘。所有成功回执在本次测试中均为 `COMMITTED_SIMULATION` / `durable=false`。

## 实际结果

| 层级 | 已执行结果 | 边界 |
| --- | --- | --- |
| 作者设计复核 | COMPLETED_AUTHOR_REVIEW | 不等于 P35 独审 |
| 最终作者测试 | 114 PASS，0 FAIL，0 error，0 skip | 含并发、故障、边界、恢复及 4 项原 P14/P17 契约测试 |
| P07 原夹具重放 | 35 PASS / 67；32 NOT_RUN | 所有期望字段逐项比较；未适配案例没有补 PASS |
| 原 P13 校验器 | 38 个去重 DTO 样例通过 | 只证明原形状合法，不代表扩展接口接收 |
| 跨进程确定性 | 3 个 PYTHONHASHSEED 结果一致 | Linux/Python 作者环境 |
| 子进程重载 | 1 项通过，已包含在总数 | stdin 传入快照和合成 fence；不是真实存档重启 |
| 正式 preflight | BLOCKED，exit 3 | 如实拒绝生产启动 |
| P21 持久化、P32/P33/P35、引擎/Windows/真实 Anki/E2E | NOT_RUN | 未代签或虚构执行 |

这些数字包含重叠验证，不能相加为额外测试总量。原始命令、时间、退出码、stdout/stderr 和对应源码快照见 `evidence/runs/`。最终 ZIP 新解压目录复跑及 ZIP/独立文件逐字节比对在包外 `P18_delivery_receipt.json`。

## 生命周期样例

非法跳 Boss 被拒绝 → 普通关首通 → Boss 战败 → Boss 重试首通 → 普通关再次胜利 → 重复终局 no-op → 重新解码。

按未获正式批准的原候选配置，普通关首通 3 代币/每人 4 XP，Boss 首通 12 代币/每人 18 XP。最终 **15 代币、三人各 22 XP、2 个首通、章节完成**。共 8 次内存模型提交，stage revision=8、meta revision=4、wallet revision=2。重复/战败没有追加奖励。

实际输入、候选、来源及模型回执在 `examples/lifecycle_execution.json`；摘要在 `examples/demo_summary.json`。`examples/native_p14_contract_execution.json` 单独保存原 P14 核心出牌后产生的终局与 P18/P17 处理结果。该原生测试使用合成战斗输入，不声称正式 Boss/平衡或整游戏通过。

## 文件入口

| 路径 | 内容 |
| --- | --- |
| `stage_runtime/**` | 关卡领域源码与事务候选 |
| `first_clear_keys.json` | 实际首通向量和身份边界 |
| `stage_progress_fixtures.json` | 原 P07 67 例的预期与引用；不是执行结果 |
| `stage_reward_tests.py` | 奖励、恢复、事务作者测试入口（完整测试的子集） |
| `tests/stage_unit/**` | 全部作者测试 |
| `tests/support/**` | 明确隔离的 authority/内存模型与原 P14/P17 测试接线 |
| `P18_API.md` | API、请求、身份、原子事务、异常和容量说明 |
| `stage_runtime_contract.json` | 机器可读接口提案说明；不是已批准 JSON Schema |
| `integration_handoff.md` | 下游接收与正式接线要求 |
| `source_input_receipt.json` | 95 份只读输入的字节哈希、固定提交及缺项 |
| `p07_projection_results.json` | 原 P07 实际场景比较结果与 NOT_RUN 项 |
| `verification_status.json` | 分层验证状态 |
| `interface_rfcs.json` / `blockers.json` | 6 项未提交 RFC、11 项正式接入阻塞 |
| `delivery_manifest.json` | 每文件实际大小、哈希、格式/版本、输入哈希、接收方和修改白名单 |
| `downstream_receipts.json` | 带实际文件哈希的准备交接记录，未被对方确认 |

## 复现

完整解压，在包根使用 Python 3.12。本次实测 Python 3.12.14 / Ubuntu 24.04.3；无需 pip 安装。

```bash
python -B tools/verify_delivery.py
python -B tools/author_tests.py
python -B tools/check_contracts.py
python -B -m stage_runtime
python -B tools/replay_demo.py
python -B tools/replay_p07.py
python -B tools/check_determinism.py
python -B tools/preflight.py
```

最后一条应退出 3 并打印 BLOCKED，其余应退出 0。可单独运行 `python -B stage_reward_tests.py` 复测奖励子集；该子集不能与完整测试相加。

## 上游核验与修改边界

收到的 5 个上传包均解包读取，包括嵌套 ZIP；共 80 个去重压缩包、5928 个展开文件成员、734 条 relay 清单校验；外层清单共 66 个原附件。最终复核全部上传和展开字节未改变。正文没有替代这些实体原件。

V6 参考固定提交 `8c370d731c323f86ff19642f4cc73f818498f641`；P17 固定提交 `566c02ac14dd29660260010aa5cf0fbb2d0f125d` 的归档清单匹配实际收到的 P17 ZIP：2,129,280 字节，SHA-256 `339c492a8f4f3963d0391e78eccb1d261a9b289bb12dc43349a22b581148daa4`。GitHub 原文本按 Git blob 逐字节验证，具体证据见源输入收据。

未将临时测试数据转成正式内容。未编辑关卡策划表、敌 AI、P14/P17 源码或真实 P21 存储。新增文件均在本隔离交付目录；当前不具备真实工程覆盖权限。正式路径、持久事务、预算/内容、目标环境和独立门禁解除前，保持生产入口关闭。
