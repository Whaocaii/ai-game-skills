/** Portable NFC sanitize used before free-input settle. */
(function (root) {
  "use strict";
  const App = root.App = root.App || {};

  App.sanitizeText = function sanitizeText(value, maxLength) {
    return String(value == null ? "" : value)
      .normalize("NFC")
      .replace(/[\u0000-\u001f\u007f]/g, " ")
      .replace(/[<>]/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, maxLength || 180);
  };
})(typeof window !== "undefined" ? window : globalThis);
