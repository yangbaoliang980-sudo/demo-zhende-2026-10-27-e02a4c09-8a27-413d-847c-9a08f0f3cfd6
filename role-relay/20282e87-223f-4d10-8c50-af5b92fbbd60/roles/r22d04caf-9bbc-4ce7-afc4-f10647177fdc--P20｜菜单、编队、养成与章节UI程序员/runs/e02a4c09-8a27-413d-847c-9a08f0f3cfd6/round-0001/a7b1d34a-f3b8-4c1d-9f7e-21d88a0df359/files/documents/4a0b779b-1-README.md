# P20｜菜单、编队、养成与章节 UI

任务：`P20-S05-S06-S07-METAUI-001`  
版本：`P20-METAUI/0.1.0-isolated`  
交付状态：`ISOLATED_META_UI_DELIVERED / PRODUCTION_INTEGRATION_BLOCKED`

这是已经实现并实际运行的非战斗界面组件，含首页、角色列表、三人编队、升级与装备、章节选择、战斗交接、结算、学习状态。实现语言为 HTML/CSS/JavaScript ES Modules；隔离验证台使用 Python。它不是已接入 Unity 的桌面游戏，也没有连接真实 Anki。

## 运行

在完整解压的本目录运行：

```bash
python -B run_ui.py --fixture
```

打开 `http://127.0.0.1:8766`。这是明确标注的隔离演练：初始角色、15 个训练代币与经验来自原 P04 生命周期测试前缀；P17/P18 原代码负责规则和候选计算。所有 P20/P18 测试提交均 `durable=false`。退出服务后这些测试状态不保留。

Windows 可运行 `start_windows.cmd`。启动脚本已提供，本轮 Windows 执行为 `NOT_RUN`；需要本机已安装并可在 PATH 找到 Python 3.12。服务默认只绑定 127.0.0.1。若 8766 已占用，可指定 `--port 8767`。

不提供 `--fixture` 时运行明确的未接入模式：

```bash
python -B run_ui.py
```

此时余额显示 `—`，无角色和关卡资料，所有领域变更关闭。也可使用 `start_windows_unbound.cmd`。

UI 运行仅使用 Python 标准库和现代浏览器，不需要 Node、npm、网络字体、游戏账号或 Anki 账号。Node 24 用于作者单元测试；Playwright/Chromium 仅用于浏览器测试。

## 一次完整演练

1. 从首页进入三人编队，改变席位，再保存。选到已占用的角色会交换位置，完整三人队伍才可提交。
2. 进入养成，选择璃火，确认 Lv.1 → Lv.2。原 P17 配置费用为 4，测试余额由 15 变为 11。
3. 进入章节。普通关可入场，Boss 关尚未解锁。点击普通关后进入战斗交接页，保留 active battle。
4. 在第二个标签页打开 `http://127.0.0.1:8766/lab`，点击“注入本次测试结果”。这是单独的测试工具，产生合成战斗结果；没有运行 P14/P19 战斗。
5. 回到界面，点击同步，进入战后结算，再点击“核对并领取关卡奖励”。P18 按原测试配置判定首通，P17 处理 3 个测试代币与角色 XP，余额变为 14，Boss 关解锁。
6. 返回菜单、重进结算或刷新页面，均不会再次领取本次奖励。

`/lab` 还可重建空数据/测试装备/未接入场景，生成 P11 隔离查询记录，设置存档迁移状态，或注入“提交后丢失响应”。重建场景后，回到界面同步或刷新；仍有未决操作时应保留该记录用于核对。测试工具不是游戏功能入口，正式工程不得安装它。

## 数据与命令的实际边界

