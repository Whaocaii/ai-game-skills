/**
 * Traversal example: local keyword rules, NOT natural-language understanding.
 * Replace classification, stats and costs for another game; constants here are example balance.
 */
(function (root) {
  "use strict";
  const App = root.App = root.App || {};

  App.FREE_INPUT_LEX = {
    progress: /前进|继续(?:走|挪|爬|移动|通过)|向前|往前|穿过|越过|绕过|通过|走过去|挪过去|爬过去|跨过|翻过|离开原地|贴着.{0,16}(?:走|挪|移动)|沿着.{0,20}(?:走|挪|移动|前进)|^(?:走|跑|冲|爬|挪|绕|穿|越|跨)$/,
    stationary: /原地|停下|休息|等待|先不走|暂时不走|不前进|观察|检查|整理|睡一会|返回|撤退|求救|待在这里/,
    injection: /忽略.{0,20}(?:指令|要求)|提示词|系统消息|开发者消息|输出代码|泄露|ignore.{0,20}(?:instruction|prompt)|system prompt|developer message/i,
    unsafe: /(?:现实|真实).{0,12}(?:路线|坐标|方位|撤离)|经纬度|GPS|海拔/i,
    impossible: /无敌|满血|数值全满|修改数值|瞬移|传送|飞过去|开挂|直接通关|召唤(?:飞机|直升机|超人)|忽略(?:规则|天气|危险)|输出提示词|泄露(?:密钥|系统)/,
    reckless: /直接冲|往前冲|向前冲|狂奔|猛跑|硬闯|闭眼|不管.{0,8}(?:风|雪|危险)|无视.{0,8}(?:风|雪|危险)|赌一把/
  };

  App.classifyLocalAction = function classifyLocalAction(action) {
    const value = String(action || "").trim();
    const lex = App.FREE_INPUT_LEX;
    const progress = lex.progress.test(value);
    const stationary = lex.stationary.test(value);
    if (lex.injection.test(value)) return "injection";
    if (lex.unsafe.test(value)) return "unsafe";
    if (progress && stationary) return "contradictory";
    if (lex.impossible.test(value)) return "impossible";
    if (lex.reckless.test(value) && progress) return "reckless";
    if (progress) return "progress";
    if (stationary) return "stationary";
    return "unclear";
  };

  App.actionPressure = function actionPressure(node, attemptsAtNode) {
    return 11 + Math.ceil(Number(node || 1) * 0.9) + Math.min(Number(attemptsAtNode) || 0, 2) * 3;
  };

  App.makeLocalActionFallback = function makeLocalActionFallback(action, ctx) {
    const kind = App.classifyLocalAction(action);
    const pressure = App.actionPressure(ctx.node, ctx.attemptsAtNode);
    const stall = Math.max(2, Math.ceil(pressure * 0.25));
    const copy = ctx.copy || {};
    let verdict = "failed";
    let failureKind = kind;
    let progressDelta = 0;
    let statsDelta;
    let summary;
    let narration;

    if (kind === "progress") {
      const firstLoss = Math.ceil((pressure + 2) / 2);
      verdict = "effective";
      failureKind = "none";
      progressDelta = 1;
      statsDelta = { energy: 2, warmth: -firstLoss, sanity: -(pressure + 2 - firstLoss) };
      summary = copy.progressSummary || "这一步还是落了下去";
      narration = copy.progressNarration || "你照着办法挪动。动作被打乱，但靴底越过了原落脚点。";
    } else if (kind === "reckless") {
      const firstLoss = Math.ceil(pressure / 2);
      verdict = "costly";
      failureKind = "none";
      progressDelta = 1;
      statsDelta = { energy: -firstLoss, warmth: -(pressure - firstLoss), sanity: 0 };
      summary = copy.recklessSummary || "你硬是冲过了这一段";
      narration = copy.recklessNarration || "脚步比判断先冲出去，最后一下仍踩住实地。";
    } else {
      const rows = {
        stationary: ["脚印停在原处", "你没有继续迈步，只守住这块落脚点。"],
        unclear: ["那句话被风吹散", "没说完整的念头落空，你仍停在原处。"],
        impossible: ["这个办法没有落地", "想象里的捷径没有落到地面上。"],
        contradictory: ["两股脚步拧在一起", "又想停又想走，一步也没迈出去。"],
        unsafe: ["那条路没有显出来", "你没有追看不见的方向，脚印留在原处。"],
        injection: ["杂音盖住了字句", "一串不属于眼前路的声音被你放下。"]
      }[kind] || ["停在原处", "你停了一拍，原来的落脚点仍在。"];
      summary = rows[0];
      narration = rows[1];
      if (kind === "stationary" || kind === "unclear") {
        const firstLoss = Math.ceil((stall + 1) / 2);
        statsDelta = { energy: -firstLoss, warmth: -(stall + 1 - firstLoss), sanity: 1 };
      } else {
        statsDelta = { energy: -stall, warmth: 0, sanity: 0 };
      }
    }

    return {
      schemaVersion: "free-input.action.v1",
      type: "action",
      result: {
        verdict,
        failureKind,
        summary,
        narration,
        statsDelta,
        progressDelta,
        weather: ctx.weather,
        nextSituation: progressDelta ? (copy.nextOnAdvance || "前方又露出一段陌生地面。") : ctx.situation,
        hallucination: { active: false, caption: "", filter: "none", imagePrompt: "" }
      },
      images: {},
      imageJobs: {},
      fallback: true
    };
  };
})(typeof window !== "undefined" ? window : globalThis);
