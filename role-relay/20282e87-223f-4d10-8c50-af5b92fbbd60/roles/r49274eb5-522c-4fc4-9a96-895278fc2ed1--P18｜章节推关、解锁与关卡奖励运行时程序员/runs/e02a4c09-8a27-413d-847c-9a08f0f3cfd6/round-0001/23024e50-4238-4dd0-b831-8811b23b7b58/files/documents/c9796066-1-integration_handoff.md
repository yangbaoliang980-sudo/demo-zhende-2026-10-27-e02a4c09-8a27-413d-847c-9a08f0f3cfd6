# P18 下一位接收说明

**交付：`P18-STAGES/0.1.0-isolated`；正式接入：BLOCKED。** 本包提供真实 P18 领域源码、可执行作者测试、只读上游原件、输入收据与执行证据；P21 持久提交、P32 独测、P33 人工验收和 P35 独审尚未执行。所有跨岗位接收记录均为 `PREPARED_NOT_ACKNOWLEDGED`，没有向他人发送消息或代签。

## 先核验再接入

1. 核对包外 `P18_delivery_receipt.json` 的 ZIP 大小和 SHA-256；解压到新目录。
2. 在包根执行 `python -B tools/verify_delivery.py`，逐文件核验清单及 95 份只读输入；不要从单独导出的 `service.py` 运行完整模块。
3. 执行 README 中的复现命令。详细原始 stdout/stderr、命令、时间与执行源码快照保存在 `evidence/runs/`。包外收据另记录最终 ZIP 新解压复跑。
4. 正式工程只能在 P13 给出 actual_path_mapping、固定 base commit 和白名单后，由用户指定 EXT-INTEGRATOR 接入。当前包内任何建议路径都不是实际工程写入授权。

## 接收范围

| 接收岗位 | 应接收文件 | 需要完成的动作 |
| --- | --- | --- |
| P20 | `stage_runtime/projection.py`、完整视图样例、API | 使用已提交快照；显示 locked/in-progress/review/pending；页面不自行领奖；本岗没有实现章节 UI |
| P21 | `transactions.py`、`state.py`、联合 bundle 样例、事务与恢复测试 | 提供真实原子提交、唯一键、回执查询、一致读取及外部备份 fence；钱包和 XP 不能分开提交 |
| P17 | grant 生成逻辑、联合事务、P17 契约测试端口 | 接受或修订 stable save scope/profile 映射与固定 campaign namespace；钱包/XP 仍由 P17 算术产生 |
| P14 | BattleResult 校验、native 契约执行文件、生命周期 RFC | 确认 admission 绑定与终局权威读取；补撤销/修订高水位契约，不让 P18 生成结果 |
| P13 | `actual_path_request.json`、`stage_runtime_contract.json`、RFC | 批准实际路径及 DTO/联合事务扩展；保留原接口 base SHA |
| P07/P05 | 原配置引用、35/67 重放结果、RFC | 确认解锁/奖励候选、ST-030/ST-031 差异及零/重复掉落预算；P18 未编辑策划表 |
| P22 | 首通向量、内容引用、alias/迁移阻塞 | 发布正式 stage IDs 和稳定映射，不因改名/版本变化重置首通 |
| P32 | 全部源码、用例、原始执行证据、固定源码快照 | 独立运行单元/契约/并发/故障/恢复用例；为真实 P21 实现补持久故障复测 |
| P33 | 生命周期样例、验收条目 | 在目标引擎/系统人工验证退出重进、状态展示、重试和章节边界 |
| P35 | 源输入收据、清单、门禁状态、包外收据 | 独立确认所有权、来源、执行证据、未执行项和最终包哈希 |
| P01/P34 | blockers、环境观测及目标环境请求 | P01 批准 S07 正式启动/预算范围，P34 提供目标工程与真机证据 |
| EXT-INTEGRATOR | 完整 ZIP 与以上接收回执 | 在用户另行授权后实施跨模块接线、构建和整机验证 |

## P21 需要保存的最小原子域

同一事务包含 StageProgress 依据、attempt admission/终局、first_clear tombstone、终局高水位、解锁依据、P17 钱包来源与角色 XP 后态、请求指纹和提交回执。实际数据库表结构、WAL、备份和落盘 API 属于 P21。本包只给不可变候选和校验函数，不提供真实数据库实现。

读取源必须与写入处于同一串行化边界。validate_atomic 成功后仍可能发生进程退出，只有真实持久 commit 回执能允许下一关。如果返回 UNKNOWN，先查询原 transaction/request；不能换 ID 重新授奖。恢复旧备份必须向备份外的权威头核对，不接受旧快照自证最新。

首通唯一约束使用 stable save scope + canonical stage。P17 的固定 `YLTT_STAGE_SCOPE` 映射需要审批，不得替换为 chapter/content version。当前 repeat 关闭；没有取得 P05 新预算前，不能开启测试用正金额 repeat Catalog。

## 源码所有权和修改白名单

P18 新交付白名单为本隔离包的 `stage_runtime/**`、`tests/stage_unit/**`、`tests/support/**`、`tools/**`、`examples/**` 及根目录 P18 文档/接口/夹具/收据。测试支持只属于本包，不替代其他岗位实现。`upstream/**`、`evidence/github/**`、原始 intake index 和已封存执行证据只读。

正式计划路径仍是 `runtime/meta/stages/**`、`runtime/meta/progression/**`、`tests/stage_unit/**`，在原 P13 mapping 中均为 null / write_allowed=false。没有修改真实工程、P07 表、P14 核心、P17 钱包、P21 存储或其他岗位独占路径。

跨接口修改采用 `interface_rfcs.json`，包含实际 base SHA 和提案文件哈希。收到不同 base 的实现时保留双方 base 与 ChangeRequest，不做覆盖式合并。某 owner 的缺陷返回该 owner；同一问题连续两轮返工无新证据才升级 P01。本次没有伪造 owner 接收或独立关单。

## 恢复交接

发生 reward 对账冲突时，保留原 BattleResult、最终快照摘要、admission、stage state、首通 tombstone、P17 grant/candidate 与 P21 回执；冻结相关新领奖请求。P07 查资格/解锁，P14 查终局，P21 查物理事务。P18 不删除证据、不自行负扣 Wallet、不把历史首通改成可再次领取。

若需要重跑而原工作目录不存在，完整 ZIP 已包含测试用 P13/P14/P17 源码及 P07/P05/P06 配置，不依赖历史绝对路径。收到的上游仓库固定提交和原件摘要已记录在 `source_input_receipt.json`；无需把全部历史压缩包再展开才能运行本包。
