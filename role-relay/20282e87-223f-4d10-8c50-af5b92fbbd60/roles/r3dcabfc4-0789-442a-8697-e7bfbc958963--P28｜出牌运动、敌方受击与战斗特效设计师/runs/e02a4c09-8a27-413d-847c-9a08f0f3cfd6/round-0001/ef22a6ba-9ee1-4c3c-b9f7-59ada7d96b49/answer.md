# P28｜出牌运动、敌方受击与战斗特效设计

本轮按照 P28 独立岗位执行，不创建子角色，不进行跨岗位整合，也不修改 P27 已交付的原始素材。

本次工作的重点是：把 P27 已有的敌方视觉资产转化为可供战斗播放器实现的动效规范、事件映射、时间轴和轻量特效素材。

已明确的工作边界：

- P27 提供敌方造型、卡面构图和视觉锚点参考。
- P28 负责动画时序、视觉反馈、特效原型和降级规则。
- 不自行决定伤害数值、HP 变化或战斗结算时点。
- 不把动画碰撞帧当作权威伤害结算时点。
- 不编写动画控制器，不擅自修改游戏工程。
- 未取得真实上游契约的部分明确标记 `BLOCKED`，不伪造接口兼容或实机运行结果。

## 一、上游素材核验

本轮实际读取了上传的压缩包及嵌套 ZIP，并检查了 P27 的 SVG、PNG、锚点和资产映射。

| 输入 | 核验结果 |
| --- | --- |
| P27 普通怪、精英怪、BOSS SVG | 已读取 |
| P27 卡面构图研究图 | 已读取 |
| P27 敌方锚点表 | 已读取 |
| P23 UX 锚点契约 | 已读取 |
| P23 减少动态效果规范 | 已读取 |
| P23 嵌入的 P02 战斗时序草案 | 已读取 |
| P25 Art Bible | 已读取 |
| P06 正式敌方机制包 | BLOCKED |
| P13 P28 实际工程路径授权 | BLOCKED |
| P29 动效播放器正式契约 | BLOCKED |

特别注意：P27 提供的三个受击中心分别是：

| 敌人 | 候选归一化坐标 |
| --- | --- |
| 普通怪 | 0.500, 0.560 |
| 精英怪 | 0.500, 0.570 |
| BOSS | 0.500, 0.625 |

这些坐标仍然是 `PROPOSAL_NOT_RUNTIME`，不能直接当作游戏实际坐标。

## 二、本轮实际交付

隔离交付包已生成

P28_BattleMotion_V0.1.zip

ZIP CRC PASS

# 84,978 bytes

SHA-256

`70504816a22e74c1dbf2a55b4f28ecad8fd5b9f555c031f1f155719be51a23f1`
下载 P28 完整交付包

独立交付回执

下载 P28_delivery_receipt.json

交付内容包括：

| 文件 | 用途 |
| --- | --- |
| `vfx_timeline.tsv` | 动效时间轴 |
| `event_to_effect.tsv` | 战斗事件到特效映射 |
| `vfx_fallback_rules.md` | 取消、跳过、倍速、减少动态效果规则 |
| `motion_storyboard.md` | 动效分镜 |
| `source_input_receipt.json` | 上游输入记录 |
| `P27_enemy_anchors.tsv` | P27 原始候选锚点 |
| `P27_enemy_phase_asset_map.json` | P27 原始敌方资产映射 |
| `delivery_manifest.json` | 文件大小及 SHA-256 清单 |
| `static_validation.json` | 静态验证记录 |

另外制作了 7 组可编辑 SVG 和 PNG 特效原型：

