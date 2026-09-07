/** Free-input transaction controller. No network endpoint or credential is bundled. */
(function (root) {
  'use strict';
  const App = root.App = root.App || {};

  App.createFreeInputController = function createFreeInputController(options) {
    for (const name of ['request', 'fallback', 'validate', 'commit', 'getContext', 'getEpoch', 'getRevision']) {
      if (typeof options[name] !== 'function') throw new TypeError('Missing callback: ' + name);
    }
    const minimumMs = options.minimumMs ?? 0;
    const timeoutMs = options.timeoutMs;
    const maxLength = options.maxLength ?? 220;
    if (!Number.isFinite(minimumMs) || minimumMs < 0) throw new RangeError('Invalid minimumMs');
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new RangeError('timeoutMs must be positive');
    if (!Number.isInteger(maxLength) || maxLength < 1) throw new RangeError('Invalid maxLength');
    const scheduleDeadline = options.scheduleDeadline || ((ms, fn) => {
      const id = setTimeout(fn, ms); return () => clearTimeout(id);
    });
    const schedulePresentation = options.schedulePresentation || scheduleDeadline;
    let sequence = 0;
    let active = null;
    let disposed = false;

    function submit(raw) {
      if (disposed) return Promise.resolve({status: 'disposed'});
      if (active) return active.promise;
      const text = App.sanitizeText(raw, maxLength);
      // Context is a JSON snapshot; provider code never receives the authoritative object.
      const context = JSON.parse(JSON.stringify(options.getContext()));
      const epoch = options.getEpoch();
      const revision = options.getRevision();
      const controller = new AbortController();
      const actionId = ++sequence; // Local correlation only; server idempotency IDs are host-owned.
      let resolve, reject;
      const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
      const job = {
        actionId, promise, ended: false, ready: false, presentationDone: false,
        value: null, source: null, cancelPresentation: () => {}, cancelDeadline: () => {},
        invalidate: () => end({status: 'ignored', actionId})
      };
      active = job;

      function current() {
        return active === job && !job.ended && !disposed &&
          options.getEpoch() === epoch && options.getRevision() === revision;
      }
      function end(outcome, error) {
        if (job.ended) return;
        job.ended = true;
        job.cancelPresentation(); job.cancelDeadline(); controller.abort();
        if (active === job) active = null;
        if (error) reject(error); else resolve(outcome);
      }
      function accepted(value) {
        try { return options.validate(value, context) === true; }
        catch (_) { return false; }
      }
      function finish() {
        if (job.ended) return;
        if (!current()) { end({status: 'ignored', actionId}); return; }
        if (!job.ready || !job.presentationDone) return;
        // Mark complete before calling host code, so a throw cannot trigger another commit.
        const envelope = job.value;
        job.ended = true;
        job.cancelPresentation(); job.cancelDeadline(); controller.abort();
        try {
          // Contract: synchronous, atomic commit. A thrown commit is surfaced, never retried.
          const result = options.commit({actionId, text, envelope, context, source: job.source});
          if (result && typeof result.then === 'function') throw new TypeError('commit must be synchronous');
          resolve({status: 'committed', actionId, source: job.source});
        } catch (error) { reject(error); }
        finally { if (active === job) active = null; }
      }
      function useFallback(reason) {
        if (job.ended || job.ready) return;
        if (!current()) { end({status: 'ignored', actionId}); return; }
        let value;
        try { value = options.fallback({text, context, reason}); }
        catch (error) { end(null, error); return; }
        if (!accepted(value)) { end(null, new Error('Invalid fallback result')); return; }
        job.value = value; job.source = 'local'; job.ready = true;
        job.cancelDeadline(); controller.abort(); finish();
      }
      // Schedulers must return a cancellation function and queue callbacks asynchronously.
      try {
        job.cancelPresentation = schedulePresentation(minimumMs, () => {
          job.presentationDone = true; finish();
        });
        job.cancelDeadline = scheduleDeadline(timeoutMs, () => useFallback('timeout'));
        if (typeof job.cancelPresentation !== 'function' || typeof job.cancelDeadline !== 'function') {
          throw new TypeError('Scheduler must return a cancellation function');
        }
      } catch (error) {
        // Restore callable cleanup even for a malformed adapter.
        if (typeof job.cancelPresentation !== 'function') job.cancelPresentation = () => {};
        if (typeof job.cancelDeadline !== 'function') job.cancelDeadline = () => {};
        end(null, error); return promise;
      }
      Promise.resolve().then(() => {
        if (!current() || job.ready) return null;
        return options.request({text, context: JSON.parse(JSON.stringify(context)), signal: controller.signal, actionId});
      }).then((value) => {
        if (job.ended || job.ready) return;
        if (!current()) { end({status: 'ignored', actionId}); return; }
        if (!accepted(value)) { useFallback('invalid-response'); return; }
        job.value = value; job.source = 'remote'; job.ready = true;
        job.cancelDeadline(); finish();
      }, () => useFallback('request-failed'));
      return promise;
    }
    return {
      submit,
      invalidate() { if (active) active.invalidate(); },
      dispose() { disposed = true; if (active) active.invalidate(); },
      get busy() { return active !== null; }
    };
  };
})(typeof window !== 'undefined' ? window : globalThis);
