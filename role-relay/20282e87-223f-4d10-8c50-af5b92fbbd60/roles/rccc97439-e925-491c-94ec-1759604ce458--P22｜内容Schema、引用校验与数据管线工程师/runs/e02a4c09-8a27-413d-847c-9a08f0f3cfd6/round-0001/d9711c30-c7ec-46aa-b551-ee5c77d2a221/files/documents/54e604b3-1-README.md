# P22｜内容 Schema、ID 注册与数据管线交付

任务：`P22-S00-S02-CONTENT-001`  
版本：`P22-CONTENT/0.1.0-isolated`  
状态：**ISOLATED_CONTENT_PIPELINE_DELIVERED / PRODUCTION_CONTENT_INTEGRATION_BLOCKED**

本包交付可运行 Python 源码、32 个 JSON Schema、18 份固定版本原始数据的校验适配、ID 注册表、引用报告、负向样本、内容清单迁移及作者测试。源码不调用引擎、Anki、P21 存档或任何业务提交接口。

## 1. 本轮实际结果

| 项目 | 结果及范围 |
| --- | --- |
| 作者自动化测试 | 109 PASS、0 FAIL、0 ERROR、0 skip；重复运行不累计覆盖 |
| Schema 元校验 | 32/32 PASS，Draft 2020-12 |
| 约定数据文件 | 18/18 结构校验及源哈希核验 PASS：9 JSON、9 TSV |
| 内容注册与引用 | 137 个有类型/作用域的定义；403 条引用；0 重复 ID、0 悬空非空引用 |
| 缺失正式绑定 | 35 条 BLOCKED，详见 `content/manifest/missing_bindings.tsv` |
| 正式素材 | 0 个；资源请求和占位字样均没有升级为素材注册 |
| V6 静态复核 | 43 个岗位、92 项职责、27 个接口；只证明映射结构，不证明职责已实施 |
| 正式接入预检 | BLOCKED，约定退出码 3 |
| P32 独测、P33 人工、P35 独审 | NOT_RUN |
| P25 风格、P37 合规验收 | NOT_RUN，本岗没有创作正式素材 |
| 目标引擎、Windows 目标机、真实 Anki、整游戏 E2E | NOT_RUN |

7 个 character 定义由 P03 的 4 个 Mock 槽位与 P04 的 3 个样例角色组成，不等于 7 名首发角色。3 个 enemy 定义来自 P06 的普通/精英/Boss 各 1 个。10 张候选卡含 8 张 Mock 可用卡及 2 张受阻扩展卡。所有记录均保持 `CANDIDATE` 和 `production_allowed=false`，没有冻结 MVP 数量。

## 2. 快速复现

在完整解压的 `P22_ContentPipeline_V0.1` 目录中运行。单独导出的 Python 文件依赖包内模块，不能当成独立单文件程序。

```bash
python -m pip install -r requirements.txt
python -B tools/content_validation/verify_delivery.py
python -B tools/content_validation/run_tests.py
python -B tools/content_validation/schema_linter.py lint --output ../P22_candidate_check
python -B tools/content_validation/schema_linter.py preflight --output ../P22_production_check
```

安装依赖以后四条命令预期退出码依次为 `0、0、0、3`。第三条证明候选数据的静态结构和引用成立；第四条保留正式接入阻塞。依赖安装可能需要网络；校验、测试和复现过程不访问网络。本轮使用 Python 3.12.14 / Linux x86_64，精确依赖见 `requirements.txt`，目标机尚未验证。

一条命令完成包完整性、109 项作者测试、两次确定性校验、正式预检、5 个负向样本、元数据迁移和真实空迁移表核验：

```bash
python -B tools/content_validation/reproduce.py --output ../P22_reproduction
```

输出目录必须尚不存在且位于包外。复现程序保留每条命令、标准输出、标准错误、退出码、日志哈希和整个包运行前后的哈希。`formal_preflight` 返回 3 是预期阻塞；总体复现 PASS 不会把该门禁改为 PASS。

## 3. 文件入口

