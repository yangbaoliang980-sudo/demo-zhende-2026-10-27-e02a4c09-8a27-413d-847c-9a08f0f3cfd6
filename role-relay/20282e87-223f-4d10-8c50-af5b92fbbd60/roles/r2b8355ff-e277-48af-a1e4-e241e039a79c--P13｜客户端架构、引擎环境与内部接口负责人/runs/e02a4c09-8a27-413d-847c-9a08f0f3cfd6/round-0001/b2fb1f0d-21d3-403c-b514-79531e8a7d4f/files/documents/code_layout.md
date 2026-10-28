# 代码布局与实际路径

本包根名 `P13_ClientArchitecture_V0.1`；所有相对路径以解压根为基准。权威映射是 [actual_path_mapping.json](actual_path_mapping.json)，执行保护声明是 [do_not_touch.txt](do_not_touch.txt)。

## 已存在的本岗位源码

| 实体路径 | 已实现职责 |
|---|---|
| `runtime/framework/yltt_framework/codec.py` | 有界 JSON 解析、规范字节、SHA-256、不可变消息复制边界 |
| `runtime/framework/yltt_framework/contracts.py` | 封闭 Schema 子集与跨字段不变量校验 |
| `runtime/framework/yltt_framework/ports.py` | 各 owner 的 Protocol、唯一 provider 装配检查、生产入口阻断 |
| `runtime/framework/yltt_framework/host.py` | 有界用户命令邮箱、线程所有权、背压、异常未知结果 |
| `runtime/framework/yltt_framework/sequence.py` | 只读批次顺序守卫与快照重同步边界 |
| `runtime/framework/yltt_framework/path_guard.py` | 隔离路径允许范围、上级目录和符号链接检查 |
| `runtime/framework/yltt_framework/testing.py` | 精确输入/输出的通用脚本化端口桩 |
| `runtime/framework/yltt_framework/demo.py` | 明确标注合成 DTO 的可执行接线演示 |
| `runtime/framework/tests/` | P13 作者单元/契约边界测试，不是 P32 路径 |
| `runtime/framework/probes/` | 只读环境/输入指纹与待目标执行的引擎导入探针 |
| `contracts/internal/` | 21 类公开 DTO、19 类事件、Schema、21 个样例、规范字节向量、RFC |
| `architecture/tools/` | 记录真实命令、结构对照、架构检查、门禁与交付字节核验 |

`architecture/evidence/upstream/` 是实际保留的只读原字节；其中 P12 完整 ZIP 用于保持完整上游来源。它们不被装配进 P13 运行代码，只在原样复跑 P12 测试时被单独执行。禁止导入其 Mock 到真实生产路径。

## 未存在的目标工程路径

V6 中 `runtime/battle/core/**`、`runtime/battle/deck/**`、`runtime/battle/enemy_ai/**`、`runtime/meta/wallet/**`、`runtime/persistence/**`、`ui/battle/screens/**` 等是各原 owner 的规划名称。本包没有创建这些目录，没有将它们映射成用户实际工程目录。

收到真实项目后，映射应该绑定实际 repository/commit/engine root 和每个 owner 的文件清单。既有程序集、Python 包或 Godot 节点布局优先以核验的工程为准；不能为了符合这份建议而重命名、覆盖或合并其他岗位目录。

## 源码依赖方向

核心实际 Python 模块的导入边已由 `check_architecture.py` 从 AST 读取，无循环。代码只依赖本包共享 contracts/ports 与标准库，不导入其他岗位业务实现，不依赖 socket、Anki、数据库或渲染引擎。

`module_graph.json` 将已存在的 P13 模块与待交付的领域实现分别标记。依赖 shared ports 并通过构造注入实现，避免 P14 直接导入 P15、P15 再导入 P14，或 P11/P17/P21 互相导入私有数据对象。请求和返回的数据流不等于源码依赖循环。实际数据写入 owner 也独立于返回方向。

`dependency_diagram.mmd` 展示已存在核心框架的依赖；完整 AST 结果见 `evidence/runs/architecture_check_001/stdout.log`。
