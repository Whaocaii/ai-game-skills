# H5 端到端验收合同

所有“通过”必须来自实际构建和浏览器证据，不得只靠阅读源码推断。

本地 validator 证明的是文件、摘要、字段与 Gate 的一致性，不是密码学意义的“浏览器来源证明”；执行方仍必须让浏览器 runner 直接采集 trace/截图/控制台，禁止手填通过证据。`tests/` 中的合成 PNG/JSON 仅用于验证校验器的正反例合同，不代表真实游戏已试玩。

## 静态硬门槛

先解析当前 `SKILL.md` 所在目录为 `QTE_SKILL_DIR`，再运行；不要假设当前目录就是 Skill 根目录：

```bash
python3 "$QTE_SKILL_DIR/scripts/check_h5_delivery.py" path/to/build > path/to/evidence/static-check.json
```

必须满足：

- 构建目录和 `index.html` 存在且非空。
- HTML 声明移动端 viewport。
- 入口引用的本地脚本、样式、图片和媒体文件存在，且没有越出包体目录。
- 禁止 `<base href>` 改写运行基址；检查 `srcset`、CSS `url()/@import` 与静态 ES module import 的递归依赖。
- 关键资源路径不是 `file://`。
- 包体可通过普通静态 HTTP 服务启动。

静态检查只要存在 warning，就必须建立至少一个带复核证据的 warning/review issue；不能只把 warning 文本留在静态输出里仍宣称无已知问题。

静态分析不能可靠覆盖运行时拼接 URL 和所有 import map。浏览器测试必须记录失败请求，关键路径出现 404 或加载异常时 `H_CONSOLE` 不得通过。

## 浏览器硬门槛

至少验证以下 Gate，并记录证据：

| Gate | 验收内容 |
|---|---|
| `H_BOOT` | HTTP 打开后出现第一个可操作界面，无白屏 |
| `H_FLOW` | scope 对应的完整闭环可达 |
| `H_INPUT` | `hasTouch: true` 的移动视口中 Pointer/触摸主操作有效，不触发页面滚动或兼容点击二次计分 |
| `H_ACTION_MEANING` | 无输入、提前占位和随机输入不能取得最高评级或稳定完成；声明的距离/路径难度没有用瞬移伪造 |
| `H_SUCCESS` | 至少一次 success 或 perfect 正确结算并反馈 |
| `H_MISS` | 不操作或错误操作能进入 miss，并说明失败原因 |
| `H_RESOLVE_ONCE` | 重复输入、输入与超时竞争不会重复加分或改写结果 |
| `H_RECOVERY` | 每个结果后能进入下一 cue 或结算，不会卡死 |
| `H_RETRY` | scope 对应的再次进入会清空旧状态、监听和定时任务 |
| `H_CONSOLE` | 关键路径无未捕获异常和资源 404 |
| `H_MOBILE` | 至少在 390×844 视口中无遮挡、无横向溢出 |
| `H_RELOAD` | HTTP 刷新宿主页后仍能重新进入相同 QTE 路径 |
| `H_ARCHIVE` | 仅 full_run/deliver：解压归档后使用同一入口可以启动 |

scope 解释：

- standalone：`H_FLOW` 为开始 → 教学 → 正式玩法 → 结算 → 重玩；`H_RETRY` 为结算页重开。
- embedded：`H_FLOW` 为父玩法进入 → QTE cue → 唯一 `resultEvent` → 清理并返回父玩法；`H_RETRY` 为父玩法再次进入同一节点且无旧状态。embedded 不要求私建开始页、教学页、结算页或长期分数。

不要用 DOM `.click()` 冒充触摸，也不要用 DOM 断言替代 Canvas/WebGL 截图。至少保留开始/教学、活跃 cue、成功或 perfect、miss、结算五类不同的视觉证据。

## 软门槛

软门槛需要试玩判断，失败不一定阻断，但必须进入报告：

