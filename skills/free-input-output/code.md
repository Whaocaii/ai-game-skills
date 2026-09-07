# 接入控制器

先加载 `sanitize.js`，再加载控制器；穿越示例另外加载分类与校验文件。浏览器代码挂在 `globalThis.App`，Node 示例不需要安装依赖。

```js
const controller = App.createFreeInputController({
  minimumMs: 0, // 按设计配置演出时长
  timeoutMs: 8000, // 示例预算；按项目服务与体验要求调整
  getEpoch: () => state.epoch,
  getRevision: () => state.revision,
  getContext: () => buildJudgementSnapshot(state),
  request: async ({ text, context, signal }) => {
    const response = await fetch('/api/action', {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, state: context })
    });
    if (!response.ok) throw new Error('action request failed');
    return response.json();
  },
  fallback: ({ text, context }) => makeLocalResult(text, context),
  validate: (envelope, context) => validateFormatAndRules(envelope, context),
  commit: ({ envelope }) => {
    const next = computeNextState(state, envelope.result);
    // computeNextState 必须先完成全部校验与计算；下面一次替换权威状态。
    state = { ...next, revision: state.revision + 1 };
  }
});
```

以上宿主函数由项目实现。可运行的独立接线见 [examples/integration.js](examples/integration.js)。

提交时锁住按钮与回车，共享一个 Promise；Promise 完成后恢复输入。`commit` 内不能发网络请求，必须是同步原子状态提交；UI 渲染放在提交成功后。若采用多表或服务端持久化，须由宿主事务保证原子性。

重玩、换场景和销毁时调用 `controller.invalidate()` 或 `dispose()`，并更新 epoch/revision。`invalidate` 会终止本地处理并发出 AbortSignal；远程服务可能已处理请求，控制器只保证迟到响应不会在本地重复结算。

计时注入：`schedulePresentation(ms, callback)` 和 `scheduleDeadline(ms, callback)` 都必须异步排队并返回取消函数。默认使用真实时间 `setTimeout`。Framework 适配时演出可接入其缩放时钟，网络截止计时保留真实时间；适配器负责生命周期取消。零毫秒也不能同步回调。

生产接口应部署在服务端并读取环境变量中的密钥。这个仓库没有模型供应商实现、真实密钥或业务服务器地址；不要把密钥填进本例、前端构建参数、Git 配置或测试记录。
