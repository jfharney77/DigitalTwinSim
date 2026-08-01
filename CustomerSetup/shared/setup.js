// Shared behavior for every CustomerSetup page. Three features, all optional
// per page — each activates only if the page carries the matching markup.
//
// 1. Twin liveness chips: any <a data-twin-port="5181" data-twin-start="DellPowerEdgeXE9712">
//    gets a running / not-running chip. A dead localhost link looks identical
//    to a live one until clicked; the chip removes the guesswork.
// 2. Walkthrough: if the page defines window.WALKTHROUGH (an array of
//    { focus: ["wt-name", ...], text: "..." }) and the SVG carries
//    <g data-wt="wt-name"> groups, prev/next controls step the story,
//    dimming everything outside the current step's focus.
// 3. Reading register: the twins' 1–5 reading-level choice (localStorage key
//    "twin-reading-level") is honored here as two authored registers —
//    1–2 novice, 3–5 standard — toggled via body[data-register] and CSS.

(function () {
  "use strict";

  // ---- twin liveness chips -------------------------------------------------
  function pingPort(port) {
    // no-cors: an opaque success means something answered on the port;
    // a network error means nothing is listening. That's all we need.
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, 2000);
    return fetch("http://localhost:" + port + "/", {
      mode: "no-cors",
      cache: "no-store",
      signal: ctrl.signal,
    }).then(
      function () { clearTimeout(t); return true; },
      function () { clearTimeout(t); return false; }
    );
  }

  // When a twin is up and its link names the trace endpoint
  // (data-twin-trace="poweron" → GET /api/poweron), enrich the chip with what
  // the twin would actually play: step count and the phase span. Vite's dev
  // server allows localhost cross-origin reads, so the JSON is readable when
  // these pages are served over http (scripts/serve.sh).
  function enrichChip(port, entry) {
    var endpoint = entry.link.getAttribute("data-twin-trace");
    if (!endpoint) return;
    fetch("http://localhost:" + port + "/api/" + endpoint, { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        var trace = data && data.trace;
        if (!Array.isArray(trace) || !trace.length) return;
        var first = trace[0].phase;
        var last = trace[trace.length - 1].phase;
        entry.chip.textContent =
          "running · " + trace.length + " steps · " + first + " → " + last;
      })
      .catch(function () { /* opaque or blocked — the plain chip stands */ });
  }

  function initChips() {
    var links = document.querySelectorAll("a[data-twin-port]");
    if (!links.length) return;
    var byPort = {};
    links.forEach(function (a) {
      var port = a.getAttribute("data-twin-port");
      (byPort[port] = byPort[port] || []).push(a);
    });
    Object.keys(byPort).forEach(function (port) {
      var entries = byPort[port].map(function (a) {
        var chip = document.createElement("span");
        chip.className = "chip unknown";
        chip.textContent = "checking…";
        a.insertAdjacentElement("afterend", chip);
        return { chip: chip, link: a };
      });
      pingPort(port).then(function (up) {
        entries.forEach(function (e, i) {
          e.chip.className = "chip " + (up ? "up" : "down");
          e.chip.textContent = up ? "running" : "not running";
          if (!up && i === 0) {
            var start = e.link.getAttribute("data-twin-start");
            if (start) {
              var hint = document.createElement("span");
              hint.className = "chip-hint";
              hint.innerHTML =
                "start it: <code>./" + start + "/scripts/start_all.sh</code>";
              e.chip.insertAdjacentElement("afterend", hint);
            }
          }
        });
        if (up) {
          var tracer = entries.filter(function (e) {
            return e.link.getAttribute("data-twin-trace");
          })[0];
          if (tracer) enrichChip(port, tracer);
        }
      });
    });
  }

  // ---- walkthrough ---------------------------------------------------------
  function initWalkthrough() {
    var steps = window.WALKTHROUGH;
    var host = document.getElementById("walkthrough");
    if (!steps || !steps.length || !host) return;
    var groups = document.querySelectorAll(".diagram svg g[data-wt]");
    if (!groups.length) return;

    var idx = -1; // -1 = show everything, no step active

    var count = document.createElement("span");
    count.className = "wt-count";
    var prev = document.createElement("button");
    prev.textContent = "Back";
    var next = document.createElement("button");
    next.textContent = "Walk through";
    var reset = document.createElement("button");
    reset.textContent = "Show all";
    var text = document.createElement("div");
    text.className = "wt-text";

    var buttons = document.createElement("div");
    buttons.className = "wt-buttons";
    buttons.appendChild(prev);
    buttons.appendChild(next);
    buttons.appendChild(reset);
    host.appendChild(buttons);
    host.appendChild(count);
    host.appendChild(text);

    function render() {
      var active = idx >= 0 ? steps[idx] : null;
      var diagram = document.querySelector(".diagram");
      if (diagram) diagram.classList.toggle("wt-active", active !== null);
      groups.forEach(function (g) {
        var dim =
          active !== null && active.focus.indexOf(g.getAttribute("data-wt")) < 0;
        g.classList.toggle("wt-dim", dim);
      });
      text.textContent = active ? active.text : "";
      count.textContent = active ? (idx + 1) + " of " + steps.length : "";
      prev.disabled = idx <= 0;
      next.disabled = idx >= steps.length - 1;
      next.textContent = idx < 0 ? "Walk through" : "Next";
      reset.disabled = idx < 0;
    }

    prev.addEventListener("click", function () { idx = Math.max(0, idx - 1); render(); });
    next.addEventListener("click", function () { idx = Math.min(steps.length - 1, idx + 1); render(); });
    reset.addEventListener("click", function () { idx = -1; render(); });
    render();
  }

  // ---- block <-> row cross-linking ----------------------------------------
  // Table rows carry data-wt-ref="group[,group]" naming SVG data-wt groups.
  // Hovering a row spotlights its blocks (unless a walkthrough step is
  // active — the walkthrough owns the dimming then); clicking a block
  // scrolls to and flashes its rows.
  function initCrossLinks() {
    var rows = Array.prototype.slice.call(
      document.querySelectorAll("tr[data-wt-ref]")
    );
    var groups = Array.prototype.slice.call(
      document.querySelectorAll(".diagram svg g[data-wt]")
    );
    if (!rows.length || !groups.length) return;
    var diagram = document.querySelector(".diagram");

    function refsOf(row) {
      return row.getAttribute("data-wt-ref").split(",");
    }

    function spotlight(refs) {
      groups.forEach(function (g) {
        g.classList.toggle("wt-dim", refs.indexOf(g.getAttribute("data-wt")) < 0);
      });
    }

    function clearSpotlight() {
      groups.forEach(function (g) { g.classList.remove("wt-dim"); });
    }

    rows.forEach(function (row) {
      row.classList.add("wt-linked");
      row.addEventListener("mouseenter", function () {
        if (diagram && diagram.classList.contains("wt-active")) return;
        spotlight(refsOf(row));
      });
      row.addEventListener("mouseleave", function () {
        if (diagram && diagram.classList.contains("wt-active")) return;
        clearSpotlight();
      });
    });

    groups.forEach(function (g) {
      var name = g.getAttribute("data-wt");
      var matches = rows.filter(function (row) {
        return refsOf(row).indexOf(name) >= 0;
      });
      if (!matches.length) return;
      g.style.cursor = "pointer";
      g.addEventListener("click", function () {
        matches[0].scrollIntoView({ behavior: "smooth", block: "center" });
        matches.forEach(function (row) {
          row.classList.add("row-flash");
          setTimeout(function () { row.classList.remove("row-flash"); }, 1600);
        });
      });
    });
  }

  // ---- reading register ----------------------------------------------------
  var LEVEL_KEY = "twin-reading-level"; // shared with every twin's level.ts

  function readLevel() {
    try {
      var n = Number(window.localStorage.getItem(LEVEL_KEY));
      if (n >= 1 && n <= 5) return n;
    } catch (e) { /* storage unavailable; default is fine */ }
    return 3;
  }

  function applyLevel(level) {
    document.body.setAttribute("data-register", level <= 2 ? "novice" : "standard");
    document.querySelectorAll(".level-control button").forEach(function (b) {
      b.classList.toggle("active", Number(b.getAttribute("data-level")) === level);
    });
  }

  function initLevel() {
    var host = document.querySelector(".level-control");
    if (!host) return;
    var labels = { 1: "Novice", 2: "Plain", 3: "Standard", 4: "Technical", 5: "Expert" };
    var caption = document.createElement("span");
    caption.textContent = "Reading level";
    host.appendChild(caption);
    [1, 2, 3, 4, 5].forEach(function (n) {
      var b = document.createElement("button");
      b.textContent = labels[n];
      b.setAttribute("data-level", String(n));
      b.title =
        n <= 2
          ? "Plain-language register (these pages author two registers; 1 and 2 read the same here)"
          : "Standard register (3–5 read the same here; the twins themselves distinguish all five)";
      b.addEventListener("click", function () {
        try { window.localStorage.setItem(LEVEL_KEY, String(n)); } catch (e) { /* fine */ }
        applyLevel(n);
      });
      host.appendChild(b);
    });
    applyLevel(readLevel());
  }

  document.addEventListener("DOMContentLoaded", function () {
    initChips();
    initWalkthrough();
    initCrossLinks();
    initLevel();
  });
})();
