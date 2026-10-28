# P12｜Anki—游戏本地传输协议

版本：`YLTT-ANKI-TRANSPORT/0.1.0-isolated`。任务：`P12-S04-S05-TRANSPORT-001`。关联：IC-14、IC-18；上位需求 REQ-003、REQ-011、REQ-025、REQ-026。状态：**FROZEN_FOR_ISOLATED_TESTS**。正式联合接收、P13路径映射及P38审查尚未完成；不能安装进真实工程。本包不修改Anki采集、P11账本、P17经济或P21物理存档。

## 1. 版本和字段边界

两端共用 `ipc_schema.json`（JSON Schema 2020-12）及 `protocol.py`。当前精确接收 `0.1.0-isolated`；旧版、未知次版本、无isolated后缀、未来主版本均显式REJECTED/E_PROTOCOL_VERSION。HELLO仅确认明确交集，不静默解释未知版本。后续发布必须保留旧outbox原字节和源身份，按版本化RFC增加解码器；不能把修改版本号当迁移。

请求Envelope固定字段：`protocol`、`protocol_version`、`message_type`、`message_id`、`producer_id`、`scope`、`payload`。响应另有 `request_sha256`，`message_type=RESULT`。所有层的未知字段拒绝。`scope`仅含 `source_id`、`collection_lineage`、`beneficiary_id`，与配对配置逐字一致。它不是客户端自行选择钱包的授权。

| 请求类型 | payload | 允许的作用 |
|---|---|---|
| HELLO | supported_versions | 确认当前明确协议交集；不产生学习事件 |
| SUBMIT_EVENT | event | 将一个已存在的来源事实交给P11；不指定奖值 |
| QUERY_STATUS | inbox_id | 在当前配对作用域内查询P11既存结果；只读 |

`message_id`为32个小写十六进制字符，只作请求关联及本地outbox标识，不是学习权益防重键。服务端不建立第二套全局message_id账本；P11对真实源事实负责防重。outbox强制一个message_id绑定不可变原字节，同一event指纹重复入队返回原message_id。改变message_id不能获得新权益；同源身份不同载荷由P11隔离。

## 2. 来源事实候选

event暂时采用P11既有 `P11-LOCAL-EVENT/0.1.0-proposal` 的字段，限缩为ASCII不透明引用。它是隔离契约测试的映射，不代表真实Anki Hook必有这些字段。正式字段须P10真实样本、P13 DTO和P38字段审批到齐后共同接收。

| 字段 | 候选含义和边界 |
|---|---|
| schema_version | 固定为上述P11提案版本；未知版本显式拒绝 |
| source_id / collection_lineage / beneficiary_id | 配对作用域；不因存档槽或奖值改变 |
| collection_epoch | 来源世代证据引用；P12不生成或证明它 |
| event_id / family_id | 源操作与修正族的不透明身份，可为null以表达未证明；null必须进入P11隔离路径 |
| kind | REVIEW、UNDO或RESTORE；只是语义，不能据此声称Anki存在Redo Hook |
| revision / predecessor_event_id | 因果修正关系；不等于网络到达序号 |
| rating | REVIEW仅为Again/Hard/Good/Easy语义名；不猜测真实按钮数值编码；控制事件为null |
| card_reference | 可为空的最小不透明引用；不接收笔记正文、路径或数据库原行 |
| source_evidence_sha256 | P10证据的哈希引用，可为空；报文自己带一个哈希不等于通过EvidencePort |

P12不生成event_id/family_id，不把时间、UUID、revlog主键或计数器自行升级为真实身份。`collection_epoch`变化不作为新一轮授奖开关。奖励数量、分类政策、余额、管理员布尔值、证据放行操作、任意命令、原始卡片内容均不进入此协议。P09分类合同未激活，协议不在本版新增未核验的分类字段。

## 3. 序列化与限权解析

