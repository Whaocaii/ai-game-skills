# 高星开源源码抽象

这是一份实现与验收规则来源，不是依赖清单。只抽象架构和测试模式，不复制第三方实现；现有项目技术栈优先。Stars 为 2026-07-24 17:40（Asia/Shanghai）的 GitHub API 快照，会随时间变化。

## 已核验参考集

| 仓库 | Stars | 许可证 | 在本 Skill 中承担的参考角色 |
|---|---:|---|---|
| [phaserjs/phaser](https://github.com/phaserjs/phaser) | 40,016 | MIT | 游戏循环、时间步、输入坐标归一化 |
| [pixijs/pixijs](https://github.com/pixijs/pixijs) | 47,882 | MIT | 原始时间与动画 delta 分离、Pointer 生命周期 |
| [straker/kontra](https://github.com/straker/kontra) | 1,067 | MIT | 轻量固定步长循环、Canvas 坐标换算 |
| [kaplayjs/kaplay](https://github.com/kaplayjs/kaplay) | 1,758 | MIT | 输入边沿态、分阶段循环、可见性恢复 |
| [hammerjs/hammer.js](https://github.com/hammerjs/hammer.js) | 24,352 | MIT | 手势特征、识别器竞争和阈值配置；源码较旧，只学模式 |
| [goldfire/howler.js](https://github.com/goldfire/howler.js) | 25,322 | MIT | 移动端音频解锁、失败降级和音效池 |
| [microsoft/playwright](https://github.com/microsoft/playwright) | 93,361 | Apache-2.0 | 触摸上下文、移动视口、跨浏览器自动化 |

[replit/kaboom](https://github.com/replit/kaboom) 有 2,737 Stars 和 MIT 许可证，但已归档；只把它与 KAPLAY 对照，不把它作为新项目默认依赖。

## 必须落实的共同模式

### 判定时钟与动画时钟分开

参考：

- Phaser 的 [Game step 顺序](https://github.com/phaserjs/phaser/blob/41be1e462bc600064e498cba370bfa8c5c055a22/src/core/Game.js#L454-L503) 与 [TimeStep 平滑](https://github.com/phaserjs/phaser/blob/41be1e462bc600064e498cba370bfa8c5c055a22/src/core/TimeStep.js#L558-L619)。
- PixiJS Ticker 的 [raw elapsedMS 与 capped deltaMS](https://github.com/pixijs/pixijs/blob/1d90a20c62433ba68dff78466e06ee372a5a5232/src/ticker/Ticker.ts#L643-L692)。
- Kontra 的 [固定步长 accumulator](https://github.com/straker/kontra/blob/a449fcdf3b1060c35a7cfd0e897e31c0a0e36a48/src/gameLoop.js#L74-L124)。
- KAPLAY 的 [delta 限幅与可见性处理](https://github.com/kaplayjs/kaplay/blob/804a0398fc22825de9aadd4ac07dbcf279c5fa1a/src/app/app.ts#L402-L469)。

落地规则：

- QTE 判定使用 `performance.now()`、事件时间戳和绝对 `openAt/deadlineAt`。
- 动画可使用限幅、平滑或固定步长后的 delta；它不能反向决定命中结果或反应时间。
- 页面隐藏时暂停；恢复时重建时间基线，丢弃超长 delta，避免瞬移和后台误判。
- 固定执行 `采集输入 → 更新判定状态 → 更新场景 → 渲染反馈 → 清理边沿输入`。

### 一次物理输入只生成一次语义动作

参考：

- Phaser 的 [DOM 到画布坐标转换](https://github.com/phaserjs/phaser/blob/41be1e462bc600064e498cba370bfa8c5c055a22/src/input/InputManager.js#L1020-L1052)。
- PixiJS 的 [触摸/鼠标归一化](https://github.com/pixijs/pixijs/blob/1d90a20c62433ba68dff78466e06ee372a5a5232/src/events/EventSystem.ts#L629-L730) 与 [监听注册清理](https://github.com/pixijs/pixijs/blob/1d90a20c62433ba68dff78466e06ee372a5a5232/src/events/EventSystem.ts#L803-L884)。
- Kontra 对 [Canvas CSS 尺寸、边框和 padding 的坐标换算](https://github.com/straker/kontra/blob/a449fcdf3b1060c35a7cfd0e897e31c0a0e36a48/src/pointer.js#L152-L195)。
- Hammer.js 的 [手势输入特征](https://github.com/hammerjs/hammer.js/blob/ff687ea0daa3c806b9accd2ecb1a46165ea3c00a/src/inputjs/compute-input-data.js#L24-L60) 与 [识别器竞争](https://github.com/hammerjs/hammer.js/blob/ff687ea0daa3c806b9accd2ecb1a46165ea3c00a/src/manager.js#L87-L137)。

落地规则：

- 优先用 Pointer Events；玩法层只接收 `tap/swipe/hold/drag` 等语义动作。
- 不并行绑定 `touchstart + mousedown + click`。必须按 `pointerId、cueId、sequence` 消重。
- 坐标只在输入边界归一化一次，并考虑 CSS 缩放、border、padding 和 DPR。
- 手势管线固定为 `原始 Pointer → 时间/几何特征 → 识别器 → 语义动作`；冲突与可并行关系显式声明。
- tap、hold、swipe 的时间与位移阈值属于 GameSpec，不能照搬 Hammer 默认值。

### 声音是反馈，不是胜负依赖

参考 Howler.js 的 [首次交互解锁](https://github.com/goldfire/howler.js/blob/1d3053576a860e9854645493ad6c4a72c6cc6e45/src/howler.core.js#L297-L412)、[播放与失败路径](https://github.com/goldfire/howler.js/blob/1d3053576a860e9854645493ad6c4a72c6cc6e45/src/howler.core.js#L736-L982) 和 [声音池复用](https://github.com/goldfire/howler.js/blob/1d3053576a860e9854645493ad6c4a72c6cc6e45/src/howler.core.js#L2052-L2115)。

落地规则：

- 开始按钮的可信用户手势内解锁 AudioContext；倒计时前完成短音效加载。
- 音频状态明确区分 `locked/loading/ready/failed`；失败后静音继续，并保留视觉反馈。
- 高频命中音效使用有上限的并发池；输入路径不得等待播放结束。
- 不硬编码第三方默认池大小或挂起时间；根据本局节奏设定。

### 移动验收必须真的启用触摸语义

参考 Playwright 的 [hasTouch 前提](https://github.com/microsoft/playwright/blob/f86bd78cc191f154d9db49dedf96e7ead7b7b694/packages/playwright-core/src/server/input.ts#L357-L379)、[tap 事件链测试](https://github.com/microsoft/playwright/blob/f86bd78cc191f154d9db49dedf96e7ead7b7b694/tests/library/tap.spec.ts#L20-L68) 和 [移动视口测试](https://github.com/microsoft/playwright/blob/f86bd78cc191f154d9db49dedf96e7ead7b7b694/tests/library/browsercontext-viewport-mobile.spec.ts#L34-L70)。

落地规则：

- 浏览器 context 设置 `hasTouch: true`，使用触摸或 locator tap；不能用 DOM `.click()` 冒充移动输入。
- 覆盖开窗前、精确开窗、截止前、精确截止和截止后；断言游戏状态，而不只看截图。
- 检查 touch 后兼容 mouse/click 是否导致二次结算。
- 自动化至少保留 390×844 证据；有条件再覆盖 Chromium 与 WebKit。移动模拟不能替代最终真机的音频延迟、振动、刷新率和 WebView 门禁。

## 选型边界

- 现有项目已使用 Phaser、PixiJS 或其他引擎时，沿用现有栈并实现上述不变量。
- 新的轻量短局 QTE 优先原生 Canvas/DOM、Kontra 或 KAPLAY 级别的最小运行时；实际局长由当前游戏校准，不要为“参考源码”强行引入完整引擎。
- 只有复杂手势才考虑 Hammer 类识别器；单击与简单拖拽直接使用 Pointer Events。
- PixiJS 只解决渲染与交互，不替代 QTE 状态机；Playwright 只用于测试公开 API，不导入仓库内部模块。
- 任何第三方依赖都要由项目自身记录版本与许可证；本 Skill 不捆绑上述仓库源码。
