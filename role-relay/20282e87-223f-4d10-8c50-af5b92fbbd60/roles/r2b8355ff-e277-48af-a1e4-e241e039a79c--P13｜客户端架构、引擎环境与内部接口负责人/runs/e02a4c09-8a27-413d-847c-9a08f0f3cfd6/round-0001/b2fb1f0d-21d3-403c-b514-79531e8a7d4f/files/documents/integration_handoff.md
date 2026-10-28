# 下游接收说明｜P13 0.1.0-isolated

任务 P13-S00-ARCH-001 / 上游 TASK-00-02。本包可以独立复现，不能作为覆盖实际工程的授权。下游回执均 PREPARED_NOT_ACKNOWLEDGED；P13 不代签其他 owner，也不任命 EXT-INTEGRATOR。

## 先核对交付字节

在解压根执行 `python -B architecture/tools/verify_delivery.py`。逐文件路径、大小、SHA-256、格式、版本、源输入哈希、接收人和修改白名单由 `delivery_manifest.sha256.tsv` 记录。清单不包含自己的哈希；外层 `delivery_receipt.json` 绑定清单、ZIP 和每个独立导出。不同名导出也会显式给出包内路径，但本次对应文件使用相同 basename 和原字节。

`actual_path_mapping.json` 的 package-relative 路径可在任意解压位置使用；observed absolute path 是作者运行环境的证据，不需要在接收机创建同名 `/workspace/...` 路径。所有 actual_production_path 仍为 null。不要把本包挂到现有游戏根后覆盖同名目录。

## 可直接使用的模块入口

```python
from runtime.framework.yltt_framework.contracts import validate, decode
from runtime.framework.yltt_framework.host import CommandMailbox
from runtime.framework.yltt_framework.sequence import BattleStreamGuard
from runtime.framework.yltt_framework.testing import ScriptedEndpoint
```

`validate(value, expected_type)` 和 `decode(raw, expected_type)` 返回 FrozenMessage；`.value` 每次产生新的副本。使用者不能通过修改拿到的字典更改原消息。`ScriptedEndpoint` 只响应明确配置的输入，其余输入抛错，不自行模拟业务。

```python
# 独立接口测试例：没有真实 Anki、账本、奖励或存档。
import json
from pathlib import Path
def example(name):
    return validate(json.loads(Path(
        f"contracts/internal/examples/{name}.json").read_text()))

query = example("StudyStatusQuery")
unknown = example("StudyStatusView")
read_stub = ScriptedEndpoint([((query,), unknown)])
assert read_stub.call(query).value["state"] == "UNKNOWN"
```

各 owner 在自己的已授权独立包中实现相应 Protocol，并消费固定本包版本；通过构造注入端口，不循环导入彼此的业务实现。PortRegistry 在启动前拒绝重复 provider 或错误 owner。当前包未绑定 P14/P17/P21 的真实实现，未绑定即显式失败。

## 各接收方的实体入口

| 接收方 | 直接接手文件 | 接收后的边界 |
|---|---|---|
| P01 | inventory、ADR、blockers、target requirements、RFC/CR | 补真实工程/目标决策，不把独立作者检查当 G0 通过 |
| P11 | StudyStatusQuery/View、StudyResultReader、P13-RFC-002/003 | 本岗实现作用域与一致读取投影；保留业务资格 owner |
| P12 | ports.py、宿主/线程语义、映射、RFC-002、保留的原 ZIP | 原 owner 改 transport adapter；P13 未改变 wire 协议 |
| P14 | BattleCommand/State/Snapshot/Event/CommitBatch/Result/Reply、P02 原规则 | 本岗实现唯一提交、费用与防重；接受 IC-05 后独测 |
| P15 | DeckPatchCandidate、签名/版本约束、ScriptedEndpoint | 只产生候选；不提交 BattleState/费用 |
| P16 | EnemyIntent/PhaseProposal、只读快照 | 固定内容与 RNG 版本产生候选；不写 HP/phase |
| P17 | PartySnapshot、WalletSnapshot/DeltaCandidate、RFC-004 | 唯一钱包/编队业务；不得绕过 P21 |
| P18 | BattleResult、StageProgressView、AtomicCommitProposal | 基于可信结果处理进度；stage 与 battle 防重分域 |
| P19/P29 | presentation_adapter_spec、stream guard、Spy 用例 | P19 实现显示租约与最终绑定；P29 实现实际动画 |
| P20 | StudyStatusView/Party/Wallet/Stage/Save 只读 DTO | 查询状态不得自行授奖/扣款 |
| P21 | RFC-003、CommitProof/Lookup、事务提案 | IC-19 owner 审定实际持久模型及恢复连续性 |
| P22 | 引用字段/fixture notice、RFC-005 | 决定正式 ID/Schema，不把 fixture:* 注册为正式资源 |
| P30 | AssetRef、源哈希与布局建议 | 正式导入与资源状态在本岗执行 |
| P32/P35 | tests、raw logs、source snapshots、manifest、分层状态 | 分别独立复测/审查，追加自身回执 |

## 真实宿主线程映射（待目标运行验证）

P12 IO 工作侧只接受其已认证/解析的输入；P11/P17/P18/P21 依据领域事务串行边界执行。P14 的 battle_id 队列不被网络时间或动画回调驱动。游戏主线程处理 P19/P29 的显示能力。队列满时保留原请求；入队不产生业务 ACK。P21 提交结果不确定时按原 transaction_id 查询；不制造新学习身份。

P13 的 CommandMailbox 是已运行的用户战斗输入示例；不能直接接收 Anki envelope，也没有包装 P12 真实 ingress。P12 主线程/工作线程接入是待其原 owner 实现的适配任务。真实场景树、回调调度、进程生命周期和死锁测试仍 NOT_RUN。

## 恢复或变更

收到新源码/契约时，先验证原 base SHA 和新 SHA、需求ID、接口版本、owner、授权及目标环境。若与本包有差异，保留两个版本并在 RFC/CR 中列出字段、行为和向量差异。修复交原 owner，P32 复测，P35 独审；连续两轮无新证据交 P01。不得通过删除失败记录、覆盖历史 ZIP 或修改状态布尔值放行。

本包没有跨模块 merge commit、GitHub 写入、最终游戏构建或正式发布。完整整合仍由用户后续指定人员执行。