- `S_FIRST_ACTION_CLARITY`：首次强制动作前，玩家已经知道观察什么、做什么和何时开始；等待时长本身不能代理“已理解”。
- `S_TELEGRAPH`：预警先于开窗，目标和轨迹可读。
- `S_ACTION_FEEL`：核心动作有可观察的技能轴、承诺成本与失败归因；第二局玩家能主动修正操作，不只是背序列。
- `S_PHASE_VARIETY`：相邻阶段的动作、序列、选择/风险、事件特征或恢复职责存在非数值变化；恢复不是空等。
- `S_CLIMAX`：standalone 高潮重组已教学 pattern 并改变玩家策略，不是只把窗口、间隔、速度或尺寸全面恶化；embedded 按父玩法声明评估或标记不适用。
- `S_FEEDBACK`：输入后下一次绘制即看到状态变化；perfect、success、miss 可区分，强度有序；连续反馈、scope 退出和再次进入后无震动、补间或粒子残留。
- `S_FAILURE_TRACE`：玩家知道下一次要修正时机、方向、路径、目标或重叠；遥测不把不同原因合并成笼统失败。
- `S_DIFFICULTY`：standalone 有教学到终局的完整节奏拓扑，embedded 有合法进入/退出边；阶段参数来自当前游戏校准，多参数变化有共同的行为理由与可读性补偿；QA seed 可复现，强制操作可达且没有不可处理并发。
- `S_HUD`：HUD 不遮挡危险来源、目标、轨迹或接取区域。
- `S_ACCESSIBILITY`：静音、色觉差异或 `prefers-reduced-motion: reduce` 时仍能理解同一结果；关闭 shake、粒子和大位移不影响流程。
- `S_REPLAY`：standalone 结算说明表现并提供重试；embedded 能安全返回父玩法并再次进入。QA 固定 seed 与正式 runtime variation policy 分离，除非明确把共同 seed/背板作为玩法，否则普通正式对局不永久固定同一序列。

浏览器模式通过时必须填写：

- `design_validation`：scope、逐阶段参数变化及其行为理由/补偿、QA seed 重放或无随机声明、可达性、三种结果视觉、scope 退出/再次进入后的效果复位和 reduced-motion 实跑。
- `play_validation`：action pattern、三种反例策略的浏览器试跑、输入/权威位置轨迹、阶段 fingerprint、高潮组合、QA/runtime seed 策略与连续试玩观察。`S_ACTION_FEEL` 只有真人观察时才能标为 `passed`；只有 Agent 观察时标为 `review` 并关联 issue。

`S_DIFFICULTY` 引用阶段参数 diff、seed 重放与可达性证据；`H_ACTION_MEANING、S_ACTION_FEEL、S_PHASE_VARIETY、S_CLIMAX、S_REPLAY` 引用对应 play evidence；`S_FEEDBACK` 至少引用三种结果图片和一份清理记录。属性测试失败时保存 seed 与最小反例或等价复现凭证。

## 结构化证据最小形状

- 静态证据直接保存 `check_h5_delivery.py` 输出：`valid、errors、warnings、summary.root、summary.entrypoint、summary.file_count、summary.total_bytes`。成功门禁会对当前 `build_dir/entrypoint` 重跑检查，并要求 JSON 与重跑结果完全一致；旧构建证据不能复用。报告每条 warning 通过 `warning_reviews[]` 的 index、原文和 issue ID 逐条闭环。
- 下述浏览器结构化证据都要携带当前 `run_id、spec_hash、build_hash` 与完整测试环境；归档证据至少携带当前 `run_id、build_hash`。任一字段不匹配时，即使内容看似通过也要拒绝。
- `test_environment.evidence` 必须登记 `browser-run-manifest.json`。该 manifest 包含 `manifest_version: "1.0"、run_id、spec_hash、build_hash、environment、gate_results、soft_gate_results、design_evidence、evidence_hashes`；`environment` 逐字段匹配报告环境，硬/软 gate 的状态和证据列表与报告一致，`design_evidence` 覆盖设计与 play validation 的全部证据，`evidence_hashes` 不多不少地记录上述截图/JSON 的实际 SHA-256。任何带 `manifest_version` 的文件都不得出现在 gate 或 design 证据中，防止双 manifest 代理/循环自证。
- `H_INPUT / H_RESOLVE_ONCE / H_RECOVERY` 必须引用 `kind: "browser_assertions"` 的 JSON，并分别记录 Pointer/语义动作/滚动计数、竞争输入/唯一 verdict/resultEvent 计数、success/miss 后继续结论。`H_BOOT / H_FLOW / H_SUCCESS / H_MISS / H_RETRY / H_MOBILE / H_RELOAD` 各至少引用一张尺寸匹配 viewport 或 viewport×DPR 的可解码 PNG，不能用无关 JSON 或小占位图充数。
- `H_CONSOLE` JSON 至少包含 `run_id、spec_hash、build_hash、tested_at、base_url、browser、browser_version、viewport、has_touch、device_scale_factor、uncaught_errors: []、failed_requests: []`；环境字段必须与报告 `test_environment` 一致。
- 设计证据 JSON 同时包含：
  - `run_id、spec_hash、build_hash、environment`。
  - `qa_seed、input_trace_hash、sequence_hash_first、sequence_hash_replay、passed`；两次序列摘要必须相同。
  - 与报告一致的 `phase_diffs[]`，包括参数变化、行为理由与补偿。
  - `reachability.passed、checked_cases、unavoidable_overlap_count`。
