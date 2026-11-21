/* Strehl Studio 2 mockups: navigation, fit-to-width scaling, the depth rail and the linked probe.
   SD (illustrative data computed by make-assets.py) is injected by build.py. */
(function () {
  "use strict";
  var SD = window.SD || { planes: 299, sampled: 100, ridge: [], strength: [], grid: "", grid_w: 24, grid_h: 16 };
  var GRID = SD.grid ? Uint8Array.from(atob(SD.grid), function (c) { return c.charCodeAt(0); }) : new Uint8Array(0);
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  document.body.classList.add("js");

  /* ---------- navigation and scaling ---------- */
  var screens = $$(".screen");
  function fit() {
    var actual = document.body.classList.contains("actual");
    $$(".screen.on .stage-wrap").forEach(function (wrap) {
      var stage = $(".stage", wrap);
      var s = actual ? 1 : Math.min(1, wrap.clientWidth / 1680);
      stage.style.transform = "scale(" + s + ")";
      wrap.style.height = Math.round(1050 * s) + "px";
    });
  }
  function show(id, quiet) {
    var target = document.getElementById("s-" + id) || screens[0];
    screens.forEach(function (s) { s.classList.toggle("on", s === target); });
    $$(".proto-nav button").forEach(function (b) { b.classList.toggle("on", "s-" + b.dataset.go === target.id); });
    if (!quiet) { try { history.replaceState(null, "", "#" + target.id.slice(2)); } catch (e) { /* sandboxed */ } }
    fit();
    redraw(target);
    window.scrollTo(0, 0);
  }
  document.addEventListener("click", function (e) {
    var go = e.target.closest("[data-go]");
    if (go) { show(go.dataset.go); return; }
    var theme = e.target.closest("[data-theme-set]");
    if (theme) {
      document.body.dataset.theme = theme.dataset.themeSet;
      $$("[data-theme-set]").forEach(function (b) { b.classList.toggle("on", b === theme); });
      redraw($(".screen.on"));
      return;
    }
    var flag = e.target.closest("[data-flag]");
    if (flag) { flag.classList.toggle("on"); document.body.classList.toggle(flag.dataset.flag); fit(); return; }
    var pop = e.target.closest("[data-pop-open]");
    var app = $(".screen.on .stage .app");
    if (pop && !app) { show("stack"); app = $(".screen.on .stage .app"); }
    if (pop && app) {
      var name = pop.dataset.popOpen;
      $$(".pop", app).forEach(function (p) { p.classList.toggle("on", p.dataset.pop === name && !p.classList.contains("on")); });
      var scrim = $(".scrim", app), pal = $(".pop.palette", app);
      if (scrim && pal) { scrim.classList.toggle("on", name === "palette" && pal.classList.contains("on")); }
      return;
    }
    if (app && !e.target.closest(".pop")) {
      $$(".pop.on", app).forEach(function (p) { p.classList.remove("on"); });
      var sc = $(".scrim", app); if (sc) { sc.classList.remove("on"); }
    }
    var tabGo = e.target.closest("[data-tab-go]");
    var tab = tabGo ? $('.tabs [data-tab="' + tabGo.dataset.tabGo + '"]', tabGo.closest(".insp")) : e.target.closest(".tabs [data-tab]");
    if (tab) {
      var host = tab.closest(".insp") || tab.closest(".app");
      $$(".tabs [data-tab]", tab.parentNode).forEach(function (t) { t.classList.toggle("on", t === tab); });
      $$(".tabpane", host).forEach(function (p) { p.style.display = p.dataset.tab === tab.dataset.tab ? "" : "none"; });
      return;
    }
    var lens = e.target.closest("[data-lens-set]");
    if (lens) {
      var scr = lens.closest(".app");
      scr.dataset.lens = lens.dataset.lensSet;
      $$(".seg [data-lens-set]", scr).forEach(function (t) { t.classList.toggle("on", t.dataset.lensSet === lens.dataset.lensSet); });
      return;
    }
    var loupe = e.target.closest("[data-loupe-toggle]");
    if (loupe) { loupe.classList.toggle("on"); loupe.closest(".app").dataset.loupe = loupe.classList.contains("on") ? "on" : "off"; return; }
    var opt = e.target.closest(".seg.pick span, .pickone > *");
    if (opt) { $$(":scope > *", opt.parentNode).forEach(function (t) { t.classList.toggle("on", t === opt); }); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.target.matches("input, textarea") || e.ctrlKey || e.metaKey || e.altKey) { return; }
    var i = screens.findIndex(function (s) { return s.classList.contains("on"); });
    if (e.key === "ArrowRight" && i < screens.length - 1) { show(screens[i + 1].id.slice(2)); }
    if (e.key === "ArrowLeft" && i > 0) { show(screens[i - 1].id.slice(2)); }
  });
  window.addEventListener("resize", fit);

  /* ---------- depth rail ---------- */
  function css(el, name) { return getComputedStyle(el).getPropertyValue(name).trim(); }
  function ridgeAt(t) {
    var r = SD.ridge; if (!r.length) { return 0; }
    var x = t * (r.length - 1), i = Math.floor(x), f = x - i;
    return r[i] * (1 - f) + (r[Math.min(r.length - 1, i + 1)] || 0) * f;
  }
  function areaPath(values, x0, x1, base, height) {
    var n = values.length, d = "M" + x0.toFixed(1) + " " + base;
    for (var i = 0; i < n; i++) {
      d += " L" + (x0 + (x1 - x0) * i / (n - 1)).toFixed(1) + " " + (base - values[i] * height).toFixed(1);
    }
    return d + " L" + x1.toFixed(1) + " " + base + " Z";
  }
  function drawRail(el) {
    var o = JSON.parse(el.dataset.rail || "{}");
    var app = el.closest(".app");
    var W = el.clientWidth || 1300, H = o.h || 86, pad = 22, N = o.planes || SD.planes;
    var base = H - 20, top = o.ticks || o.progress ? 18 : (o.ranges ? 17 : 8), hgt = base - top - 2;
    var X = function (p) { return pad + (p - 1) / (N - 1) * (W - 2 * pad); };
    var c = { ink: css(app, "--ink"), ink2: css(app, "--ink-2"), ink3: css(app, "--ink-3"), line: css(app, "--line-2"),
      acc: css(app, "--accent"), ok: css(app, "--ok"), warn: css(app, "--warn"), bad: css(app, "--bad"), info: css(app, "--info"), ridge: css(app, "--ridge"), panel: css(app, "--panel") };
    var id = "r" + Math.random().toString(36).slice(2, 8);
    var s = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + " " + H + '">';
    s += '<defs><pattern id="' + id + 'h" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2" height="6" fill="' + c.line + '" opacity=".55"/></pattern>';
    s += '<clipPath id="' + id + 'c"><rect x="0" y="0" width="' + (o.progress ? X(o.progress) : W) + '" height="' + H + '"/></clipPath></defs>';
    var ridge = [];
    for (var i = 0; i < 160; i++) { ridge.push(Math.pow(ridgeAt(i / 159), 0.8)); }
    (o.margins || []).forEach(function (m) {
      s += '<rect x="' + X(m[0]) + '" y="' + top + '" width="' + (X(m[1]) - X(m[0])) + '" height="' + (base - top) + '" fill="url(#' + id + 'h)"/>';
      if (X(m[1]) - X(m[0]) > 150) {
        s += '<text x="' + (X(m[0]) + X(m[1])) / 2 + '" y="' + (top + 14) + '" text-anchor="middle" fill="' + c.ink3 + '">no subject detail in these planes</text>';
      }
    });
    (o.ranges || []).forEach(function (r) {
      var col = c[r.c || "acc"];
      s += '<rect x="' + X(r.a) + '" y="' + top + '" width="' + Math.max(2, X(r.b) - X(r.a)) + '" height="' + (base - top) + '" fill="' + col + '" opacity=".16"/>';
      s += '<path d="M' + X(r.a) + " " + (top + 5) + "V" + top + "H" + X(r.b) + "V" + (top + 5) + '" stroke="' + col + '" stroke-width="1.5" fill="none"/>';
      if (r.t) { s += '<text x="' + (X(r.a) + X(r.b)) / 2 + '" y="' + (top - 3) + '" text-anchor="middle" style="fill:' + col + '">' + r.t + "</text>"; }
    });
    s += '<path d="' + areaPath(ridge, pad, W - pad, base, hgt) + '" fill="' + c.ridge + '" opacity="' + (o.progress ? ".28" : ".5") + '"/>';
    if (o.progress) { s += '<path d="' + areaPath(ridge, pad, W - pad, base, hgt) + '" fill="' + c.ok + '" opacity=".55" clip-path="url(#' + id + 'c)"/>'; }
    s += '<path class="trace" d="" fill="' + c.acc + '" fill-opacity=".2" stroke="' + c.acc + '" stroke-width="1.6"/>';
    if (o.ticks) {
      var a = o.bounds ? o.bounds[0] : 1, b = o.bounds ? o.bounds[1] : N;
      for (var t = 0; t < o.ticks; t++) {
        var p = a + (b - a) * t / (o.ticks - 1), done = o.progress && p <= o.progress;
        var col = done ? c.ok : c.line;
        if (done && o.retaken && o.retaken.indexOf(t) >= 0) { col = c.warn; }
        if (done && o.behind && p > o.progress - o.behind * (b - a) / (o.ticks - 1) - 0.01) { col = c.info; }
        s += '<rect x="' + (X(p) - 1) + '" y="5" width="2" height="' + (col === c.warn ? 10 : 7) + '" fill="' + col + '"/>';
      }
    }
    (o.flags || []).forEach(function (f) {
      s += '<path d="M' + (X(f.p) - 5) + " " + (top - 2) + "h10l-5 8z" + '" fill="' + c[f.k || "warn"] + '"><title>' + (f.t || "") + "</title></path>";
      s += '<line x1="' + X(f.p) + '" x2="' + X(f.p) + '" y1="' + (top + 6) + '" y2="' + base + '" stroke="' + c[f.k || "warn"] + '" stroke-dasharray="2 3" opacity=".7"/>';
    });
    s += '<line x1="' + pad + '" x2="' + (W - pad) + '" y1="' + base + '" y2="' + base + '" stroke="' + c.line + '"/>';
    var step = N > 200 ? 25 : 10, label = o.axis === "focus" ? function (p) { return (36900 + p * 4).toLocaleString("en-US"); } : function (p) { return p; };
    for (var q = step; q < N - step / 2; q += step) {
      s += '<line x1="' + X(q) + '" x2="' + X(q) + '" y1="' + base + '" y2="' + (base + 4) + '" stroke="' + c.line + '"/>';
      if (o.axis !== "focus" || q % 50 === 0) { s += '<text x="' + X(q) + '" y="' + (H - 4) + '" text-anchor="middle">' + label(q) + "</text>"; }
    }
    s += '<text x="' + pad + '" y="' + (H - 4) + '">near</text><text x="' + (W - pad) + '" y="' + (H - 4) + '" text-anchor="end">far</text>';
    if (o.bounds) {
      [["Start", o.bounds[0], 1], ["End", o.bounds[1], -1]].forEach(function (h) {
        var x = X(h[1]);
        s += '<line x1="' + x + '" x2="' + x + '" y1="2" y2="' + base + '" stroke="' + c.acc + '" stroke-width="2"/>';
        s += '<path d="M' + x + " 16h" + 8 * h[2] + "v12h" + -8 * h[2] + 'z" fill="' + c.acc + '"/>';
        s += '<text x="' + (x - 6 * h[2]) + '" y="13" text-anchor="' + (h[2] > 0 ? "end" : "start") + '" style="fill:' + c.acc + ';font-weight:600">' + h[0] + " " + label(h[1]) + "</text>";
      });
    }
    if (o.lens) {
      var lx = X(o.lens);
      s += '<path d="M' + (lx - 6) + " " + (base + 1) + "h12l-6 -9z" + '" fill="' + c.ink + '"/><line x1="' + lx + '" x2="' + lx + '" y1="' + top + '" y2="' + base + '" stroke="' + c.ink + '" opacity=".8"/>';
      s += '<text x="' + (lx + 8) + '" y="' + (top + 24) + '" style="fill:' + c.ink + '">lens ' + label(o.lens) + "</text>";
    }
    s += '<g class="head" style="display:none"><line y1="2" y2="' + base + '" stroke="' + c.acc + '" stroke-width="1.5"/><rect y="' + (base - 16) + '" width="34" height="15" rx="3" fill="' + c.acc + '"/><text y="' + (base - 5) + '" text-anchor="middle" style="fill:#1a1204;font-weight:700"></text></g>';
    s += '<line class="hover" y1="2" y2="' + base + '" stroke="' + c.ink2 + '" stroke-dasharray="2 2" style="display:none"/>';
    s += "</svg>";
    var host = $(".rail-svg", el) || el;
    host.innerHTML = s;
    el._X = X; el._N = N; el._geo = { base: base, hgt: hgt, pad: pad, W: W };
    setHead(el, o.playhead);
    var svg = $("svg", host), hover = $(".hover", svg), read = $(".read", el);
    svg.onmousemove = function (e) {
      var r = svg.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * W;
      var p = Math.max(1, Math.min(N, Math.round(1 + (x - pad) / (W - 2 * pad) * (N - 1))));
      hover.style.display = ""; hover.setAttribute("x1", X(p)); hover.setAttribute("x2", X(p));
      if (read) { read.textContent = "Plane " + p + " of " + N; }
    };
    svg.onmouseleave = function () { hover.style.display = "none"; if (read) { read.textContent = read.dataset.rest || ""; } };
    svg.onclick = function (e) {
      var r = svg.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * W;
      setHead(el, Math.max(1, Math.min(N, Math.round(1 + (x - pad) / (W - 2 * pad) * (N - 1)))));
    };
  }
  function setHead(el, p) {
    var g = $(".head", el); if (!g) { return; }
    if (!p) { g.style.display = "none"; return; }
    var x = el._X(p);
    g.style.display = "";
    g.querySelector("line").setAttribute("x1", x); g.querySelector("line").setAttribute("x2", x);
    g.querySelector("rect").setAttribute("x", x - 17);
    var t = g.querySelector("text"); t.setAttribute("x", x); t.textContent = p;
  }
  function setTrace(el, profile) {
    var path = $(".trace", el); if (!path || !el._geo) { return; }
    if (!profile) { path.setAttribute("d", ""); return; }
    var g = el._geo, vals = profile.map(function (v) { return v * 0.92; });
    path.setAttribute("d", areaPath(vals, g.pad, g.W - g.pad, g.base, g.hgt));
  }

  /* ---------- the probe: a core sample through the stack under the pointer ---------- */
  function profileAt(u, v) {
    var gx = Math.max(0, Math.min(SD.grid_w - 1, Math.floor(u * SD.grid_w)));
    var gy = Math.max(0, Math.min(SD.grid_h - 1, Math.floor(v * SD.grid_h)));
    var cell = gy * SD.grid_w + gx, n = SD.sampled, out = [];
    for (var i = 0; i < n; i++) { out.push((GRID[cell * n + i] || 0) / 255); }
    var sm = out.map(function (_, k) { return (out[Math.max(0, k - 1)] + out[k] * 2 + out[Math.min(n - 1, k + 1)]) / 4; });
    return { values: sm, strength: SD.strength[cell] || 0 };
  }
  function span(values, level) {
    var peak = 0, at = 0;
    values.forEach(function (v, i) { if (v > peak) { peak = v; at = i; } });
    var a = at, b = at;
    while (a > 0 && values[a - 1] >= peak * level) { a--; }
    while (b < values.length - 1 && values[b + 1] >= peak * level) { b++; }
    var k = (SD.planes - 1) / (values.length - 1);
    return { peak: Math.round(1 + at * k), a: Math.round(1 + a * k), b: Math.round(1 + b * k) };
  }
  function matrix(host, values, app) {
    var rows = ["2 px", "4", "8", "16", "32", "64", "128"], W = 252, rh = 9, n = values.length;
    var ok = css(app, "--ok"), line = css(app, "--line");
    var s = '<svg width="' + W + '" height="' + rows.length * (rh + 2) + '">';
    rows.forEach(function (label, r) {
      var w = Math.round(r * 1.4), sm = [], top = 0;
      for (var q = 0; q < n; q++) {
        var acc = 0, cnt = 0;
        for (var d = -w; d <= w; d++) { var z = q + d; if (z >= 0 && z < n) { acc += values[z]; cnt++; } }
        sm.push(acc / cnt); top = Math.max(top, acc / cnt);
      }
      s += '<text x="0" y="' + (r * (rh + 2) + 8) + '" style="font:9.5px Segoe UI,sans-serif;fill:' + css(app, "--ink-3") + '">' + label + "</text>";
      s += '<rect x="30" y="' + r * (rh + 2) + '" width="' + (W - 30) + '" height="' + rh + '" fill="' + line + '" opacity=".5"/>';
      for (var i = 0; i < n; i++) {
        if (top > 0 && sm[i] > top * 0.45) { s += '<rect x="' + (30 + i * (W - 30) / n).toFixed(1) + '" y="' + r * (rh + 2) + '" width="' + ((W - 30) / n + 0.3).toFixed(1) + '" height="' + rh + '" fill="' + ok + '"/>'; }
      }
    });
    host.innerHTML = s + "</svg>";
  }
  function probeAt(photo, uv) {
    var app = photo.closest(".app"), pinned = (photo.dataset.probe || "0.5,0.5").split(",").map(Number);
    var live = !!uv; uv = uv || pinned;
    var pr = profileAt(uv[0], uv[1]), rail = $(".rail", app), core = $(".core", app);
    var sp = span(pr.values, 0.5), wide = span(pr.values, 0.2), empty = pr.strength < 0.035;
    if (rail) { setTrace(rail, empty ? null : pr.values); setHead(rail, empty ? null : sp.peak); }
    if (!core) { return; }
    var set = function (k, t) { var e = $('[data-k="' + k + '"]', core); if (e) { e.textContent = t; } };
    set("mode", live ? "live" : "pinned");
    set("xy", Math.round(uv[0] * 7032) + ", " + Math.round(uv[1] * 4688));
    if (empty) {
      set("plane", "—"); set("range", "background");
      set("words", "No plane holds detail here. This is background: nothing to keep, nothing lost.");
    } else {
      set("plane", sp.peak); set("range", sp.a + "–" + sp.b);
      set("words", "Fine detail here comes from planes " + sp.a + "–" + sp.b + " (" + (sp.b - sp.a + 1) + " planes). Broad shapes draw on " + wide.a + "–" + wide.b + ". Nothing was filled in.");
    }
    var m = $('[data-k="matrix"]', core); if (m) { matrix(m, empty ? pr.values.map(function () { return 0; }) : pr.values, app); }
  }
  $$(".photo[data-probe]").forEach(function (photo) {
    var app = photo.closest(".app"), loupe = $(".loupe", photo);
    photo.addEventListener("mousemove", function (e) {
      var r = photo.getBoundingClientRect(), u = (e.clientX - r.left) / r.width, v = (e.clientY - r.top) / r.height;
      probeAt(photo, [u, v]);
      if (loupe) { loupe.style.clipPath = "circle(" + (photo.dataset.loupeR || 92) + "px at " + (u * 100).toFixed(2) + "% " + (v * 100).toFixed(2) + "%)"; }
      app.dataset.hover = "on";
    });
    photo.addEventListener("mouseleave", function () { probeAt(photo, null); app.dataset.hover = "off"; });
  });

  /* ---------- small instruments ---------- */
  function drawSpark(el) {
    var o = JSON.parse(el.dataset.spark || "{}"), app = el.closest(".app");
    var W = +el.getAttribute("width"), H = +el.getAttribute("height"), n = 80, vals = [], N = SD.planes;
    for (var i = 0; i < n; i++) { vals.push(Math.pow(ridgeAt(Math.max(0, Math.min(1, (i / (n - 1) - 0.5) / (o.s || 1) + 0.5 + (o.o || 0)))), 0.8)); }
    var s = "";
    (o.m || []).forEach(function (m) {
      s += '<rect x="' + (m[0] - 1) / (N - 1) * W + '" y="2" width="' + (m[1] - m[0]) / (N - 1) * W + '" height="' + (H - 6) + '" fill="' + css(app, "--line-2") + '" opacity=".35"/>';
    });
    s += '<path d="' + areaPath(vals, 0, W, H - 4, H - 8) + '" fill="' + css(app, "--ridge") + '" opacity=".6"/>';
    if (o.p) {
      s += '<clipPath id="sp' + W + '"><rect x="0" y="0" width="' + W * o.p + '" height="' + H + '"/></clipPath>';
      s += '<path d="' + areaPath(vals, 0, W, H - 4, H - 8) + '" fill="' + css(app, "--ok") + '" opacity=".8" clip-path="url(#sp' + W + ')"/>';
      s += '<line x1="' + W * o.p + '" x2="' + W * o.p + '" y1="0" y2="' + H + '" stroke="' + css(app, "--accent") + '" stroke-width="1.5"/>';
    }
    s += '<line x1="0" x2="' + W + '" y1="' + (H - 4) + '" y2="' + (H - 4) + '" stroke="' + css(app, "--line-2") + '"/>';
    el.innerHTML = s;
  }
  function drawRing(el) {
    var app = el.closest(".app"), W = +el.getAttribute("width"), c = W / 2, R = c - 14, n = 90, s = "";
    var ok = css(app, "--ok"), warn = css(app, "--warn"), acc = css(app, "--accent"), ink3 = css(app, "--ink-3");
    var P = function (i, r) { var a = i / n * Math.PI * 2 - Math.PI / 2; return [(c + Math.cos(a) * r).toFixed(1), (c + Math.sin(a) * r).toFixed(1)]; };
    [1, 2, 4, 8].forEach(function (k, ki) {
      for (var i = 0; i < n; i += (ki < 2 ? 1 : 2)) {
        var a = P(i, R - 6), b = P((i + k) % n, R - 6), refused = (i === 37 && k === 8);
        s += '<path d="M' + a[0] + " " + a[1] + " Q" + c + " " + c + " " + b[0] + " " + b[1] + '" fill="none" stroke="' + (refused ? warn : ok) + '" stroke-opacity="' + (refused ? 1 : 0.16 + ki * 0.05) + '" stroke-width="' + (refused ? 1.6 : 1) + '"/>';
      }
    });
    var a1 = P(57, R - 6), b1 = P(60, R - 6);
    s += '<path d="M' + a1[0] + " " + a1[1] + " Q" + c + " " + c + " " + b1[0] + " " + b1[1] + '" fill="none" stroke="' + acc + '" stroke-width="2"/>';
    for (var j = 0; j < n; j++) {
      var p = P(j, R), dull = j < 17 || j > 63;
      s += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="' + (j === 57 || j === 60 ? 4.5 : 2.6) + '" fill="' + (j === 57 || j === 60 ? acc : dull ? ink3 : ok) + '"/>';
    }
    s += '<text x="' + c + '" y="' + (c - 4) + '" text-anchor="middle" style="font:600 13px Segoe UI,sans-serif;fill:' + css(app, "--ink") + '">2,340 of 2,340</text>';
    s += '<text x="' + c + '" y="' + (c + 14) + '" text-anchor="middle" style="font:11.5px Segoe UI,sans-serif;fill:' + css(app, "--ink-2") + '">pair fits accepted</text>';
    el.innerHTML = s;
  }
  function drawGridmap(el) {
    var app = el.closest(".app"), W = +el.getAttribute("width"), H = +el.getAttribute("height"), rows = ["2 px", "4", "8", "16", "32", "64", "128", "tone"];
    var n = 100, x0 = 34, cw = (W - x0) / n, rh = (H - 16) / rows.length, ok = css(app, "--ok"), s = "";
    rows.forEach(function (label, r) {
      s += '<text x="0" y="' + (r * rh + rh * 0.68) + '" style="font:10.5px Segoe UI,sans-serif;fill:' + css(app, "--ink-3") + '">' + label + "</text>";
      s += '<rect x="' + x0 + '" y="' + r * rh + '" width="' + (W - x0) + '" height="' + (rh - 2) + '" fill="' + css(app, "--line") + '" opacity=".45"/>';
      for (var i = 0; i < n; i++) {
        var w = 1 + r * 2, a = 0, m = 0;
        for (var k = -w; k <= w; k++) { var j = i + k; if (j >= 0 && j < n) { a += SD.ridge[j] || 0; m++; } }
        var v = Math.min(1, Math.pow(a / m, 0.6) * (1 - r * 0.04));
        if (v > 0.06) { s += '<rect x="' + (x0 + i * cw).toFixed(1) + '" y="' + r * rh + '" width="' + (cw + 0.3).toFixed(1) + '" height="' + (rh - 2) + '" fill="' + ok + '" opacity="' + v.toFixed(2) + '"/>'; }
      }
    });
    s += '<text x="' + x0 + '" y="' + (H - 2) + '" style="font:10.5px Segoe UI,sans-serif;fill:' + css(app, "--ink-3") + '">plane 1</text><text x="' + W + '" y="' + (H - 2) + '" text-anchor="end" style="font:10.5px Segoe UI,sans-serif;fill:' + css(app, "--ink-3") + '">299</text>';
    el.innerHTML = s;
  }
  function drawLadder(el) {
    var rows = [["Fine texture", "2 px", 0, 62, 2], ["Texture", "4 px", 0.4, 77, 1], ["Small edges", "8 px", 0.9, 100, 0], ["Edges", "16 px", 1.6, 100, 0],
      ["Small forms", "32 px", 2.6, 100, 0], ["Forms", "64 px", 4, 100, 0], ["Broad forms", "128 px", 6, 100, 0], ["Broad tone", "what is left", 9, 100, 0]];
    el.innerHTML = rows.map(function (r) {
      var blur = "blur(" + r[2] + "px)", dots = 5 + r[2] * 2.2;
      return '<div class="lrow"><div><b>' + r[0] + "</b><small>" + r[1] + "</small></div>" +
        '<div class="ltile"><div class="im im-hero-small" style="filter:grayscale(1) contrast(1.5) ' + blur + '"></div></div>' +
        '<div class="ltile"><div style="background:radial-gradient(ellipse at 55% 50%,#3a3a40,#111113 70%);filter:' + blur + '"></div></div>' +
        '<div class="ltile"><div class="im im-hero-small" style="filter:grayscale(1) brightness(.45) ' + blur + '"></div><div style="background-image:radial-gradient(circle,#9be28a 0 1.3px,transparent 1.8px);background-size:' + dots + "px " + dots + 'px;opacity:' + (r[3] / 100 * 0.85) + ';-webkit-mask-image:radial-gradient(ellipse 46% 40% at 52% 50%,#000 55%,transparent 75%);mask-image:radial-gradient(ellipse 46% 40% at 52% 50%,#000 55%,transparent 75%)"></div><em>' + r[3] + " %</em></div>" +
        '<div class="ltile"><div class="im im-hero-small" style="filter:grayscale(1) brightness(.3) ' + blur + '"></div>' + (r[4] ? '<div style="background-image:radial-gradient(circle,#ff9548 0 1.5px,transparent 2px);background-size:23px 19px;opacity:.9;-webkit-mask-image:radial-gradient(ellipse 40% 34% at 52% 50%,#000 50%,transparent 75%);mask-image:radial-gradient(ellipse 40% 34% at 52% 50%,#000 50%,transparent 75%)"></div>' : "") + "<em>" + r[4] + " %</em></div>" +
        '<div class="ltile"><div class="im im-hero-small" style="filter:' + blur + '"></div></div></div>';
    }).join("");
  }
  function redraw(root) {
    if (!root) { return; }
    $$(".rail[data-rail]", root).forEach(drawRail);
    $$("[data-spark]", root).forEach(drawSpark);
    $$("[data-ring]", root).forEach(drawRing);
    $$("[data-gridmap]", root).forEach(drawGridmap);
    $$("[data-ladder]", root).forEach(drawLadder);
    $$(".photo[data-probe]", root).forEach(function (p) { probeAt(p, null); });
  }

  show((location.hash || "").slice(1) || screens[0].id.slice(2), true);

  /* Deep links, also used to check states in a headless browser:
     ?theme=lightbox&do=lens:depth;tab:recipe;pop:jobs;hover:0.4,0.5#stack */
  var qs = new URLSearchParams(location.search);
  if (qs.get("theme")) { var tb = $('[data-theme-set="' + qs.get("theme") + '"]'); if (tb) { tb.click(); } }
  (qs.get("do") || "").split(";").forEach(function (cmd) {
    var kv = cmd.split(":"), app = $(".screen.on .stage .app"), el = null;
    if (!app || !kv[1]) { return; }
    if (kv[0] === "lens") { el = $('.seg [data-lens-set="' + kv[1] + '"]', app); }
    if (kv[0] === "tab") { el = $('.tabs [data-tab="' + kv[1] + '"]', app); }
    if (kv[0] === "pop") { el = $('.top [data-pop-open="' + kv[1] + '"]', app); }
    if (el) { el.click(); }
    if (kv[0] === "hover") {
      var photo = $(".photo[data-probe]", app), uv = kv[1].split(",").map(Number), loupe = photo && $(".loupe", photo);
      if (photo) { probeAt(photo, uv); app.dataset.hover = "on"; }
      if (loupe) { loupe.style.clipPath = "circle(92px at " + uv[0] * 100 + "% " + uv[1] * 100 + "%)"; }
    }
  });
})();