| 路径 | 内容 |
| --- | --- |
| `schema/content/content_schema_spec.md` | 字段、ID、版本、引用和错误定位说明 |
| `schema/content/*.schema.json` | 记录、资源、注册表、迁移表、计划和清单 Schema |
| `schema/content/compat/*.schema.json` | 18 份固定上游格式的兼容 Schema |
| `tools/content_validation/schema_linter.py` | 只读 CLI |
| `tools/content_validation/p22_content/` | 解析、Schema、注册/引用、资源、迁移实现 |
| `tools/content_validation/tests/` | 109 项作者自动化测试 |
| `tools/content_validation/fixtures/` | 5 个实体错误样例和合成元数据迁移样例 |
| `content/manifest/dataset.plan.json` | 18 数据输入及 28 个辅助绑定的路径、哈希与版本 |
| `content/manifest/content_id_registry.tsv` | 137 项候选 ID 注册表 |
| `content/manifest/id_migration_map.tsv` | 正式历史迁移表；仅表头，0 条已发行迁移 |
| `content/manifest/reference_check_log.txt` | 可读校验日志和每个阻塞点 |
| `content/manifest/reference_report.json` | 完整机器可读报告 |
| `content/manifest/references.tsv` | 403 条引用及目标字段定位 |
| `content/manifest/missing_bindings.tsv` | 35 条缺失绑定及责任方 |
| `content/manifest/content_manifest.json` | 排序稳定的内容文件清单 |
| `content/manifest/resource_manifest.json` | 明确资产数量为 0 的资源清单 |
| `content_migration_plan.md` | 迁移范围、默认值、ID 历史保留与 P21 边界 |
| `integration_handoff.md` | 接收方、使用方式和正式接入条件 |
| `content/manifest/interface_rfcs.json` | 版本化 RFC，均尚未提交/受理 |
| `content/manifest/actual_path_request.json` | 保留 P13 当前拒绝写入状态的映射请求 |
| `evidence/intake/source_input_receipt.json` | 输入字节、固定提交及原包成员来源 |
| `evidence/author_final/` | 实际作者运行结果 |
| `evidence/failures/` | 真实失败报告、修复前源码/Schema 快照 |
| `verification_status.json` | 分层验收状态 |
| `delivery_manifest.json` | 逐件文件大小、SHA-256、版本、来源哈希、接收方、修改白名单 |

## 4. 上游核验与授权

15 个上传件已经逐字节读取。递归核验 120 个去重 ZIP、9,684 个文件成员、813 条 relay 清单记录，0 个大小/哈希错误。另从固定职责提交读取 V6 原 ZIP，并核验 14/14 内部清单项。10 个上传件可直接匹配 P21 固定提交 Git blob，另外 5 个是重打包容器，按成员及嵌套原包核验。没有把重打包 ZIP 声称为 Git 同字节容器。

固定职责提交：`8c370d731c323f86ff19642f4cc73f818498f641`。固定 P21 交接提交：`775369b34f6691f864d1682a83af1e36f0bc1d81`。P21 原 ZIP SHA-256 为 `05ec1111199f90da2f3e3f814048256ef21264e6a229c4163113de51836f3f23`。本包保留 76 份本岗相关原件；未复跑 P21 的 104 项测试，因此不将上游测试计入本轮结果。

当前 P13 `actual_path_mapping.json` SHA-256 为 `388113be16ac8cd4aa84e49cf2a563c2c12f738a528a0d81ba434f5ec61b1d6f`。P22 三条正式路径均 `actual_production_path=null`、`write_allowed=false`。本次授权仅来自用户要求的**新建隔离交付包**；没有覆盖实际工程，没有替 P13 补写授权，也没有实施跨模块合并。

历史独立导出的 `P04_progression_costs.tsv` 只有 6 字节 `row_id`。本轮使用 P04 原 ZIP 中 5,346 字节、21 行的完整原表，其 SHA-256 为 `5c872fb5ac0a0834ecdfe270a6dd81a42c10aaecf8d58559b822b1fcdc4df41f`。两份原字节及定位均保留在 `evidence/intake/source_variants.json` 所指路径；未自行修补设计表。另一份历史 P13 映射属于旧运行源码快照，不作为当前授权。

## 5. 边界与后续

P22 只负责内容定义、类型/引用、版本和清单。P13 负责内部 DTO；P12 负责 Anki 跨进程协议；P21 负责物理存档与事务；P14 保留战斗状态唯一提交权。

缺失素材、正式词性/资源绑定、路径和目标环境均进入 BLOCKED 报告。P32/P35 可直接接收此包独立复测和审查；真正的工程落位等待 P13 授权以及用户指定的 EXT-INTEGRATOR。RFC 和接收条目均为 PREPARED 状态，没有宣称已通知或获批。
