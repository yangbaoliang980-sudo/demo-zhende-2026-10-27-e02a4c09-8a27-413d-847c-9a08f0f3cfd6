# P34｜目标设备兼容、性能与可靠性测试

已开始实际资料核验
 
真实设备测试条件待确认

本次严格限定为 P34，不创建子角色，不修改其他岗位的生产源码，不代替 P13、P32、P33、P35 或 EXT-INTEGRATOR 执行其职责。

P34 的重点不是编造一份性能报告，而是建立能够追溯到真实设备、真实版本和实际运行记录的兼容性与性能证据。

## 一、已完成的附件接收核验

已实际读取四个 relay-materials ZIP，并检查其目录成员。

| 文件 | 实际大小 | SHA-256 核验 |
| --- | --- | --- |
| relay-materials-1 | 11,028,234 B | 已计算 |
| relay-materials-2 | 12,571,594 B | 已计算 |
| relay-materials-3 | 15,634,025 B | 已计算 |
| relay-materials-4 | 6,652,005 B | 已计算 |

四个 ZIP 均能正常打开并读取目录，没有因缺少素材而停止。

此外，已经确认：

- P33 交付回执实际存在，JSON 可以正常解析。
- P33 提供了 22 条人工验收用例。
- P33 已明确标记真实 RC 阻塞，完整 E2E 尚未运行。
- 目前不能将 P33 的人工用例准备状态当成真实游戏运行证据。

## 二、P13 与目标环境核验

BLOCKED_TARGET_ENV

从附件中的实际文件读取到以下结果：

| 核验项目 | 实际结果 |
| --- | --- |
| 游戏实际 GitHub 仓库 | 未提供 |
| 游戏固定 Commit | null |
| 实际游戏引擎 | null |
| 目标操作系统 | null |
| 目标架构 | null |
| 生产工程写入授权 | false |
| P13 实际路径映射 | `ISOLATED_MAPPING_VERIFIED_TARGET_BLOCKED` |

关键文件：

- `actual_path_mapping.json`
- `target_environment_requirements.json`
- `execution_environment.json`

其中，P32 的执行记录显示，它使用的是 Linux 隔离 Python 测试环境，Python 3.13.5。该环境没有实际 Unity 导入、Windows 游戏客户端、Anki 或真实 E2E 测试。

这不能作为目标 Windows 设备的性能基线。

另外，GitHub 方面已经检查你提供的43岗位参考仓库。当前仓库默认分支为 `main`，但代码搜索没有找到 `ProjectVersion.txt`，也没有找到可确认的实际 Unity 游戏工程。

因此，我不会把角色职责仓库或隔离测试包冒充成游戏工程。

## 三、P34 本轮实际执行边界

在真实目标机资料缺失的情况下，我继续推进不依赖目标机的部分：

1. 建立环境信息采集工具。
2. 建立 OS、Anki、引擎和硬件兼容矩阵。
3. 建立性能采样记录格式。
4. 建立休眠唤醒、长时间运行、端口权限和崩溃恢复的验收记录结构。
5. 将每项未知条件关联到具体上游责任人。

真实设备上的 FPS、帧时间、峰值内存和长时运行结果仍然保持 `NOT_RUN`，不会用设计值代替实测值。

## 四、P34 实际交付文件

隔离交付包已生成并验证

P34_Compatibility_Performance_V0.1.zip

ZIP 大小

9,762 bytes

内部文件

9 个

CRC 校验

PASS

文件字节一致性

9/9

SHA-256

0629974b17742575078f3a82230f21ff9a4aca6968df05ed5875e4c4571f8663

下载 P34 完整交付包

下载 P34_delivery_receipt.json

主要文件：

| 文件 | 用途 |
| --- | --- |
| `qa/environment_inventory.tsv` | 环境信息清单 |
| `qa/compat_matrix.tsv` | 兼容性矩阵 |
| `qa/perf_logs/perf_log_template.tsv` | 性能记录模板 |
| `tools/collect_windows_environment.ps1` | Windows 环境采集 |
| `tools/sample_process_resources.ps1` | 进程 CPU、内存采样 |
| `source_evidence_manifest.json` | 上游输入哈希 |
| `reports/environment/P34_environment_performance_report.md` | 正式报告 |
| `delivery_manifest.json` | 逐文件交付清单 |
| `README.md` | 使用说明 |

交付包已经实际重新打开 ZIP 检查，9 个成员与独立源文件逐字节一致。

## 五、目前验收状态