运行协议的字符引用只允许ASCII标识；不接受路径分隔符、空格、控制字符、日文正文。引用最大128字符，哈希64位，message_id 32位。JSON为UTF-8，不接受BOM、非法UTF-8、未配对surrogate、重复键、NaN/Infinity、浮点数、指数数值和超安全范围整数。整数绝对值不得超过2^53-1；revision还按事件语义约束。

单帧JSON最多32,768字节；在读取body前检查长度。JSON解码前先限制嵌套深度为12，解码后限制值及键节点总数512。没有压缩、反序列化对象、脚本执行、文件路径读取或外部Schema解析。Schema内引用仅允许`#/$defs/…`。运行时校验器只支持当前Schema所用的闭合集；新增不认识的Schema关键词将直接报错。

候选规范化采用ASCII字符串、按键排序、紧凑分隔符、无浮点的JSON字节。它是本协议的受限编码约定，未宣称实现RFC 8785。event指纹与未改动P11 Event.fingerprint在这个受限域一致；HMAC和request_sha256绑定实际发送字节。一般JSON可有无害空白，源事实指纹仍按规范化event计算。

## 4. 本机连接与认证

本次唯一已实现和实测的候选适配是IPv4 TCP，服务端与客户端只接受字面量`127.0.0.1`。不接受`localhost`、其他127网段、IPv6、域名、`0.0.0.0`或任意远端；没有远程回退、代理、广播、遥测或HTTP接口。端口由操作系统分配临时端口，测试夹具经本机进程通道传递；正式端点发现归P13/P34/P38批准。

每条连接一个请求和一个响应，服务端单消费者，listen backlog=8，默认总网络deadline=2秒，配置上限5秒。慢包不会通过逐字节发送不断延长同一个deadline。P11/P21适配器仍需提供有界事务/查询耗时；当前单消费者模型不构成引擎主线程调度方案。事务可能已提交但网络deadline已到时，客户端必须查询，不能假定失败后另建交易。

配对密钥为32个随机字节，独立于Envelope。POSIX参考辅助代码要求当前uid私有目录和私有常规密钥文件，拒绝符号链接、多硬链接、其他用户所有权和组/其他用户权限。密钥不进入日志、交付样例或outbox。Windows DACL辅助实现尚未提供，调用会显式拒绝；不能把POSIX chmod测试等同Windows ACL测试。

帧格式：4字节无符号网络序长度N，随后N字节JSON，最后32字节HMAC-SHA256。服务端先发送6字节ASCII `YLAT01` 和32字节随机challenge。

- 请求MAC输入：`YLAT01:request:` + challenge + u32(N) + request_bytes。
- 响应MAC输入：`YLAT01:response:` + challenge + SHA256(request_bytes)原始32字节 + u32(N) + response_bytes。

每次重连challenge重新生成。方向和请求哈希绑定防止将旧请求帧或旧响应直接套到新连接。认证失败、无效帧长度、截断帧在进入JSON业务解析之前关闭连接，不发持久ACK。能通过认证但JSON/版本不合法的报文收到明确REJECTED。

HMAC提供报文认证和完整性，不提供加密，也不证明对端确为Anki、源事件真实或奖值获批。不能防御已控制同一用户、读取密钥的恶意进程或管理员；该威胁范围交P38评审。本包所有运行凭证都明确为P21_SIMULATOR，正式模式不能由参数或JSON布尔值打开。

## 5. 成功回执必须经权威凭证门禁

`bridge.py`对P11 handle结果不直接发成功ACK，而是查询当前业务状态，核验P21候选authority的连续性、输入/作用域、当前行或修正族的提交引用、实例、水位、请求哈希、凭证durable及origin，并再次查询COMMITTED凭证和P11当前结果。检查未知、不一致或异常时返回RETRY_LATER。

客户端只收到精简凭证摘要：origin、transaction_id、sequence、store_id_sha256、receipt_sha256；不收到完整钱包、账本摘要内容、余额、原始学习材料或本机路径。摘要并非P21独立签名；其可信链是配对连接→游戏权威适配器→P21提交查询。生产证据链未完成，不能把模拟摘要标为真实存档凭证。

