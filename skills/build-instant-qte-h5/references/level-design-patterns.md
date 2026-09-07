# QTE 关卡设计源码抽象

本文件深化 `generation_rules.md` 已确定的创意，不替代题材转译、子型选择或核心闭环。它把 standalone QTE 的 cue 序列变成可实现、可复现、可验收的短局关卡；embedded QTE 只使用节点 ID、进入/退出边、可达性和并发约束，父玩法继续拥有整局拓扑。只抽象结构与验证方法，不复制第三方源码，也不要求项目安装这些依赖。

Stars 为 2026-07-26（Asia/Shanghai）的 GitHub API 快照，会随时间变化。源码链接固定到核验时 commit。

## 已核验参考集

| 仓库 | Stars | 许可证 | 状态 | 抽象用途 |
|---|---:|---|---|---|
| [Anuken/Mindustry](https://github.com/Anuken/Mindustry) | 28,367 | GPL-3.0 | 未归档 | 波次分段、过渡尾段、并发上限、显式高潮 |
| [OndrejNepozitek/Edgar-DotNet](https://github.com/OndrejNepozitek/Edgar-DotNet) | 357 | MIT | 未归档 | 先拓扑后模板、主路径、最低间距与生成回退 |
| [deepnight/ldtk](https://github.com/deepnight/ldtk) | 4,135 | MIT | 未归档 | 稳定 ID、分层字段、创作格式到运行时投影 |
| [OpenRA/OpenRA](https://github.com/OpenRA/OpenRA) | 17,142 | GPL-3.0 | 未归档 | 事件驱动目标链、主次目标、触发器清理 |

关键证据：

- Mindustry 的[基础波次与过渡尾段](https://github.com/Anuken/Mindustry/blob/c407e3851607b33ff14739f96639c21e187e5d91/core/src/mindustry/game/Waves.java#L298-L344)、[叠加波次与 Boss 节点](https://github.com/Anuken/Mindustry/blob/c407e3851607b33ff14739f96639c21e187e5d91/core/src/mindustry/game/Waves.java#L356-L406)。
- Edgar-DotNet 的[房间类型、模板与最小间距](https://github.com/OndrejNepozitek/Edgar-DotNet/blob/258c83a88656bd6095255a1b749232ade2b87589/src/Edgar.Examples/Grid2D/ComplexDungeonExample.cs#L27-L108)、[先保证主路径再添加分支](https://github.com/OndrejNepozitek/Edgar-DotNet/blob/258c83a88656bd6095255a1b749232ade2b87589/src/Edgar.Examples/Grid2D/ComplexDungeonExample.cs#L406-L469)。
- LDtk 的[稳定 ID、尺寸、层与字段](https://github.com/deepnight/ldtk/blob/6d69bd1d6be92f01ac30778f6a934f0da8448b16/src/electron.renderer/data/Level.hx#L5-L20)、[创作格式序列化](https://github.com/deepnight/ldtk/blob/6d69bd1d6be92f01ac30778f6a934f0da8448b16/src/electron.renderer/data/Level.hx#L147-L208)、[精简运行时投影](https://github.com/deepnight/ldtk/blob/6d69bd1d6be92f01ac30778f6a934f0da8448b16/src/electron.renderer/data/Level.hx#L220-L270)。
- OpenRA 的[开场活动、状态触发与延迟提示](https://github.com/OpenRA/OpenRA/blob/bbd36d9e6a2d7f0d3b24f102858af6dc8caf8a78/mods/ra/maps/allies-01/allies01.lua#L20-L42)、[事件完成后切换目标](https://github.com/OpenRA/OpenRA/blob/bbd36d9e6a2d7f0d3b24f102858af6dc8caf8a78/mods/ra/maps/allies-01/allies01.lua#L119-L169)。

## Author：先做节奏拓扑，再填题材内容

把目标时长内的 QTE 表示为有向主路径，而不是把若干随机 cue 塞进时间轴。时长由当前游戏的使用场景、动作负荷和试玩结果校准，Skill 不提供统一局长。常用节奏语义为：

`教学 → 建立节奏 → 首次变招 → 短恢复 → 复合压力 → 终局`

每个节点至少冻结：

- `id`：稳定逻辑 ID，不使用展示名、素材名或 DOM ID。
- `type`：`tutorial / establish / variation / recovery / pressure / climax`。
- `start_condition、success_condition、failure_condition`。
- `telegraph_ms、window_ms、recovery_ms`。
- `cue_template、variation_axis、concurrency_limit`。
- `required_refs`：目标、危险、预警和反馈锚点的稳定 ID。

必须满足：

1. 存在一条从教学到终局的完整主路径；奖励或次要目标不能阻断主路径。
2. 新强度段开始时允许上一段短暂退场，但交叠不能超过 `concurrency_limit`。
3. 高潮是显式节点，组合玩家已经学会的语法；终局不首次引入新的主操作。
4. 高压节点后安排恢复节点或足够的 `recovery_ms`，终局除外。
5. 教学与首次变招优先只引入一个尚未掌握的玩家需求；高潮可以组合已经教学的需求。多个数值可随同一个行为变化一起调整，但必须说明各自作用和可读性补偿，不能把“全面恶化”冒充新玩法。
6. 关卡推进以“节点已结算”事件为主；计时器只负责预警、延迟和超时。
7. 主目标失败可以结束本轮；次要目标失败只影响分数、评级或结局。

## 空间与时间可达性

提示出现时，必须至少存在一条合法输入路径。对连续拖拽或跨区拦截，使用实测移动端低分位速度，而不是理论最大速度：

`预计反应时间 + 预计完成位移时间 + 安全余量 <= 有效间隔`

其中有效间隔从玩家能看懂预警的时刻开始，到判定截止为止。多目标节点还要检查：

- 目标和输入路径不越出安全区。
- HUD、手指遮挡区和系统手势区不会堵死唯一可行路径。
- 任一强制连续操作之间都有足够位移与时间预算。
- 预警早于开窗；不能把尚未显示的轨迹时间算进玩家预算。

## Implement：创作格式与运行时投影分开

创作规格可保留策划说明、来源、调参理由和备选模板；coder 使用的 Runtime LevelSpec 只保留判定所需事实。投影前执行：

- 校验节点、目标和反馈锚点 ID 唯一且引用存在。
- 补齐必需层并固定顺序：节奏段、可交互目标、危险物、触发器、预警、反馈锚点。
- 拒绝越界目标、负时长、超出单局预算的节点和不可处理的并发组合。
- 所有自定义字段有类型、单位和默认值；Schema 变化显式迁移。
- 每个节点只在激活时注册监听，结算后以 resolved-once 守卫关闭并注销。

随机选择只能发生在经过审核的 pattern 池内，必须记录 `run_seed`。使用 shuffle-bag、近期降权或冷却避免短期连刷；玩法 RNG 与装饰 RNG 分离。约束冲突时进行有界重试，仍失败则回退到审核模板；重试预算由本局生成规模和性能预算派生，不在 Skill 中写固定次数。

## Verify：固定种子与结构门禁

至少对发布种子和多组抽样种子检查：

- ID 唯一、引用存在、主路径连通、高潮实际出现。
- 节点与总局时长不越界。
- 所有强制操作时间可达、空间可达。
- 同时出现的 cue 不超过并发上限。
- 教学后才出现变招；终局不引入未教学主操作。
- QA seed 与相同分支输入可复现相同节点序列和关键参数；正式普通对局按 `replay_policy` 产生新的 run seed，不能无意中永久固定同一发布序列。
- 相邻阶段的 `phase fingerprint` 至少在动作集合、序列形状、选择/风险、事件特征或恢复职责之一发生非数值变化；只改速度、窗口、尺寸或间隔不算新阶段。
- 高潮重组已教学 pattern；恢复降低负荷但仍提供主动反馈或下一段预告，不能只有空等。
- 约束失败会落到审核模板而非白屏、卡死或死循环。

把失败证据写入 `S_DIFFICULTY`；导致无解、主路径中断或流程卡死时，同时让对应硬 Gate 失败。

## 许可证与选型边界

- GPL 项目只用于阅读和抽象，不复制 `Waves.java`、Lua 任务脚本或其他实现到 Skill/游戏包。
- MIT 项目的模式同样默认重写为项目自身的最小数据合同，不捆绑编辑器或生成器。
- 不把长局 RTS/地牢的规模和具体数值照搬到短局 QTE；所有时长、密度、间隔和并发上限都进入当前游戏的校准合同。
- 已有项目格式优先；本文件约束行为与验证，不强迫更换技术栈。
