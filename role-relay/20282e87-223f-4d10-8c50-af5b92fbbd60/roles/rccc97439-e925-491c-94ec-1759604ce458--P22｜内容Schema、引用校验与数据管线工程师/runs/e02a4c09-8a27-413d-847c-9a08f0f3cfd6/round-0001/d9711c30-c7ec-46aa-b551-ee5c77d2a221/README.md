# P22｜内容 Schema、ID 注册与数据管线交付

**已完成可运行的隔离交付包。最终 ZIP 已在新解压目录复跑：109 项作者测试全部通过；18 份固定数据静态校验通过；137 项候选 ID、403 条引用中，重复 ID 和悬空非空引用均为 0。**

任务编号：`P22-S00-S02-CONTENT-001`
交付版本：`P22-CONTENT/0.1.0-isolated`
当前状态：**ISOLATED_CONTENT_PIPELINE_DELIVERED / PRODUCTION_CONTENT_INTEGRATION_BLOCKED**

正式接入仍为 **BLOCKED**：P13 的实际工程路径与授权尚未提供，P30 正式资源目录契约和素材未交付，部分正式词性/资源绑定缺失。P32 独测、P33 人工验收、P35 独审、目标引擎及真实 Anki/E2E 均未代签通过。分层结果见下方交付文件。

## 一、完整成果下载

| 文件 | 实际大小 | 内容 |
| --- | --- | --- |
| **P22_ContentPipeline_V0.1.zip** | **1,537,563 字节** | 229 个实体文件：源码、32 个 Schema、注册表、引用报告、错误样例、测试、原始日志、失败快照及 76 份相关上游原件 |
| **P22_delivery_receipt.json** | **89,492 字节** | ZIP 与 24 个独立导出的大小和 SHA-256；最终新解压复跑命令、原始输出、退出码及完整性检查 |

ZIP 的 SHA-256：

纯文本

`59823066d3449ec3fb88f08b61ff91ec93c23922bfe9965e9660f247a5f44cb8`

已实际完成：

- ZIP CRC 检查。
- **229 个包内文件与生成目录逐字节比对。**
- **24 个独立导出与 ZIP 对应文件同名、同字节检查。**
- 新解压目录完整复跑，以及全部 229 个文件运行前后的不变性检查。
- 两个不同进程哈希种子下，完整校验输出逐字节一致。

这些结果及原始输出均保存在上述交付回执中。逐件清单记录包内其余 228 个文件，清单自身与 ZIP 由包外回执绑定，避免循环哈希。

### 必交文件与阅读入口

**运行和测试请使用完整 ZIP。** 单独下载的 Python 入口依赖包内其他模块。

| 文件 | 用途 |
| --- | --- |
| README.md | 启动命令、结果、输入版本与能力边界 |
| content_schema_spec.md | 字段、ID 命名、版本、作用域、引用和错误定位契约 |
| schema_linter.py | 内容读取及静态校验 CLI |
|  | 137 项候选 ID 注册表 |
|  | 已发行 ID 迁移表；本轮保留表头，0 条获批历史迁移 |
| reference_check_log.txt | 可读校验日志及阻塞定位 |
| reference_report.json | 完整机器可读校验结果 |
| content_manifest.json | 稳定排序、固定哈希的内容清单 |
|  | 35 条缺失绑定与责任方 |
| content_migration_plan.md | 默认值迁移、ID 历史保留及 P21 边界 |
| integration_handoff.md | 下游接收、接口使用与正式接入条件 |
| source_input_receipt.json | 输入来源、固定提交、原包成员及 SHA-256 |
| delivery_manifest.json | 逐件路径、大小、SHA-256、格式/版本、源输入哈希、接收方与修改白名单 |

## 二、已经实现的内容能力

### 1. 固定版本内容读取与 Schema 校验

已为 **9 份 JSON、9 份 TSV** 建立可执行兼容校验，覆盖以下上游数据：

| 上游 | 本轮读取的数据 |
| --- | --- |
| P03 | 卡牌目录、卡牌字典、角色卡池 |
| P04 | 角色骨架、养成费用、角色卡组贡献 |
| P06 | 敌人定义、Boss 阶段图、意图字典、资源请求 |
| P07 | 关卡图、关卡内容目录、奖励表、关卡镜像表 |
| P09 | 词性映射规则、分类字典、映射版本注册、资源倾向候选 |

