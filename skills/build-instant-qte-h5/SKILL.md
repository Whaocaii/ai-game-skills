---
name: build-instant-qte-h5
description: "把题材直接构建成好玩、有真实操作感并经过浏览器试玩验收的移动端瞬时反应 QTE H5，贯穿创意规格、逐游戏数值校准、既有 JSON Schema 交接、coder 实现、静态检查、反自动成功测试、浏览器试玩、缺陷修复和归档交付。用于用户要求生成、实现、试玩或交付完整 QTE H5，而不是只要创意方案时；也可在拆分式管线中作为同一规则包注入 orchestrator、创意、coder 和 QA 阶段。默认不修改既有 coder 接口。 Build and validate mobile HTML5 quick-time event (QTE) games with real player input and browser playtest evidence."
---

# 构建瞬时反应 QTE H5 整链路

Skill revision：`1.2.0`。创意模板仍为 `qte.instant_intercept@1.0.0`，并逐字保留原 `generation_rules.md` 的题材转译与 QTE 生命周期；fallback Authoring Schema 升为 `1.1.0`，管线报告升为 `1.2.0`，新增逐游戏校准、真实控制模型、反自动成功与可玩性证据。

把“可试玩交付”视为默认终点。用户要求完整 H5 时，创意 JSON、实现计划和源码都只是中间产物；未完成浏览器验收前，不得宣称完成或停在创意阶段。

默认使用单 Agent 完成全链路。除非调用方明确授权，否则不要调用子 Agent；不要让 Agent 数量成为 Skill 对照实验的额外变量。

## 读取参考文件

始终先阅读：

- [references/pipeline-stages.md](references/pipeline-stages.md)：阶段路由、Schema 保持和交接方式。
- [references/generation_rules.md](references/generation_rules.md)：与旧版模板逐字一致的题材转译、子型、生命周期和生成基线。
- [references/fun-action-patterns.md](references/fun-action-patterns.md)：高星源码抽象出的真实控制模型、动作句法、反自动成功、高潮、恢复、风险收益与重玩规则。它与 generation rules 一起构成创意冻结前的必读合同。
- [references/fun-action-sources.json](references/fun-action-sources.json)：上述来源的机器可读快照，用于审计 Stars、许可证、归档状态、固定 commit 与抽象用途；不作为代码依赖。

调用方没有创意 Schema 时，使用 [references/authoring.schema.json](references/authoring.schema.json) 作为内部 fallback，并参考 [references/authoring.template.json](references/authoring.template.json)；调用方已有 Schema 时不得换成 fallback。

兼容裁决：`generation_rules.md` 中“输出 Authoring Schema”的要求只适用于调用方没有既有 Schema 的 fallback 情况；一旦调用方提供 Schema，以保持其键、层级和类型为最高优先级。旧规则中的“一个主变量”指教学阶段一次只引入一个新的玩家需求，不限制为实现同一个可感知行为变化而共同校准多个相关参数。

`authoring.template.json` 只演示字段关系，不是默认玩法。开始 author/full_run 时必须按题材的原生动作重新选择控制模型、action pattern 与阶段结构；不得因为示例出现拖拽、拦截、优先级或四段式结构就照搬。具体玩法数值也不得从示例或报告示例复制。

进入创意与关卡冻结阶段时，再阅读：

- [references/level-design-patterns.md](references/level-design-patterns.md)：节奏拓扑、phase fingerprint、主动恢复、可达性、运行时随机与投影。
- [references/numeric-design-patterns.md](references/numeric-design-patterns.md)：逐游戏校准、唯一 BalanceProfile、判定轴、评分、仿真、属性测试与遥测；不提供全局玩法常数。
- [references/game-feel-patterns.md](references/game-feel-patterns.md)：从 verdict 到按压、hit-stop、震动、粒子、降级与复位的反馈 recipe。

进入实现阶段时，再阅读：

