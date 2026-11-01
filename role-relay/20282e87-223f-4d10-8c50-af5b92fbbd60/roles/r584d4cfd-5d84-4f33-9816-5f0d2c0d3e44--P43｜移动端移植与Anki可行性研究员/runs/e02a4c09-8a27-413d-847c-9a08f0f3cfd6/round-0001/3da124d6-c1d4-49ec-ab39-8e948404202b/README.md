# P43｜移动端移植与 Anki 可行性研究

本轮按 P43 的独占职责执行，不创建子角色，不修改桌面主线，不擅自进行跨模块集成。

首先明确一个验收边界：桌面版 Anki 插件能够获取复习事件，不代表 iOS 或 Android 客户端也能获取相同事件。 必须分别验证移动客户端的扩展接口、权限、事件身份、撤销能力及离线同步，不能用桌面端测试代替。

本轮交付将区分四种状态：

- `PASS`：已有真实证据支持。
- `FAIL`：实际测试失败。
- `BLOCKED`：缺少完成验证的必要输入。
- `NOT_RUN`：尚未在目标设备或环境执行。

不会把技术调研、接口推测或 Mock 当作真机兼容性测试。

## 一、现有工程基线核验

从此前的项目记录中，能够确认以下历史决策：

| 项目 | 已知情况 |
| --- | --- |
| 原目标平台 | Windows x64 |
| 原引擎 | Unity 6.3 LTS |
| 原 Anki 环境 | Anki 桌面端 |
| 原通信方案 | Python 本地桥接 |
| 游戏账本 | SQLite |
| 移动端批准 | 未找到 P01 批准记录 |
| P13 实际工程映射 | 尚未确认真实工程及生产路径 |
| P10 Hook 实测 | 尚无可核验的目标版本实测记录 |
| 移动端真机测试 | 未执行 |

这里有一个重要结论：目前不能把另一项 iOS 文本翻译项目的 iOS 26 目标套用到《言灵旅团》。

因此，P43 可以开展平台能力研究，但不能自行决定游戏正式转向 iOS 或 Android，也不能宣布移动端已经兼容。

---

## 本次归档的原始文件

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
- [relay-materials-1-e26970a5e7.zip](files/archives/relay-materials-1-e26970a5e7.zip)
- [relay-materials-2-ca6ada3652.zip](files/archives/relay-materials-2-ca6ada3652.zip)
- [relay-materials-3-166c0973a2.zip](files/archives/relay-materials-3-166c0973a2.zip)
- [relay-materials-4-1c81a8a0fa.zip](files/archives/relay-materials-4-1c81a8a0fa.zip)