- play evidence JSON 同时包含 `run_id、spec_hash、build_hash、environment`，并与报告一致地记录：
  - `kind: "browser_play_trials"`，表明证据来自浏览器试跑采集，而不是设计声明。
  - action pattern 的 ID、玩家问题、技能轴、承诺和 mastery signal。
  - 无输入、提前占位、随机输入各自的 run seed、尝试数、完成数、最高评级数、输入轨迹摘要与结果序列摘要；尝试规模由当前 working spec 的风险与置信目标决定，Skill 不给统一次数。
  - 空间控制适用时的输入路径摘要、权威位置轨迹摘要、直接位置写入次数，以及每一步是否能由冻结控制模型解释。
  - 各阶段 pattern ID、fingerprint、是否仅数值变化、恢复职责；高潮引用的 pattern 必须存在且在高潮前出现。
  - 高潮是否组合已教学 pattern、玩家行为变化和是否仅数值变化。
  - QA seed 与正式 runtime variation policy。
  - 匿名试玩 session、第一局观察、第二局主动修正、可定位的险胜/失败时刻与是否选择重玩；不能把 Agent 自测伪装成真人试玩。
- 无随机性时 seed 证据改为 `randomness: false` 与非空 `reason`。
- 效果清理 JSON 至少包含 `run_id、spec_hash、build_hash、environment、verdict_before_feedback: true、active_effect_count_after_exit: 0、root_transform_identity: true、reentry_passed: true`。
- `H_ARCHIVE` JSON 至少包含 `run_id、build_hash、archive_safe、content_match、http_retest_passed`，三个结论字段均为 true。
- 视觉证据使用真实可解析的 PNG；只写扩展名、文件头、损坏压缩流或不完整扫描行不能通过。开始/教学、活跃 cue、success、miss、结算五类截图的内容 SHA-256 必须彼此不同；`perfect / success / miss` 三张结果图也必须互不相同。复制同一张空白图后改文件名不计作多份证据。

## 修复循环

1. 按 blocker、error、warning、review 排序问题。
2. 为每项记录复现步骤、玩家看到什么、责任子系统和证据。
3. 只做能解决根因的最小修改。
4. 修改后从 `H_BOOT` 开始重新跑完整关键路径，避免局部修复引入新回归。
5. 默认最多三轮。硬门槛仍失败时，最终状态不得为 passed。

## 报告与最终交付

报告、证据和归档放在 build 目录外。归档必须拒绝绝对路径、`..`、符号链接、硬链接和设备成员，并与当前 build 逐文件一致；随后安全解包，通过 HTTP 复测入口。

按照 `pipeline-report.schema.json` 生成 `qte-pipeline-report.json`。成功交付运行：

```bash
python3 "$QTE_SKILL_DIR/scripts/validate_pipeline_report.py" \
  path/to/qte-pipeline-report.json \
  --artifact-root path/to/run-root \
  --require-passed
```

所有模式成功都要求 `valid: true`、`artifacts_verified: true`、`final_status: passed`、`mode_passed: true`。只有 full_run 会进一步返回 `deliverable: true`；author、implement、verify 的局部通过不能称为完整游戏交付。结构有效的 failed/blocked 报告可以在不加 `--require-passed` 时退出 0，但这只表示失败被如实记录。

full_run 报告门禁通过后，再交付：

- 可运行目录。
- 归档包。
- 报告文件。
- 本地 HTTP 启动命令或稳定试玩 URL。

最终回复只摘要硬门槛、已知 warning 和启动方式；完整证据保留在报告与截图中。
