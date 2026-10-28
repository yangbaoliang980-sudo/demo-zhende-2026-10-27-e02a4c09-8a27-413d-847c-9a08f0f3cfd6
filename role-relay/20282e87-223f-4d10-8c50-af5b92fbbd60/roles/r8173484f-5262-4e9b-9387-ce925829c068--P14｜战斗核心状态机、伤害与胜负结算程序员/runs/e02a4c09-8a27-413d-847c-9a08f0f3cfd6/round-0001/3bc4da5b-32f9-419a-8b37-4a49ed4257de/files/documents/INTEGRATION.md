# 下游接收与集成说明

## 接收原则

这是可执行、可复现的P12隔离组件。包内contracts/runtime/mocks路径为设计布局；`path_mapping_request.json`的actual_path仍为null，不能当作P13授权。所有sources文件只读；发生冲突时保留双方base SHA和ChangeRequest，由原owner修改。

运行时适配层不导入Anki、SQLite账本、奖励计算或P11模拟证据。它调用P11候选LedgerPort以及P21候选ReceiptAuthority。outbox SQLite只承担插件侧传输保管参考用途；当前仅由Mock使用，不接触Anki数据库和游戏物理存档。

## 核心接口

```python
# 这些调用只用于0.1.0-isolated，不具备生产启动授权。
from runtime.anki.transport.ipc_server_client.bridge import Pairing, P11Bridge, GameIngress
from runtime.anki.transport.ipc_server_client.wire import LoopbackServer, LoopbackClient, LoopbackAddress

pair = Pairing(producer_id, source_id, collection_lineage, beneficiary_id, secret_bytes)
bridge = P11Bridge(p11_service, p21_candidate_authority, pair.scope,
                   execution_mode="isolated")
ingress = GameIngress(pair, bridge)
server = LoopbackServer(ingress, LoopbackAddress(port=0))
client = LoopbackClient(server.address, pair)
```

P11服务提供handle(raw_bytes)、query(inbox_id)。P21候选authority提供snapshot()、lookup(transaction_id)；类型当前依据P11原始提案。bridge暂时读取P11当前行/修正族的提交关联以严格核验回执；这是已测试的隔离结构耦合。P13/P11/P21在正式接收时应共同决定稳定的内部只读结果投影，不允许P12自行改P11内部状态或存储结构。

`Backpressure`、`BackendUnavailable`是本包适配器局部异常，映射为可保留重试的传输结果，不是已批准的P21生产错误枚举。真实适配要保留“可能已提交”的不确定性；不得将未知数据库异常当作权威未提交。

生产执行模式会抛出PRODUCTION_ADAPTER_NOT_APPROVED。P11Evidence/Policy默认关闭的行为保留；线上正式来源认证必须由真实适配器实现。不能以删除isolated后缀或将FixtureEvidence复制到runtime的方式绕过门禁。

## 两端Mock独立运行

自动驱动最方便：

```bash
python -B -m mocks.anki_transport.process_replay --output /tmp/p12-process-review
```

它创建私有临时目录和随机密钥，启动真正不同PID的game/plugin进程，注入退出点，恢复后检查模拟钱包只变更一次。仅输出脱离密钥/数据库的合成执行日志。

需要逐端观察时，可在允许本机socket的Linux环境创建一个全新的测试目录（先选择自己的未使用目录）：

```bash
python -B -c 'from runtime.anki.transport.ipc_server_client.local import private_directory,create_key; p=private_directory("/tmp/p12-demo-session",create=True); create_key(p)'
python -B -m mocks.anki_transport.process_peer game --directory /tmp/p12-demo-session
```

game进程输出READY及实际临时端口。保持它运行，在另一个终端把下例的PORT替换为该端口：

```bash
python -B -m mocks.anki_transport.process_peer plugin --directory /tmp/p12-demo-session --port PORT --now-ms 0
```

第二次运行同一默认message_id会读取同一个outbox条目，已确认时不再发送。示例时间now-ms是可控调度时钟，只影响重试，不是学习发生时间或奖励日期。测试目录存在或密钥已存在时辅助代码不会静默覆盖；不要指向真实档案。实际运行不要求调用者人工编码HMAC，wire.py承担帧处理。

## 交给各owner的具体边界

| 接收方 | 可以直接接手的工件 | 在正式接入前必须解决 |
|---|---|---|
| P10 | Schema/版本矩阵/9组样例、outbox、LoopbackClient、IC-14回应 | 目标版真实来源字段及源身份/Undo/恢复；Hook到outbox之间的采集缺口；真实最小字段授权 |
| P11 | bridge.py、ack_replay_tests.py、IC-18映射表 | 正式接受STATUS/REVERTED及PENDING映射；稳定只读结果投影；不得把隔离重试变成自动释放 |
| P13 | 运行接口、path_mapping_request、比较表 | 真实引擎/目标平台、实际路径与改动白名单、主线程/工作线程边界、内部DTO映射 |
| P21 | ACK门禁、提交未知/恢复栅栏用例 | 权威COMMITTED/ABSENT/UNKNOWN、真正耐久原子事务、实例与外部恢复水位 |
| P32 | 73项作者测试、过程源码快照、3个进程场景、原始日志 | 在独立环境固定同一版本复测并记录独立结论 |
| P34 | 本机适配与平台比较、运行环境证据 | 目标OS/Anki/引擎实际部署、Windows DACL/会话、防火墙、睡眠恢复和离线条件 |
| P38 | security_review_p38.md、字段Schema、权限测试 | 同用户威胁模型、字段/保留/删除、目标系统本机绑定的独立审核 |
| P35 | source receipt、manifest、verification_status和独立门禁缺口 | 不能以作者测试替代SPEC/CONTRACT/RUNTIME/E2E独立验收 |

这些材料已随包准备，未声称对方已接收。用户指定EXT-INTEGRATOR前，不进行跨模块源码合并。