- [references/implementation-contract.md](references/implementation-contract.md)：coder 的状态、时钟、输入和资源合同。
- 再次读取 [references/fun-action-patterns.md](references/fun-action-patterns.md) 的 Implement 部分，确保声明的动作成本在运行时真实存在。
- [references/open-source-patterns.md](references/open-source-patterns.md)：七个高星开源项目中经过许可证核验的可复用模式与禁用项。
- 直接以 `implement` 启动时也必须读取 [references/level-design-patterns.md](references/level-design-patterns.md) 的 Implement 部分和 [references/numeric-design-patterns.md](references/numeric-design-patterns.md) 的 BalanceProfile、判定与属性测试部分。
- 再次读取 [references/game-feel-patterns.md](references/game-feel-patterns.md)，按冻结 recipe 实现单一反馈控制器。

进入静态检查、浏览器测试或交付阶段时，读取 [references/acceptance-contract.md](references/acceptance-contract.md)，并必须读取上述可玩性、关卡、数值与手感文件的 `Verify` 部分以及 [references/open-source-patterns.md](references/open-source-patterns.md) 的移动验收规则。

需要生成验收报告时，使用 [references/pipeline-report.schema.json](references/pipeline-report.schema.json)；仅把 [references/example-pipeline-report.json](references/example-pipeline-report.json) 当作结构示例，不得照抄结果。

## 选择运行模式

- `full_run`：用户要求生成、实现、完成、试玩或交付独立 H5 时默认选择。依次完成创意、实现、静态检查、浏览器测试、修复和归档。
- `author`：只有调用方明确只要方案、创意或上游 JSON 时才选择。保持调用方 Schema，不写游戏代码。
- `implement`：已有上游方案或项目，当前任务明确要求实现时选择。读取既有事实并构建，不重做已锁定创意。
- `verify`：已有可运行构建，当前任务只要求验收、复测或出报告时选择。不要擅自改代码；只有调用方同时要求修复时才修改。

无法确认时，用户说“完整游戏”“可试玩”或“测完整链路”即选择 `full_run`。

## 执行 full_run

1. 检查工作区、既有项目、调用方 Schema、coder 约定和用户未提交改动；保留现有技术栈与接口。
2. 生成调用方业务创意规格。若调用方有固定 JSON Schema，严格保持其键、层级和类型；若没有，使用本 Skill 的 fallback Authoring Schema。fallback 输出必须运行 `scripts/validate_authoring_spec.py SPEC --require-ready`；`decision_status.open` 非空、校准参数仍为 `open/null`、参数或 pattern 引用断裂时不得进入 coder。调用方已有 Schema 时把同等未决策写进 working spec，不改其接口。
3. 在业务规格旁冻结一个内部 working spec，记录业务规格原始摘要、action patterns、真实控制模型、反自动成功策略、节奏拓扑、phase fingerprints、逐游戏校准的 BalanceProfile、feedback recipe、QA/runtime seed 策略、所有影响胜负/时长/顺序/分数/动作成本的假设与 open decisions。多个参数可以共同服务同一行为变化，但必须逐项说明作用和可读性补偿；不能把纯数值恶化写成玩法阶段。`spec_hash` 计算 working spec 原始字节，`schema_hash` 计算调用方 Schema 或 fallback Schema 原始字节。不得把内部 working spec 包装进业务 JSON，也不得修改 coder 接口。
4. 从上游方案提取只读实现事实，建立唯一运行时真值。把创作关卡投影成精简 Runtime LevelSpec；判定层只读同一 BalanceProfile；反馈层只消费已提交结果。距离或路径是技能轴时实现真实移动/拖拽成本，瞬时选区不得用距离伪造难度。按实现合同完成开始、教学、非数值变化、主动恢复、高潮组合、结算和重玩闭环。
5. 使用 Skill 目录中的 `scripts/check_h5_delivery.py` 检查静态包体并保存机器可读输出。错误必须修复；每条警告必须汇总到带证据的 warning/review issue，必要时同时关联浏览器 Gate。静态修复完成后用 `scripts/hash_artifact.py --directory` 计算 `build_hash`。
6. 通过本地 HTTP 启动实际入口，在 390×844、`hasTouch: true` 的移动环境中完成黑盒试玩；检查控制台、网络失败、关键分支、边界时刻、重复输入、超时、结算、重玩和截图证据。QA 固定 run seed 复测，同时按正式 runtime policy 覆盖不同 run seed；执行无输入、提前占位、随机输入和瞬移检查，验证阶段 fingerprint、高潮组合、关卡可达性、数值来源与边界、反馈复位和 reduced-motion 降级。真人试玩记录预判、纠正、险胜和重玩意愿，不能用通关率或模拟器代理好玩性。
7. 硬门槛失败时修复并重测。默认最多进行三轮“定位 → 最小修复 → 静态检查 → 重算 build_hash → 完整浏览器复测”；不要用改低验收标准的方式制造通过。
8. 把证据放在 build 目录外。创建只包含完整运行目录的 `.tar.gz` 或 `.zip`，验证无路径逃逸/链接成员且与 build 逐文件一致；安全解包后通过 HTTP 复测同一入口，完成 `H_ARCHIVE`。
9. 在 build 与归档之外生成 `qte-pipeline-report.json`。使用绝对 Skill 脚本路径运行 `validate_pipeline_report.py REPORT --artifact-root RUN_ROOT --require-passed`。
10. 只有 `full_run` 报告返回 `deliverable: true` 后，才交付可运行目录、压缩包、启动方式和验收摘要。`author / implement / verify` 只认 `mode_passed: true`，不得称为完整游戏交付。若最终为 failed/blocked，去掉 `--require-passed` 只验证报告能否诚实表达失败，并明确它不是成功交付。

