// Run with Node.js 18+: node examples/integration.js
// Entirely local demonstration; no network, provider account, or API key required.
require('../snippets/sanitize.js');
require('../snippets/validate-action-result.js');
require('../snippets/classify-and-fallback.js');
require('../snippets/wait-and-settle.js');
const App = globalThis.App;
let state = {epoch: 1, revision: 0, node: 1, attemptsAtNode: 0, weather: '阴天', situation: '岔路口',
  stats: {energy: 50, warmth: 50, sanity: 50}};
const controller = App.createFreeInputController({
  minimumMs: 0,
  timeoutMs: 1000,
  getEpoch: () => state.epoch,
  getRevision: () => state.revision,
  getContext: () => state,
  request: () => Promise.reject(new Error('Local demonstration: provider not configured')),
  fallback: ({text, context}) => App.makeLocalActionFallback(text, context),
  validate: (data) => App.assertActionEnvelope(data, 20),
  commit: ({envelope}) => {
    const result = envelope.result;
    const stats = Object.fromEntries(Object.keys(state.stats).map((key) => [key,
      Math.max(0, Math.min(100, state.stats[key] + result.statsDelta[key]))]));
    state = {...state, stats, node: state.node + result.progressDelta,
      weather: result.weather, situation: result.nextSituation, revision: state.revision + 1};
  }
});
controller.submit('沿着石阶向前走').then((outcome) => {
  console.log(JSON.stringify({outcome, state}, null, 2));
  controller.dispose();
}, (error) => { console.error(error.message); process.exitCode = 1; });