校验先验证固定输入 SHA-256，再检查结构与跨文件引用。缺字段、重复 JSON 键、非法 TSV 列数、错误数值类型、未知目标和镜像字段不一致均会定位到文件及字段；TSV 错误还提供实际行号。不能通过删掉某份约定输入来取得 PASS。

32 个实体 Schema、18 个输入的版本及哈希均随包提供；具体结果见 reference_report.json。

### 2. 有类型、作用域和来源的 ID 注册

注册键采用 (kind, scope, id)，保留原始 ID；注册表按固定顺序输出，并记录定义所在文件、字段位置及源文件哈希。

本轮主要类型的实际数量如下：

| 类型 | 数量 | 解释 |
| --- | --- | --- |
| character | 7 | P03 的 4 个 Mock 槽位，加 P04 的 3 个样例角色；没有合并身份 |
| card | 10 | 8 张 Mock 可用卡、2 张受阻扩展卡 |
| enemy | 3 | 普通、精英、Boss 各 1 个 |
| phase | 3 | P06 候选 Boss 阶段 |
| stage | 2 | P07 候选关卡 |
| effect | 10 | P03 效果定义 |
| asset | **0** | 没有把资源请求、UI 截图或占位内容登记为正式游戏素材 |

其他注册项包括技能、状态、意图、奖励、资源、阶段图及有作用域的行动状态，总计 **137 项**。以上数量属于收到的候选数据，**不构成首发角色、敌人或卡牌规模的批准**。全部注册记录仍为 CANDIDATE、`production_allowed=false`。详见 。

### 3. 跨文件引用与不同类型的循环检查

已实现并测试：

- 卡牌到效果、角色槽位及关联技能的引用检查。
- P03/P04 角色兼容关系检查，兼容关系不转成 ID 别名。
- 敌人状态、技能、意图及 Boss 阶段的归属检查。
- Boss 阶段图与敌人、初始状态及关卡敌人列表的对应检查。
- 关卡前置、章节和奖励引用检查。
- JSON 主数据与 TSV 镜像中的关键字段一致性检查。
- 关卡解锁图和 Boss 阶段转换图的无环检查。
- 正常敌人行动循环允许存在，但其目标必须有效，且不能直接跨越权威阶段。

**“0 悬空引用”覆盖本轮明确的 403 条非空内容引用。** 空缺的正式素材、类别和资源绑定另列为 BLOCKED，没有通过忽略缺项来宣称正式内容完整。逐条定位见  和 。

### 4. 内容版本与默认值迁移

实际实现并运行的是：

纯文本

`P22-CONTENT-MANIFEST/0.1.0 → P22-CONTENT-MANIFEST/0.2.0`

该迁移仅为本岗内容清单增加：

JSON

`{
  "lifecycle": "CANDIDATE",
  "production_allowed": false,
  "tags": []
}`

原文档路径、哈希及版本保持不变；重复迁移具有幂等性；未知版本、缺失必填哈希和非法空值会被拒绝。**没有填入角色属性、卡牌费用或奖励数值，没有改写 P21 存档。**

本轮没有取得已发行内容的旧注册表及获批改名记录，因此真实 id_migration_map.tsv 只有表头。迁移算法使用明确的测试链验证了环、重复源、未知目标、tombstone 和原始 canonical 身份保留；测试别名不会进入正式注册。具体范围与审计说明见 content_migration_plan.md。

## 三、实际验证结果

以下以**最终 ZIP 新解压目录复跑**为准；重复运行不累计为新增覆盖。

