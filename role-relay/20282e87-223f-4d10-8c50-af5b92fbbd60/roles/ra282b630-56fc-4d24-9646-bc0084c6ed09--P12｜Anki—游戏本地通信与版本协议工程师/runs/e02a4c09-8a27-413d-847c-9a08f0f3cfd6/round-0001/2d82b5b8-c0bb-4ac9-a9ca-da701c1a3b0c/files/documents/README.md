# P12｜《言灵旅团》Anki—游戏本地通信独立交付

**已实现可执行协议、游戏侧限权入口、只绑定127.0.0.1的通信适配器、持久outbox参考组件及双端Mock。最终作者单元/契约/套接字与outbox测试73/73通过，3项真实双进程退出恢复通过。正式S05接入BLOCKED；真实Anki、真实游戏引擎、P21生产事务、目标机和独立验收NOT_RUN。**

任务：`P12-S04-S05-TRANSPORT-001`  
交付：`P12-ANKI-TRANSPORT/0.1.0-isolated`  
协议：`YLTT-ANKI-TRANSPORT/0.1.0-isolated`  
接口：IC-14、IC-18；上位需求：REQ-003、REQ-011、REQ-025、REQ-026。  
本轮由P12直接执行，未创建子角色，未改写上游源码，未跨模块合并或正式发布。

## 1. 直接读取哪些文件

| 交付内容 | 包内实际相对路径 |
|---|---|
| 协议Schema | contracts/anki_transport/ipc_schema.json |
| 精确版本兼容矩阵 | contracts/anki_transport/protocol_version_matrix.tsv |
| 完整协议、ACK语义、帧认证和字段边界 | contracts/anki_transport/protocol_spec.md |
| ACK/重试时序 | contracts/anki_transport/ack_retry_sequence.md |
| 错误码与重试边界 | contracts/anki_transport/error_codes.tsv |
| 文件交换/Unix socket/named pipe/loopback比较 | contracts/anki_transport/transport_comparison.md |
| 运行源码 | runtime/anki/transport/ipc_server_client/ |
| ACK和P11重放测试 | mocks/anki_transport/ack_replay_tests.py |
| 解析器、套接字、outbox测试 | mocks/anki_transport/parser_contract_tests.py；wire_outbox_tests.py |
| 双端可执行Mock | mocks/anki_transport/process_peer.py |
| 真实双进程恢复驱动 | mocks/anki_transport/process_replay.py |
| 9组请求/响应实体样例 | mocks/anki_transport/fixtures/ |
| 交接与接入边界 | INTEGRATION.md；downstream_handoff.json |
| 原始测试证据及固定源码快照 | evidence/author_run_001 至 author_run_006 |
| 输入、所有权及逐件完整性 | source_input_receipt.json；task_receipt.json；delivery_manifest.sha256.tsv |

上表为阅读入口，完整文件大小、SHA-256、格式/版本、源输入哈希、接收人和修改白名单均逐件写入delivery_manifest.sha256.tsv。清单不散列自己；外层回执绑定清单和ZIP，避免循环哈希。

## 2. 本次真正实现的行为

`protocol.py`执行32KiB帧上限、12层深度、512节点、严格数字及封闭字段校验。未知协议/版本/消息类型显式拒绝。两端从同一Schema读取字段；另用jsonschema 4.25.1对2,369个有效/无效实例交叉核验，结果一致。它是作者算法交叉检查，不是P32独测。

`bridge.py`仅适配收到的P11提案。输入通过校验后交P11；成功回执前再查当前结果与权威凭证。提交成功但回复丢失时，QUERY查询既有账本，不创建新的业务身份。对同一真实事件更换message_id，不产生第二笔奖励。

四类核心处置是ACK_APPLIED、ACK_QUARANTINED、RETRY_LATER、REJECTED。撤销和查询使用STATUS，以免将撤销误写为授奖。ACK_QUARANTINED明确表示本输入已持久隔离、未授奖，outbox仍留存并查询；不是最终消费结束。PENDING_RECONCILIATION可能已有部分回收，因此按未决状态返回，不能冒称无任何经济变化。

`wire.py`只绑定字面量127.0.0.1，采用fresh challenge与HMAC-SHA256绑定方向和原请求；未提供公网、域名或代理回退。`outbox.py`在网络发送前持久记录未确认状态，使用原字节重投，拒绝同message_id不同载荷；容量不足不淘汰原记录。收到终态也保留原输入，等待正式留存政策。

本次没有重写P11账本。`sources/P11/`为原字节只读依赖；SQLiteAtomicModel、FixtureEvidence/Policy/Wallet只在Mock中装配。合成奖励量10复用P08/P11数学夹具，**不是四个评分键的正式奖值**。

## 3. 实际输入核验

