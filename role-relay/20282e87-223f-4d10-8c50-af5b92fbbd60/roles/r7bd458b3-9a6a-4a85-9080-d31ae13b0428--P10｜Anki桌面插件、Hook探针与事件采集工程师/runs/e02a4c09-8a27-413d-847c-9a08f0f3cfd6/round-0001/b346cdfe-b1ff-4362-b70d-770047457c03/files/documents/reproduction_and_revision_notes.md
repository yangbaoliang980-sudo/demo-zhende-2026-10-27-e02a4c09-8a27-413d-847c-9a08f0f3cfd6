# P10 证据复现边界与作者修订说明

本轮没有执行失败的功能测试，也没有真实 Anki 日志。首次报告检查器运行的 18 项测试通过。作者在封包前核对源码，将报告中的评分映射所属类名从误写的 ReviewerV3State 修正为实际 V3CardInfo；没有改官方源码或插件行为。最终作者运行使用 author_run_002。

作者运行只固定命令实际消费的 Python 检查源码、前置 JSON 和只读源快照；报告排版、后生成的交接记录与清单由最终交付 SHA-256 清单固定，避免自哈希循环。作者检查的输入哈希不是 P35 签署或外部真实性证明。

`evidence/intake/intake_archives_method.py` 是最初实际解包方法的原字节副本：在独立工作目录中，其原始布局为 `upload/两份输入ZIP` 与 `work/intake_archives.py`。运行 `python -B work/intake_archives.py` 将创建 `work/intake/` 及 `work/intake_report.json`。不要直接在固定交付包内运行这个历史方法副本。当前完整交付的日常验证使用 `verification/verify_delivery.py` 和 `anki_hook_probe.py`。

官方源码的网页读取通道曾返回不可访问；已通过用户选用的 GitHub 连接成功读取相同固定提交的原始文件。没有把网页失败称作源码成功读取；源码证据以 GitHub 原字节、reference_inputs.json 和静态提取原始输出为准。公开参考没有指定或替代用户目标 Anki 环境。

源码快照保留 Anki 官方 LICENSE 和版权头；它们是第三方只读证据，与本岗原创报告检查脚本分开。不得将源码快照误作为 addon_source。正式插件的许可、发布和安全审核仍由对应 owner 后续执行，本轮未发布任何插件。
