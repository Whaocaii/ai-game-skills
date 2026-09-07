# 行动与结算合同

## 通用控制器

控制器不规定游戏数值字段。`validate(envelope, context)` 必须覆盖响应格式与当前场景的合法性；它返回严格的 `true` 才能结算。

每次提交记录：本地 actionId、清洗后的 text、JSON 状态快照、epoch 与 revision。epoch 代表重玩/会话代次，revision 代表权威游戏状态版本。任何需要使在途决策失效的修改都应改变相应版本。

同一个控制器的在途重复提交返回同一个 Promise。跨页面、跨进程和服务端重复请求不在此保证内；涉及持久资源时服务端还需独立的幂等键和事务。

返回状态：

- `committed`：同步提交函数执行完成，来源为 `remote` 或 `local`。
- `ignored`：被取消、重玩或状态版本改变，没有提交。
- `disposed`：控制器已销毁，不再处理输入。
- Promise reject：本地兜底或提交失败，调用方显示错误并恢复可操作 UI。不能据此自动重试状态修改。

## 穿越示例外壳

```json
{
  "schemaVersion": "free-input.action.v1",
  "type": "action",
  "result": {
    "verdict": "failed",
    "failureKind": "unclear",
    "summary": "还没有形成可执行的行动",
    "narration": "你停下来重新想了想。",
    "statsDelta": {"energy": 0, "warmth": 0, "sanity": 0},
    "progressDelta": 0,
    "weather": "阴天",
    "nextSituation": "路口",
    "hallucination": {"active": false}
  }
}
```

此示例使用 `effective / costly / failed` 和 0/1 格推进。失败必须停留并说明 failureKind；前进必须为非失败且 failureKind 为 none。三轴增减必须为安全整数且在调用方给定的绝对幅度范围内；还需要结合当前游戏的库存、消耗等条件进一步校验。

`assertActionEnvelope` 要求版本与任务名匹配。示例的最大文案长度属于显示约束，不是所有游戏的统一上限。

`classify-and-fallback.js` 是旧穿越案例的词表规则。原地观察、传送或请求路线是否有效由游戏规则决定；切换题材时必须重写分类和成本，不能把该词表当成语义模型或通用安全检测器。

## 隔离规则

- 请求函数拿到的是快照副本，不能直接修改权威状态。
- 远程叙述在 DOM 中用文本方式展示，不能直接作为 HTML 执行。
- 接口鉴权、服务端状态验证、计费和限流由宿主应用负责。
- 日志可保留请求 ID、耗时、结果类型和脱敏错误；不能保存或输出 API key、Authorization 头、完整环境变量或私有配置。