| 验收项目 | 状态 |
| --- | --- |
| 上游资料核验 | PASS |
| 环境清单建立 | PARTIAL |
| 兼容矩阵建立 | PASS |
| 性能采样工具 | 已交付 |
| 真实目标机兼容性 | BLOCKED |
| FPS/帧时间实测 | NOT_RUN |
| 峰值内存实测 | NOT_RUN |
| Anki 插件共存 | NOT_RUN |
| 休眠唤醒 | NOT_RUN |
| 长时运行 | NOT_RUN |
| P35 独立审查 | NOT_RUN |

## 六、下一步需要你提供的关键证据

目前最重要的不是继续制作测试文档，而是拿到真实目标电脑的环境数据和实际游戏构建。

请先在你准备运行《言灵旅团》的 Windows 电脑上运行交付包中的 `collect_windows_environment.ps1`，把生成的 `p34_environment_capture.json` 发给我。

另外，我需要确认一个问题：

你最终准备在哪台电脑上运行游戏？是你目前开发、使用 Anki 的那台 Windows 电脑，还是另外一台专门的游戏运行电脑？

这会决定 P34 后续的性能基线、显示缩放测试和兼容性支持范围。

本轮 P34 已完成隔离证据工具包交付，但整个岗位尚未完成真实设备验收。不会提前宣布 PASS。

---

## 本次归档的原始文件

- [P34_delivery_receipt.json](files/data/P34_delivery_receipt.json)
- [ZeninTCG - Fan made - Tamers Chibi Sticker Pack.jpg](files/images/ZeninTCG%20-%20Fan%20made%20-%20Tamers%20Chibi%20Sticker%20Pack.jpg)
- [InnoFusion 3.0 _ The Clan Wars - 30-Hour India's Premier Software + Hardware Hackathon.jpg](files/images/InnoFusion%203.0%20_%20The%20Clan%20Wars%20-%2030-Hour%20India's%20Premier%20Software%20%2B%20Hardware%20Hackathon.jpg)
- [エレメンタルストーリー公式攻略Wiki _ マッシュエンペラー.jpg](files/images/%E3%82%A8%E3%83%AC%E3%83%A1%E3%83%B3%E3%82%BF%E3%83%AB%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AA%E3%83%BC%E5%85%AC%E5%BC%8F%E6%94%BB%E7%95%A5Wiki%20_%20%E3%83%9E%E3%83%83%E3%82%B7%E3%83%A5%E3%82%A8%E3%83%B3%E3%83%9A%E3%83%A9%E3%83%BC.jpg)
- [Glowing arrow creating a neon light speed trail.jpg](files/images/Glowing%20arrow%20creating%20a%20neon%20light%20speed%20trail.jpg)
- [50 Hit Impact VFX.jpg](files/images/50%20Hit%20Impact%20VFX.jpg)
- [VFX Area of Effect.jpg](files/images/VFX%20Area%20of%20Effect.jpg)
- [Unity Game VFX - Light Skill Collection - EricWang(Unity VFX Artist) - BOOTH.jpg](files/images/Unity%20Game%20VFX%20-%20Light%20Skill%20Collection%20-%20EricWang(Unity%20VFX%20Artist)%20-%20BOOTH.jpg)
- [Download Twinkling Starburst Emblem PNG 05252024 PNG _ Wallpapers.com.jpg](files/images/Download%20Twinkling%20Starburst%20Emblem%20PNG%2005252024%20PNG%20_%20Wallpapers.com.jpg)
- [Purple Shard Cascade.jpg](files/images/Purple%20Shard%20Cascade.jpg)
- [千棘海刺 - 洛克王国_手游WIKI_BWIKI_哔哩哔哩.jpg](files/images/%E5%8D%83%E6%A3%98%E6%B5%B7%E5%88%BA%20-%20%E6%B4%9B%E5%85%8B%E7%8E%8B%E5%9B%BD_%E6%89%8B%E6%B8%B8WIKI_BWIKI_%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9.jpg)
- [P27_silhouette_review_board.png](files/images/P27_silhouette_review_board.png)
- [P27_card_layout_studies.png](files/images/P27_card_layout_studies.png)
- [relay-materials-1-a9935c60fd.zip](files/archives/relay-materials-1-a9935c60fd.zip)
- [relay-materials-2-ca6ada3652.zip](files/archives/relay-materials-2-ca6ada3652.zip)
- [relay-materials-3-166c0973a2.zip](files/archives/relay-materials-3-166c0973a2.zip)
- [relay-materials-4-1c81a8a0fa.zip](files/archives/relay-materials-4-1c81a8a0fa.zip)

