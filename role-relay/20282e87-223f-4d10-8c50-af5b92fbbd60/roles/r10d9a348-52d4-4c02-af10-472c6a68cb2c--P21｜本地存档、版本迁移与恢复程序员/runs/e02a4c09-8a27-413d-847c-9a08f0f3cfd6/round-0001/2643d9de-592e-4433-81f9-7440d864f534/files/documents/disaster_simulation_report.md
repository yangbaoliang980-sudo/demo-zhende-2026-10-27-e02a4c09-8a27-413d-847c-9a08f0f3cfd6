# P21 灾难模拟与实际验证报告

版本：P21-PERSISTENCE/0.1.0-isolated。范围：作者在当前 Linux 隔离环境执行，不代替 P32/P33/P35。

## 实际最终结果

最终主测试 **104 PASS，0 FAIL，0 ERROR，0 skip**。完整 stdout/stderr、argv、cwd、起止 UTC、退出码和执行源码快照在 `recovery_logs/author_final_002/`。环境：Python 3.12.14、SQLite 3.53.1、Linux-6.18.55-x86_64-with-glibc2.39。目标平台仍 BLOCKED。

| 测试分类 | 用例数 | 实际结果 |
| --- | ---: | --- |
| 物理原子事务、防重、围栏、并发 | 30 | PASS |
| 规范序列化与大小限制 | 7 | PASS |
| 原 P11 契约（测试钱包绑定） | 6 | PASS |
| 原 P17/P18 与 P13 契约 | 12 | PASS |
| 原件字节与 import 所有权 | 2 | PASS |
| 核心回执/保存标记回归 | 2 | PASS |
| 真实 SIGKILL：原领域数据 | 7 | PASS |
| 真实 SIGKILL：基础事务/迁移 | 12 | PASS |
| 物理迁移 | 4 | PASS |
| 备份、损坏、回滚与恢复 | 17 | PASS |
| 原请求、未知结果、审计、回执回归 | 5 | PASS |
| 合计 | 104 | PASS |

其中 18 项原代码契约、19 项 SIGKILL 都包含在 104 项内，不另加总。JSON Schema oracle 另有 **25 项检查 PASS**，包括四个 Draft2020-12 metaschema、真实程序输出和负例；原始报告为 `recovery_logs/schema_oracle_001/schema_results.json`。

## 原子性与真实进程终止

8 个通用提交 SIGKILL 点：after_begin、after_record:ledger、after_record:meta、after_receipt、before_commit、after_sql_commit、after_anchor、before_reply。

4 个迁移 SIGKILL 点：after_migration_ddl、before_commit、after_sql_commit、after_anchor。

7 个原领域数据 SIGKILL 点：P11 学习在账本写后/SQL 提交后；P18 关卡在 stage 写后/meta 写后/SQL 提交后；P17 升级在 meta 写后/SQL 提交后。每次子进程真实以 -9 退出，原始 argv、stdout checkpoint、退出码、重开后序号/哈希及净额断言均保存在 cases JSON。

提交前中断重开后保持完整旧状态；提交后中断重开后保持完整新状态，必要时验证回执链上旧 checkpoint 再推进独立连续性记录。重试原请求最多一笔物理事务；原 P17 角色与扣款、原 P18 首通与钱包/经验不会分开落盘。6 个并发独立进程提交同请求，实际只产生一个新提交；读者不观察跨记录混合状态。

这证明的是进程崩溃路径，**真实硬件断电 NOT_RUN**。没有以日志字符串冒充终止：测试确实调用 SIGKILL 并断言操作系统子进程返回码。

## 磁盘满的证据范围

主测试将真实 SQLite `max_page_count` 限制到当前页数，然后写入较大的完整记录，数据库引擎实际返回 SQLITE_FULL；之前已经写入的账本变化随事务回滚，两个记录与 sequence 保持旧值。

另对备份复制和 SQL 已提交后的连续性文件写入注入 OS ENOSPC：不完整备份无 complete 封印，不能当有效备份；提交后外部写失败返回 UNKNOWN，重新校验并查询原事务得到 COMMITTED，不重复入账。**没有填满整个物理卷，物理卷满与目标硬盘故障为 NOT_RUN**。