- 钱包、等级、经验、属性、编队与装备：调用未修改的 P17 运行库。UI 不扣资源、不生成角色、不计算属性成长。
- 关卡状态、首通资格、奖励与解锁：调用未修改的 P18 运行库。`first_clear_consumed` 和 `review_required` 独立显示；隔离记录不能领取。
- 学习状态：真实执行原 P11 的 `StudyLedger.query()`，但来源是 P11 自带测试 SQLite 模型与合成事件，未连接真实 Anki，也未将其测试钱包连接到 P17。
- `APPLIED` 若来自 `P21_SIMULATOR`，界面显示“测试记录已处理”。当前包未启用正式“已入账”分支：缺少 P13/P21 接受的正式身份、提交证明与一致读取适配，状态为 `BLOCKED`。
- 进入战斗、取得终局和真实重启恢复需要正式协调端口。本包交付等待页与返回结算页、相关请求和恢复保护，没有合并 P19 战斗 HUD。

正式 `ui/meta/**` 与 `tests/meta_ui_unit/**` 在原 P13 映射中均为 `BLOCKED_NOT_MAPPED / write_allowed=false`。本次文件全部位于新建的隔离交付目录，依据本次用户任务允许的隔离研发范围创建；没有改写原 P13 映射，也未覆盖正式工程。

## 验证入口

```bash
python -B tools/verify_delivery.py
python -B meta_ui_tests.py
python -B tools/preflight.py
```

预期：文件校验退出 0；作者测试退出 0；正式接入前置检查退出 **3 / BLOCKED**。最后一项不应改写成 PASS。

作者测试入口执行 Node 的 `--test-isolation=none`，要求逐项输出测试名称与总数，避免把只有文件包装层的“1 项通过”误计为单元测试覆盖。

浏览器复测需要 Playwright 1.62.1 和一个可用的 Chromium。已测 Chromium 为 153.0.8010.0；下载依赖锁文件、初次环境错误和实际环境记录在 `evidence/environment/`。在提供相应浏览器的机器上运行：

```bash
node tools/browser_check.mjs --out /absolute/path/to/new-browser-evidence
```

通过环境变量 `P20_CHROMIUM_PATH` 指定已有浏览器可执行文件；不设置时使用 Playwright 默认路径。输出目录必须尚不存在。脚本自启本机测试服务、真实点击 DOM、保存截图和原始日志，并测试一次测试服务进程重启。该重启验证的是旧未决请求的阻断行为，不是正式存档恢复。

## 交接文件

| 文件/目录 | 内容 |
| --- | --- |
| `ui/meta/` | 可执行 UI、控制器、只读校验、传输适配、样式与原字体 |
| `tests/meta_ui_unit/` | JavaScript 单元测试、Python 原代码契约测试、测试组合根、实际生成的视图夹具 |
| `party_menu_flow.md` | 页面导航、编队草稿、未决请求与恢复规则 |
| `page_state_diagram.mmd` / `.svg` | 页面状态图的可编辑源与矢量图 |
| `stage_unlock_views.json` | P18 六类状态、按钮条件、首通与隔离显示 |
| `learning_status_ui_tests.md` | P11 状态、显示条件、测试证据与正式到账阻塞 |
| `domain_api_mapping.json` | 逐控件领域 API、原文件 SHA-256、接收 owner |
| `P20_API.md` | 本岗显示/意图/回复提案及正式接线边界 |
| `integration_handoff.md` | 接收、复跑、正式适配、禁止替代的 owner 工作 |
| `source_input_receipt.json` | 上传附件、Git 固定提交、来源路径和原字节哈希 |
| `verification_status.json` | 分层验证结果，不代签 P32/P33/P35 |
| `delivery_manifest.json` | 逐文件大小、SHA-256、格式、来源、接收人及修改白名单 |

交付 ZIP 的最终 SHA-256、所有单独导出和新解压复跑结果由包外 `P20_delivery_receipt.json` 绑定。清单不哈希自身，回执不放入其所哈希的 ZIP，以避免循环哈希。

P23/P24/P25/P37、P32/P33/P35、目标 Windows/引擎、真实 Anki、整游戏 E2E 和外部整合均未在本岗代签。下一步由已明确列出的 owner 接收工件；实际合并仍由用户指定的 EXT-INTEGRATOR 执行。