| 验证层级 | 实际结果 | 证明范围 |
| --- | --- | --- |
| P22 作者设计与代码复核 | COMPLETED_AUTHOR_REVIEW | 内容/存档分离、所有权、输入版本、引用及证据边界 |
| 作者自动化测试 | **109 PASS，0 FAIL，0 ERROR，0 skip** | 内容约束、CLI、输入契约、路径、资源字节、迁移与回归 |
| Schema 元校验 | **32/32 PASS** | Schema 定义有效 |
| 固定数据结构与哈希 | **18/18 PASS** | 本轮约定 JSON/TSV 原件 |
| ID 与引用检查 | **137 项定义、403 条引用；0 重复、0 悬空非空引用** | 当前候选数据 |
| 实体负向样本 | **5/5 按预期拒绝** | 缺费用字段、重复卡牌 ID、关卡环、坏资源路径、悬空效果引用 |
| 确定性输出 | **PASS** | 不同进程哈希种子下完整输出逐字节一致 |
| V6 静态映射复核 | **PASS** | 43 岗、92 项职责、27 条 IC；不代表这些职责均已实施 |
| ZIP、包内文件与独立导出 | **PASS** | 229 个包内文件、24 个独立导出 |
| 正式接入预检 | **BLOCKED，exit 3** | 路径、目标环境、素材和正式绑定条件不足 |
| P32 独测、P33 人工、P35 独审 | **NOT_RUN** | 未代签 |
| P25 风格、P37 合规验收 | **NOT_RUN** | 未将字节校验当作美术或许可验收 |
| 目标引擎、Windows、真实 Anki、整游戏 E2E | **NOT_RUN** | 本轮未执行 |

实际作者环境为 **Python 3.12.14、Linux x86_64**。精确依赖随包固定；测试原始结果、环境和分层状态分别见交付回执、environment_observed.json 与 verification_status.json。

### 已修复缺陷及保留证据

本轮实际复现并修复 **5 项 P22 自身缺陷**，涉及角色枚举、未收到资源的哈希标记、随机种子范围、外部文档来源分类，以及迁移入口对传入注册表的重复 ID 检查。

修复前报告、源码或 Schema 快照保存在 evidence/failures/；最终 109 项测试包含相应回归验证。**P32 独立复测及 P35 关单仍为 NOT_RUN。** 详情见 defect_log.json。

## 四、上游核验与正式接入阻塞

### 已核验的来源

实际读取并核验了：

- **15 个上传件。**
- **120 个去重的附件及嵌套 ZIP。**
- **9,684 个文件成员。**
- **813 条 relay 大小/SHA-256 校验记录，0 错误。**
- 另行从固定职责提交取得的 V6 原 ZIP，其内部清单 **14/14 校验通过**。

其中 10 个上传件直接匹配 P21 固定提交的 Git blob，另外 5 个为重打包容器，按内部成员及嵌套原包核验。没有将重打包容器误报为 Git 中的同字节 ZIP。固定提交、完整 SHA-256 和成员路径均见 source_input_receipt.json。

还发现一份历史独立导出的 P04 养成表只有 **6 字节 row_id**。本轮采用原 P04 ZIP 内 **5,346 字节、21 行**的完整原表；两份字节与来源都已保留，没有代 P04 补写或修复设计数据。

### 仍需补齐的条件

| 缺项 | 责任方及所需工件 |
| --- | --- |
| 实际工程路径与写权限 | **P13**：真实工程固定提交、三条实际路径映射、修改白名单；当前均为 actual_production_path=null、`write_allowed=false` |
| 目标环境 | **P13/P34**：引擎、目标 OS、构建入口及实际执行证据 |
| 正式资源目录和素材 | **P30、P26/P27**：目录契约、实际素材与源文件；风格/合规由 **P25/P37** 验收 |
| 正式词性与资源绑定 | **P09/P08/P22**，范围批准 **P01**：语义、资源契约、正式 ID 和固定来源 |
| 内容生产提升及 MVP 数量 | **P01 与原内容 owner**：明确批准范围及数据版本 |
| 已发行 ID 变更 | **P13/P21/P01**：旧注册表、迁移批准和 canonical 身份要求 |
| 独立验收及工程整合 | **P32/P33/P35**；跨模块合并由用户指定 **EXT-INTEGRATOR** |

已经准备 **6 项版本化 RFC、12 个接收方交接条目**，状态分别为 PREPARED_NOT_SUBMITTED、`PREPARED_NOT_ACKNOWLEDGED`，没有宣称已提交或获批。见 interface_rfcs.json 与 integration_handoff.md。

## 五、下一位直接复现

完整解压后进入 P22_ContentPipeline_V0.1：

Bash

`python -m pip install -r requirements.txt

python -B tools/content_validation/verify_delivery.py

python -B tools/content_validation/reproduce.py \
  --output ../P22_reproduction`

