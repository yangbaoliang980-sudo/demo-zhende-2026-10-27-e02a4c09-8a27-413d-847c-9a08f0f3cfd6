# P20 交接与正式接线说明

任务 `P20-S05-S06-S07-METAUI-001`；交付 `P20-METAUI/0.1.0-isolated`。接收状态为 `PREPARED_NOT_ACKNOWLEDGED`；RFC 为 `PREPARED_NOT_SUBMITTED`。没有向外部人员发送消息、提交 PR、合并或部署。

## 接收顺序

先核验包外 `P20_delivery_receipt.json` 的 ZIP 大小/SHA-256，完整解压，再执行 `tools/verify_delivery.py`。单独导出仅用于阅读，运行必须使用完整 ZIP。不能把独立的 controller 文件当成完整应用。

然后执行 `meta_ui_tests.py`。有浏览器的接收环境可执行 `tools/browser_check.mjs --out 新目录`，保存自己的执行环境、日志与截图，不能沿用本作者的 PASS 签名。P32 独测、P33 人工、P35 独审分别签署。

## 原始输入

P19 原上传 ZIP 为 22,498,864 字节，SHA-256 `bab95fd7337b10da4257c7171f0dc21eea14e830631d25da4cb65d7f55c23093`。本轮还收到 6 个 relay ZIP。全部附件与用户指定归档提交的 Git blob 相符，且递归 relay 清单校验通过。

V6 固定提交：`8c370d731c323f86ff19642f4cc73f818498f641`。上游归档提交：`1979821ec38f75098fef34ca9fdd493630a7b8bc`。逐来源完整路径、Git blob SHA-1、文件 SHA-256、原 ZIP 成员与使用副本在 `source_input_receipt.json`。所有哈希值由实际字节计算；Git blob SHA-1 与文件 SHA-256 分列。

本包只携带运行及审查所需的 126 份原字节输入，不层层重新打包所有历史大 ZIP。P19 原战斗源码未修改；本岗没有嵌入或重写战斗 HUD。

## 各接收方取得什么

| 接收方 | 工件与下一动作 |
| --- | --- |
| P23 | `party_menu_flow.md`、页面状态图、UI 截图、源码；审查操作顺序、词汇、空态和恢复路径 |
| P24 / P25 / P37 | HTML/CSS 组件、占位位置、字体原许可；提供正式资产并分别完成组件/风格/合规受理 |
| P17 | `domain_api_mapping.json`、P20_API、原代码契约测试；接受角色列表/报价读接口与命令映射 |
| P18 | stage_unlock_views、结算页面、关卡契约测试；确认扩展状态和 active/terminal/claim 流程 |
| P11 / P12 | 学习状态文档、原 query 测试；提供真实跨进程查询与补发状态绑定 |
| P13 | actual_path_request、5 项 RFC；确认实际仓库/分支/base SHA/路径、DTO、路由与测试宿主选择 |
| P21 | 未决操作恢复规则、保存状态与提交/lookup 请求；提供真实持久事务和跨重启 fence |
| P01 / P22 | 测试角色/关卡/装备范围及 ID 声明；正式内容批准不能由本包测试数目代替 |
| P32 / P33 | 可执行单元/契约/浏览器测试及原始失败/通过记录；分别独测与人工复核 |
| P35 | 完整清单、来源、验收分层、缺陷、BLOCKED/NOT_RUN 项；独立证据门禁 |
| P39 | 完整 ZIP、包外回执、完整性校验器；接收记录和归档 |
| EXT-INTEGRATOR | 本岗源文件、端口说明、白名单与未接入项；仅在用户任命并获路径授权后实施合并 |

逐文件接收表在 `downstream_receipts.json`，不表示这些岗位已实际签收。

## 正式适配步骤与限制

1. P13 先给出实际路径映射和 base SHA。本包不能自行把 `ui/meta` 映射到 Unity Assets，也不能把当前 Web 实现宣称为已批准的引擎选型。
2. P13/P17/P18/P21 提供在同一一致性边界读取的角色、钱包、进度与提交状态。只替换 `HttpMetaPort` 或受信任 composition root；不要把测试 host 或测试注册表迁入正式运行时。
3. 所有消耗与领取走领域候选和 P21 持久事务。回执成功条件必须由 owner 接受，不将本包 `COMMITTED_SIMULATION` 改名为真实成功。
4. P13/P19 定义外部战斗路由、入场接收、返回结果引用及活动 battle 恢复。P20 只展示入口/返回，不接受页面自报的胜利或掉落金额。
5. P11/P12/P21 提供真实学习查询与补发队列；保留 QUARANTINED/PENDING_RECONCILIATION。正式“已入账”需要另行实现已接受的可信提交证明显示分支。
6. P23/P24 以固定版本替换占位流程/资产，P25/P37 完成独立验收；角色占位文字与测试名称不能用作正式美术。

## 已知限制

验证宿主是 Linux 浏览器与 Python，不是目标 Windows 游戏引擎。P17/P18 状态在内存中，关闭服务后重置；只有浏览器 UI 的未决请求会保留。真实测试服务重启已验证“旧请求继续待核对”，没有证明正式存档续读或断电恢复。

当前读取/刷新由用户操作或浏览器前台恢复触发，没有真实 Anki 推送订阅。装备默认关闭，`equipment` 场景仅启用 P17 原测试配置。P11 模拟 SQLite 中的 durable=true 指向模拟器本身，绝不等于 P21 生产提交。

正式场景还缺 P23/P24/P21 真实工件、P13 路径/环境授权、接口接收、正式内容和独立门禁。可复现程序已经交付；这些缺项保留在 `blockers.json`，由对应 owner 解决。