| P11当前结果 | P12 disposition / state | 含义 | outbox行为 |
|---|---|---|---|
| 有核验凭证的APPLIED | ACK_APPLIED / APPLIED | 当前权益已由对应事务确认；本次查询/重复投递不新增权益 | SETTLED，保留原字节与摘要 |
| 有核验凭证的QUARANTINED | ACK_QUARANTINED / QUARANTINED | 本输入已持久隔离、未授奖；不否定其他既存权益 | WATCHING_QUARANTINE，30秒起查询，保留 |
| REVERTED或有效Undo墓碑 | STATUS / REVERTED | 已持久确认撤销或原完成受墓碑抑制；不是新增奖励 | SETTLED，保留 |
| PENDING_RECONCILIATION | RETRY_LATER / PENDING_RECONCILIATION | 因果或补偿等仍未解决，可能有部分回收；不谎称未发生任何经济变化 | 保留，按next_action查询或重投 |
| 有持久业务拒绝 | REJECTED / REJECTED | 本输入有拒绝记录，未为本输入授奖 | HELD_REJECTED，保留供owner处理 |
| 提交/查询不明、恢复连续性不明 | RETRY_LATER / UNKNOWN | 无法证明当前结果 | 保留，查询 |
| 连续性已确认的快照中不存在该输入 | STATUS / NOT_FOUND | 该查询时点未发现；不是全历史从未授奖证明 | 重投同一不可变输入，由P11再防重 |
| JSON/协议/作用域拒绝 | REJECTED / null | 传输前置错误；未承诺持久接收 | 停止盲重试，保留供修复 |

REJECTED前置错误不是成功ACK，不要求先向P21写一个非法报文。ACK_APPLIED与ACK_QUARANTINED均不可仅凭“已收到”“写入队列”“网络发送成功”或“事务调用返回”生成。

`delivery_terminal`仅表示这个输入当前不再需要自动重投，不保证修正族永远不变。UI不得按ACK再次加钱，也不得把历史ACK缓存当钱包当前余额。隔离响应强制terminal=false；消费完成不由隔离ACK宣告。

## 6. 查询、重试和乱序

发生断开、超时、异常退出、未知结果时，outbox在联网前已持久记录下次QUERY状态。重启后使用同一event指纹查询。NOT_FOUND或已持久收件但未processed时，可按next_action=SUBMIT重投原始SUBMIT字节；业务已进入隔离或待对账时，普通重投不会释放，须P11接收新增证据。

没有按到达先后发奖的传输水位，也不在P12重排业务事实。Undo先到、因果缺口、同身份冲突、世代变化均按P11当前结果映射。对方重新生成message_id、重启、等待或更换协议版本均不提供新学习事实证明。

重试基础等待250毫秒，指数增长至30秒，加稳定有界抖动；最终等待不超过60秒。服从有效响应retry_after_ms的下界。每次ClientPump工作调用默认最多8个网络请求，可配置1—64；耗尽返回BUDGET_EXHAUSTED_DATA_RETAINED，下一次由调用方调度。不是无限忙循环或到期删除。持久lease为10秒，迟到的旧attempt不能覆盖新确认。

outbox默认最多1,000行及16MiB原请求字节，包含已确认留存行；容量不足明确报错，不淘汰待确认项。本版无自动清理API；磁盘/留存容量治理及最终删除政策等待P10/P21/P38。outbox只保管传输事实，不写游戏钱包。P10 Hook提交到outbox持久化之前的采集缺口并未由本协议解决。

## 7. 兼容和变更接收

P10真实Hook字段、P13 DTO/实际路径、P21生产凭证和恢复栅栏到齐后，由相应owner接收 `interface_rfc.md`。正式批准前不得删除isolated标志、放开模拟凭证origin、把FixtureEvidence搬进游戏或修改上游快照。外部整合者须在批准的实际路径下完成整合；本岗位没有执行跨模块合并或发布。
