/** Validation for the traversal example only. Other games supply their own contract. */
(function (root) {
  'use strict';
  const App = root.App = root.App || {};
  const isObject = (v) => !!v && typeof v === 'object' && !Array.isArray(v);
  App.assertActionResult = function (result, maxAbsDelta) {
    if (!isObject(result) || !Number.isSafeInteger(maxAbsDelta) || maxAbsDelta < 0) return false;
    if (!['effective', 'costly', 'failed'].includes(result.verdict)) return false;
    if (!['none', 'stationary', 'unclear', 'impossible', 'contradictory', 'unsafe', 'injection'].includes(result.failureKind)) return false;
    if (typeof result.summary !== 'string' || typeof result.narration !== 'string') return false;
    if (result.summary.length > 500 || result.narration.length > 4000) return false;
    if (!isObject(result.statsDelta)) return false;
    const axes = ['energy', 'warmth', 'sanity'];
    if (Object.keys(result.statsDelta).length !== axes.length ||
        !axes.every((key) => Number.isSafeInteger(result.statsDelta[key]) && Math.abs(result.statsDelta[key]) <= maxAbsDelta)) return false;
    if (![0, 1].includes(result.progressDelta)) return false;
    const advancing = result.progressDelta === 1;
    if (advancing ? (result.verdict === 'failed' || result.failureKind !== 'none') :
        (result.verdict !== 'failed' || result.failureKind === 'none')) return false;
    if (typeof result.weather !== 'string' || typeof result.nextSituation !== 'string') return false;
    if (!isObject(result.hallucination) || typeof result.hallucination.active !== 'boolean') return false;
    return true;
  };
  App.assertActionEnvelope = function (data, maxAbsDelta) {
    return isObject(data) && data.schemaVersion === 'free-input.action.v1' &&
      data.type === 'action' && App.assertActionResult(data.result, maxAbsDelta);
  };
})(typeof window !== 'undefined' ? window : globalThis);
