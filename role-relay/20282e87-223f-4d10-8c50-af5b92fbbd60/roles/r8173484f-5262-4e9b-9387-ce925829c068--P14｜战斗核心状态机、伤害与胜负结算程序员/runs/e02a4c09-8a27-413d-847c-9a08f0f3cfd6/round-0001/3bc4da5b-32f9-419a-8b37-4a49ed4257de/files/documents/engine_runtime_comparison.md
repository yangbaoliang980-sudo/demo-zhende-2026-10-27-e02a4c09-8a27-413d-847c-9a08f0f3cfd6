# 引擎、运行时与平台比较｜基于本轮证据

**选择状态：游戏引擎 UNDECIDED；P13 可执行交付仅采用已实测 Python 3.12。**

比较的输入是 25 个已核验 ZIP、两个明确指定的 GitHub 固定树和当前执行主机；没有用户目标设备的 P34 指纹。本表不使用“适配桌面”推断目标 Windows 版本，不使用浏览器信息推断游戏机器。

| 候选/用途 | 本轮实际入口与依赖 | 可复现探针 | 本轮判断 | 选择前必须补证 |
|---|---|---|---|---|
| 复用历史 Godot 工程 | 未取得 project.godot/场景；PATH 未发现 Godot | 先固定 binary/source SHA，复制工程后 `--headless --path COPY --editor --quit --log-file LOG` | 引擎未启动；NOT_RUN；选择 BLOCKED | 原工程、确切 Godot 版本、主场景/目标渲染与导出证据 |
| 复用历史 Unity 工程 | 未取得 ProjectSettings/ProjectVersion.txt 或 Packages/manifest.json；PATH 未发现 Unity/.NET | 复制工程后 `-batchmode -nographics -projectPath COPY -quit -logFile LOG` | 引擎未启动；NOT_RUN；选择 BLOCKED | Editor 完整版本、包锁定、许可/模块可用性、主场景和构建探针 |
| Python 隔离框架 | Python 3.12.14 可用，P11/P12 为现存独立 Python 组件 | `python -B -m runtime.framework.yltt_framework.demo` 与 unittest | 本轮作者运行成功，仅接口桩 | 不证明 Python 游戏呈现方案/打包/性能可行；正式宿主另定 |
| Node 契约验证工具 | Node v24.22.1 可用；没有 Electron/网页工程包入口 | `node architecture/tools/canonical_oracle.js` | 用于 JSON/SHA 跨语言对照 | 不因此选择 Electron、网页客户端或桌面打包器 |

Godot 官方命令行文档明确 `--path` 指向含 project.godot 的目录，`--headless` 为无显示模式；本表命令只核验编辑器导入，不能自动证明游戏主场景已成功运行。[官方文档](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)

Unity 官方文档提供 batchmode、projectPath、quit 与日志参数。参数存在不代表当前环境有对应 Editor、有效许可、构建模块或目标图形支持。[官方文档](https://docs.unity3d.com/6000.0/Documentation/Manual/EditorCommandLineArguments.html)

## 已执行的环境探针

`runtime/framework/probes/probe_environment.py` 的实际运行日志、每个发现/版本命令、exit_code 与来源扫描根位于 `architecture/evidence/runs/environment_probe_001/`。完整输出保留在 stdout.log，摘要 `environment_observed.json` 为相同结构的派生副本。

发现可执行文件的子命令返回 0 或 1；1 的含义是当前 PATH 未找到名字，不是运行该引擎失败。外层探针返回 **3 / BLOCKED**，原因是没有已核验的目标工程/目标环境。**实际引擎启动仍 NOT_RUN**。当前主机没有 DISPLAY/WAYLAND_DISPLAY，但本轮未推断 GPU 不存在，也未给目标帧率、显存或启动时长指标。

## 收到工程后的实际探针

先用 P01/P34 固定输入：源码提交/ZIP SHA、工程根、入口文件 SHA、引擎完整版本和可执行文件 SHA、目标 OS/架构及授权。`run_engine_probe.py` 只在一个新目录创建副本并对副本运行编辑器导入；先核对完整文件清单树 SHA，不覆盖源工程，不自动升级依赖。

示例（全部参数必须由真实输入替换；**本轮未执行**）：

```bash
python -B runtime/framework/probes/fingerprint_tree.py --project /absolute/verified/project

python -B runtime/framework/probes/run_engine_probe.py \
  --engine godot \
  --executable /absolute/verified/godot \
  --project /absolute/verified/project \
  --source-commit ACTUAL_FIXED_COMMIT \
  --expected-tree-sha256 HASH_FROM_FINGERPRINT_TREE \
  --output /absolute/new/probe-output
```

Unity 使用 `--engine unity` 及其实际 executable，其余同理。脚本将 original source 清单、实际 binary SHA、命令、时间、cwd、副本路径、stdout/stderr、exit_code 一起保存。引擎 editor import 的进程返回 0 只标记 PROCESS_EXITED_ZERO_REVIEW_LOG_REQUIRED；主场景 handshake、UI、GPU、导出、真机兼容与 E2E 另测。

不能仅用 `--version` 成功、编辑器空启动、导入返回 0 或 Python demo 成功冻结引擎为已验证。P01 取得用户对新建/复用方案的决策后，P13 再按真实输入出新 ADR，P32/P35 对同版本审查。

## 目标平台与 P12 IPC

P12 已交付的隔离候选为 Python loopback transport。此次只原样复跑其解析和 ACK/状态测试，没有把它接入游戏引擎，也没有重跑其全部套接字/双进程场景。既有 P12 Linux 运行证据随原 ZIP 保留，标明为上游证据。

若选 Godot/Unity，如何承接 Python P11/P12 需要原 owner 评估：目标语言显式适配或受控 Python 服务进程会带来不同依赖、生命周期和事务边界，不能认为“都在本机”就已经可直接调用。P13 本轮不选择额外 sidecar 架构，不授权复制 Mock 充当生产实现。

Windows/macOS 均未实测；Windows DACL、端点发现、会话隔离、休眠恢复与防火墙行为交 P12/P34/P38。对 Anki，目标完整版本、真实事件身份和 Undo 证据仍交 P10。所有具体缺项见 `target_environment_requirements.json`。