## 损坏、恢复与反回滚

已执行数据库头损坏、payload checksum 错误、回执 hash 错误、receipt/claims 截断、迁移审计缺失、保存标记畸形、外部连续性缺失/外来身份、只回滚数据库等反例。不能确认历史时返回 UNKNOWN/冻结，不新建零余额存档、不凭备份自证连续性。

`recovery_logs/forensic_demo_001/` 额外保留实际损坏数据库、只读保全副本、旧/当前备份和恢复报告。报告中的 damaged_source_sha256 与 captured_original_sha256 相同；旧备份激活被拒绝，精确备份恢复后 head 与净额不变，awards_replayed=0，重复请求返回原回执。

该损坏演练使用新建测试目录，未读取或修改任何 Anki 数据库。它和早先工具演练对应的运行实现可在 `recovery_logs/author_final/executed_sources.zip` 检查；随后保存标记错误处理加固由最终 author_final_002 全量覆盖。最终 ZIP 复跑证据另见包外回执。

恢复限制：recover_exact 要求活跃身份标记仍可验证，且备份 head 与独立记录完全相同。标记本身损坏会保全并阻塞，需要身份核对；旧备份只能隔离审查。整个磁盘连同独立记录一起回滚没有外部可信依据，仍为正式 BLOCKED。

## 迁移与旧版兼容

实际实现和执行 v1→v2；不是未取得的历史游戏版本。升级在同一事务新增维护审计、改版本、写回执。领域原 bytes 不变。异常 DDL 与 COMMIT 前 SIGKILL 都回到完整 v1；COMMIT 后为完整 v2。原只读备份保存，备份副本可独立迁移演练且保持冻结，reader 1 拒绝读迁移后 v2。

## 原领域可观察净额

原 P17/P18 配合合成入场/终局证据：普通关首通余额 3、每人经验 4；重复请求无新增；Boss 首通后余额 15、每人经验 22；角色升级扣 4，余额 11；重开保持相同角色、关卡与净额。

原 P11 配合明确测试奖励和旧钱包映射：复习净额 10，Undo 后 0，Restore 后 10，重复事件不重复变化。正式 P11 原生 P17 钱包映射未批准，不能把此项写成真实学习到账通过。

## 历史失败与修复

| 执行目录 | 实际用例数 | PASS | failures | errors |
| --- | ---: | ---: | ---: | ---: |
| author_001 | 90 | 90 | 0 | 0 |
| review_counterexamples_001 | 5 | 0 | 3 | 2 |
| review_fixed_001 | 5 | 5 | 0 | 0 |
| native_crash_001 | 7 | 7 | 0 | 0 |
| envelope_counterexample_001 | 1 | 0 | 1 | 0 |
| envelope_fixed_001 | 1 | 1 | 0 | 0 |
| author_final | 103 | 103 | 0 | 0 |
| marker_counterexample_001 | 2 | 1 | 0 | 1 |
| author_final_002 | 104 | 104 | 0 | 0 |

保留以上失败源码和日志，未删去失败后只留绿灯。7 个缺陷均由 P21 自己修复，详见 defect_log.json；独立复测/关单 NOT_RUN。历史运行的同一用例重复执行不计作新增覆盖。

## 门禁状态

| 层级 | 状态 |
| --- | --- |
| 作者设计/代码复核 | COMPLETED_AUTHOR_REVIEW |
| 作者最终单元/契约/故障测试 | PASS（104） |
| Schema oracle | PASS（25） |
| 输入 ZIP/relay 核验与随包原件 | PASS；范围见 source_input_receipt.json |
| 正式接入 preflight | BLOCKED，实际 exit 3 |
| P32 独测、P33 人工目标机、P35 独审 | NOT_RUN |
| 目标引擎、Windows、真实物理断电/盘满 | NOT_RUN |
| P11 原生 P17 学习钱包、P20 生产网关 | BLOCKED |
| 真实 Anki、整游戏 E2E | NOT_RUN |
| 跨模块合并、正式发布 | NOT_PERFORMED |

完整工具执行与用户可下载包的最后字节校验在 P21_delivery_receipt.json。下游需要在同一个交付 SHA 上独立复跑和签收。