![Glowing arrow creating a neon light speed trail](https://images.openai.com/static-rsc-4/M65F6Erp4TLwD2Eudqdql234_NgBpYRSh7pzEWXo1isD6_a39diqqHEsQcqvE6Q5MLlXomhOzhZ6l3YDeO9PIKLBYP9Z7YMkF8Kcun5jslp-AWgat900VuWaRlM4Ew05plgdZHAda7KbXz--bMI7FkORwJNKxI1shZkeTQ69KFjnwwe-wWGvaINA16ADVW2q?purpose=inline)

卡牌飞行拖尾
FX Card Trail

![50 Hit Impact VFX](https://images.openai.com/static-rsc-4/-bZrvFrutCV8dWOafu1bbc7GWoMV6_jSaTzUWuk1H17wkKSlxe01NdiN1KxCVFzmDfeTVdUBoLmtFRHl3J1wXzALRzWEpzM9R4AWAoS8L07omX027tkHDuvyOWLgEKLxH2dwvq8RiIem4wu7orh84dVWpiJ_61RnzC2Ftcl-ABY?purpose=inline)

撞击爆点
FX Impact Burst

![VFX Area of Effect](https://images.openai.com/static-rsc-4/PyhLylnNhRhgkDT_H6_ii6EUxmH1Iwjc4KgCoNHluL4bvpNVpPwxKQJQiPO40g9ZzvQs4mx6vW4IEY0VYsfLVy9Zt1S0Bx-LYOclP0X_g9NEXPcMKuG9t91GDRhZ8dg9_6-JHcbtdttNAIzPNWw48e5hizgTR_zneyS-aRtSEjc?purpose=inline)

护盾环
FX Shield Ring

![Unity Game VFX - Light Skill Collection - EricWang(Unity VFX Artist) - BOOTH](https://images.openai.com/static-rsc-4/NEsyB8qS-7nFqpne0MBcgRhBeMy-K7PG_G96L7fhtlOo_jYC0rFJG9q-ZNpH7WJTmV5pZ3PRq8gJSs4guDU_bPS7CpJqvHP587DQAO8otIiqHCtuMoSG5I2McmzYXXnTN10c0Is0r0Y-Y81uwaa5tXZ9YFMsbSehlYGRBovoZio?purpose=inline)

治疗反馈
FX Heal Cross

![Download Twinkling Starburst Emblem PNG 05252024 PNG | Wallpapers.com](https://images.openai.com/static-rsc-4/5afFRMxTRKGtKD21ZGMRVj-G0MtszYg2UBMG9l7C3Iddb5WjUFBA8vSF_tU96Se0n_cObaV7-6x5syA2z-ZdWBD871r5RonTx3DSnz5eiXmWZ_Gc7-EDu7YTmFHtmAchNfoSk1PnNDhNixAJ0HqXA0-sbTtC4InPlJprqdrrKoQ?purpose=inline)

状态特效
FX Status Spark

![Purple Shard Cascade](https://images.openai.com/static-rsc-4/BK-0jgpj_6cUXc7OmD5zkxfA4it6oFK9HoQqQa7HHEbieAblZyo38p5wBuMflsL_TuSWYHkXSJ7uRJAbdOMVtT-CK36frDuIo7x2aaaPFS-JZbLHswiUkHojsiyHdy07pXqQ79T0NpDJ_Q7LjkBLlxO35BesAe-T_GvEfL6cNPPlyrupOHRHTER4AG1Sx9Ii?purpose=inline)

死亡消散
FX Death Dissolve

上面是效果类型的视觉参考，不是本次交付文件的实际预览；实际原稿和 PNG 均在 ZIP 中。

## 三、动效时序设计

本轮提出的建议参数如下，最终由 P29 适配并由 P32 验证。

| 表现 | 建议时长 |
| --- | --- |
| 抽牌 | 420ms |
| 卡牌飞行 | 260ms |
| 命中反馈 | 90ms |
| 护盾反馈 | 180ms |
| 治疗反馈 | 240ms |
| 状态反馈 | 220ms |
| 死亡消散 | 360ms |
| 敌方意图强调 | 160ms |
| BOSS 阶段提案提示 | 420ms |

最重要的时序原则：

卡牌撞击只是视觉表现，不能作为伤害结算依据。

例如：

1. P14 提交真实战斗结果。
2. 播放器收到 `DAMAGE_APPLIED`。
3. 播放受击效果。
4. 从权威快照更新 HP 和护盾。
5. 展示真实结算数字。

如果动画关闭，仍然必须得到完全相同的战斗结果。

## 四、验证情况

| 验证项目 | 状态 |
| --- | --- |
| 7 个 SVG XML 解析 | PASS |
| 7 个 PNG 解码 | PASS |
| PNG RGBA 检查 | PASS |
| 逐件 SHA-256 校验 | PASS |
| ZIP CRC | PASS |
| P25 审美复核 | NOT_RUN |
| P30 实际引擎导入 | NOT_RUN |
| P32 独立测试 | NOT_RUN |
| P35 工程审查 | NOT_RUN |
| P37 许可审查 | NOT_RUN |
| P29 实际播放器联调 | BLOCKED |

## 五、下一位接手人员

P29｜动效播放器程序员

可以直接接收本次 ZIP，重点读取：

- `vfx_timeline.tsv`
- `event_to_effect.tsv`
- `vfx_fallback_rules.md`
- `art/fx/source/`
- `art/fx/exports/`

需要先处理正式事件契约、动画 epoch、取消和倍速语义，再实现播放器。

另外，P06 正式机制资料缺失，P13 生产路径授权缺失。这两项不能由 P28 擅自补造。

P28 本轮结论：隔离设计和特效原型实体交付完成；正式接口绑定、引擎导入和独立验收尚未完成。

没有修改 P27 原始素材，没有修改游戏工程，也没有代替 P29 编写动画控制器。交付包可以直接交给接力台归档。