## 不变量

- 不修改既有 coder 的调用接口；通过 Skill 阶段指令和原 Schema 内已有字段传递规则。
- 不让渲染动画、CSS 尺寸或定时器回调成为胜负真值。
- 一个 cue 只能结算一次；输入与超时必须经过同一结算入口。
- 同一 `spec_hash + run_seed + 语义输入轨迹` 必须复现同一关卡事件序列；随机约束失败时回退到审核模板。
- 策划、运行时、模拟与 QA 读取同一 BalanceProfile；不得另藏魔法阈值。
- Skill 不提供统一毫秒、速度、尺寸、倍率、数量、概率、分数或特效预算；实际值必须由当前游戏的控制成本、设备、目标玩家、父合同和试玩校准后写入 frozen working spec。
- 无输入、提前占位和随机输入不能取得最高评级或稳定完成；若距离是难度，权威运动不得瞬移。
- 相邻阶段必须改变玩家问题或 pattern 关系；高潮组合已学技能，恢复降低负荷但不形成纯等待。
- QA 固定 seed 与正式运行变化策略分离；除非明确设计为共同挑战或背板技能，普通正式对局不永久固定同一序列。
- hit-stop、震动、补间和粒子只属于表现层；切换 cue、场景或重玩时可取消并归位。
- 关键资源失败时不得白屏或卡死；视觉反馈必须能独立表达逻辑结果。
- 不用 `file://` 代替真实 HTTP 运行验证。
- 不以“源码已生成”代替“游戏已启动并完成关键路径试玩”。
- 不隐藏失败。无法完成硬门槛时，交付状态必须为 `failed` 或 `blocked`，并提供证据。
- 不把报告、截图、日志或归档放进 build 目录；`build_hash` 只覆盖排序后的运行文件，避免自引用。
- 不把 `valid: true` 的失败报告或局部模式的 `mode_passed: true` 误称为完整交付；完整成功门禁只认 full_run 的 `deliverable: true`。

## 分阶段管线注入

如果创意、coder、QA 是不同 Agent，仅把 Skill 挂到创意阶段不会影响后续实现。应选择以下一种方式：

- 在顶层 orchestrator 显式调用 `$build-instant-qte-h5`，让它持有整条链路直到交付。
- 在每个阶段注入同一个 Skill，并由管线侧分别声明 `author`、`implement`、`verify` 模式；用户原始 Prompt 保持不变。

不得把阶段控制文字混入用户对照 Prompt，否则会污染 A/B 测试。

## 最终回复

先给可试玩结果，再给简短验收结论。只链接用户可访问的最终目录、归档和报告。除非用户要求，不要展示内部创意 JSON、调试日志或中间修复版本。
