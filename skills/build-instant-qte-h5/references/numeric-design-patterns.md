# QTE 数值设计源码抽象

本文件把 `generation_rules.md` 的时间窗、评级、分数与难度变化变成唯一可追踪的校准合同。它不替代玩法创意，也不提供一套可直接照抄的毫秒、速度、尺寸、概率或分数表；优化器、统计库和遥测 SDK 只用于方法参考，不默认进入运行包。

Stars 为 2026-07-26（Asia/Shanghai）的 GitHub API 快照，会随时间变化。源码链接固定到核验时 commit。

## 已核验参考集

| 仓库 | Stars | 许可证 | 状态 | 抽象用途 |
|---|---:|---|---|---|
| [optuna/optuna](https://github.com/optuna/optuna) | 14,565 | MIT | 未归档 | 有边界参数、连续/离散/对数搜索、约束剪枝 |
| [facebookresearch/nevergrad](https://github.com/facebookresearch/nevergrad) | 4,199 | MIT | 未归档 | 有界参数化、ask/tell、有限预算优化 |
| [dubzzz/fast-check](https://github.com/dubzzz/fast-check) | 5,077 | MIT | 未归档 | seed、运行预算、失败收缩与最小反例复现 |
| [simple-statistics/simple-statistics](https://github.com/simple-statistics/simple-statistics) | 3,514 | ISC | 未归档 | 分位数与样本离散度 |
| [ondras/rot.js](https://github.com/ondras/rot.js) | 2,704 | BSD-3-Clause | 未归档 | seed、状态快照、shuffle 与加权随机 |
| [open-telemetry/opentelemetry-js](https://github.com/open-telemetry/opentelemetry-js) | 3,421 | Apache-2.0 | 未归档 | Counter/Histogram、单位、桶和低基数属性 |

关键证据：

- Optuna 的[连续、离散与对数参数边界](https://github.com/optuna/optuna/blob/5893a4b410ba5d6b54964bb1091c252551042724/optuna/trial/_trial.py#L87-L171)和[约束结果处理](https://github.com/optuna/optuna/blob/5893a4b410ba5d6b54964bb1091c252551042724/optuna/samplers/_base.py#L240-L265)。
- Nevergrad 的[有界 Scalar](https://github.com/facebookresearch/nevergrad/blob/617a3b0bcd9b7faa89f68ed6f17b59bec58f2360/nevergrad/parametrization/data.py#L43-L101)与[ask/tell 预算循环](https://github.com/facebookresearch/nevergrad/blob/617a3b0bcd9b7faa89f68ed6f17b59bec58f2360/nevergrad/optimization/base.py#L300-L560)。
- fast-check 的[seed、运行预算、失败收缩和路径复现](https://github.com/dubzzz/fast-check/blob/731493716ed0031564527535e0e7a87a83434255/packages/fast-check/src/check/runner/Runner.ts#L24-L170)。
- simple-statistics 的[分位数](https://github.com/simple-statistics/simple-statistics/blob/43e343916c3829e0f56d3e67c6f79fe9e9a5cec7/src/quantile.js#L1-L103)和[样本离散度](https://github.com/simple-statistics/simple-statistics/blob/43e343916c3829e0f56d3e67c6f79fe9e9a5cec7/src/sample_standard_deviation.js#L1-L20)。
- rot.js 的[可设 seed、状态快照、shuffle 与加权随机](https://github.com/ondras/rot.js/blob/46782e248c2db9d379a5e4f13bb8323f18dff04b/src/rng.ts#L1-L141)。
- OpenTelemetry JS 的[计数与分布语义](https://github.com/open-telemetry/opentelemetry-js/blob/76fa6b509e2b48d9cbee31cb37a2efc61dc4d384/api/src/metrics/Meter.ts#L16-L69)及[单位、桶边界和属性](https://github.com/open-telemetry/opentelemetry-js/blob/76fa6b509e2b48d9cbee31cb37a2efc61dc4d384/api/src/metrics/Metric.ts#L9-L100)。

## 唯一 BalanceProfile

Author、coder、离线模拟器和 QA 必须读取同一组参数；CSS、动画、监听器和测试脚本不得另藏阈值。每个参数登记：

`id / status / value / unit / scope / source / constraints / validation_signal / changed_in_phase`

- `open`：值为 `null`，说明还需什么观察或测量；存在 open 决策就阻断 coder。
- `measured`：来自本游戏目标设备或玩家实测，附样本与证据。
- `inherited`：来自父玩法或已锁定项目合同，附来源位置。

Skill 不给全局 `baseline/min/max`。每个实际游戏按当前控制模型建立自己的有界搜索空间，并在 frozen working spec 中保存最终值、单位、边界来源和验证结果。时间、距离、速度、比例与数量必须显式声明单位；embedded QTE 的父层分数、生命和长期胜负标为 `parent_owned`。

## 参数如何从本局派生

- 预警时长：从玩家真正看懂预警的时刻开始测，取决于信息量、目标辨识、动作语法和目标玩家，不从动画总时长倒推。
- 输入窗口：覆盖识别、设备输入、声明控制模型的旅行/路径/释放成本与合理宽容；不能用视觉速度直接推导。
- 目标尺寸与空间容差：来自目标设备、手指遮挡、画面安全区、目标形状与所声明的空间技能轴。
- cue 间隔：由前一动作的完成/恢复成本、下一预警所需读图时间和并发选择可达性派生。
- 并发上限：由“是否产生可理解取舍”决定，不以更多物体等同更难；所有强制组合必须可达。
- 反馈参数：由事件到首个可见反馈的设备实测、下一预警遮挡风险和效果收束条件决定。
- perfect 边界：用于区分 mastery，不默认成为基础通关边界；基础 success 先保证动作可达和失败可归因。

来自开源项目的默认数值、桌面键盘窗口或引擎参数都不是校准来源。

## 关系硬约束

- 任意 cue 都满足 `telegraph_visible_at <= window_open_at < deadline_at`；若有目标时刻，它位于合法输入区间内。
- 评级边界有序、无空洞、无含糊重叠；`perfect` 是合法基础命中的 mastery 子集，而不是另一条隐藏失败线。
- 时间、空间、方向、路径和选择轴分别判定；一个轴失败不能被另一轴高分平均成成功。
- 所有窗口、尺寸、速度、权重和分数必须有限；时长与可交互尺寸为正，随机权重非负且存在合法候选。
- 强制 cue 的 `unavoidable_overlap_count` 为零；连续运动从最不利合法起点也存在可达路径。
- 同一 `spec_hash + run_seed + semantic input trace` 复现相同事件序列、匹配 cue、评级和关键参数。
- 多个阶段参数可以一起变化，但每项都要服务同一个明确的玩家行为变化或可读性补偿；相邻阶段不能只有数值变化而没有 `phase fingerprint` 变化。

## 判定与评分

保留带符号时机误差：

```text
signed_error = input_at - target_at
timing_distance = abs(signed_error)
```

结果同时记录 `early / late / exact`、匹配 cue 和失败轴。空间或路径误差按当前游戏声明的容差归一化；不得把不同必需轴先平均再判成功。

基础 success、mastery grade、bonus 和长期奖励分层：

- 一个 cue 只提交一次 verdict 和一次账本变更。
- 分数公式、连击上限与失败代价属于当前游戏，不在 Skill 给默认常数。
- 高风险 bonus 必须在行动前可理解、可拒绝或保留安全路径；奖励单独计算，避免多个 modifier 叠加漏洞。
- 前期失误是否可追回由目标体验决定并通过模拟与试玩验证，不能从统一 combo 公式推断。

## 离线仿真与属性测试

优化器只用于离线；运行时不依赖 Optuna/Nevergrad。搜索空间、硬约束、运行预算、停止条件和留出验证 seed 都由当前参数维度、随机方差和可用计算预算派生并记录，不能把一个固定 seed 数量当作所有游戏的充分样本。

合成策略至少覆盖实际存在的行为风险：无输入、提前占位、随机输入、不同反应/空间误差、帧抖动、误触和最不利合法起点。每组候选验证：

- 每个 cue 恰好结算一次，结果与账本为有限值。
- 参数始终位于本游戏声明的边界。
- 暂停、恢复、后台和时钟校正不造成时间倒流或输入泄漏。
- 放宽成功条件时，同一输入轨迹下原本成功的结果不能变失败。
- 最早合法 cue、最近合法 cue或显式优先级的匹配策略按规格执行，后出现 cue 不抢输入。
- 无输入、提前占位和随机输入不能取得最高评级或稳定完成。
- 失败保存 `run_seed + shrink path` 或等价最小反例，可精确重放。

属性测试证明安全性与一致性，不证明好玩。自动优化只给候选，最终参数必须经过真人浏览器试玩。

## 遥测合同

遥测异步、可丢弃、失败静默，不影响判定或帧循环。

- Counter 记录尝试、cue 暴露、结果、重玩和 pattern 使用。
- Histogram 记录反应时间、signed error、空间/路径误差、动作完成成本、局长和帧时。
- 按阶段、pattern、控制模型和结果查看与样本规模匹配的分位数、离散度和失败原因；禁止只看平均数或在样本不足时自动调参。
- 指标标签只用低基数、非身份字段；不把用户 ID、精确设备标识或原始输入轨迹放入标签。

## Verify：数值门禁

- 冻结规格、运行时、模拟和测试读取的参数摘要一致；不存在模板默认常数回流。
- 每个最终参数有单位、来源、状态和验证信号；无 open 参数进入 coder。
- 覆盖开窗、目标时刻、评级边界、截止和边界外输入，并检查 Early/Late 归属。
- 属性测试保存运行预算、seed 与最小反例；QA seed 可复现，正式 runtime variation policy 另行验证。
- 逐阶段比较数值 diff 与 `phase fingerprint`：多参数变化有共同的行为理由和补偿，纯数值变难标为 review。
- 样本结论附样本规模与不确定性；miss 原因不能笼统写成“操作失败”。

把结果写入 `S_DIFFICULTY、S_FAILURE_TRACE、S_ACTION_FEEL、S_PHASE_VARIETY`。负窗口、NaN、无解节点、重复结算、输入抢占或不可复现时，同时让对应硬 Gate 失败。

## 禁止照搬

- 不把 Optuna、Nevergrad、fast-check、rot.js 或 OpenTelemetry 整包作为生产 H5 默认依赖。
- 不复制任何来源项目或旧模板中的毫秒、速度、尺寸、概率、分数、粒子数量和测试轮数。
- 小样本统计不自动决定发布；优化器会钻目标函数漏洞，必须保留硬约束、留出验证和人工复核。
- 统计优化与通关率不能替代真人操作感和好玩性证据。
