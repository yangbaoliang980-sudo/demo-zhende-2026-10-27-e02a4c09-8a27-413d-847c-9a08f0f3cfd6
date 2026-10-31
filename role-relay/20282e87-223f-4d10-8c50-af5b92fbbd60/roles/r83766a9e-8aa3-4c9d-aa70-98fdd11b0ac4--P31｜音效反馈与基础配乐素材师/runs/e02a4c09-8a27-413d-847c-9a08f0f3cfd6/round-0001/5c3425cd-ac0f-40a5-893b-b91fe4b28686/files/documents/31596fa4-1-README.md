# P31｜音效反馈与基础配乐素材 V0.1（隔离原型）

状态：`ISOLATED_PROCEDURAL_SFX_DRAFT / PRODUCTION_BLOCKED`

本包生成 10 段原创程序合成短音效：卡牌移动、命中、护盾、治疗、增益、胜利、失败、奖励、错误、点击。未制作 BGM。所有声音均由随包提供的 Python 标准库脚本合成，不使用第三方采样或现成音乐。

## 关键边界
- 本包不是生产工程导入，不修改游戏项目。
- P13 `actual_path_mapping.json` 中 `runtime/audio_playback/**` 为 `BLOCKED_NOT_MAPPED`；P31 的 `audio/source/**`、`audio/exports/**`、`design/audio/**` 也未获得生产路径授权。
- P02/P13 的 BattleEvent 仅能作为隔离 DTO/规格参考；P28 回执显示 `P02_event_contract=BLOCKED_DRAFT_ONLY`，P28 时间轴未提供生产绑定证据。
- UI click 与 reward grant 不是本包可确认的冻结 BattleEvent，故在事件表中标记阻塞，不伪造绑定。
- P37 许可审核、P29 播放器接收、P32 独立测试、P35 审查均未执行。
- P23 `none` 模式要求所有可选音效/触觉/动效关闭；音效不可承担唯一玩法信息。

## 重建
在包根目录运行：
`python tools/generate_sfx.py`
脚本重建 `audio/source/` 下的程序合成 WAV。当前 `audio/exports/` 为与 source 字节一致的隔离导出副本。

## 下游
P29：播放器/事件消费与播放策略；P23：静音/无障碍；P37：来源与权利审核；P32：独立自动化测试；P35：独立证据门禁。跨岗位集成仍需用户授权的 EXT-INTEGRATOR。
