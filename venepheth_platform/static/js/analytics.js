/* Google Analytics bootstrap.
   Lives in a file rather than inline because the enforced CSP has no
   'unsafe-inline' and no 'nonce-' in script-src, so an inline <script> is
   refused by the browser. Loaded with defer, only rendered when
   GOOGLE_ANALYTICS_ID is set; the measurement id arrives via data-ga-id. */
(function () {
  var script = document.currentScript || document.querySelector('script[data-ga-id]');
  if (!script) {
    return;
  }
  var id = script.getAttribute('data-ga-id');
  if (!id) {
    return;
  }
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () {
    window.dataLayer.push(arguments);
  };
  window.gtag('js', new Date());
  window.gtag('config', id);
})();
