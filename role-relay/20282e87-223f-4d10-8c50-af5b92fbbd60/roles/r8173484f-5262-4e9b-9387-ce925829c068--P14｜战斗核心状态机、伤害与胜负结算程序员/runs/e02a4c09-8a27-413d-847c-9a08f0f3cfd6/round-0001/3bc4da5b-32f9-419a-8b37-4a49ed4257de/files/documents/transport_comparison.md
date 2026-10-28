# 文件交换与本机IPC比较

本文件是P12候选工程比较。正式目标OS、引擎及P13/P34实测选型未收到，**正式选型BLOCKED**。本轮只实现并在Linux作者环境验证了 `127.0.0.1` TCP候选；没有用文档比较代替目标机验证。

| 方案 | 平台及依赖 | 权限和认证条件 | 互联网断开 / 游戏关闭 | 本轮状态 |
|---|---|---|---|---|
| 私有目录文件交换 | 桌面平台均有文件API；原子替换、目录同步、锁和监听行为需按本机文件系统验证 | 目录及文件仅当前用户可访问；固定目录、固定文件名、拒绝符号链接；接收者仍须认证与Schema校验 | 互联网无依赖；游戏关闭时可保留队列，但半写入、重放、扫描和容量治理仍要实现 | 比较完成；适配器NOT_IMPLEMENTED，目标机NOT_RUN |
| Unix domain socket | 候选Linux/macOS；具体解释器/OS的AF_UNIX支持需实测 | 私有socket目录及同用户访问控制；必要时同用户凭据核验；不使用共享抽象命名空间绕过文件权限 | 无互联网依赖；服务端关闭需outbox保留和重连 | 比较完成；正式适配器NOT_IMPLEMENTED |
| Windows named pipe | Windows原生IPC，需本地管道、显式DACL及会话范围 | 不能把默认安全描述符当作仅本人；应审查logon SID、管道实例和访问权 | 无互联网依赖；断开后同样需要outbox/查询 | 比较完成；NOT_IMPLEMENTED / NOT_RUN |
| IPv4 loopback TCP | Python标准socket API有跨桌面平台接口，实际行为仍由OS决定；当前实现只测Linux | 仅字面量127.0.0.1；随机私有密钥、fresh challenge与双向HMAC；无公网/域名回退 | 协议代码无互联网依赖；游戏断开真实测试可恢复；物理拔网及目标防火墙尚未测试 | 候选实现及Linux作者IPC测试PASS；正式选型和Windows/macOS NOT_RUN |

文件落盘并不等于P21账本与钱包事务完成；无论采用哪种传输，两个成功ACK都必须通过同一权威提交门禁。文件交换也不能通过删除“已读文件”替代业务隔离跟踪。网络包接收成功同样不证明授奖完成。

文件方案若进一步实施，候选写入顺序是同目录临时文件→flush/fsync→受控替换→接收者校验；具体目录同步和故障耐久性由P21/P34定义。Python os.replace文档说明成功替换的原子性与同文件系统约束；这不能推导跨盘、同步盘、断电恢复都可靠。[Python os](https://docs.python.org/3.12/library/os.html#os.replace)

Python socket文档说明平台行为依赖操作系统，并说明空字符串bind会指向所有接口；因此当前实现显式拒绝空字符串与通配地址。[Python socket](https://docs.python.org/3.12/library/socket.html)

Windows named pipe的默认权限及会话限制须独立核查；Microsoft文档列出默认描述符及logon SID的用途。不能将本包POSIX模式位验证视为Windows DACL审核。[Microsoft pipe security](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights)

本机绑定是网络范围约束，不是源事件真实性证明。端点发现、凭据轮换、系统睡眠恢复、多用户会话、杀毒软件/防火墙、目标Anki Qt线程和引擎调度接入均需P13/P34/P38追加目标环境证据。
