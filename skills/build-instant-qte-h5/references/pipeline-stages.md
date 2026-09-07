# 整链路阶段与注入合同

## 目标

同一个 Skill 必须约束创意、实现和验收，而不是只提升创意文案。用户要求完整 H5 时，默认终点为：

`用户需求 → 创意规格 → coder 实现 → 静态检查 → HTTP 启动 → 浏览器试玩 → 修复复测 → 可试玩归档`

## 阶段路由

| 模式 | 当前输入 | 必须完成 | 可以停止的位置 |
|---|---|---|---|
| `full_run` | 用户题材或游戏需求 | 全部阶段 | 可试玩包体通过验收后 |
| `author` | 用户题材、既有 Schema | 创意方案与交接事实 | 上游合同通过后 |
| `implement` | 上游 JSON、现有项目 | 可运行实现与静态检查 | 构建可启动后 |
| `verify` | 本地可运行目录、对应冻结 working spec | 静态检查、浏览器测试与报告 | 报告生成后 |

用户说“完整游戏”“生成 H5”“直接试玩”“测完整链路”时，不得选择 `author`。

只有远程 URL 而没有本地 build/spec 时，可以做诊断性浏览器检查，但不能生成 `mode_passed: true` 的本合同报告；不得伪造 build hash、归档或 receipts。

## 数据面、控制面与证据面

- 数据面：调用方原有业务 JSON 和 Schema。Skill 不新增 wrapper 或元数据字段。
- 控制面：由 orchestrator 或阶段配置保存 `mode、skill_revision、schema_hash、spec_hash、build_hash、attempt`，不写入业务 JSON。`spec_hash` 指向内部冻结 working spec，不是只覆盖业务 JSON。
- 证据面：构建物、日志、截图和报告走工作区或调用方既有 artifact 通道。

build 目录只能含启动游戏所需文件。冻结规格、外部 Schema、截图、日志、报告和归档都放在 build 外的同一运行根目录中。

内部 working spec 至少记录：`scope、business_spec_path、business_spec_hash、schema_hash、open_decisions、action_patterns、control_model、anti_autoplay、level_plan、balance_profile、feedback_recipes、replay_policy、result_affecting_assumptions`。它只属于控制/证据面；报告的 `artifacts.spec` 与三份 receipt 都绑定它的 `spec_hash`。

平台若只能向创意 Agent 注入 Prompt，且不能向 coder/QA 继续注入规则或传递证据，就无法保证整链路生效。此时必须报告能力缺口，不能宣称已经完成整链路注入。

## Schema 保持

调用方既有 JSON 是上游合同：

1. 记录原有顶层键、嵌套键、数组形状和类型。
2. 只把 QTE 规则写入最接近的玩法、互动、流程、事件、状态、反馈或 reasoning 字段。
3. 不增加 Skill 版本、运行报告、代码路径、测试结果或研究来源字段。
4. 无法进入原 Schema 的实现事实写入内部冻结 working spec，不回灌上游 JSON；报告只复述摘要，不能成为唯一真值。
5. coder 继续接收原接口中的内容；Skill 只约束解释和执行方式。

冲突优先级：

`用户本轮要求 > 调用方 Schema > 已锁定上游内容 > 现有项目约定 > Skill 默认值`

调用方没有 Schema 时，使用 Skill 内 `authoring.schema.json`；此时 `decision_status.open` 非空即阻断。调用方已有 Schema 但没有 `decision_status` 时，不新增字段，而把 open decisions 写入 working spec 并同样阻断。这样保持 `generation_rules.md` 的决策门禁语义，而不破坏外部 Schema。

fallback Authoring Spec 先运行 `scripts/validate_authoring_spec.py SPEC` 检查结构、参数状态与引用；交给 coder 前再加 `--require-ready`。模板里的 `open + null` 是待校准占位，不是运行时默认值。

## 阶段交接

### Author

先声明 `scope: standalone | embedded`。`full_run` 默认 standalone；现有父游戏内的局部 QTE 使用 embedded。两者都必须明确：

- 玩家幻想和唯一主操作。
- `危险或机会 → 预警 → 输入窗 → 动作 → 判定 → 反馈 → recovery`。
- standalone 生成足以完成教学、非数值变化、主动恢复与高潮组合的代表性 cue；数量由当前动作语法与目标局长决定，不使用 Skill 常数。embedded 至少冻结当前节点及其输入/结果事件。
- perfect、success、miss 的可观察条件。
- action pattern、真实控制模型、技能轴、动作承诺、失败归因，以及无输入/提前占位/随机输入反例。
- standalone 的学习、非数值变化、主动恢复和高潮组合；embedded 只声明父玩法分配给该节点的强度与退出条件。
- standalone 的开始、教学、玩法、结算、重玩流程；embedded 则声明进入条件、结果事件和清理/返回父玩法路径。
- standalone 从教学到终局的节奏拓扑；embedded 使用稳定节点 ID、进入/退出边和父玩法给定的并发上限。
- 带单位、状态、值、来源和验证信号的唯一 BalanceProfile；Skill 不提供默认数值，所有值按本游戏校准，评级边界无歧义。embedded 的父层分数、生命和长期胜负标为 `parent_owned`，不得由 QTE 私建。
- perfect、success、miss 的反馈 recipe，以及 reduced-motion、静音和特效失败时的等价表达。

