# QTE 可玩性与操作感源码抽象

本文件约束“操作本身是否好玩”，不替代 `generation_rules.md` 的题材转译和 QTE 生命周期。只抽象高星开源项目的设计与实现模式，不复制源码、素材、品牌、具体判定窗或默认参数，也不强迫项目安装这些依赖。

Stars 为 2026-07-26（Asia/Shanghai）的 GitHub API 快照，会随时间变化；源码证据固定到核验时 commit。
同一快照也保存为机器可读的 [`fun-action-sources.json`](fun-action-sources.json)，供离线审计仓库、commit、许可证、归档状态和抽象用途；联网刷新应独立执行，不能把 Stars 漂移当成 Skill 失效。

## 已核验参考集

| 仓库 | Stars | 许可证与状态 | 本 Skill 抽象用途 |
|---|---:|---|---|
| [phaserjs/phaser](https://github.com/phaserjs/phaser) | 40,024 | MIT，未归档 | 事件时间戳、真实位移、镜头与判定隔离 |
| [libgdx/libgdx](https://github.com/libgdx/libgdx) | 25,254 | Apache-2.0，未归档 | 输入队列、move 合并、有时长动作 |
| [godotengine/godot](https://github.com/godotengine/godot) | 114,614 | MIT，未归档 | 输入边沿态、独立时钟、camera reset |
| [HaxeFlixel/flixel](https://github.com/HaxeFlixel/flixel) | 2,195 | MIT，未归档 | 一次性输入、tween/audio 取消与复位 |
| [NoelFB/Celeste](https://github.com/NoelFB/Celeste) | 3,980 | 仓内代码 MIT，已归档 | 宽容机制承认玩家意图而不自动成功；仅作历史参考 |
| [ppy/osu](https://github.com/ppy/osu) | 18,740 | MIT，未归档 | 分级判定、Break 节点、基础成功与 mastery/bonus 分层 |
| [stepmania/stepmania](https://github.com/stepmania/stepmania) | 2,085 | 源码 MIT，未归档 | signed timing error、Early/Late、候选 cue 归属 |
| [FunkinCrew/Funkin](https://github.com/FunkinCrew/Funkin) | 3,690 | 源码 Apache-2.0，未归档 | 连续精度、离散评级、pattern 与事件轨 |
| [Quaver/Quaver](https://github.com/Quaver/Quaver) | 789 | MPL-2.0，未归档 | 可替换判定 profile、保护基础成功边界 |
| [vittorioromeo/SSVOpenHexagon](https://github.com/vittorioromeo/SSVOpenHexagon) | 655 | AFL-3.0，未归档 | 有名字的动作句法、按移动成本安排间隔 |
| [taisei-project/taisei](https://github.com/taisei-project/taisei) | 1,591 | 源码 MIT，未归档 | tell—commit—resolve—exit 与延迟叠层高潮 |
| [00-Evan/shattered-pixel-dungeon](https://github.com/00-Evan/shattered-pixel-dungeon) | 6,358 | GPL-3.0，未归档 | shuffle-bag 防重复、约束随机、RNG 隔离 |

资源授权可能与源码不同：Funkin、Taisei、StepMania 和 Celeste 的素材不得按表中源码许可证推断。GPL、AFL、MPL 项目默认只阅读和抽象，不向 Skill 或游戏包复制实现。

## 源码证据

操作与状态：

- Phaser 的 [Pointer 事件时间、位置、速度与 reset](https://github.com/phaserjs/phaser/blob/41be1e462bc600064e498cba370bfa8c5c055a22/src/input/Pointer.js)、[有速度约束的运动](https://github.com/phaserjs/phaser/blob/41be1e462bc600064e498cba370bfa8c5c055a22/src/physics/arcade/components/Velocity.js)、[只改变 camera viewport 且可归零的 shake](https://github.com/phaserjs/phaser/blob/41be1e462bc600064e498cba370bfa8c5c055a22/src/cameras/2d/effects/Shake.js)。
- libGDX 的[带时间输入队列与冗余 move 合并](https://github.com/libgdx/libgdx/blob/9a44e78b1ee6df1dfac6d42c52d7242b522e4cc9/gdx/src/com/badlogic/gdx/InputEventQueue.java)、[有 begin/update/end/reset 的动作](https://github.com/libgdx/libgdx/blob/9a44e78b1ee6df1dfac6d42c52d7242b522e4cc9/gdx/src/com/badlogic/gdx/scenes/scene2d/actions/TemporalAction.java)与[有时长的移动](https://github.com/libgdx/libgdx/blob/9a44e78b1ee6df1dfac6d42c52d7242b522e4cc9/gdx/src/com/badlogic/gdx/scenes/scene2d/actions/MoveToAction.java)。
- Godot 的[按事件区分 pressed/just pressed/just released](https://github.com/godotengine/godot/blob/159701651ad44335691dcbd632d8074307074c7b/core/input/input.cpp)、[tween 状态清理](https://github.com/godotengine/godot/blob/159701651ad44335691dcbd632d8074307074c7b/scene/animation/tween.cpp)与 [camera smoothing reset](https://github.com/godotengine/godot/blob/159701651ad44335691dcbd632d8074307074c7b/scene/2d/camera_2d.cpp)。
- HaxeFlixel 的[输入边沿态与 reset](https://github.com/HaxeFlixel/flixel/blob/ba033b3bc743f0cf3d1c5ca5add8f8c023928cb2/flixel/input/FlxInput.hx)、[按目标取消 tween](https://github.com/HaxeFlixel/flixel/blob/ba033b3bc743f0cf3d1c5ca5add8f8c023928cb2/flixel/tweens/FlxTween.hx)与[销毁声音时取消 fade tween](https://github.com/HaxeFlixel/flixel/blob/ba033b3bc743f0cf3d1c5ca5add8f8c023928cb2/flixel/sound/FlxSound.hx)。
- Celeste 的[动作状态与宽容机制](https://github.com/NoelFB/Celeste/blob/1b0ce45c75e05649ae91b44a8bb6b196684e4352/Source/Player/Player.cs)及[动作代码说明](https://github.com/NoelFB/Celeste/blob/1b0ce45c75e05649ae91b44a8bb6b196684e4352/Source/Player/Readme.md)。

时机与输入归属：

- osu! Mania 的[有序判定窗以及速度与判定难度解耦](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game.Rulesets.Mania/Scoring/ManiaHitWindows.cs#L10-L184)。
- StepMania 的[signed timing offset 与 Early 结果](https://github.com/stepmania/stepmania/blob/21bb8dcd6c7e3782f23d5f4e01b6ee4c82cccc71/src/Player.cpp#L3174-L3184)。
- Funkin 的[连续时机得分与离散评级](https://github.com/FunkinCrew/Funkin/blob/45a0d33a5843ba33b4414e36f32ac1400030e3ee/source/funkin/play/scoring/Scoring.hx#L41-L190)和[按目标时刻排序候选 cue](https://github.com/FunkinCrew/Funkin/blob/45a0d33a5843ba33b4414e36f32ac1400030e3ee/source/funkin/play/notes/Strumline.hx#L928-L947)。
- Quaver 的[可替换判定档位与基础命中边界保护](https://github.com/Quaver/Quaver/blob/892bc8ae5dc68d1d7c38c1db31048367c7e39541/Quaver.Shared/Database/Judgements/JudgementWindowsDatabaseCache.cs#L74-L132)。

关卡语法与节奏：

- Open Hexagon 的[命名 pattern、按距离推导 delay 与显式模式结束](https://github.com/vittorioromeo/SSVOpenHexagon/blob/1e2cba71242ab149d548abdb54d3bceb92c33922/_RELEASE/Packs/base/Scripts/commonpatterns.lua)。
- Funkin 的[输入种类、长度、参数和事件轨](https://github.com/FunkinCrew/Funkin/blob/45a0d33a5843ba33b4414e36f32ac1400030e3ee/source/funkin/data/song/SongData.hx)。
- Taisei 的[入场、预警、攻击、退出及延迟叠层时间线](https://github.com/taisei-project/taisei/blob/70563e942db868be97a3c314b4ce4dac9b270d70/src/stages/stage1/timeline.c)。
- Shattered Pixel Dungeon 的[抽中过的条目降权、耗尽重置与 RNG 隔离](https://github.com/00-Evan/shattered-pixel-dungeon/blob/7b8b845a76fe76c6b7c031ae9e570852411f56db/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/Generator.java)。
- osu! 的 [Break 一等时间线节点](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game/Beatmaps/Beatmap.cs)、[基础结果与 bonus 分离](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game/Rulesets/Scoring/HitResult.cs)和[可组合、可冲突的可选规则](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game/Rulesets/Mods/Mod.cs)。

## Author：先证明动作有意义

每个核心动作都写成：

`机制 → 玩家行为 → 感受 → 可观察信号`

并额外声明：

- `player_question`：此刻玩家真正要判断什么。
- `skill_axes`：练习后能提高时机、空间、方向、选择、路径、序列、承诺或风险管理中的什么。
- `commitment`：输入后承担什么旅行、路径、方向、恢复或机会成本。
- `failure_signal`：失败如何归因，下一次可怎样修正。
- `counterplay`：玩家能预判、取舍、改线或选择安全策略的空间。

若去掉计分、文案、粒子和震动后，玩家只是在相同位置等提示再点一下，这只是可运行 cue，不是合格的核心玩法。

### 真实控制模型

先选择并冻结一种控制模型：

- `continuous_body`：输入只更新方向或目标，实体以权威速度/加速度/有时长路径移动。
- `direct_drag`：实体跟随手指，成本来自真实位移、遮挡、路径保持和释放时机。
- `discrete_select`：点击立即选择区域，没有实体旅行时间；不得再把跨区距离当难度。
- `gesture`：挑战来自方向、长度、顺序、路径或释放时机。

连续移动模式中，点击目标只能更新目标或方向，不能直接改权威位置。若设计选择瞬时选区，就从时机、辨识、目标选择或风险收益制造难度，不伪造旅行成本。

### 防止自动成功

创意阶段必须预先设计以下反例策略：无输入、提前占位、随机输入。它们不能获得最高评级或稳定完成；若提前站在目标区就会在时刻到达时自动 Perfect，说明玩家操作没有因果作用。

宽容机制只承认“接近正确的意图”。输入 buffer/grace 若启用，必须写起点、截止、消费、失效和取消条件；不能替玩家完成目标选择、位移或释放。

## Author：用动作句法组织关卡

把 cue 组织为有名字的 pattern，而不是一串独立随机事件。pattern 可表达重复、交替、反转、路径承诺、目标优先级、诱饵辨识、风险选择、旧模式回归等，但必须来自题材动作，不强行音游化。

每个阶段冻结 `phase fingerprint`：

`verb_set + sequence_shape + choice_or_risk + event_signature + recovery_role`

相邻阶段至少在一个非数值维度上改变玩家问题。只改变速度、窗口、尺寸、生成间隔或特效强度，仍是同一阶段。`generation_rules.md` 所说的“主变量”用于保持教学可读，不是禁止在高潮组合已掌握要求：

- 教学只引入当前必须学会的需求。
- 变化段改变识别、动作组合、目标关系或风险收益。
- 高潮重组已经教学的 pattern；不能首次偷渡新主操作，也不能只做全面加速。
- 恢复是显式节点：降低失败压力，同时保留奖励收取、无失败轻操作、结果呼吸或下一阶段预告，避免纯等待。
- 高风险 cue 必须预警清楚，并允许拒绝、绕开或保留安全成功路径；收益在行动前可理解。

## Implement：判定、运动与表现分离

固定顺序：

`记录原始输入 → 映射语义动作 → 更新权威运动 → 捕获判定快照 → 锁定唯一 verdict → 落账 → 发布表现事件`

- 原始输入记录事件时间、pointer ID、归一化位置与 down/move/up/cancel 生命周期。press/release 不能因掉帧丢失；连续 move 可按 pointer 合并。
- 输入匹配当前最早合法 cue；只有玩法明确声明时才改用最近目标或显式优先级。后出现目标不能抢走本属于前一 cue 的输入。
- 每次结果保留 `matched_cue_id、signed_error、early/late/exact、failure_axis`。多个评级使用同一 profile 和明确边界。
- 动画速度、内容密度与判定容错是独立轴。提高视觉速度不能顺带压缩全部成功边界。
- camera、shake、tween、粒子、音频和 hit-stop 不改变 world position、hitbox、pointer mapping 或 deadline。
- retry、scene exit、visibility change、下一结果覆盖旧结果时，统一取消 gesture、buffer、tween、camera offset、audio fade、定时回调和粒子，并恢复 canonical state。

## 数值只从本局校准产生

Skill 不提供统一毫秒、速度、尺寸、倍率、数量、概率或粒子预算。每个实际游戏仍必须在 frozen working spec 中写最终值、单位和来源，但值只能来自：

- 题材预警的信息量与可读时刻。
- 声明控制模型的识别、旅行、路径或释放成本。
- 目标设备的输入、帧时、音频和渲染实测。
- 目标玩家的反应、误差和失败原因分布。
- 父玩法已锁定的合同。

每个参数记录 `status / value / unit / scope / source / validation_signal`。模板中的 `open + null` 不是运行时默认值；未校准就阻断 coder。具体值不得从本文件源码链接里的常量复制。

## 随机与重玩

- QA 使用固定 `run_seed` 复现问题；正式普通对局默认生成新的 `run_seed` 并记录到结果。
- 共享挑战、每日挑战或竞赛可固定共同 seed，但要声明背板/记忆是有意技能。
- 随机单位是经过审核的 pattern chunk；先过滤不可达、重复、冲突和不合阶段目标的候选，再做加权选择。
- 使用 shuffle-bag、近期降权或冷却避免短局连续重复；主线教学与收束节点保持受控。
- 玩法序列 RNG 与装饰/粒子 RNG 隔离。相同 `spec + run_seed + semantic input trace` 必须复现；不同正式 run seed 应产生可感知但公平的变化。

## Verify：好玩性不能由通关率代理

浏览器验证必须同时给结构化行为证据与真人试玩观察：

- `H_ACTION_MEANING`：无输入、提前占位和随机输入不能取得最高评级或稳定完成；距离难度没有使用瞬移。
- `S_ACTION_FEEL`：核心动作存在可观察的技能轴、承诺成本与失败归因；第二局玩家能主动修正。
- `S_PHASE_VARIETY`：相邻阶段 fingerprint 存在非数值变化；恢复不是空等。
- `S_CLIMAX`：高潮组合已学 pattern，并改变玩家策略；不是只缩短窗口或间隔。
- `S_REPLAY`：QA seed 可复现；正式运行策略不会无意中永久固定同一序列；随机序列没有短期连刷。
- `S_FEEDBACK`：相同输入轨迹在关闭特效、reduced-motion 与不同渲染条件下 verdict 一致；结果反馈不遮挡下一预警。

合成玩家、seed sweep 和属性测试用于发现无解、边界和重复问题，不能单独证明好玩。试玩记录至少说明玩家何时预判、何时纠正、哪一刻形成险胜、为什么愿意或不愿意再来一局。

## 禁止照搬

- 不复制源项目源码、函数名、谱面格式、角色、音乐、评级文案、关卡几何或资源。
- 不把 osu!/StepMania/Funkin 的桌面键盘窗口套到移动触控，也不把 QTE 强行变成轨道音游。
- 不照搬 Celeste 的状态机或 Godot/Phaser/libGDX/HaxeFlixel 的默认速度、buffer、shake、easing、camera 参数。
- 不把 GPL/AFL/MPL 项目变成运行依赖；需要代码时按当前项目许可证重新设计最小实现。
