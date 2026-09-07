# AI Game Skills

**作者与维护者：Whaocaii** · **MIT License** · **版本：0.2.0**

面向 AI 辅助游戏设计与开发的个人 Skill 库。把游戏任务整理成 Agent 可以执行的输入约定、判断步骤、交付要求和检查方法，持续积累数值、系统、交互与表现方面的工作流。

当前提供 **24 个游戏 Skill**。包含 24 个基础工作流，由维护者主导方向，使用 AI 辅助编写与维护。编写说明见 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 适合解决什么问题

- 把“太难”“没反馈”“成长慢”等感受转换成可检查的设计问题。
- 为冒险、卡牌、刷宝、幸存者、塔防等玩法建立数值思路与对照实验。
- 定义背包、体力、时间和转场的状态、边界与恢复行为。
- 改善打击感、射击反馈、震屏、日夜表现和生存游戏 UI。
- 规划单图角色的网页动效与素材需求。

**本库提供工作流及配套校验工具。** QTE 附带规格与交付校验脚本，自由输入附带可测试的 JavaScript 控制器；本版没有随附游戏引擎、图片处理工具或模型服务。需要实现时，Agent 结合项目代码与可用工具执行对应工作流。跨引擎运行、实际生图和完整游戏交付需单独验证。

## 快速开始

需要 Git 和 Python 3.9+，安装脚本仅使用 Python 标准库。

```bash
git clone https://github.com/Whaocaii/ai-game-skills.git
cd ai-game-skills

# 看目录
python3 scripts/install.py --list

# 预览完整安装
python3 scripts/install.py all --dry-run

# 安装全部 24 个 Skill
python3 scripts/install.py all
```

默认目录为 `${CODEX_HOME}/skills`，未设置 `CODEX_HOME` 时为 `~/.codex/skills`。安装后新建 Codex 会话以发现 Skill。

只安装一个方向：

```bash
# 自动带上两个公共数值依赖
python3 scripts/install.py number-survivor-like

# 单独安装背包与体力
python3 scripts/install.py inventory-system stamina-system

# 安装 QTE 与自由输入
python3 scripts/install.py build-instant-qte-h5 free-input-output

# 先装到隔离目录试用
python3 scripts/install.py all --dest ./work/skills-preview
```

安装器遇到已存在的同名目录会在复制前停止，**不会覆盖你已经改过的 Skill**。如果安装过旧集合，请先备份并移走需要替换的同名目录，再安装新版。不要同时启用新旧同名 Skill。

手动安装时复制完整的 `skills/<名称>/`，并按 [catalog.json](catalog.json) 携带依赖。其他 Agent 可使用其支持的 Skill 目录或显式读取入口文件，工具接口需按实际环境适配。

## 怎么调用

```text
使用 $game-skill-router，诊断这款塔防游戏“升级没有感觉”的问题。
我提供录像和配置表；先确定是数值收益还是音画反馈，给出最小修改方案。
```

```text
使用 $number-survivor-like，分析这局 8 分钟游戏的升级节奏。
第 4 分钟经验掉落很多但拾取困难。区分火力不足、经验不足与路线被堵。
```

```text
使用 $inventory-system，检查满背包购买药品的逻辑。
要求整单成功或整单失败，重试不能重复扣钱；基于当前项目实现并验证。
```

可以只要求设计、只要求诊断或要求实现；任务范围由你的请求决定。提供实际规则、目标平台、已有素材和预期结果，会比只说“优化一下”更容易得到可验证的交付。

## Skill 目录

### 调度与公共数值（3 个）

| Skill | 用途 |
| --- | --- |
| [game-skill-router](skills/game-skill-router/SKILL.md) | 按当前问题选择模块，组织跨系统交付 |
| [number-orchestrator](skills/number-orchestrator/SKILL.md) | 从体验目标到参数、模型、对照实验与配置 |
| [number-shared](skills/number-shared/SKILL.md) | 单位、概率口径、分布、边界和敏感性复核 |

### 玩法领域数值（11 个）