`generation_rules.md` 是题材转译、子型和生命周期的创意基线；`fun-action-patterns.md` 是可玩性合同。关卡、数值和手感模式只把已选创意具体化，不得据此换题材或扩成另一个品类，但必须拒绝“只有包装或数值变化、没有玩家技能表达”的方案。

### Implement

先读取上游和项目，不重写创意。把上游事实归一为只读工作规格，并保留来源位置。关卡创作数据先校验 ID、引用、主路径、action pattern、控制模型、时间/空间可达性和并发，再投影为精简 Runtime LevelSpec。运行时、模拟和测试读取同一 BalanceProfile；反馈控制器只消费已提交的 verdict，所有效果可取消、可降级、可复位。距离是难度时必须存在真实旅行成本；瞬时选区不能伪称远距离更难。未校准数值、会改变胜负、时长、顺序、分数或动作成本的冲突必须阻断并报告。

### Verify

必须测试本地真实构建，不接受源码推断。先完成静态检查，再通过 HTTP 打开入口，执行关键操作，记录控制台与截图。QA 使用固定 run seed，并按正式 `runtime_variation_policy` 抽查不同 run seed；验证主路径、可达性、阶段 fingerprint、高潮组合、反自动成功、参数来源、数值边界、效果复位和 reduced-motion 降级。属性测试失败时保存可复现 seed/最小反例；真人试玩补充“何时预判、如何纠正、哪里形成险胜”的观察，不能用 seed sweep 代替好玩性。硬门槛失败时，`full_run` 进入修复循环；纯 `verify` 模式只报告，除非用户授权修复。verify 不要求归档，只有 full_run 必须通过 `H_ARCHIVE`。

### Deliver

只有 `full_run` 的完整交付至少包含：

- 可直接运行的入口文件。
- 完整运行目录。
- 可传输的归档包。
- 通过校验的 `qte-pipeline-report.json`。
- 简短启动说明。

交付顺序固定为：

`冻结规格并哈希 → 实现 → 静态检查/修复 → 计算最终 build_hash → 浏览器验收/必要时回到静态检查 → 创建归档 → 安全解包并 HTTP 复测 → 生成报告 → 报告成功门禁`

author、implement、verify 的阶段报告以 `mode_passed: true` 表示本模式完成；它们不返回完整交付意义上的 `deliverable: true`。

## 匹配凭证与失效规则

整链路完成必须同时拥有：

`author receipt(schema_hash, spec_hash) + implement receipt(schema_hash, spec_hash, build_hash) + verify receipt(schema_hash, spec_hash, build_hash)`

- 业务创意、working spec 内的关卡/数值/反馈事实或结果相关假设变化时生成新的 `spec_hash`，implement 和 verify 凭证全部失效。
- 调用方或 fallback Schema 变化时生成新的 `schema_hash`，三阶段凭证全部失效。
- 代码或资源变化时生成新的 `build_hash`，verify 凭证失效。
- 设计重放、浏览器控制台和效果清理等结构化证据同时写入 `run_id + spec_hash + build_hash + test_environment`。用 browser-run manifest 把所有硬门禁、软门禁和 design_validation 的截图/JSON 列表与文件摘要绑定本次运行，禁止任何 manifest 代理或循环自证。静态证据与当前构建重跑结果逐字段比对，防止复用旧报告。
- 只有测试环境变化时，保留规格和构建摘要，但重新执行 verify。
- `qte-pipeline-report.json` 中的三份凭证摘要不匹配时，不得标记 passed。

摘要算法：

- `spec_hash` 是内部 working spec 原始字节的 SHA-256。working spec 必须包含业务规格摘要、关卡/数值/反馈事实和影响结果的假设；`schema_hash` 是调用方或 fallback Schema 原始字节的 SHA-256。
- `build_hash` 使用 `scripts/hash_artifact.py --directory`。算法按 UTF-8 POSIX 相对路径排序，依次写入域分隔、路径字节长度、路径、文件字节长度和原始内容；拒绝符号链接。
- 报告、证据和归档不得进入 build manifest，因此不会产生自引用。
- 归档必须只包含一个与 build 目录同名的顶层目录，并与当前 build 逐文件一致；链接、设备、绝对路径和 `..` 成员一律拒绝。

保持以下追踪链：

`qte/cue ID → 原 JSON 位置 → 实现模块 → 验收 Gate → 运行证据`

## 单点与多 Agent 注入

### 单点注入

把 Skill 注入能控制工作区、coder 和浏览器验收的顶层 orchestrator。它在同一任务内完成 full_run，不把中间 JSON 当最终答案。

### 分阶段注入

如果各阶段隔离，在管线配置层将同一个 Skill 注入：

- 创意 Agent：`author`
- coder Agent：`implement`
- QA Agent：`verify`

阶段参数属于系统或管线配置，不属于用户 Prompt。各阶段使用相同 Skill 版本，避免规则漂移。

## 失败与重试

- 结构或核心规则冲突：阻断，不让 coder 猜。
- 静态错误：修复后重跑静态检查。
- 浏览器硬门槛失败：定位责任子系统，最小修复并完整重测。
- 默认最多三轮修复；三轮后仍失败，报告为 `failed`。
- 缺少权限、运行环境或必须由用户决定的规则时，报告为 `blocked`，不得伪造通过。
- 非关键音频或美术缺失且降级验证通过，可以带 warning 交付。
