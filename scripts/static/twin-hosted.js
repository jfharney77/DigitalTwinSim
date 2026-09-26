// Injected by scripts/build_site.sh into the hosted copies of index.html,
// Learn/ and CustomerSetup/ — never into the sources. On the hosted site there
// are no localhost ports: this is the one resolver that turns
// http://localhost:<port>/<hash> into the sibling twin's path, and answers the
// pages' liveness pings so their chips read "hosted".
//
// window.TWIN_HOSTED = { root: "<relative path to site root>", byPort: {port: dir},
//                        byDir: {dir: true}, trace: {dir: "poweron"} } is written
// just before this script by build_site.sh.
(function () {
  "use strict";
  var H = window.TWIN_HOSTED;
  if (!H) return;
  var LOCAL = /^http:\/\/(localhost|127\.0\.0\.1):(\d+)(\/[^#?]*)?(\?[^#]*)?(#.*)?$/;

  function dirFor(port, hint) {
    if (hint && H.byDir[hint]) return hint;          // data-twin-start wins (5178 is shared)
    var d = H.byPort[port];
    return d && H.byDir[d] ? d : null;
  }

  function resolve(url, hint) {
    var m = LOCAL.exec(url);
    if (!m) return null;
    var dir = dirFor(m[2], hint);
    if (!dir) return null;
    return { dir: dir, path: m[3] || "/", hash: m[5] || "" };
  }

  function rewrite(a) {
    var href = a.getAttribute("href");
    if (!href) return;
    var m = LOCAL.exec(href);
    if (!m) return;
    var r = resolve(href, a.getAttribute("data-twin-start"));
    if (r) {
      a.setAttribute("href", H.root + r.dir + "/" + r.hash);
      if (/^localhost:\d+$/.test(a.textContent.trim())) a.textContent = r.dir;
    } else {
      a.setAttribute("data-twin-unhosted", "1");
      a.removeAttribute("href");
      a.title = "This twin is not on the hosted site yet — run it locally.";
    }
  }

  function relabel(node) {
    if (node.nodeType !== 1) return;
    var chips = node.matches && node.matches(".chip, .chip-hint") ? [node] : [];
    if (node.querySelectorAll) chips = chips.concat([].slice.call(node.querySelectorAll(".chip, .chip-hint")));
    chips.forEach(function (c) {
      if (c.classList.contains("chip-hint")) { c.remove(); return; }
      var t = c.textContent;
      if (/^running/.test(t)) c.textContent = t.replace(/^running/, "hosted");
      else if (t === "not running") c.textContent = "not hosted";
    });
  }

  // The pages ping http://localhost:<port>/ and read /api/<trace>. Answer both
  // from the hosted site: the twin's index.html, and its api-static snapshot.
  var realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    var url = typeof input === "string" ? input : input && input.url;
    var m = url && LOCAL.exec(url);
    if (!m) return realFetch(input, init);
    var dir = dirFor(m[2], null);
    if (!dir) return Promise.reject(new TypeError("twin not hosted"));
    var path = m[3] || "/";
    var target = H.root + dir + "/";
    if (path.indexOf("/api/") === 0) target += "api-static/" + path.slice(5) + "/_.json";
    var opts = {};
    if (init && init.signal) opts.signal = init.signal;
    return realFetch(target, opts);
  };

  function sweep(root) {
    [].forEach.call(root.querySelectorAll ? root.querySelectorAll("a[href]") : [], rewrite);
    if (root.matches && root.matches("a[href]")) rewrite(root);
    relabel(root);
  }

  new MutationObserver(function (records) {
    records.forEach(function (rec) {
      if (rec.type === "characterData") { if (rec.target.parentNode) relabel(rec.target.parentNode); return; }
      [].forEach.call(rec.addedNodes, function (n) { if (n.nodeType === 1) sweep(n); else if (n.parentNode) relabel(n.parentNode); });
    });
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { sweep(document); });
  else sweep(document);
})();
