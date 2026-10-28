# P10｜配置、停用与卸载说明

版本：P10-REPORT-OPERATIONS/0.1.0。适用对象是本次隔离报告包；本轮没有可安装的 Anki 插件，安装、停用后调度回归和卸载测试均 NOT_RUN。

## 运行本报告的复核工具

从解压后的包根执行，Python 3.10+ 标准库即可。使用 `-B` 避免把缓存文件写入已固定的包。命令不会导入 Anki 源码、读取集合或连接游戏。

```bash
python -B anki_hook_probe.py preflight
python -B anki_hook_probe.py scan-reference
python -B -m unittest discover -s verification -p 'test_report_guards.py' -v
python -B verification/verify_delivery.py
```

第一条应输出 BLOCKED/QUARANTINED，退出码 3。第二条退出 0 仅表示固定源码提取成功。第三条是报告检查器作者单测入口，不是插件或 outbox 测试。第四条验证包内字节清单，不验证来源事实或真机能力。输入文件哈希错误等完整性问题退出 2。

保留自己的复核证据，可以使用以下命令。输出目录必须不存在且位于本包之外，不得覆盖原作者日志。

```bash
python -B verification/run_author_checks.py --output ../p10_receiver_run_001
```

报告文件没有 `enabled=true`、监听端口、IPC 密钥或发奖开关。编辑状态 JSON 不能创建合法授权或启用插件。

## 安装与禁用

不要把 `anki_hook_probe.py` 放入 Anki 插件目录，也不要把此 ZIP 改名为 `.ankiaddon`。`addon_manifest.json` 是不可安装交付描述，不是 Anki 安装清单。本轮没有创建插件包 ID，也没有在任何用户机器安装东西。

未来取得正式目标版、P13 路径映射、P38 字段授权和 P12 合同并交付真正的插件后，才由 P10/P34 给出绑定具体包 ID、版本和 SHA 的安装步骤。安装范围仅限获准测试档案。当前不能写一份指向假目录或假包 ID 的安装指南。

Anki 官方手册提供通用的 Add-ons 管理与安全模式入口，可作为未来故障恢复参考：[Add-ons](https://docs.ankiweb.net/addons.html)、[Troubleshooting](https://docs.ankiweb.net/troubleshooting.html)。这些通用文档不是本插件禁用后正常的运行证明。未来停用必须在目标机实测：不再注册回调、不再发送或后台重试，Anki 正常评分、Undo 与正常调度继续；未确认状态时不删除未确认的队列记录。

## 当前包的移除与未来插件卸载

本轮只产生报告文件；移除报告目录不会卸载或修改 Anki。按项目证据留存要求保留完整 ZIP 和回执即可，无需删除 Anki 目录、collection 文件或个人复习历史。

未来正式插件的卸载路径必须由已批准安装清单确定。卸载前关闭插件发送并保留待确认来源证据；数据保留期限、主动清除及用户授权由 P38/P01 确认，当前没有批准任何默认删除期限。重装不能通过生成新世代或新事件 ID 重发旧事件获得收益；未知谱系仍须 QUARANTINED。此流程未实际执行，不称为卸载功能已完成。
