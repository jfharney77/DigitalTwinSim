// The Learn course renderer. Draws the course home and the module pages from
// window.COURSE (course.js), and keeps the reader's progress in localStorage.
//
// Load order matters: course.js, then this file, then
// ../CustomerSetup/shared/setup.js. This file renders synchronously while it
// executes, so by the time setup.js runs its DOMContentLoaded work the entry
// links are already in the page and get their liveness chips and start hints.
//
// Plain ES5 and DOM calls, like setup.js: no build step, and it works from
// file:// as well as from Learn/scripts/serve.sh.

(function () {
  "use strict";

  var COURSE = window.COURSE;
  var mount = document.getElementById("learn");
  if (!COURSE || !mount) return;

  var PROGRESS_KEY = "learn-progress-v1";
  var LEVEL_KEY = "twin-reading-level"; // shared with the twins and setup.js

  // ---- data helpers -------------------------------------------------------
  var byId = {};
  COURSE.modules.forEach(function (m) { byId[m.id] = m; });
  var tracksById = {};
  COURSE.tracks.forEach(function (t) { tracksById[t.id] = t; });

  function hashParam(name) {
    var m = window.location.hash.match(new RegExp("[#&]" + name + "=([A-Za-z0-9-]+)"));
    return m ? m[1] : null;
  }

  // ---- progress store (every access guarded; the course works without it) --
  function loadProgress() {
    try {
      var raw = window.localStorage.getItem(PROGRESS_KEY);
      var data = raw ? JSON.parse(raw) : {};
      return data && typeof data === "object" ? data : {};
    } catch (e) { return {}; }
  }
  var progress = loadProgress();
  function save() {
    try { window.localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress)); } catch (e) { /* fine */ }
  }
  function modState(id) {
    if (!progress.modules) progress.modules = {};
    if (!progress.modules[id]) progress.modules[id] = { checks: {} };
    return progress.modules[id];
  }
  function peek(id) {
    return (progress.modules && progress.modules[id]) || null;
  }

  function currentTrack() {
    var t = hashParam("track") || progress.track || "full";
    return tracksById[t] ? tracksById[t] : tracksById.full;
  }

  function stepFor(track, id) {
    for (var i = 0; i < track.steps.length; i++) if (track.steps[i].module === id) return track.steps[i];
    return null;
  }

  function isDone(m, track) {
    var s = peek(m.id);
    if (!s || !s.revealed) return false;
    if (track && track.predictOnly) return true;
    for (var i = 0; i < m.checks.length; i++) if (!s.checks || !s.checks[i]) return false;
    return true;
  }

  function status(m, track) {
    if (isDone(m, track)) return "done";
    var s = peek(m.id);
    return s && (s.predicted !== undefined || s.revealed) ? "started" : "new";
  }
  var STATUS_TEXT = { done: "Done", started: "In progress", "new": "Not started" };

  // ---- DOM helpers --------------------------------------------------------
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (attrs[k] === null || attrs[k] === undefined) return;
        if (k === "text") node.textContent = attrs[k];
        else if (k === "class") node.className = attrs[k];
        else node.setAttribute(k, attrs[k]);
      });
    }
    (children || []).forEach(function (c) {
      if (c === null || c === undefined) return;
      node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  }

  // A text field is a string or {standard, novice}. Two registers become two
  // elements; setup.css shows the one matching body[data-register].
  function reg(tag, value, cls) {
    if (typeof value === "string") return el(tag, { "class": cls || null, text: value });
    var wrap = document.createDocumentFragment();
    wrap.appendChild(el(tag, { "class": (cls ? cls + " " : "") + "lvl-standard", text: value.standard }));
    wrap.appendChild(el(tag, { "class": (cls ? cls + " " : "") + "lvl-novice", text: value.novice }));
    return wrap;
  }

  function modulePath(id, track, fromHome) {
    var base = (fromHome ? "modules/" : "") + id.toLowerCase() + ".html";
    return track && track.id !== "full" ? base + "#track=" + track.id : base;
  }

  function homePath(fromHome, track) {
    var base = fromHome ? "index.html" : "../index.html";
    return track ? base + "#track=" + track.id : base;
  }

  function levelControl() { return el("div", { "class": "level-control" }); }

  // ---- entry links ----------------------------------------------------------
  function hrefFor(entry, link) {
    var base = "http://localhost:" + entry.port + "/";
    switch (link.kind) {
      case "tour": return base + "#tour/" + link.id;
      case "phase": return base + "#phase=" + link.value;
      case "step": return base + "#step=" + link.value;
      case "scenario": return base + "#scenario=" + link.id;
      case "lesson": return base + link.hash;
      case "setup": return "../../CustomerSetup/" + link.path;
      default: return base;
    }
  }

  function renderEntry(entry, locked) {
    var box = el("div", { "class": "entry" });
    box.appendChild(el("h3", { text: entry.name }));
    var list = el("ul", { "class": "entry-links" });
    entry.links.forEach(function (link, i) {
      var attrs = {
        href: hrefFor(entry, link),
        "class": "entry-link" + (locked ? " locked" : ""),
        target: "_blank",
        rel: "noopener"
      };
      if (locked) attrs["aria-disabled"] = "true";
      if (entry.port) {
        attrs["data-twin-port"] = String(entry.port);
        attrs["data-twin-start"] = entry.twin;
        if (entry.trace && i === 0) attrs["data-twin-trace"] = entry.trace;
      }
      var a = el("a", attrs, [link.label]);
      var item = el("li", null, [a]);
      if (link.how) item.appendChild(el("p", { "class": "how", text: link.how }));
      if (link.kind === "lesson") {
        item.appendChild(el("p", { "class": "how", text: "The lesson tour opens at its first lesson." }));
      }
      list.appendChild(item);
    });
    box.appendChild(list);
    if (entry.port) {
      box.appendChild(el("p", { "class": "start" }, [
        "Start it from the repository root: ",
        el("code", { text: "scripts/dev.sh " + entry.twin })
      ]));
    } else {
      box.appendChild(el("p", { "class": "start" }, [
        "These pages are served with the course; no twin needs to be running to read them."
      ]));
    }
    return box;
  }

  // ---- module page ----------------------------------------------------------
  function renderModule(id) {
    var m = byId[id];
    if (!m) { mount.appendChild(el("p", { text: "This module is not in course.js." })); return; }
    var track = currentTrack();
    var step = stepFor(track, m.id);
    if (!step) {
      // Opened under a track that skips this module (or an elective under
      // the full track): use the first track that includes it.
      for (var k = 0; k < COURSE.tracks.length && !step; k++) {
        step = stepFor(COURSE.tracks[k], m.id);
        if (step) track = COURSE.tracks[k];
      }
    }
    var predictOnly = !!(track && track.predictOnly);
    var state = modState(m.id);

    var crumb = el("p", { "class": "crumb" }, [
      el("a", { href: homePath(false, track), text: "Learn the twins" }),
      track && track.id !== "full" ? " · " + track.title : null
    ]);
    mount.appendChild(levelControl());
    mount.appendChild(crumb);
    mount.appendChild(el("h1", { text: m.title }));
    mount.appendChild(reg("p", m.idea, "lede"));

    if (m.prereqs.length || m.background) {
      var pre = el("p", { "class": "prereqs" }, ["Before you start: "]);
      if (m.background) pre.appendChild(document.createTextNode(m.background + " "));
      if (m.prereqs.length) {
        pre.appendChild(document.createTextNode("It builds on "));
        m.prereqs.forEach(function (p, i) {
          if (i) pre.appendChild(document.createTextNode(i === m.prereqs.length - 1 ? " and " : ", "));
          pre.appendChild(el("a", { href: modulePath(p, track, false), text: byId[p].title }));
        });
        pre.appendChild(document.createTextNode("."));
      }
      mount.appendChild(pre);
    }

    if (m.objectives.length) {
      mount.appendChild(el("h2", { text: "What you will be able to do" }));
      mount.appendChild(el("ul", { "class": "objectives" }, m.objectives.map(function (o) {
        return el("li", { text: o });
      })));
    }

    // Predict before you play.
    mount.appendChild(el("h2", { text: "Predict before you play" }));
    var predict = el("section", { "class": "predict" });
    predict.appendChild(reg("p", m.predict.q, "question"));
    var form = el("div", { "class": "options", role: "radiogroup" });
    var name = "predict-" + m.id;
    m.predict.options.forEach(function (opt, i) {
      var input = el("input", { type: "radio", name: name, value: String(i), id: name + "-" + i });
      if (state.predicted === i) input.checked = true;
      form.appendChild(el("label", { "class": "option", "for": name + "-" + i }, [input, el("span", { text: opt })]));
    });
    predict.appendChild(form);
    var commit = el("button", { type: "button", "class": "primary", text: "Commit my answer" });
    var revealBtn = el("button", { type: "button", text: "Show the answer" });
    var controls = el("div", { "class": "buttons" }, [commit, revealBtn]);
    predict.appendChild(controls);
    var hint = el("p", { "class": "hint", text: "Commit an answer to unlock the links below. Nothing is graded; committing first is the point." });
    predict.appendChild(hint);
    var answer = el("div", { "class": "answer", hidden: "hidden" });
    predict.appendChild(answer);
    mount.appendChild(predict);

    function drawAnswer() {
      answer.innerHTML = "";
      var right = state.predicted === m.predict.answer;
      answer.appendChild(el("p", { "class": "verdict " + (right ? "right" : "wrong"),
        text: right ? "Your prediction matched." : "The answer is: " + m.predict.options[m.predict.answer] + "." }));
      answer.appendChild(reg("p", m.predict.reveal));
      answer.appendChild(citeList(m.predict.cite));
      answer.hidden = false;
    }

    // Play it.
    mount.appendChild(el("h2", { text: "Play it" }));
    var entries = m.entries;
    if (step && step.only) {
      entries = entries.filter(function (e) { return step.only.indexOf(e.twin) >= 0; });
      mount.appendChild(el("p", { "class": "trim" }, [
        "This track uses part of this module. ",
        el("a", { href: modulePath(m.id, null, false), text: "Open the whole module" }),
        "."
      ]));
    }
    var play = el("section", { "class": "play" });
    var locked = state.predicted === undefined;
    entries.forEach(function (e) { play.appendChild(renderEntry(e, locked)); });
    mount.appendChild(play);
    play.addEventListener("click", function (ev) {
      var a = ev.target.closest ? ev.target.closest("a.locked") : null;
      if (!a) return;
      ev.preventDefault();
      hint.classList.add("nudge");
      predict.scrollIntoView({ behavior: "smooth", block: "center" });
    });

    function unlock() {
      play.querySelectorAll("a.locked").forEach(function (a) {
        a.classList.remove("locked");
        a.removeAttribute("aria-disabled");
      });
      hint.hidden = true;
    }

    function syncPredict() {
      var chosen = state.predicted !== undefined;
      commit.disabled = chosen;
      commit.textContent = chosen ? "Answer committed" : "Commit my answer";
      form.querySelectorAll("input").forEach(function (i) { i.disabled = chosen; });
      revealBtn.hidden = !chosen || !!state.revealed;
      if (chosen) unlock();
      if (state.revealed) drawAnswer();
    }

    commit.addEventListener("click", function () {
      var picked = form.querySelector("input:checked");
      if (!picked) { hint.classList.add("nudge"); hint.textContent = "Pick one of the options first."; return; }
      state.predicted = Number(picked.value);
      state.at = new Date().toISOString().slice(0, 10);
      save();
      syncPredict();
      refreshDone();
    });
    revealBtn.addEventListener("click", function () {
      state.revealed = true;
      save();
      syncPredict();
      refreshDone();
    });

    // Check your understanding.
    if (!predictOnly) {
      mount.appendChild(el("h2", { text: "Check your understanding" }));
      var checks = el("section", { "class": "checks" });
      m.checks.forEach(function (c, i) {
        var box = el("div", { "class": "check" });
        box.appendChild(el("p", { "class": "question", text: c.q }));
        var d = el("details");
        d.appendChild(el("summary", { text: "Show answer" }));
        d.appendChild(el("p", { text: c.a }));
        d.appendChild(citeList(c.cite));
        var got = el("button", { type: "button", text: "Got it" });
        var missed = el("button", { type: "button", text: "Missed it" });
        var marks = el("div", { "class": "buttons marks" }, [got, missed]);
        function syncMarks() {
          var v = state.checks && state.checks[i];
          got.classList.toggle("active", v === "got");
          missed.classList.toggle("active", v === "missed");
        }
        [["got", got], ["missed", missed]].forEach(function (pair) {
          pair[1].addEventListener("click", function () {
            if (!state.checks) state.checks = {};
            state.checks[i] = pair[0];
            save();
            syncMarks();
            refreshDone();
          });
        });
        syncMarks();
        d.appendChild(marks);
        box.appendChild(d);
        checks.appendChild(box);
      });
      mount.appendChild(checks);
    }

    // Bridge and next.
    mount.appendChild(el("h2", { text: "Where this leads" }));
    mount.appendChild(reg("p", m.bridge.text, "bridge"));
    var idx = -1;
    for (var i = 0; i < track.steps.length; i++) if (track.steps[i].module === m.id) idx = i;
    var nav = el("p", { "class": "next-nav" });
    if (idx > 0) {
      var prev = byId[track.steps[idx - 1].module];
      nav.appendChild(el("a", { href: modulePath(prev.id, track, false), text: "Back: " + prev.title }));
    }
    if (idx >= 0 && idx < track.steps.length - 1) {
      var nxt = byId[track.steps[idx + 1].module];
      nav.appendChild(el("a", { "class": "next", href: modulePath(nxt.id, track, false), text: "Next: " + nxt.title }));
    } else {
      nav.appendChild(el("a", { "class": "next", href: homePath(false, track), text: "Back to the course home" }));
    }
    mount.appendChild(nav);
    var doneLine = el("p", { "class": "done-line" });
    mount.appendChild(doneLine);

    function refreshDone() {
      var done = isDone(m, track);
      state.done = done;
      save();
      doneLine.textContent = done
        ? "You have finished this module."
        : predictOnly
          ? "Reveal the answer to finish this module."
          : "Reveal the answer and mark each check to finish this module.";
    }

    if (track.register === "novice") applyTrackRegister();
    syncPredict();
    refreshDone();
  }

  function citeList(cites) {
    var p = el("p", { "class": "cite" }, ["Settled by "]);
    cites.forEach(function (c, i) {
      if (i) p.appendChild(document.createTextNode(", "));
      p.appendChild(el("code", { text: c }));
    });
    return p;
  }

  // The short track reads in the plain register unless the reader already
  // chose a level somewhere (in a twin or on these pages).
  function applyTrackRegister() {
    var chosen = null;
    try { chosen = window.localStorage.getItem(LEVEL_KEY); } catch (e) { /* fine */ }
    if (chosen) return;
    window.addEventListener("load", function () {
      document.body.setAttribute("data-register", "novice");
      document.querySelectorAll(".level-control button").forEach(function (b) {
        b.classList.toggle("active", b.getAttribute("data-level") === "1");
      });
    });
  }

  // ---- course home ----------------------------------------------------------
  function renderHome() {
    var track = currentTrack();
    mount.appendChild(levelControl());
    mount.appendChild(el("p", { "class": "crumb" }, [el("a", { href: "../index.html", text: "DigitalTwinSim" })]));
    mount.appendChild(el("h1", { text: COURSE.title }));
    mount.appendChild(reg("p", {
      standard: "Each twin in this repository teaches one idea. This course puts them in a teaching order, from the arithmetic inside one chip to an AI factory that couples everything. Every module asks you to predict something before you press play, links you to the step of the running twin that settles it, and checks every answer against the twin's own tests.",
      novice: "Each model in this project explains one idea about how computers, storage, networks and data centers work. This course puts them in a sensible order, starting small and ending with a whole AI data center. In every module you guess first, then watch the model show you the answer."
    }, "lede"));

    mount.appendChild(el("h2", { text: "Choose a track" }));
    var picker = el("div", { "class": "tracks" });
    COURSE.tracks.forEach(function (t) {
      var done = 0;
      t.steps.forEach(function (s) { if (isDone(byId[s.module], t)) done++; });
      var card = el("a", {
        "class": "track" + (t.id === track.id ? " active" : ""),
        href: "#track=" + t.id,
        "aria-current": t.id === track.id ? "true" : null
      }, [
        el("span", { "class": "track-title", text: t.title }),
        el("span", { "class": "track-meta", text: t["for"] + " · " + t.time }),
        el("span", { "class": "track-meta", text: "Finished: " + done + ". Still to do: " + (t.steps.length - done) + "." })
      ]);
      picker.appendChild(card);
    });
    mount.appendChild(picker);

    mount.appendChild(el("h2", { text: track.title }));
    if (track.predictOnly) {
      mount.appendChild(el("p", { "class": "prereqs", text: "This track keeps each module's prediction and skips the check questions." }));
    }
    var list = el("ul", { "class": "modules" });
    track.steps.forEach(function (s) {
      var m = byId[s.module];
      var st = status(m, track);
      var item = el("li", { "class": "module " + st }, [
        el("a", { href: modulePath(m.id, track, true), text: m.title }),
        el("span", { "class": "status " + st, text: STATUS_TEXT[st] })
      ]);
      item.appendChild(reg("p", m.idea, "idea"));
      var twins = el("p", { "class": "twins" });
      m.entries.forEach(function (e) {
        if (s.only && s.only.indexOf(e.twin) < 0) return;
        twins.appendChild(el("span", { text: e.name }));
      });
      item.appendChild(twins);
      list.appendChild(item);
    });
    mount.appendChild(list);

    mount.appendChild(el("h2", { text: "How to run it" }));
    mount.appendChild(el("p", null, [
      "Serve these pages with ", el("code", { text: "./Learn/scripts/serve.sh" }),
      " and open ", el("code", { text: "http://localhost:5172/Learn/" }),
      ". Each module lists the twins it uses; start one with ",
      el("code", { text: "scripts/dev.sh <Twin>" }),
      ". A chip beside every link says whether that twin is running, and gives the start command when it is not."
    ]));
    mount.appendChild(el("div", { "class": "note" }, [
      reg("p", {
        standard: "The numbers in the answers are the twins' own illustrative values, not measurements. Each answer names the pytest case that pins it, and Learn/tests/test_links.py re-reads the quoted numbers from the twins' traces, so the course fails its tests before it can drift from the code.",
        novice: "The numbers here come from the models, which are simplified on purpose. They show how things relate, not exact real-world figures. Every answer names the automatic test that checks it."
      })
    ]));

    var reset = el("button", { type: "button", "class": "reset", text: "Reset progress" });
    reset.addEventListener("click", function () {
      try { window.localStorage.removeItem(PROGRESS_KEY); } catch (e) { /* fine */ }
      window.location.reload();
    });
    mount.appendChild(el("p", null, [reset]));

    if (track.register === "novice") applyTrackRegister();
  }

  // ---- boot -----------------------------------------------------------------
  var page = mount.getAttribute("data-page");
  var t = hashParam("track");
  if (t && tracksById[t]) { progress.track = t; save(); }
  if (page === "module") renderModule(mount.getAttribute("data-module"));
  else renderHome();

  // Picking a track on the home page, or following a #track= link inside an
  // open module page, reloads the page: setup.js wires the level control and
  // the chips once per load, so a fresh load is the simplest correct redraw.
  window.addEventListener("hashchange", function () {
    var nt = hashParam("track");
    if (!nt || !tracksById[nt]) return;
    progress.track = nt;
    save();
    window.location.reload();
  });
})();
