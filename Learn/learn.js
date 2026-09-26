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

  // The failure stops a module shows under a track step: all of them, or
  // the ones for the twins the step keeps.
  function failuresFor(m, step) {
    return (m.failures || []).filter(function (f) {
      return !step || !step.only || step.only.indexOf(f.twin) >= 0;
    });
  }

  // The lab state a module keeps: attempted (the reader opened it) and passed
  // (the reader scored it 70 or better in the app and said so here). The
  // course never talks to the grader; the app does the grading.
  function labState(m) {
    var s = peek(m.id);
    if (!s || !s.labs || !m.lab) return null;
    return s.labs[m.lab.id] || null;
  }

  function isDone(m, track) {
    var s = peek(m.id);
    if (track && track.labsOnly) {
      var ls = labState(m);
      return !!(m.lab && ls && ls.passed);
    }
    if (track && track.failuresOnly) {
      var stops = failuresFor(m, stepFor(track, m.id));
      if (!s || !s.failures || !stops.length) return false;
      for (var k = 0; k < stops.length; k++) {
        var fs = s.failures[stops[k].scenario];
        if (!fs || !fs.revealed) return false;
      }
      return true;
    }
    if (!s || !s.revealed) return false;
    if (track && track.predictOnly) return true;
    for (var i = 0; i < m.checks.length; i++) if (!s.checks || !s.checks[i]) return false;
    return true;
  }

  function status(m, track) {
    if (isDone(m, track)) return "done";
    var s = peek(m.id);
    if (track && track.labsOnly) {
      var ls = labState(m);
      return ls && (ls.attempted || ls.passed) ? "started" : "new";
    }
    if (track && track.failuresOnly) {
      var touched = false;
      if (s && s.failures) Object.keys(s.failures).forEach(function (k) {
        if (s.failures[k].predicted !== undefined) touched = true;
      });
      return touched ? "started" : "new";
    }
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

  // The same, inline: for an option label, a link label or a list item's text.
  function regSpan(value) {
    if (typeof value === "string") return document.createTextNode(value);
    var wrap = document.createDocumentFragment();
    wrap.appendChild(el("span", { "class": "lvl-standard", text: value.standard }));
    wrap.appendChild(el("span", { "class": "lvl-novice", text: value.novice }));
    return wrap;
  }

  function modulePath(id, track, fromHome) {
    var base = (fromHome ? "modules/" : "") + id.toLowerCase() + ".html";
    return track && track.id !== "full" ? base + "#track=" + track.id : base;
  }

  // A track that shows the module whole: no failures-only view, no
  // predict-only view, no trimmed entry list. The full course for a core
  // module, the electives for an elective.
  function wholeTrack(id) {
    for (var i = 0; i < COURSE.tracks.length; i++) {
      var t = COURSE.tracks[i];
      var s = stepFor(t, id);
      if (s && !s.only && !t.failuresOnly && !t.predictOnly && !t.labsOnly) return t;
    }
    return null;
  }

  // The "Open the whole module" link. It always names a track, because a
  // bare module URL falls back to the reader's remembered track, which is
  // the trimmed one they are trying to leave.
  function wholePath(id) {
    var t = wholeTrack(id);
    return id.toLowerCase() + ".html#track=" + (t ? t.id : "full");
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

  function failureHref(f) {
    return "http://localhost:" + f.port + "/#scenario=" + f.scenario + "&" + f.at.kind + "=" + f.at.value;
  }

  // One "when it goes wrong" stop: a question about a failure scenario, a
  // commitment, then the deep link into the twin's failure trace and the
  // answer with the tests that settle it. Same contract as the module's own
  // prediction: the link and the answer stay shut until the reader commits.
  function renderFailure(m, f, state, onChange) {
    if (!state.failures) state.failures = {};
    if (!state.failures[f.scenario]) state.failures[f.scenario] = {};
    var fs = state.failures[f.scenario];
    var box = el("section", { "class": "failure predict" });
    box.appendChild(el("h3", null, [regSpan(f.name)]));
    box.appendChild(reg("p", f.q, "question"));
    var form = el("div", { "class": "options", role: "radiogroup" });
    var name = "failure-" + m.id + "-" + f.scenario;
    f.options.forEach(function (opt, i) {
      var input = el("input", { type: "radio", name: name, value: String(i), id: name + "-" + i });
      if (fs.predicted === i) input.checked = true;
      form.appendChild(el("label", { "class": "option", "for": name + "-" + i }, [input, el("span", null, [regSpan(opt)])]));
    });
    box.appendChild(form);
    var commit = el("button", { type: "button", "class": "primary", text: "Commit my answer" });
    var revealBtn = el("button", { type: "button", text: "Show the answer" });
    box.appendChild(el("div", { "class": "buttons" }, [commit, revealBtn]));
    var hint = el("p", { "class": "hint", text: "Commit an answer to unlock the failure trace and the answer." });
    box.appendChild(hint);
    var link = el("a", {
      href: failureHref(f), "class": "entry-link locked", target: "_blank", rel: "noopener",
      "aria-disabled": "true", "data-twin-port": String(f.port), "data-twin-start": f.twin
    }, [
      // A label that would name the answer has a neutral twin, lockedLabel,
      // shown until the reader commits — as the entry links do.
      el("span", { "class": "label-open" }, [regSpan(f.label)]),
      el("span", { "class": "label-locked" }, [regSpan(f.lockedLabel || f.label)])
    ]);
    box.appendChild(el("ul", { "class": "entry-links" }, [el("li", null, [
      link,
      f.how ? reg("p", f.how, "how") : null,
      reg("p", {
        standard: "The link opens the twin on its failure trace, paused at this state. Press Reset there to play it through from the start.",
        novice: "The link opens the model on the sequence where something goes wrong, stopped at this moment. Press Reset there to watch it from the beginning."
      }, "how"),
      // learn.css hides this once the liveness chip beside the link reports
      // the twin running, exactly as it does for an entry's start line.
      el("p", { "class": "start" }, [
        "Start it from the repository root: ",
        el("code", { text: "scripts/dev.sh " + f.twin })
      ])
    ])]));
    var answer = el("div", { "class": "answer", hidden: "hidden" });
    box.appendChild(answer);

    link.addEventListener("click", function (ev) {
      if (!link.classList.contains("locked")) return;
      ev.preventDefault();
      hint.classList.add("nudge");
    });

    function sync() {
      var chosen = fs.predicted !== undefined;
      commit.disabled = chosen;
      commit.textContent = chosen ? "Answer committed" : "Commit my answer";
      form.querySelectorAll("input").forEach(function (i) { i.disabled = chosen; });
      revealBtn.hidden = !chosen || !!fs.revealed;
      if (chosen) {
        link.classList.remove("locked");
        link.removeAttribute("aria-disabled");
        hint.hidden = true;
      }
      if (fs.revealed) {
        answer.innerHTML = "";
        var right = fs.predicted === f.answer;
        answer.appendChild(verdict(right, f.options[f.answer]));
        answer.appendChild(reg("p", f.a));
        answer.appendChild(citeList(f.cite));
        answer.hidden = false;
      }
    }
    commit.addEventListener("click", function () {
      var picked = form.querySelector("input:checked");
      if (!picked) { hint.classList.add("nudge"); hint.textContent = "Pick one of the options first."; return; }
      fs.predicted = Number(picked.value);
      save(); sync(); onChange();
    });
    revealBtn.addEventListener("click", function () {
      fs.revealed = true;
      save(); sync(); onChange();
    });
    sync();
    return box;
  }

  function renderFailures(m, stops, state, onChange) {
    mount.appendChild(el("h2", { text: "When it goes wrong" }));
    mount.appendChild(reg("p", {
      standard: "A twin's default trace is the path where everything works. Each twin named below also carries a failure trace, with its own invariant and its own tests. Predict first, then open the failure and step through it.",
      novice: "The models normally show everything going right. Here something breaks. Guess what happens first, then open the model and watch."
    }, "prereqs"));
    stops.forEach(function (f) { mount.appendChild(renderFailure(m, f, state, onChange)); });
  }

  // setup.js's chip says "running" when anything answers on the port. A dev
  // server that found its own port busy can drift onto a neighbour's, so ask
  // the page on that port for its title and compare it with the twin's. Vite
  // lets a localhost page read it; from file:// the read fails and nothing
  // is shown.
  function checkIdentity(entry, box) {
    if (!window.fetch) return;
    fetch("http://localhost:" + entry.port + "/", { cache: "no-store" })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var m = html.match(/<title>([\s\S]*?)<\/title>/i);
        if (!m || m[1].trim() === entry.pageTitle) return;
        // A textarea decodes entities without parsing markup.
        var holder = el("textarea");
        holder.innerHTML = m[1].trim();
        box.classList.add("wrong-app");
        box.insertBefore(el("p", { "class": "wrong-app-line" }, [
          "Port " + entry.port + " is answering, but with a different app (" + holder.value +
          "), so these links will not open this twin. Stop that app, then start this one."
        ]), box.querySelector(".entry-links"));
      })
      .catch(function () { /* not running, or not readable from here */ });
  }

  // ---- the graded lab ------------------------------------------------------
  // A guided scenario is watch-mode; a lab is do-mode. The course does not
  // grade — the app does, in its own pure engine — so this section is a deep
  // link into that app's lab, the reason the lab belongs to this module, and
  // one honest self-report so a Labs-track reader can see where they are.
  function labHref(lab) {
    return "http://localhost:" + lab.port + "/#lab=" + lab.id;
  }

  function renderLab(m, state, onChange) {
    var lab = m.lab;
    if (!state.labs) state.labs = {};
    if (!state.labs[lab.id]) state.labs[lab.id] = {};
    var ls = state.labs[lab.id];
    var box = el("section", { "class": "lab" });
    box.appendChild(el("h3", null, [regSpan(lab.title)]));
    box.appendChild(reg("p", lab.goal, "question"));
    box.appendChild(reg("p", lab.lever, "how"));
    var link = el("a", {
      href: labHref(lab), "class": "entry-link", target: "_blank", rel: "noopener",
      "data-twin-port": String(lab.port), "data-twin-start": lab.twin
    }, [regSpan(lab.label)]);
    box.appendChild(el("ul", { "class": "entry-links" }, [el("li", null, [
      link,
      reg("p", lab.how, "how"),
      el("p", { "class": "start" }, [
        "Start it from the repository root: ",
        el("code", { text: "scripts/dev.sh " + lab.twin })
      ])
    ])]));
    var mark = el("button", { type: "button", text: "I passed this lab" });
    box.appendChild(el("div", { "class": "buttons marks" }, [mark]));
    var line = el("p", { "class": "hint" });
    box.appendChild(line);
    box.appendChild(citeList(lab.cite));

    function sync() {
      mark.classList.toggle("active", !!ls.passed);
      mark.textContent = ls.passed ? "Passed" : "I passed this lab";
      line.textContent = ls.passed
        ? "Marked as passed here. The app keeps the score; this page only remembers that you got there."
        : "The app grades the run and shows the score. Mark it here when it passes, to keep your place in the Labs track.";
    }
    link.addEventListener("click", function () {
      ls.attempted = true;
      save();
      onChange();
    });
    mark.addEventListener("click", function () {
      ls.passed = !ls.passed;
      ls.attempted = true;
      save();
      sync();
      onChange();
    });
    sync();
    return box;
  }

  function renderLabSection(m, state, onChange) {
    mount.appendChild(el("h2", { text: "Do it: the graded lab" }));
    mount.appendChild(reg("p", {
      standard: "A guided scenario sets the dials and narrates. A lab hands you the goal and the constraints and grades what you build: the app runs its own pure engine over your scenario and measures every constraint from the trace, so delivered work is always one of them and an idle build cannot pass.",
      novice: "So far the models have set their own controls and explained what happens. A lab is the other way round: it gives you a goal and some rules, you set the controls, and the app marks the result. One of the rules is always that the machine did real work, so doing nothing never passes."
    }, "prereqs"));
    mount.appendChild(renderLab(m, state, onChange));
  }

  // ---- the coupled chain (the capstone's last stop) -------------------------
  function renderCouplings(m) {
    var c = m.couplings;
    mount.appendChild(el("h2", { text: "The chain, coupled" }));
    mount.appendChild(reg("p", c.text, "prereqs"));
    var box = el("section", { "class": "coupling" });
    var list = el("ul", { "class": "entry-links" });
    var chain = el("a", {
      href: "http://localhost:" + c.port + "/#chain=" + c.chain,
      "class": "entry-link", target: "_blank", rel: "noopener",
      "data-twin-port": String(c.port), "data-twin-start": c.twin
    }, ["Open the chain: the AI factory, fed by engines"]);
    list.appendChild(el("li", null, [chain, reg("p", c.how, "how")]));
    var seams = el("a", {
      href: "http://localhost:" + c.port + "/#seams",
      "class": "entry-link", target: "_blank", rel: "noopener",
      "data-twin-port": String(c.port), "data-twin-start": c.twin
    }, ["Open the seam table: every hand-off and its identity"]);
    list.appendChild(el("li", null, [seams, el("p", { "class": "how" }, [
      "The couplings this chain leans on: ", el("code", { text: c.ids.join(", ") }), "."
    ])]));
    box.appendChild(list);
    box.appendChild(el("p", { "class": "start" }, [
      "Start it from the repository root: ",
      el("code", { text: "scripts/dev.sh " + c.twin })
    ]));
    box.appendChild(citeList(c.cite));
    mount.appendChild(box);
  }

  function renderEntry(entry, locked) {
    var box = el("div", { "class": "entry" });
    box.appendChild(el("h3", null, [regSpan(entry.name)]));
    if (entry.note) box.appendChild(reg("p", entry.note, "note-line"));
    var list = el("ul", { "class": "entry-links" });
    // The step-count chip describes the trace, so it goes on the first link
    // that opens the trace, not on a guided-tour link (a tour has its own,
    // different number of beats).
    var traceAt = 0;
    for (var t = entry.links.length - 1; t >= 0; t--) if (entry.links[t].kind !== "tour") traceAt = t;
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
        if (entry.trace && i === traceAt) attrs["data-twin-trace"] = entry.trace;
      }
      // A label that would give the prediction away has a neutral twin,
      // lockedLabel, shown until the reader commits.
      var a = el("a", attrs, [
        el("span", { "class": "label-open" }, [regSpan(link.label)]),
        el("span", { "class": "label-locked" }, [regSpan(link.lockedLabel || link.label)])
      ]);
      var item = el("li", null, [a]);
      if (link.how) item.appendChild(reg("p", link.how, "how"));
      if (link.kind === "lesson") {
        item.appendChild(el("p", { "class": "how", text: "The lesson tour opens at its first lesson." }));
      }
      list.appendChild(item);
    });
    box.appendChild(list);
    if (entry.port && entry.pageTitle) checkIdentity(entry, box);
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
    if (!hashParam("track") && wholeTrack(m.id) &&
        (track.failuresOnly || track.predictOnly || (step && step.only))) {
      // A bare module URL names no track. The remembered one would trim this
      // module, so show it whole; every link inside a track carries #track=.
      step = null;
    }
    if (!step && wholeTrack(m.id)) {
      // Opened under a track that skips this module (or an elective under
      // the full track): prefer a track that shows the module whole.
      track = wholeTrack(m.id);
      step = stepFor(track, m.id);
    }
    if (!step) {
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

    if (track && track.labsOnly && m.lab) {
      var doneLab = el("p", { "class": "done-line" });
      var refreshLab = function () {
        doneLab.textContent = isDone(m, track)
          ? "You have finished this stop."
          : "Pass the lab in the app, then mark it here to finish this stop.";
      };
      mount.appendChild(el("p", { "class": "trim" }, [
        "This track keeps only the lab in this module. ",
        el("a", { href: wholePath(m.id), text: "Open the whole module" }),
        " for the idea the lab is built on."
      ]));
      renderLabSection(m, state, refreshLab);
      renderNav(m, track);
      mount.appendChild(doneLab);
      refreshLab();
      return;
    }

    if (track && track.failuresOnly) {
      var onlyStops = failuresFor(m, step);
      var doneOnly = el("p", { "class": "done-line" });
      var refreshOnly = function () {
        var d = isDone(m, track);
        doneOnly.textContent = d ? "You have finished this stop." : "Reveal each answer to finish this stop.";
      };
      mount.appendChild(el("p", { "class": "trim" }, [
        "This track keeps only the failure in this module. ",
        el("a", { href: wholePath(m.id), text: "Open the whole module" }),
        " for the path where everything works."
      ]));
      renderFailures(m, onlyStops, state, refreshOnly);
      renderNav(m, track);
      mount.appendChild(doneOnly);
      refreshOnly();
      return;
    }

    if (m.prereqs.length || m.background) {
      var pre = el("p", { "class": "prereqs" }, ["Before you start: "]);
      if (m.background) { pre.appendChild(regSpan(m.background)); pre.appendChild(document.createTextNode(" ")); }
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
        return el("li", null, [regSpan(o)]);
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
      form.appendChild(el("label", { "class": "option", "for": name + "-" + i }, [input, el("span", null, [regSpan(opt)])]));
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
      answer.appendChild(verdict(right, m.predict.options[m.predict.answer]));
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
        el("a", { href: wholePath(m.id), text: "Open the whole module" }),
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
        box.appendChild(reg("p", c.q, "question"));
        var d = el("details");
        d.appendChild(el("summary", { text: "Show answer" }));
        d.appendChild(reg("p", c.a));
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

    // When it goes wrong: optional stops, not part of finishing the module
    // (the "What goes wrong" track is where they count).
    var stops = failuresFor(m, step);
    if (stops.length && !predictOnly) renderFailures(m, stops, state, function () {});

    // Do it: the graded lab, where the module's app has one. Optional, like
    // the failure stops — the "Labs" track is where it counts.
    if (m.lab && !predictOnly) renderLabSection(m, state, function () {});

    // The capstone ends on the coupled chain: the whole course, computed once.
    if (m.couplings && !predictOnly) renderCouplings(m);

    // Bridge and next.
    mount.appendChild(el("h2", { text: "Where this leads" }));
    mount.appendChild(reg("p", m.bridge.text, "bridge"));
    renderNav(m, track);
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

  function renderNav(m, track) {
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
  }

  function verdict(right, option) {
    if (right) return el("p", { "class": "verdict right", text: "Your prediction matched." });
    return el("p", { "class": "verdict wrong" }, ["The answer is: ", regSpan(option), "."]);
  }

  // The tests that settle an answer. A reader in the novice register is told
  // that the answer is tested; the test ids are for readers who will open them.
  function citeList(cites) {
    var wrap = document.createDocumentFragment();
    var p = el("p", { "class": "cite lvl-standard" }, ["Settled by "]);
    cites.forEach(function (c, i) {
      if (i) p.appendChild(document.createTextNode(", "));
      p.appendChild(el("code", { text: c }));
    });
    wrap.appendChild(p);
    wrap.appendChild(el("p", { "class": "cite lvl-novice", text: "The model's own automatic tests check this answer." }));
    return wrap;
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
    if (track.labsOnly) {
      mount.appendChild(el("p", { "class": "prereqs", text: "This track visits only the graded lab in each module that has one: a goal, some constraints, and a scenario you build yourself. The app grades the run in its own engine; each stop links back to the module the lab is built on." }));
    }
    if (track.failuresOnly) {
      mount.appendChild(el("p", { "class": "prereqs", text: "This track visits only the failure in each module: one thing that breaks, what you would see, and the test that pins what the twin does about it. Each stop links back to its whole module." }));
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
      if (track.labsOnly) {
        if (m.lab) twins.appendChild(el("span", null, [regSpan(m.lab.title)]));
      } else if (track.failuresOnly) {
        failuresFor(m, s).forEach(function (f) { twins.appendChild(el("span", null, [regSpan(f.name)])); });
      } else {
        m.entries.forEach(function (e) {
          if (s.only && s.only.indexOf(e.twin) < 0) return;
          twins.appendChild(el("span", null, [regSpan(e.name)]));
        });
      }
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
