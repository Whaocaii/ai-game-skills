# QTE 特效与手感源码抽象

本文件约束判定后的表现层：按压回馈、hit-stop、镜头震动、粒子、补间、声音与减少动态效果。它不改变 `generation_rules.md` 的胜负规则；所有表现都必须可取消、可降级、可复位。只抽象模式，不复制源码，也不强制引入第三方库。

Stars 为 2026-07-26（Asia/Shanghai）的 GitHub API 快照，会随时间变化。源码链接固定到核验时 commit。

## 已核验参考集

| 仓库 | Stars | 许可证 | 状态 | 抽象用途 |
|---|---:|---|---|---|
| [juliangarnier/anime](https://github.com/juliangarnier/anime) | 71,490 | MIT | 未归档 | 统一表现时钟、弹簧边界、暂停与复位 |
| [catdad/canvas-confetti](https://github.com/catdad/canvas-confetti) | 12,665 | ISC | 未归档 | 粒子 canvas 复用、worker、减少动态效果、reset |
| [tweenjs/tween.js](https://github.com/tweenjs/tween.js) | 10,127 | MIT（许可证正文；API 为 NOASSERTION） | 未归档 | 显式更新时间、easing、repeat/yoyo、停止语义 |
| [pixijs-userland/particle-emitter](https://github.com/pixijs-userland/particle-emitter) | 853 | MIT | 未归档 | 粒子预算、频率、生命周期、对象池和清理 |
| [rexrainbow/phaser3-rex-notes](https://github.com/rexrainbow/phaser3-rex-notes) | 1,334 | MIT | 未归档 | 震动原点、轴向、衰减和归位 |

关键证据：

- Anime.js 的[统一引擎时钟、可见性暂停与恢复](https://github.com/juliangarnier/anime/blob/2c9cf8ea00329f6768c7d7902252ed977d75ce42/src/engine/engine.js#L44-L165)和[弹簧参数限幅、静止阈值与求解上限](https://github.com/juliangarnier/anime/blob/2c9cf8ea00329f6768c7d7902252ed977d75ce42/src/easings/spring/index.js#L53-L185)。
- tween.js 的[显式时间更新、repeat、yoyo 与完成流程](https://github.com/tweenjs/tween.js/blob/20079e65f77bb2b8e52cc9d7dbed044b86e537d3/src/Tween.ts#L436-L556)和 [MIT 许可证正文](https://github.com/tweenjs/tween.js/blob/20079e65f77bb2b8e52cc9d7dbed044b86e537d3/LICENSE)。
- canvas-confetti 的[减少动态效果、canvas 复用、worker 与 reset](https://github.com/catdad/canvas-confetti/blob/20eebad51dde793070c373d594099a7ed8d96e22/src/confetti.js#L520-L720)。
- Particle Emitter 的[预算、频率与寿命配置](https://github.com/pixijs-userland/particle-emitter/blob/0fffdd9d18cabd99e5ee1d5dc94136613d5fcb04/src/Emitter.ts#L65-L175)、[对象池回收](https://github.com/pixijs-userland/particle-emitter/blob/0fffdd9d18cabd99e5ee1d5dc94136613d5fcb04/src/Emitter.ts#L397-L447)和[清理销毁](https://github.com/pixijs-userland/particle-emitter/blob/0fffdd9d18cabd99e5ee1d5dc94136613d5fcb04/src/Emitter.ts#L983-L1028)。
- Rex Shake 的[保存原点、轴向选择、常量/衰减与结束归位](https://github.com/rexrainbow/phaser3-rex-notes/blob/12d1ed131105e47515fc429ef0ba8abc93fb025f/plugins/behaviors/shake/ShakePosition.js#L1-L220)。

## 反馈事件顺序

每次输入固定经过：

`提交唯一 verdict → 落账分数/连击 → 发布 feedback event → 首个局部反馈 → 支持性反馈 → settle/reset`

- 逻辑状态先落账；动画、音频、震动 Promise 不参与成败。
- 首个可见变化在设备允许的下一次有效绘制尽快出现，实际延迟写入本游戏校准合同并以设备实测验证。
- 支持性反馈在首个局部反馈后展开，并在下一次冲突动作或预警前收束；下一 cue 不等待动画 callback。
- perfect、success、miss 使用不同 recipe；mastery 结果比基础成功更明确，但失败反馈不做庆祝式爆发。
- miss 必须指出时机、方向、目标、路径、重叠或选择中的实际失败轴，不能只做红闪。

## 双时钟与效果所有权

- 判定使用单调时钟与绝对逻辑 deadline；前台的 hit-stop、补间暂停和 presentation timeScale 永远不能延长输入窗。
- 页面隐藏遵循 `generation_rules.md`：冻结逻辑时间线；恢复时重建基线和 deadline，丢弃超长表现 delta，不能暗中消耗窗口，也不能补播漏掉的特效。
- 同一渲染帧的所有补间共享同一个 monotonic timestamp，明确 start、cancel、reset；禁止依赖隐式 auto-start。
- 每类效果只有一个 owner。连续反馈采用 replace 或 merge，不让多个控制器叠加相机 transform。
- scene、round、cue 切换以及 `visibilitychange` 都必须取消旧效果；新一轮开始前 `activeEffectCount == 0` 且根 transform 为 identity。

## 镜头震动与 hit-stop

- 只震 camera/root visual layer，不移动命中层、hitbox、Pointer 坐标或逻辑世界。
- 保存 canonical origin；每帧偏移从原点计算，使用零均值、衰减包络并限幅，完成与取消都强制归位。
- 轴向服务语义：坠落撞击偏 Y 或小幅双轴；挡刀偏冲击方向；不要无意义全屏乱抖。
- HUD 的可读信息原则上不随玩法层震动；倒计时、失败原因和重试按钮保持稳定。
- hit-stop 只冻结表现层，不能冻结事件采样或改变 verdict。shake 时长与幅度以“不遮挡下一预警、不造成输入坐标错觉、不掩盖失败原因”为边界，具体值只写入当前游戏 frozen working spec。

## 粒子与性能预算

- 粒子使用对象池，并在当前游戏声明 `maxAlive、burstCount、lifetime、spawnFrequency` 及其来源。
- 预算由目标设备的帧时、同屏玩法负荷、效果重叠和回退策略实测派生；Skill 不提供低端、常规或绝对数量上限。
- VFX delta 要限幅；后台恢复或严重掉帧时丢掉漏发批次，不用 while 循环补发整段历史粒子。
- 特效 canvas 设置 `pointer-events: none`，不得拦截玩法输入；worker、WebGL 或粒子失败时静默降级，不阻断判定和结算。
- cue、scene 和 retry 都清空发射器、回收活动粒子并释放监听；测试模式固定随机种子或关闭装饰粒子。

## 减少动态效果与反馈降级

检测 `prefers-reduced-motion: reduce`，并在系统设置变化时重读或监听 `change`：

- 关闭 camera shake、装饰粒子、大位移、弹簧过冲和表现层 hit-stop。
- 用颜色、描边、透明度、形状和结果文字表达同一 verdict；持续时间以读得懂且不阻塞下一动作来校准，不在 Skill 写统一常数。
- 音频/震动可用时作为补充，不作为唯一反馈；静音时视觉仍完整。
- 不能照搬 canvas-confetti 的 `disableForReducedMotion: false` 默认值；若使用该库必须显式启用减少动态效果。

## 每局 feedback recipe

不要从 Skill 复制统一 recipe。每个结果在 frozen working spec 中分别声明：

`local_response / supportive_channels / intensity_relation / settle_condition / cancel_path / reduced_motion_equivalent / calibration_source`

- 按下确认：只证明输入已被接收，不提前暗示成功。
- success：清晰表达命中、状态变化和下一步。
- perfect：在 success 基础上增强轮廓、节奏或荣誉反馈，但不遮挡玩法信息。
- miss：沿实际失败轴给方向性提示，避免与成功相似的爆发。

shake、hit-stop、粒子、补间、音效的具体值来自目标设备和真人试玩；若某通道没有增加辨识、因果或爽感，就删除它，而不是堆满所有通道。

## Verify：手感门禁

- 输入后下一次绘制必须出现可观察变化；逻辑落账不等待效果结束。
- perfect、success、miss 截图和事件记录可以明确区分。
- 以足以覆盖效果叠加、取消、场景退出与重试生命周期的压力序列验证相机/根节点不漂移；测试长度由本游戏效果寿命与最坏重叠派生，不写固定次数。
- reduced-motion、静音、粒子初始化失败时仍能完成全流程并看懂结果。
- 低性能或大 delta 不出现粒子补发风暴、长时间卡顿或输入丢失。
- 震动期间点击坐标和 hitbox 不随画面偏移。

把结果写入 `S_FEEDBACK` 和 `S_ACCESSIBILITY`；效果导致输入失效、重复结算或流程卡死时，同时让对应硬 Gate 失败。

## 禁止照搬

- 不把 Anime.js 或 tween.js 的 completion callback 当判定真相。
- 不照搬 canvas-confetti 默认粒子量、ticks 或减少动态效果默认值。
- 不照搬 Particle Emitter 的高粒子上限，也不在恢复后台后 catch-up 发射。
- 不照搬 Rex Shake 的默认时长/幅度，不整体 vendor 大型示例仓库。
- 不为引用源码而强制更换现有技术栈；第三方依赖由项目单独记录版本与许可证。
