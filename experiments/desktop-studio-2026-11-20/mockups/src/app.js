/* Strehl Studio 2 mockups, iteration 2: navigation, fit-to-width scaling, the depth rail with its
   filmstrip, the plane lens (peek and hold), and the core sample.
   SD (illustrative data computed by make-assets.py) is injected by build.py. */
(function () {
  "use strict";
  var SD = window.SD || { planes: 299, sampled: 100, ridge: [], strength: [], grid_w: 24, grid_h: 16, plane_ids: [], map_w: 240, map_h: 160 };
  var bytes = function (s) { return s ? Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }) : new Uint8Array(0); };
  var GRID = bytes(SD.grid), ORDER = bytes(SD.order), SUPPORT = bytes(SD.support);
  var PLANES = (SD.plane_ids && SD.plane_ids.length) ? SD.plane_ids : Array.from({ length: 33 }, function (_, i) { return Math.round(i * (SD.planes - 1) / 32) + 1; });
  /* the detail spectrum: fine detail is cool, broad shapes are warm */
  var SPEC = ["#5fd9cf", "#7fd3ea", "#a7c9f2", "#c8c0ef", "#e2b9dc", "#f1b7b4", "#f4c18a", "#edd06c"];
  var SPEC_PAPER = ["#0f9d92", "#1f8fb5", "#3f78c9", "#6a5fc4", "#a2529f", "#c2524d", "#c47a1c", "#a58a00"];
  function spec() { return document.body.dataset.theme === "lightbox" ? SPEC_PAPER : SPEC; }
  var SIZES = ["2 px", "4", "8", "16", "32", "64", "128", "256"];
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
  document.body.classList.add("js");

  /* ---------- navigation and scaling ---------- */
  var screens = $$(".screen");
  function fit() {
    var actual = document.body.classList.contains("actual");
    $$(".screen.on .stage-wrap").forEach(function (wrap) {
      var stage = $(".stage", wrap), s = actual ? 1 : Math.min(1, wrap.clientWidth / 1680);
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
      masks = {};
      $$(".tu-sizes").forEach(function (s) { s.innerHTML = ""; });
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
    if (lens) { setLens(lens.closest(".app"), lens.dataset.lensSet); return; }
    var opt = e.target.closest(".seg.pick span, .pickone > *");
    if (opt) { $$(":scope > *", opt.parentNode).forEach(function (t) { t.classList.toggle("on", t === opt); }); }
  });
  document.addEventListener("keydown", function (e) {
    if ((e.target.matches && e.target.matches("input, textarea")) || e.ctrlKey || e.metaKey || e.altKey) { return; }
    var app = $(".screen.on .stage .app");
    if (e.key === "Escape" && app && app.dataset.hold) { release(app); return; }
    var cur = ($(".screen.on") || {}).id || "", key = e.key.toLowerCase();
    if (cur === "s-stack" && app) {
      var lensKeys = { "1": "photo", "2": "plane", "3": "depth", "4": "soft", "5": "align" };
      if (lensKeys[key]) { setLens(app, lensKeys[key]); return; }
      if (key === " ") { app.dataset.clean = "on"; e.preventDefault(); return; }
      if (key === "e") { show("engine"); return; }
    } else if (cur === "s-engine" && key === "e") { show("stack"); return; }
    if (cur === "s-flight" && key === "g") { show("glance"); return; }
    if (cur === "s-glance" && e.key === "Escape") { show("flight"); return; }
    var i = screens.findIndex(function (s) { return s.classList.contains("on"); });
    if (e.key === "ArrowRight" && i < screens.length - 1) { show(screens[i + 1].id.slice(2)); }
    if (e.key === "ArrowLeft" && i > 0) { show(screens[i - 1].id.slice(2)); }
  });
  document.addEventListener("keyup", function (e) {
    var app = $(".screen.on .stage .app");
    if (e.key === " " && app) { delete app.dataset.clean; }
  });
  window.addEventListener("resize", fit);

  /* ---------- helpers ---------- */
  function css(el, name) { return getComputedStyle(el).getPropertyValue(name).trim(); }
  function rgb(hex) {
    hex = hex.replace("#", "");
    if (hex.length === 3) { hex = hex.replace(/./g, "$&$&"); }
    return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
  }
  function ridgeAt(t) {
    var r = SD.ridge; if (!r.length) { return 0; }
    var x = clamp(t, 0, 1) * (r.length - 1), i = Math.floor(x), f = x - i;
    return r[i] * (1 - f) + (r[Math.min(r.length - 1, i + 1)] || 0) * f;
  }
  function held(p) { return Math.pow(ridgeAt((p - 1) / (SD.planes - 1)), 0.8); }
  function nearestSlot(p) {
    var best = 0, d = 1e9;
    PLANES.forEach(function (id, i) { if (Math.abs(id - p) < d) { d = Math.abs(id - p); best = i; } });
    return best;
  }
  function slotClass(i) { return "im-pl-" + (i < 10 ? "0" : "") + i; }

  /* ---------- depth rail: one bar per plane, an engraved scale beneath ---------- */
  function drawRail(el) {
    var o = JSON.parse(el.dataset.rail || "{}"), app = el.closest(".app");
    var host = $(".rail-svg", el) || el;
    var W = host.clientWidth || 1332, H = o.h || 96, pad = 20, N = o.planes || SD.planes;
    var topGap = o.ticks ? 22 : (o.ranges ? 18 : 8), base = H - 19, hgt = base - topGap;
    var step = (W - 2 * pad) / (N - 1), bw = Math.max(1, step - 1);
    var X = function (p) { return pad + (p - 1) * step; };
    var c = { ink: css(app, "--ink"), ink2: css(app, "--ink-2"), ink3: css(app, "--ink-3"), line: css(app, "--line"), line2: css(app, "--line-2"),
      acc: css(app, "--accent"), ok: css(app, "--ok"), warn: css(app, "--warn"), info: css(app, "--info"), plane: css(app, "--plane"), panel: css(app, "--panel") };
    var focus = o.axis === "focus", label = focus ? function (p) { return (36900 + p * 4).toLocaleString("en-US"); } : function (p) { return p; };
    var a0 = o.bounds ? o.bounds[0] : 1, b0 = o.bounds ? o.bounds[1] : N;
    var s = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + " " + H + '">';
    [0.5, 1].forEach(function (g) { s += '<line x1="' + pad + '" x2="' + (W - pad) + '" y1="' + (base - hgt * g) + '" y2="' + (base - hgt * g) + '" stroke="' + c.line + '"/>'; });
    (o.ranges || []).forEach(function (r) {
      s += '<rect x="' + (X(r.a) - bw / 2) + '" y="' + topGap + '" width="' + (X(r.b) - X(r.a) + bw) + '" height="' + hgt + '" fill="' + c.acc + '" opacity=".1"/>';
      s += '<path d="M' + X(r.a) + " " + (topGap - 1) + "v-5H" + X(r.b) + 'v5" stroke="' + c.acc + '" fill="none"/>';
      if (r.t) { s += '<text x="' + (X(r.b) + 7) + '" y="' + (topGap - 2) + '" style="fill:' + c.acc + ';letter-spacing:.08em">' + r.t.toUpperCase() + "</text>"; }
    });
    var top = "", dots = "";
    for (var p = 1; p <= N; p++) {
      var v = held(p), h = v * hgt, x = X(p);
      var done = !o.progress || p <= o.progress, inside = p >= a0 && p <= b0;
      if (h < 0.8) { s += '<rect x="' + (x - bw / 2).toFixed(1) + '" y="' + (base - 1) + '" width="' + bw.toFixed(1) + '" height="1" fill="' + c.line2 + '"/>'; }
      else {
        s += '<rect x="' + (x - bw / 2).toFixed(1) + '" y="' + (base - h).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" fill="' +
          (done ? c.ok : c.ink3) + '" opacity="' + (done ? (inside ? 0.6 : 0.28) : 0.3) + '"/>';
      }
      top += (p === 1 ? "M" : "L") + x.toFixed(1) + " " + (base - Math.max(h, 0.5)).toFixed(1);
      if (step >= 3.4 && done && h >= 0.8) { dots += '<circle cx="' + x.toFixed(1) + '" cy="' + (base - h).toFixed(1) + '" r="1" />'; }
    }
    s += '<path d="' + top + '" fill="none" stroke="' + c.ok + '" stroke-opacity=".9"/><g fill="' + c.ink + '" opacity=".75">' + dots + "</g>";
    (o.margins || []).forEach(function (m) {
      var mid = (X(m[0]) + X(m[1])) / 2;
      s += '<path d="M' + X(m[0]) + " " + (base - 11) + "v-4H" + X(m[1]) + 'v4" stroke="' + c.line2 + '" fill="none"/>';
      if (X(m[1]) - X(m[0]) > 190) { s += '<text x="' + mid + '" y="' + (base - 21) + '" text-anchor="middle" style="letter-spacing:.1em">PLANES ' + m[0] + "–" + m[1] + " · NO SUBJECT DETAIL</text>"; }
    });
    s += '<g class="trace"></g>';
    if (o.ticks) {
      for (var t = 0; t < o.ticks; t++) {
        var q = a0 + (b0 - a0) * t / (o.ticks - 1), isDone = o.progress && q <= o.progress, col = isDone ? c.ok : c.line2, th = 6;
        if (isDone && o.retaken && o.retaken.indexOf(t) >= 0) { col = c.warn; th = 10; }
        if (isDone && o.behind && q > o.progress - o.behind * (b0 - a0) / (o.ticks - 1) - 0.01) { col = c.info; }
        s += '<rect x="' + (X(q) - 0.75).toFixed(1) + '" y="' + (16 - th) + '" width="1.5" height="' + th + '" fill="' + col + '"/>';
      }
    }
    s += '<line x1="' + pad + '" x2="' + (W - pad) + '" y1="' + base + '" y2="' + base + '" stroke="' + c.line2 + '"/>';
    for (var k = 5; k <= N; k += 5) {
      var major = k % 25 === 0;
      s += '<line x1="' + X(k) + '" x2="' + X(k) + '" y1="' + base + '" y2="' + (base + (major ? 6 : 3)) + '" stroke="' + (major ? c.ink3 : c.line2) + '"/>';
      if (major && (!focus || k % 50 === 0) && k < N - 8) { s += '<text class="ax" x="' + X(k) + '" y="' + (H - 3) + '" text-anchor="middle">' + label(k) + "</text>"; }
    }
    s += '<text class="ax" data-w="46" x="' + pad + '" y="' + (H - 3) + '" style="letter-spacing:.12em">NEAR</text><text class="ax" data-w="40" x="' + (W - pad) + '" y="' + (H - 3) + '" text-anchor="end" style="letter-spacing:.12em">FAR</text>';
    if (o.bounds) {
      [["START", o.bounds[0], -1], ["END", o.bounds[1], 1]].forEach(function (b) {
        var x = X(b[1]);
        s += '<line x1="' + x + '" x2="' + x + '" y1="2" y2="' + base + '" stroke="' + c.acc + '" stroke-width="1.5"/>';
        s += '<path d="M' + x + " 2h" + 6 * -b[2] + 'l' + 6 * b[2] + ' 7z" fill="' + c.acc + '"/>';
        s += '<text x="' + (x + 9 * b[2]) + '" y="11" text-anchor="' + (b[2] < 0 ? "end" : "start") + '" style="fill:' + c.acc + ';letter-spacing:.1em">' + b[0] + " " + label(b[1]) + "</text>";
      });
    }
    if (o.lens) {
      var lx = X(o.lens);
      s += '<line x1="' + lx + '" x2="' + lx + '" y1="' + topGap + '" y2="' + base + '" stroke="' + c.ink + '"/><path d="M' + (lx - 5) + " " + (base + 7) + "h10l-5 -7z" + '" fill="' + c.ink + '"/>';
      s += '<text x="' + (lx + 7) + '" y="' + (topGap + 9) + '" style="fill:' + c.ink + ';letter-spacing:.1em">LENS ' + label(o.lens) + "</text>";
    }
    s += '<g class="head" style="display:none"><line y1="' + (topGap - 4) + '" y2="' + (base + 6) + '" stroke="' + c.acc + '"/><circle r="2.6" fill="' + c.acc + '"/>' +
      '<rect y="' + (H - 13) + '" width="30" height="13" fill="' + c.acc + '"/><text y="' + (H - 3) + '" text-anchor="middle" style="fill:#171204;font-weight:600"></text></g>';
    s += '<g class="hover" style="display:none"><line y1="2" y2="' + (base + 6) + '" stroke="' + c.plane + '"/>' +
      '<rect y="' + (H - 13) + '" width="30" height="13" fill="' + c.plane + '"/><text y="' + (H - 3) + '" text-anchor="middle" style="fill:#04201c;font-weight:600"></text></g>';
    host.innerHTML = s + "</svg>";
    el._g = { X: X, N: N, W: W, pad: pad, base: base, hgt: hgt, step: step, c: c };
    mark(el, "head", o.playhead || null);
    if (o.held) { mark(el, "head", o.held); }
    var film = $(".film", el);
    if (film && o.film) { drawFilm(el, film, o.film); }
    var svg = $("svg", host), read = $(".read", el);
    if (read) { read.textContent = (app.dataset.hold && read.dataset.held) || read.dataset.rest || ""; }
    var planeAt = function (e) {
      var r = svg.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * W;
      return clamp(Math.round(1 + (x - pad) / step), 1, N);
    };
    svg.onmousemove = function (e) {
      var pl = planeAt(e);
      mark(el, "hover", pl);
      if (read) { read.textContent = "Plane " + pl + " of " + N + (focus ? " · focus " + label(pl) : ""); }
      if (o.inspect) { peek(app, el, pl); }
    };
    svg.onmouseleave = function () {
      mark(el, "hover", null);
      if (read) { read.textContent = (app.dataset.hold && read.dataset.held) || read.dataset.rest || ""; }
      if (o.inspect) { peek(app, el, null); }
    };
    svg.onclick = function (e) { if (o.inspect) { hold(app, planeAt(e)); } else { mark(el, "head", planeAt(e)); } };
  }
  function mark(el, cls, p) {
    var g = $("." + cls, el), geo = el._g; if (!g || !geo) { return; }
    if (!p) { g.style.display = "none"; maskAxis(el); return; }
    var x = geo.X(p), line = g.querySelector("line"), dot = g.querySelector("circle"), box = g.querySelector("rect"), text = g.querySelector("text");
    g.style.display = "";
    line.setAttribute("x1", x); line.setAttribute("x2", x);
    if (dot) { dot.setAttribute("cx", x); dot.setAttribute("cy", geo.base - held(p) * geo.hgt); }
    box.setAttribute("x", clamp(x - 15, 0, geo.W - 30)); text.setAttribute("x", clamp(x, 15, geo.W - 15)); text.textContent = p;
    maskAxis(el);
  }
  function maskAxis(el) {
    var xs = [];
    ["head", "hover"].forEach(function (cls) {
      var g = $("." + cls, el);
      if (g && g.style.display !== "none") { xs.push(+g.querySelector("text").getAttribute("x")); }
    });
    $$("text.ax", el).forEach(function (t) {
      var x = +t.getAttribute("x"), reach = +(t.dataset.w || 28);
      t.style.opacity = xs.some(function (v) { return Math.abs(v - x) < reach; }) ? 0 : 1;
    });
  }
  function setTrace(el, profile) {
    var g = $(".trace", el), geo = el._g; if (!g || !geo) { return; }
    if (!profile) { g.innerHTML = ""; return; }
    var n = profile.length, d = "", dots = "", x0 = geo.pad, x1 = geo.W - geo.pad;
    for (var i = 0; i < n; i++) {
      var x = x0 + (x1 - x0) * i / (n - 1), y = geo.base - profile[i] * geo.hgt * 0.96;
      d += (i ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
      if (profile[i] > 0.04) { dots += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="1.3"/>'; }
    }
    g.innerHTML = '<path d="' + d + '" fill="none" stroke="' + geo.c.acc + '" stroke-width="1.3" stroke-dasharray="4 3"/><g fill="' + geo.c.acc + '">' + dots + "</g>";
  }
  function drawFilm(el, film, count) {
    var html = "", last = PLANES.length - 1;
    for (var i = 0; i < count; i++) {
      var slot = Math.round(i * last / (count - 1)), p = PLANES[slot] || 1, bars = "";
      for (var r = 0; r < 8; r++) {
        var v = 0, m = 0;
        for (var d = -r * 3; d <= r * 3; d += 3) { v += held(clamp(p + d, 1, SD.planes)); m++; }
        v = Math.pow(v / m, 0.7);
        bars += '<u style="height:' + (1 + v * 7).toFixed(1) + "px;background:" + spec()[r] + ";opacity:" + (0.25 + v * 0.75).toFixed(2) + '"></u>';
      }
      html += '<div data-plane="' + p + '" data-slot="' + slot + '"><i class="' + slotClass(slot) + '"></i><span><b>' + p + "</b><em>" + bars + "</em></span></div>";
    }
    film.innerHTML = html;
    var app = el.closest(".app"), o = JSON.parse(el.dataset.rail || "{}");
    $$("div", film).forEach(function (d) {
      d.onmouseenter = function () { mark(el, "hover", +d.dataset.plane); if (o.inspect) { peek(app, el, +d.dataset.plane); } };
      d.onmouseleave = function () { mark(el, "hover", null); if (o.inspect) { peek(app, el, null); } };
      d.onclick = function () { if (o.inspect) { hold(app, +d.dataset.plane); } else { mark(el, "head", +d.dataset.plane); } };
    });
    nearFilm(el, null);
  }
  function nearFilm(el, p) {
    var app = el.closest(".app"), heldPlane = +app.dataset.hold || 0;
    $$(".film div", el).forEach(function (d) {
      var id = +d.dataset.plane;
      d.classList.toggle("near", !!p && Math.abs(id - p) <= 5);
      d.classList.toggle("held", !!heldPlane && Math.abs(id - heldPlane) <= 5);
    });
  }

  /* ---------- the plane lens: where one plane gave the photograph its detail ---------- */
  var masks = {};
  function planeMask(p, half) {
    var at = Math.round((p - 1) / (SD.planes - 1) * (SD.sampled - 1)), key = at + "/" + (half || 2);
    half = half || 2;
    if (masks[key]) { return masks[key]; }
    var w = SD.map_w, h = SD.map_h, W = 720, H = 480;
    var small = document.createElement("canvas"); small.width = w; small.height = h;
    var sx = small.getContext("2d"), img = sx.createImageData(w, h);
    for (var i = 0; i < w * h; i++) { img.data[i * 4 + 3] = (SUPPORT[i] > 46 && Math.abs(ORDER[i] - at) <= half) ? 255 : 0; }
    sx.putImageData(img, 0, 0);
    var big = document.createElement("canvas"); big.width = W; big.height = H;
    var bx = big.getContext("2d"); bx.imageSmoothingEnabled = true; bx.imageSmoothingQuality = "high";
    bx.drawImage(small, 0, 0, W, H);
    var a = bx.getImageData(0, 0, W, H).data, m = new Uint8Array(W * H);
    for (var j = 0; j < W * H; j++) { m[j] = a[j * 4 + 3] > 104 ? 1 : 0; }
    masks[key] = { w: W, h: H, m: m };
    return masks[key];
  }
  function paintRegion(canvas, p, kind, app, half) {
    if (!canvas) { return; }
    var ctx = canvas.getContext("2d");
    if (!p || !ORDER.length) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
    var k = planeMask(p, half), W = k.w, H = k.h, m = k.m, col = rgb(css(app, "--plane")), out = ctx.createImageData(W, H), d = out.data;
    var fill = kind === "final" ? 58 : 26;
    for (var y = 1; y < H - 1; y++) {
      for (var x = 1; x < W - 1; x++) {
        var i = y * W + x; if (!m[i]) { continue; }
        var edge = !(m[i - 1] && m[i + 1] && m[i - W] && m[i + W] && m[i - 2] && m[i + 2] && m[i - 2 * W] && m[i + 2 * W]);
        var o4 = i * 4;
        if (edge) {
          if (kind === "source" && ((x + y) % 12) >= 7) { continue; }
          d[o4] = col[0]; d[o4 + 1] = col[1]; d[o4 + 2] = col[2]; d[o4 + 3] = 235;
        } else if (kind === "final" && (x % 7 === 3) && (y % 7 === 3)) {
          d[o4] = 244; d[o4 + 1] = 236; d[o4 + 2] = 170; d[o4 + 3] = 235;
        } else { d[o4] = col[0]; d[o4 + 1] = col[1]; d[o4 + 2] = col[2]; d[o4 + 3] = fill; }
      }
    }
    ctx.putImageData(out, 0, 0);
  }
  function share(p, half) {
    if (!ORDER.length) { return 0; }
    var at = Math.round((p - 1) / (SD.planes - 1) * (SD.sampled - 1)), n = 0;
    half = half || 2;
    for (var i = 0; i < ORDER.length; i++) { if (SUPPORT[i] > 46 && Math.abs(ORDER[i] - at) <= half) { n++; } }
    return n / ORDER.length;
  }
  function paintSmall(canvas, p, half, app) {
    var w = SD.map_w, h = SD.map_h, ctx = canvas.getContext("2d"), out = ctx.createImageData(w, h), d = out.data, col = rgb(css(app, "--plane"));
    var at = Math.round((p - 1) / (SD.planes - 1) * (SD.sampled - 1));
    var on = function (i) { return SUPPORT[i] > 46 && Math.abs(ORDER[i] - at) <= half; };
    for (var y = 1; y < h - 1; y++) {
      for (var x = 1; x < w - 1; x++) {
        var i = y * w + x; if (!on(i)) { continue; }
        var edge = !(on(i - 1) && on(i + 1) && on(i - w) && on(i + w)), o = i * 4;
        d[o] = col[0]; d[o + 1] = col[1]; d[o + 2] = col[2]; d[o + 3] = edge ? 255 : 110;
      }
    }
    ctx.putImageData(out, 0, 0);
  }
  function twoUp(app, p) {
    var two = $(".twoup", app); if (!two) { return; }
    paintRegion($(".tu-final canvas", two), p, "final", app);
    $(".tu-plane .base", two).className = "base im " + slotClass(nearestSlot(p));
    paintRegion($(".tu-plane canvas", two), p, "source", app);
    $$('[data-k="hold-plane"]', app).forEach(function (e) { e.textContent = p; });
    $$('[data-k="hold-share"]', app).forEach(function (e) { e.textContent = Math.round(share(p) * 1000) / 10 + " %"; });
    var sizes = $(".tu-sizes", two); if (!sizes) { return; }
    if (!sizes.firstChild) {
      sizes.innerHTML = SIZES.map(function (name, r) {
        return "<div" + (r ? "" : ' class="on"') + '><i class="im im-hero-small"><canvas width="' + SD.map_w + '" height="' + SD.map_h + '"></canvas></i><b style="color:' + spec()[r] + '">' + name + "</b><span></span></div>";
      }).join("");
    }
    $$(":scope > div", sizes).forEach(function (cell, r) {
      paintSmall($("canvas", cell), p, 2 + r * 0.9, app);
      $("span", cell).textContent = Math.round(share(p, 2 + r * 0.9) * 1000) / 10 + " % kept";
    });
  }
  function peek(app, rail, p) {
    var box = $(".peek", app), photo = $(".photo.single", app), heldPlane = +app.dataset.hold || 0;
    nearFilm(rail, p);
    if (heldPlane) { twoUp(app, p || heldPlane); return; }   /* while holding, the two-up follows the pointer */
    if (!p) {
      app.dataset.peek = "off";
      if (photo) { paintRegion($("canvas.lens-plane", photo), 0, "final", app); }
      return;
    }
    app.dataset.peek = "on";
    if (photo) { paintRegion($("canvas.lens-plane", photo), p, "final", app); }
    if (!box) { return; }
    var geo = rail._g, railBox = rail.getBoundingClientRect(), canvasBox = box.parentNode.getBoundingClientRect(), scale = railBox.width / rail.offsetWidth;
    var x = geo.X(p) + (railBox.left - canvasBox.left) / scale, w = box.offsetWidth;
    box.style.left = clamp(x - w / 2, 10, box.parentNode.offsetWidth - w - 10) + "px";
    $(".peek-arrow", box).style.left = clamp(x - parseFloat(box.style.left), 12, w - 12) + "px";
    $(".peek-im", box).className = "peek-im im " + slotClass(nearestSlot(p));
    paintRegion($("canvas", box), p, "source", app);
    $('[data-k="pk-plane"]', box).textContent = "Plane " + p;
    $('[data-k="pk-share"]', box).textContent = Math.round(share(p) * 1000) / 10 + " % of the frame kept from here";
  }
  function hold(app, p) {
    if (+app.dataset.hold === p) { release(app); return; }
    app.dataset.hold = p; app.dataset.plane = p; app.dataset.lens = "plane"; app.dataset.peek = "off";
    var rail = $(".rail", app);
    twoUp(app, p);
    $$(".seg [data-lens-set]", app).forEach(function (t) { t.classList.toggle("on", t.dataset.lensSet === "plane"); });
    if (rail) { mark(rail, "head", p); setTrace(rail, null); nearFilm(rail, null); restRead(app); }
  }
  function restRead(app) {
    var read = $(".rail .read", app);
    if (read) { read.textContent = (app.dataset.hold && read.dataset.held) || read.dataset.rest || ""; }
  }
  function release(app) {
    delete app.dataset.hold;
    if (app.dataset.lens === "plane") { app.dataset.lens = "photo"; }
    $$(".seg [data-lens-set]", app).forEach(function (t) { t.classList.toggle("on", t.dataset.lensSet === app.dataset.lens); });
    var photo = $(".photo.single", app), rail = $(".rail", app);
    if (photo) { paintRegion($("canvas.lens-plane", photo), 0, "final", app); probe(photo, null); }
    if (rail) { nearFilm(rail, null); }
    restRead(app);
  }
  function setLens(app, name) {
    if (name === "plane") { hold(app, +app.dataset.plane || 143); return; }
    if (app.dataset.hold) { delete app.dataset.hold; var rail = $(".rail", app); if (rail) { nearFilm(rail, null); } }
    app.dataset.lens = name;
    $$(".seg [data-lens-set]", app).forEach(function (t) { t.classList.toggle("on", t.dataset.lensSet === name); });
    var photo = $(".photo.single", app);
    if (photo) { paintRegion($("canvas.lens-plane", photo), 0, "final", app); probe(photo, null); }
  }

  /* ---------- the core sample: one region of the photograph, plane by plane ---------- */
  function profileAt(u, v) {
    var gx = clamp(Math.floor(u * SD.grid_w), 0, SD.grid_w - 1), gy = clamp(Math.floor(v * SD.grid_h), 0, SD.grid_h - 1);
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
  function strips(host, values, app, marks) {
    var W = 232, x0 = 34, rh = 8, gap = 3, n = values.length, s = '<svg width="' + (x0 + W) + '" height="' + (8 * (rh + gap) + 12) + '">';
    SIZES.forEach(function (name, r) {
      var w = Math.round(r * 1.5), sm = [], top = 0, y = r * (rh + gap);
      for (var q = 0; q < n; q++) {
        var acc = 0, cnt = 0;
        for (var d = -w; d <= w; d++) { var z = q + d; if (z >= 0 && z < n) { acc += values[z]; cnt++; } }
        sm.push(acc / cnt); top = Math.max(top, acc / cnt);
      }
      s += '<text x="0" y="' + (y + 7.5) + '" style="font:9.5px var(--ui);letter-spacing:.04em;fill:' + spec()[r] + '">' + name + "</text>";
      s += '<rect x="' + x0 + '" y="' + y + '" width="' + W + '" height="' + rh + '" fill="' + css(app, "--line") + '"/>';
      for (var i = 0; i < n; i++) {
        var val = top > 0 ? sm[i] / top : 0;
        if (val > 0.05) { s += '<rect x="' + (x0 + i * W / n).toFixed(1) + '" y="' + y + '" width="' + (W / n + 0.4).toFixed(1) + '" height="' + rh + '" fill="' + spec()[r] + '" opacity="' + Math.min(1, val * 1.05).toFixed(2) + '"/>'; }
      }
    });
    (marks || []).forEach(function (p) {
      var x = x0 + (p - 1) / (SD.planes - 1) * W;
      s += '<line x1="' + x.toFixed(1) + '" x2="' + x.toFixed(1) + '" y1="-1" y2="' + (8 * (rh + gap) - gap + 1) + '" stroke="' + css(app, "--ink") + '" stroke-width="1"/>';
    });
    var yy = 8 * (rh + gap) + 9;
    s += '<text x="' + x0 + '" y="' + yy + '" style="font:9.5px var(--ui);fill:' + css(app, "--ink-3") + '">1</text><text x="' + (x0 + W) + '" y="' + yy + '" text-anchor="end" style="font:9.5px var(--ui);fill:' + css(app, "--ink-3") + '">' + SD.planes + "</text>";
    host.innerHTML = s + "</svg>";
  }
  function crop(el, cls, u, v, r, photoRatio) {
    if (!el) { return; }
    var size = el.offsetWidth || 88, z = 1 / r;              /* r: reticle width as a share of the photograph */
    el.className = "crop im " + cls;
    el.style.backgroundSize = (z * 100) + "% auto";
    var bw = size * z, bh = bw / photoRatio;
    el.style.backgroundPosition = (-(u * bw - size / 2)).toFixed(1) + "px " + (-(v * bh - size / 2)).toFixed(1) + "px";
  }
  function probe(photo, uv) {
    var app = photo.closest(".app"), pinned = (photo.dataset.probe || "0.5,0.5").split(",").map(Number);
    var live = !!uv; uv = uv || pinned;
    var pr = profileAt(uv[0], uv[1]), rail = $(".rail", app), cs = $(".cs", photo), ret = $(".reticle", photo);
    var sp = span(pr.values, 0.5), wide = span(pr.values, 0.2), empty = pr.strength < 0.035, R = 0.115;
    if (rail && !app.dataset.hold) { setTrace(rail, empty ? null : pr.values); mark(rail, "head", empty ? null : sp.peak); }
    if (ret) {
      ret.style.left = (uv[0] - R / 2) * 100 + "%"; ret.style.top = (uv[1] - R * 0.75) * 100 + "%";
      ret.style.width = R * 100 + "%"; ret.style.height = R * 150 + "%";
      ret.classList.toggle("empty", empty);
    }
    if (!cs) { return; }
    var W = photo.offsetWidth, H = photo.offsetHeight, cw = cs.offsetWidth || 330, ch = cs.offsetHeight || 340;
    var right = (uv[0] + R / 2) * W + 16 + cw < W - 8, x = right ? (uv[0] + R / 2) * W + 16 : (uv[0] - R / 2) * W - 16 - cw, y = clamp(uv[1] * H - ch / 2, 8, H - ch - 8);
    cs.style.transform = "translate(" + clamp(x, 8, W - cw - 8).toFixed(0) + "px," + y.toFixed(0) + "px)";
    cs.style.setProperty("--ly", clamp(uv[1] * H - y, 10, ch - 10).toFixed(0) + "px");
    cs.classList.toggle("r", right); cs.classList.toggle("l", !right);
    cs.classList.toggle("live", live);
    var set = function (k, t) { var e = $('[data-k="' + k + '"]', cs); if (e) { e.textContent = t; } };
    var pct = function (slot) { var i = Math.round((PLANES[slot] - 1) / (SD.planes - 1) * (pr.values.length - 1)); return Math.round(Math.min(1, pr.values[i] * 1.02) * 92); };
    var lead = PLANES.map(function (_, i) { return i; }).sort(function (a, b) { return pct(b) - pct(a) || Math.abs(PLANES[a] - sp.peak) - Math.abs(PLANES[b] - sp.peak); }).slice(0, 3);
    var s1 = lead[0], s2 = lead[1], s3 = lead[2];
    set("mode", live ? "live" : "pinned");
    set("xy", Math.round(R * 7032) + " px square at " + Math.round(uv[0] * 7032) + ", " + Math.round(uv[1] * 4688));
    crop($('[data-k="c0"]', cs), "im-hero", uv[0], uv[1], R, 1.5);
    [[s1, "c1", "l1"], [s2, "c2", "l2"], [s3, "c3", "l3"]].forEach(function (t) {
      crop($('[data-k="' + t[1] + '"]', cs), slotClass(t[0]), uv[0], uv[1], R, 1.5);
      set(t[2], empty ? "plane " + PLANES[t[0]] : "plane " + PLANES[t[0]] + " · " + pct(t[0]) + " %");
    });
    if (empty) {
      set("words", "No plane holds detail here. This is background: nothing to keep, nothing lost.");
    } else {
      set("words", "Fine detail here comes from planes " + sp.a + "–" + sp.b + " (" + (sp.b - sp.a + 1) + " planes). Broad shapes draw on " + wide.a + "–" + wide.b + ". Nothing was filled in.");
    }
    var st = $('[data-k="strips"]', cs);
    if (st) { strips(st, empty ? pr.values.map(function () { return 0; }) : pr.values, app, empty ? [] : [PLANES[s1], PLANES[s2], PLANES[s3]]); }
  }
  $$(".photo[data-probe]").forEach(function (photo) {
    var app = photo.closest(".app");
    photo.addEventListener("mousemove", function (e) {
      if (e.target.closest(".cs")) { return; }
      var r = photo.getBoundingClientRect();
      probe(photo, [clamp((e.clientX - r.left) / r.width, 0, 1), clamp((e.clientY - r.top) / r.height, 0, 1)]);
      app.dataset.hover = "on";
    });
    photo.addEventListener("mouseleave", function () { probe(photo, null); app.dataset.hover = "off"; });
    photo.addEventListener("click", function (e) {
      if (e.target.closest(".cs")) { return; }
      var r = photo.getBoundingClientRect();
      photo.dataset.probe = ((e.clientX - r.left) / r.width).toFixed(3) + "," + ((e.clientY - r.top) / r.height).toFixed(3);
      probe(photo, null);
    });
  });

  /* ---------- small instruments ---------- */
  function drawMm(svg) {
    var mm = +svg.dataset.mm, W = svg.parentNode.offsetWidth, app = svg.closest(".app"), s = "", per = W / mm;
    svg.setAttribute("width", W); svg.setAttribute("height", 20);
    for (var t = 0; t <= Math.floor(mm * 10); t++) {
      var x = t / 10 * per, major = t % 10 === 0, mid = t % 5 === 0;
      s += '<line x1="' + x.toFixed(1) + '" x2="' + x.toFixed(1) + '" y1="0" y2="' + (major ? 8 : mid ? 5 : 3) + '" stroke="' + css(app, major ? "--ink-3" : "--line-2") + '"/>';
      if (major) { s += '<text x="' + (x + 3).toFixed(1) + '" y="17" style="font:9.5px var(--ui);letter-spacing:.06em;fill:' + css(app, "--ink-3") + '">' + (t / 10) + (t === 0 ? " mm" : "") + "</text>"; }
    }
    svg.innerHTML = s;
  }
  function drawSpark(el) {
    var o = JSON.parse(el.dataset.spark || "{}"), app = el.closest(".app");
    var W = +el.getAttribute("width"), H = +el.getAttribute("height"), n = 76, s = "", bw = W / n - 1;
    for (var i = 0; i < n; i++) {
      var t = clamp((i / (n - 1) - 0.5) / (o.s || 1) + 0.5 + (o.o || 0), 0, 1), v = Math.pow(ridgeAt(t), 0.8), h = Math.max(1, v * (H - 6));
      var done = !o.p || i / (n - 1) <= o.p;
      s += '<rect x="' + (i * W / n).toFixed(1) + '" y="' + (H - 3 - h).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" fill="' + css(app, v < 0.02 ? "--line-2" : done ? "--ok" : "--ink-3") + '" opacity="' + (v < 0.02 ? 1 : done ? 0.7 : 0.4) + '"/>';
    }
    if (o.p) { s += '<line x1="' + W * o.p + '" x2="' + W * o.p + '" y1="0" y2="' + H + '" stroke="' + css(app, "--accent") + '"/>'; }
    el.innerHTML = s;
  }
  function drawRing(el) {
    var app = el.closest(".app"), W = +el.getAttribute("width"), c = W / 2, R = c - 14, n = 90, s = "";
    var ok = css(app, "--ok"), warn = css(app, "--warn"), acc = css(app, "--accent"), ink3 = css(app, "--ink-3");
    var P = function (i, r) { var a = i / n * Math.PI * 2 - Math.PI / 2; return [(c + Math.cos(a) * r).toFixed(1), (c + Math.sin(a) * r).toFixed(1)]; };
    [1, 2, 4, 8].forEach(function (k, ki) {
      for (var i = 0; i < n; i += (ki < 2 ? 1 : 2)) {
        var a = P(i, R - 6), b = P((i + k) % n, R - 6), refused = (i === 37 && k === 8);
        s += '<path d="M' + a[0] + " " + a[1] + " Q" + c + " " + c + " " + b[0] + " " + b[1] + '" fill="none" stroke="' + (refused ? warn : ok) + '" stroke-opacity="' + (refused ? 1 : 0.16 + ki * 0.05) + '" stroke-width="' + (refused ? 1.4 : 1) + '"/>';
      }
    });
    var a1 = P(57, R - 6), b1 = P(60, R - 6);
    s += '<path d="M' + a1[0] + " " + a1[1] + " Q" + c + " " + c + " " + b1[0] + " " + b1[1] + '" fill="none" stroke="' + acc + '" stroke-width="1.6"/>';
    for (var j = 0; j < n; j++) {
      var p = P(j, R), dull = j < 17 || j > 63, sel = j === 57 || j === 60, r = sel ? 3.5 : 2;
      s += '<rect x="' + (p[0] - r) + '" y="' + (p[1] - r) + '" width="' + r * 2 + '" height="' + r * 2 + '" fill="' + (sel ? acc : dull ? ink3 : ok) + '" transform="rotate(' + (j / n * 360) + " " + p[0] + " " + p[1] + ')"/>';
    }
    s += '<text x="' + c + '" y="' + (c - 2) + '" text-anchor="middle" style="font:300 26px var(--ui);fill:' + css(app, "--ink") + '">2,340</text>';
    s += '<text x="' + c + '" y="' + (c + 16) + '" text-anchor="middle" style="font:600 9.5px var(--ui);letter-spacing:.13em;fill:' + css(app, "--ink-3") + '">PAIR FITS</text>';
    el.innerHTML = s;
  }
  function drawGridmap(el) {
    var app = el.closest(".app"), W = +el.getAttribute("width"), H = +el.getAttribute("height"), rows = SIZES.concat([]);
    var n = 100, x0 = 34, cw = (W - x0) / n, rh = (H - 16) / rows.length, s = "";
    rows.forEach(function (label, r) {
      s += '<text x="0" y="' + (r * rh + rh * 0.66) + '" style="font:9.5px var(--ui);fill:' + spec()[r] + '">' + label + "</text>";
      s += '<rect x="' + x0 + '" y="' + r * rh + '" width="' + (W - x0) + '" height="' + (rh - 3) + '" fill="' + css(app, "--line") + '"/>';
      for (var i = 0; i < n; i++) {
        var w = 1 + r * 2, a = 0, m = 0;
        for (var k = -w; k <= w; k++) { var j = i + k; if (j >= 0 && j < n) { a += SD.ridge[j] || 0; m++; } }
        var v = Math.min(1, Math.pow(a / m, 0.6));
        if (v > 0.06) { s += '<rect x="' + (x0 + i * cw).toFixed(1) + '" y="' + r * rh + '" width="' + (cw + 0.3).toFixed(1) + '" height="' + (rh - 3) + '" fill="' + spec()[r] + '" opacity="' + v.toFixed(2) + '"/>'; }
      }
    });
    s += '<text x="' + x0 + '" y="' + (H - 2) + '" style="font:9.5px var(--ui);fill:' + css(app, "--ink-3") + '">1</text><text x="' + W + '" y="' + (H - 2) + '" text-anchor="end" style="font:9.5px var(--ui);fill:' + css(app, "--ink-3") + '">299</text>';
    el.innerHTML = s;
  }
  function drawLadder(el) {
    var rows = [["Fine texture", "2 px", 0, 62, 2], ["Texture", "4 px", 0.4, 77, 1], ["Small edges", "8 px", 0.9, 100, 0], ["Edges", "16 px", 1.6, 100, 0],
      ["Small forms", "32 px", 2.6, 100, 0], ["Forms", "64 px", 4, 100, 0], ["Broad forms", "128 px", 6, 100, 0], ["Broad tone", "what is left", 9, 100, 0]];
    el.innerHTML = rows.map(function (r, idx) {
      var blur = "blur(" + r[2] + "px)", dots = 5 + r[2] * 2.2, m = "radial-gradient(ellipse 46% 40% at 52% 50%,#000 55%,transparent 75%)";
      return '<div class="lrow"><div><b style="box-shadow:inset 2px 0 0 ' + spec()[idx] + ';padding-left:8px">' + r[0] + '</b><small style="padding-left:8px">' + r[1] + "</small></div>" +
        '<div class="ltile"><div class="im im-hero-small" style="filter:grayscale(1) contrast(1.5) ' + blur + '"></div></div>' +
        '<div class="ltile"><div style="background:radial-gradient(ellipse at 55% 50%,#333338,#101012 70%);filter:' + blur + '"></div></div>' +
        '<div class="ltile"><div class="im im-hero-small" style="filter:grayscale(1) brightness(.45) ' + blur + '"></div><div style="background-image:radial-gradient(circle,#a9c779 0 1.2px,transparent 1.7px);background-size:' + dots + "px " + dots + "px;opacity:" + (r[3] / 100 * 0.9) + ";-webkit-mask-image:" + m + ";mask-image:" + m + '"></div><em>' + r[3] + " %</em></div>" +
        '<div class="ltile"><div class="im im-hero-small" style="filter:grayscale(1) brightness(.3) ' + blur + '"></div>' + (r[4] ? '<div style="background-image:radial-gradient(circle,#f08a4b 0 1.4px,transparent 1.9px);background-size:23px 19px;opacity:.9;-webkit-mask-image:' + m + ";mask-image:" + m + '"></div>' : "") + "<em>" + r[4] + " %</em></div>" +
        '<div class="ltile"><div class="im im-hero-small" style="filter:' + blur + '"></div></div></div>';
    }).join("");
  }
  function redraw(root) {
    if (!root) { return; }
    $$(".rail[data-rail]", root).forEach(drawRail);
    $$("svg[data-mm]", root).forEach(drawMm);
    $$("[data-spark]", root).forEach(drawSpark);
    $$("[data-ring]", root).forEach(drawRing);
    $$("[data-gridmap]", root).forEach(drawGridmap);
    $$("[data-ladder]", root).forEach(drawLadder);
    $$(".photo[data-probe]", root).forEach(function (p) { probe(p, null); });
    $$(".stage .app[data-hold]", root).forEach(function (a) { var p = +a.dataset.hold; delete a.dataset.hold; hold(a, p); });
  }

  show((location.hash || "").slice(1) || screens[0].id.slice(2), true);

  /* Deep links, also used to check states in a headless browser:
     ?theme=lightbox&do=lens:depth;tab:recipe;pop:jobs;hover:0.4,0.5;peek:95;hold:95#stack */
  var qs = new URLSearchParams(location.search);
  if (qs.get("theme")) { var tb = $('[data-theme-set="' + qs.get("theme") + '"]'); if (tb) { tb.click(); } }
  (qs.get("do") || "").split(";").forEach(function (cmd) {
    var kv = cmd.split(":"), app = $(".screen.on .stage .app"), el = null;
    if (!app || !kv[1]) { return; }
    if (kv[0] === "lens") { setLens(app, kv[1]); }
    if (kv[0] === "tab") { el = $('.tabs [data-tab="' + kv[1] + '"]', app); }
    if (kv[0] === "pop") { el = $('.top [data-pop-open="' + kv[1] + '"]', app); }
    if (el) { el.click(); }
    var rail = $(".rail", app);
    if (kv[0] === "peek" && rail) { mark(rail, "hover", +kv[1]); peek(app, rail, +kv[1]); }
    if (kv[0] === "hold") { hold(app, +kv[1]); }
    if (kv[0] === "hover") {
      var photo = $(".photo[data-probe]", app), uv = kv[1].split(",").map(Number);
      if (photo) { probe(photo, uv); app.dataset.hover = "on"; }
    }
  });
})();