输出目录必须尚不存在，并位于包外。最终新解压复跑中，后两条命令实际退出码均为 **0**。`reproduce.py` 内部执行了完整测试、两次确定性校验、正式预检、负向样本、元数据迁移及 ID 迁移表检查；其中正式预检实际返回 **3**，按约定保留 BLOCKED。

单独查看正式预检：

Bash

`python -B tools/content_validation/schema_linter.py preflight`

**下一接收方可以立即用完整包开展 P32 独立复测、P35 证据审查，以及 P03/P04/P06/P07/P09/P13/P30 的内容契约受理。实际工程落位和跨模块合并继续等待 P13 授权及用户指定的 EXT-INTEGRATOR。**

---

## 本次归档的原始文件

- [P22_ContentPipeline_V0.1.zip](files/archives/P22_ContentPipeline_V0.1.zip)
- [P22_delivery_receipt.json](files/data/P22_delivery_receipt.json)
- [54e604b3-1-README.md](files/documents/54e604b3-1-README.md)
- [schema_linter.py](files/code/schema_linter.py)
- [run_tests.py](files/code/run_tests.py)
- [332ab142-1-verify_delivery.py](files/code/332ab142-1-verify_delivery.py)
- [reproduce.py](files/code/reproduce.py)
- [requirements.txt](files/documents/requirements.txt)
- [content_id_registry.tsv](files/data/content_id_registry.tsv)
- [id_migration_map.tsv](files/data/id_migration_map.tsv)
- [reference_check_log.txt](files/documents/reference_check_log.txt)
- [reference_report.json](files/data/reference_report.json)
- [content_manifest.json](files/data/content_manifest.json)
- [resource_manifest.json](files/data/resource_manifest.json)
- [missing_bindings.tsv](files/data/missing_bindings.tsv)
- [references.tsv](files/data/references.tsv)
- [content_schema_spec.md](files/documents/content_schema_spec.md)
- [content_migration_plan.md](files/documents/content_migration_plan.md)
- [2c6843ea-1-integration_handoff.md](files/documents/2c6843ea-1-integration_handoff.md)
- [a2201b68-1-interface_rfcs.json](files/data/a2201b68-1-interface_rfcs.json)
- [644b4412-1-actual_path_request.json](files/data/644b4412-1-actual_path_request.json)
- [7543396d-1-verification_status.json](files/data/7543396d-1-verification_status.json)
- [eff58696-1-defect_log.json](files/data/eff58696-1-defect_log.json)
- [ae4117bd-1-environment_observed.json](files/data/ae4117bd-1-environment_observed.json)
- [fd7d1416-1-source_input_receipt.json](files/data/fd7d1416-1-source_input_receipt.json)
- [7ccd26df-1-delivery_manifest.json](files/data/7ccd26df-1-delivery_manifest.json)
- [P20_Menu_1280.png](files/images/P20_Menu_1280.png)
- [P20_Party_1280.png](files/images/P20_Party_1280.png)
- [P20_Growth_1280.png](files/images/P20_Growth_1280.png)
- [P20_Chapters_1280.png](files/images/P20_Chapters_1280.png)
- [P20_Settlement_1280.png](files/images/P20_Settlement_1280.png)
- [P20_Learning_Quarantine.png](files/images/P20_Learning_Quarantine.png)
- [P20_Migration_Failed.png](files/images/P20_Migration_Failed.png)
- [P20_Menu_390.png](files/images/P20_Menu_390.png)
- [P20_Restart_Pending.png](files/images/P20_Restart_Pending.png)
- [relay-materials-1-236d59e507.zip](files/archives/relay-materials-1-236d59e507.zip)
- [relay-materials-2-29da14dfaa.zip](files/archives/relay-materials-2-29da14dfaa.zip)
- [relay-materials-3-359996fd72.zip](files/archives/relay-materials-3-359996fd72.zip)
- [relay-materials-4-279d81665e.zip](files/archives/relay-materials-4-279d81665e.zip)
- [relay-materials-5-93fd453ebe.zip](files/archives/relay-materials-5-93fd453ebe.zip)
- [relay-materials-6-4a55082585.zip](files/archives/relay-materials-6-4a55082585.zip)
- [relay-materials-7-9e66ba3f56.zip](files/archives/relay-materials-7-9e66ba3f56.zip)