| Skill | 关注重点 |
| --- | --- |
| [number-adventure-like](skills/number-adventure-like/SKILL.md) | 路线、检查点、恢复资源与失败代价 |
| [number-card-roguelike](skills/number-card-roguelike/SKILL.md) | 抽牌、费用、构筑选择与卡组循环 |
| [number-diablo-arpg-like](skills/number-diablo-arpg-like/SKILL.md) | 伤害、生存、装备替换与刷取效率 |
| [number-legend-like](skills/number-legend-like/SKILL.md) | 长期成长、强化、交易与经济回收 |
| [number-shmup-like](skills/number-shmup-like/SKILL.md) | 弹幕空间、火力覆盖、容错与得分 |
| [number-sim-management-like](skills/number-sim-management-like/SKILL.md) | 生产网络、库存、瓶颈与投资回报 |
| [number-survivor-like](skills/number-survivor-like/SKILL.md) | 敌群压力、经验拾取和升级反馈 |
| [number-tower-defense-like](skills/number-tower-defense-like/SKILL.md) | 路径暴露、部署预算、覆盖与波次 |
| [number-turn-card-like](skills/number-turn-card-like/SKILL.md) | 行动经济、速度、阵容与养成替换 |
| [build-instant-qte-h5](skills/build-instant-qte-h5/SKILL.md) | QTE 创意、真实操作、逐游戏数值校准、反自动成功和交付证据|
| [free-input-output](skills/free-input-output/SKILL.md) | 自由输入、结果校验、超时降级、过期响应丢弃和原子结算|

### 状态与系统（4 个）

| Skill | 关注重点 |
| --- | --- |
| [inventory-system](skills/inventory-system/SKILL.md) | 物品身份、容量、原子交易与存档 |
| [stamina-system](skills/stamina-system/SKILL.md) | 扣费时点、恢复锚点、上限与重试 |
| [day-time-system](skills/day-time-system/SKILL.md) | 模拟时间、暂停、跨日与离线推进 |
| [scene-transition](skills/scene-transition/SKILL.md) | 加载状态、输入锁、交接与失败恢复 |

### 交互与表现（6 个）

| Skill | 关注重点 |
| --- | --- |
| [day-night-cycle](skills/day-night-cycle/SKILL.md) | 视觉时段、天气叠加与夜间可读性 |
| [screen-shake-effects](skills/screen-shake-effects/SKILL.md) | 冲击偏移、叠加上限和减弱动态效果 |
| [improve-arpg-hit-feel](skills/improve-arpg-hit-feel/SKILL.md) | 近战输入、接触、受击与恢复时序 |
| [fps-feel](skills/fps-feel/SKILL.md) | 实际命中、后坐力、散布与换弹反馈 |
| [survival-ui-guidelines](skills/survival-ui-guidelines/SKILL.md) | HUD、背包、制作和建造任务流 |
| [build-pseudo-live2d-character](skills/build-pseudo-live2d-character/SKILL.md) | 单图角色分层、锚点、遮挡与动作降级 |


```text
使用 $build-instant-qte-h5，把接住飞来物的题材做成移动端 QTE。
要求真实操作、失败与重试，并按实际试玩证据验收。

使用 $free-input-output，为当前游戏接入玩家自由输入。
保留项目现有结果 Schema，覆盖请求超时、重复点击与重开后的旧响应。
```

自由输入示例使用本地降级规则，可离线运行；关键词分类不等于模型理解。真实模型接入由项目服务端完成，API key 只从服务端环境读取，不进入前端、示例或仓库。见 [SECURITY.md](SECURITY.md)。

## 依赖与目录结构

```text
skills/<名称>/SKILL.md     每个 Skill 的任务入口与案例
skills/*/references/      仅在确实需要时附加参考文件
catalog.json              名称、分组与安装依赖
scripts/install.py        安装与依赖解析
scripts/validate.py       结构、依赖与文档链接检查
tests/                    仓库工具测试
CHANGELOG.md              版本变化
```

- 游戏总调度器安装时携带其余 23 个游戏模块，运行任务时只读取需要的部分。
- 每个领域数值模块依赖 `number-orchestrator` 与 `number-shared`。
- 数值总调度器只自动安装公共计算模块；单独使用它时，按任务安装所需领域 Skill。
- 原本地系统配置不随仓库安装而修改，图片和引擎工具由实际项目提供。

## 检查与持续更新

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s skills/build-instant-qte-h5/tests -v
# 自由输入示例与测试需要 Node.js 18+
node --test skills/free-input-output/tests/test-free-input.cjs
node skills/free-input-output/examples/integration.js
```

这些检查覆盖仓库完整性、安装行为、QTE 校验器及自由输入控制器，不代替 Skill 的实际任务评测。当前验证状态见 [VALIDATION.md](VALIDATION.md)。

后续会继续积累 AI 游戏相关 Skill。新增模块应来自明确的问题与使用案例；先写清能力边界，再加入脚本或模板，避免只有泛化提示词。贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可与引用

本仓库内容采用 [MIT License](LICENSE)。使用、修改和分发时保留许可证要求的版权与许可声明。

引用具体版本时可使用：

```text
Whaocaii. AI Game Skills.
https://github.com/Whaocaii/ai-game-skills
Skill: <名称>
Version: <tag 或完整 commit SHA>
```

欢迎通过 Issue 提交真实案例，通过 PR 改进现有流程或增加新的 AI 游戏能力。