3个上传ZIP及包内ZIP已解包。去重后21个ZIP，933个文件成员；CRC全部通过。403条relay清单记录与307条P08/P09/P10/P11内部文件清单记录最终通过。P08清单初次因本岗校验器使用错误基目录而失败，原失败记录保留，修复了校验器基目录，未修改上游文件。

P11完整包SHA-256为`54185f5093f1e7ce8639c883fd5b83dd93ac22bb2de6cc1e89ec8658359181f9`，已通过Git blob内容计算与固定提交`d6e09fe07d1c3674b242ea59dd05231a3cd8acdb`绑定。V6正文与`8c370d731c323f86ff19642f4cc73f818498f641`绑定。详见source_input_receipt及evidence/intake。

P10真实样本数仍为0。提供材料及指定固定仓库树内未取得P13实际路径映射、真实引擎接入及P21生产适配。该结论只覆盖本次提供的范围，不推断其他未提供工程不存在。

## 4. 验证分层

| 层级 | 状态 | 实际覆盖 |
|---|---|---|
| 输入ZIP/清单/固定Git字节绑定 | PASS | 来源及文件完整性，不是程序验收 |
| 作者单元/模拟合同 | PASS，46项 | 18项解析器 + 28项P11 ACK/状态协作 |
| 作者套接字与outbox | PASS，27项 | 实际本机连接及队列边界；部分队列测试不需要套接字 |
| 作者全套汇总 | PASS，73/73 | 上两行合计，不重复计数 |
| JSON Schema算法交叉核验 | PASS，2,369实例 | jsonschema 4.25.1与闭合运行校验器比较 |
| Linux双进程退出恢复 | PASS，3/3 | 提交前退出、提交后ACK丢失、客户端确认前退出 |
| 正式接入前置检查 | BLOCKED，退出码3 | 不产生正式启动能力 |
| 正式设计/合同独立审核 | NOT_RUN | 等待P32/P35及各owner接收 |
| Windows/macOS/用户目标机 | NOT_RUN | 本轮仅Linux环境；Windows私有文件DACL辅助未实现 |
| 真实Anki→游戏→P21→收益E2E | NOT_RUN | 无真实Hook事件、真实游戏或生产事务 |
| P38审核；P32独测；P33人工；P35独审 | NOT_RUN | 未代签独立结果 |

实际环境：Linux x86_64、Python 3.12.14、SQLite 3.53.1。初始沙箱禁止创建socket；之后通过已批准的本机测试执行范围实际运行。3个进程恢复用例最终均为模拟余额10、钱包版本1；并非断电或磁盘故障证据。

最终73项原始日志在evidence/author_run_005；最终进程恢复日志在evidence/author_run_006。Schema交叉核验在author_run_003。开发工具失败和修正见defect_log.json，不删除早期失败记录。

## 5. 下一位复现命令

在解压后的本包根目录，用Python 3.12执行。主程序和普通测试仅使用标准库；不要将Mock装进Anki。

```bash
python -B verification/preflight.py
python -B -m unittest discover -s mocks/anki_transport -p '*_tests.py' -v
python -B -m mocks.anki_transport.process_replay --output /tmp/p12-process-review
python -B verification/verify_delivery.py
```

第一条预期BLOCKED/退出码3，其余成功时为0。套接字测试需要运行环境允许创建本机socket。Windows不是本轮可宣称支持的目标；其权限辅助明确阻断，等待P34/P38完成目标适配。

需要生成新的作者运行回执时，使用包外输出目录，避免改变本交付清单：

```bash
python -B verification/run_author_checks.py --group all --output /tmp/p12-author-review
python -B verification/run_author_checks.py --group process --output /tmp/p12-author-review
```

可选Schema交叉检查需要单独安装requirements-dev.txt中的校验器，在包外环境执行：

```bash
python -m pip install -r requirements-dev.txt
python -B -m mocks.anki_transport.schema_oracle --output /tmp/p12-schema-oracle.json
```

JSON帧、请求/响应、接口调用和权限边界见protocol_spec；双端独立进程用法见INTEGRATION.md。

## 6. 下一位接收和正式阻塞

P10接收Schema、样例、outbox及重试合同；补真实字段/身份能力。P11接收五态到传输处置的具体映射；保持原业务唯一提交逻辑。P13接收actual_path_mapping请求、宿主接口边界和仅隔离可运行源码。P32/P34接收固定测试及原始日志；P35、P38分别执行独立证据/安全门禁。

全部接收状态为PREPARED_NOT_ACKNOWLEDGED。P13批准实际映射前，不得把本包的设计路径直接覆盖到真实工程。正式接入仍缺P13真实工程/路径、P10目标探针、P11/P21正式事务合同、P34目标环境、P38字段/权限批准及政策/分类/钱包相关依赖。完整条目和唯一责任入口见formal_prerequisites.json。

跨模块整合仍等待用户指定EXT-INTEGRATOR。本包没有GitHub写入、整合PR、正式安装或发布行为。
