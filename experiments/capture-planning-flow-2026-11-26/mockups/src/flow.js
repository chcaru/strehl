
/* Capture planning flow mockups: the depth rail with the measurement's evidence drawn on it.
   Every curve here is fabricated for the picture; none is engine or camera output. */
(function () {
  "use strict";
  function css(el, name) { return getComputedStyle(el).getPropertyValue(name).trim(); }
  function fmt(p) { return Math.round(p).toLocaleString("en-US"); }
  function clamp01(v) { return Math.max(0, Math.min(1, v)); }
  function sharpness(p, s) {
    var u = (p - s[0]) / (s[1] - s[0]);
    var edge = clamp01((u + 0.05) / 0.09) * clamp01((1.05 - u) / 0.09);
    var body = 0.56 + 0.26 * Math.sin(u * 3.05) + 0.07 * Math.sin(u * 15 + 1) + 0.04 * Math.sin(u * 37);
    return Math.max(0.035, edge * body);
  }
  function draw(el) {
    var o = JSON.parse(el.dataset.flowrail || "{}"), app = el.closest(".app"), host = el.querySelector(".rail-svg");
    var W = host.clientWidth || 1332, H = o.h || 118, pad = 20, lane = 29, top = 38, base = H - 19, hgt = base - top;
    var lo = o.view[0], hi = o.view[1];
    var X = function (p) { return pad + (p - lo) / (hi - lo) * (W - 2 * pad); };
    var c = { ink: css(app, "--ink"), ink2: css(app, "--ink-2"), ink3: css(app, "--ink-3"), line: css(app, "--line"), line2: css(app, "--line-2"),
      acc: css(app, "--accent"), ok: css(app, "--ok"), warn: css(app, "--warn"), plane: css(app, "--plane") };
    var s = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + " " + H + '">';
    [0.5, 1].forEach(function (g) { s += '<line x1="' + pad + '" x2="' + (W - pad) + '" y1="' + (base - hgt * g) + '" y2="' + (base - hgt * g) + '" stroke="' + c.line + '"/>'; });
    var a = o.start, b = o.end;
    /* measured: tiles in focus by position (the survey's counts), or the sweep's peaks by 40 units */
    var real = (o.real && window.CPF) ? (o.real === "sweep" ? window.CPF.sweep : window.CPF) : null;
    if (real) {
      var top0 = Math.max.apply(null, real.counts), rw = Math.max(1, real.step * (W - 2 * pad) / (hi - lo) - 1);
      real.counts.forEach(function (n, k) {
        var rp = real.from + k * real.step, rh = n / top0 * hgt * 0.96;
        if (n > 0 && rp >= lo && rp <= hi) {
          s += '<rect x="' + (X(rp) - rw / 2).toFixed(1) + '" y="' + (base - rh).toFixed(1) + '" width="' + rw.toFixed(1) + '" height="' + rh.toFixed(1) + '" fill="' + c.plane + '" opacity="' + (o.real === "sweep" ? 0.42 : 0.8) + '"/>';
        }
      });
    } else if (o.profile) {
      var stepB = o.bar || 7, bw = Math.max(1, stepB * (W - 2 * pad) / (hi - lo) - 1), path = "", first = true;
      var until = o.profile.from + (o.profile.to - o.profile.from) * (o.profile.shown === undefined ? 1 : o.profile.shown);
      for (var p = o.profile.from; p <= until; p += stepB) {
        var v = sharpness(p, o.profile.subject), h = v * hgt, x = X(p), inside = (a === undefined || p >= a) && (b === undefined || p <= b);
        s += '<rect x="' + (x - bw / 2).toFixed(1) + '" y="' + (base - h).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" fill="' + c.ok + '" opacity="' + (inside ? 0.6 : 0.28) + '"/>';
        path += (first ? "M" : "L") + x.toFixed(1) + " " + (base - h).toFixed(1); first = false;
      }
      s += '<path d="' + path + '" fill="none" stroke="' + c.ok + '" stroke-opacity=".9"/>';
    }
    /* planned planes; a taller tick where a highlight group is taken */
    if (o.step && a !== undefined && b !== undefined) {
      var n = 0;
      for (var q = a; q <= b + 0.01; q += o.step) {
        var tall = o.hl && n % o.hl === 0 && (!o.hlspan || (q >= o.hlspan[0] && q <= o.hlspan[1]));
        s += '<rect x="' + (X(q) - 0.75).toFixed(1) + '" y="' + (tall ? 5 : 10) + '" width="1.5" height="' + (tall ? 11 : 6) + '" fill="' + (tall ? c.ink2 : c.line2) + '"/>';
        n++;
      }
    }
    /* the evidence lane: the subject's sharp range, or the RAW survey's positions while it runs */
    if (o.subject) {
      var x0 = X(o.subject[0]), x1 = X(o.subject[1]);
      s += '<path d="M' + x0 + " " + (lane - 4) + "v8M" + x1 + " " + (lane - 4) + "v8M" + x0 + " " + lane + "H" + x1 + '" stroke="' + c.plane + '" stroke-width="1.5" fill="none"/>';
      s += '<text x="' + (x0 + 8) + '" y="' + (lane - 5) + '" style="fill:' + c.plane + ';letter-spacing:.1em">SUBJECT SHARP ' + fmt(o.subject[0]) + " – " + fmt(o.subject[1]) + "</text>";
    }
    if (o.survey) {
      var shots = [];
      for (var i = 0; i < o.survey.dense[2]; i++) { shots.push([o.survey.dense[0] + i * o.survey.dense[1], 1]); }
      if (o.survey.grid) {            /* [from, to, count]: the long shutter everywhere, the short at every second and at both ends */
        for (var q = 0; q < o.survey.grid[2]; q++) {
          shots.push([o.survey.grid[0] + (o.survey.grid[1] - o.survey.grid[0]) * q / (o.survey.grid[2] - 1), (q % 2 === 0 || q === o.survey.grid[2] - 1) ? 2 : 1]);
        }
      }
      for (var k = 0; o.survey.pairs && k < o.survey.pairs[2]; k++) { shots.push([o.survey.pairs[0] + (o.survey.pairs[1] - o.survey.pairs[0]) * k / (o.survey.pairs[2] - 1), 2]); }
      shots.sort(function (m, r) { return m[0] - r[0]; });
      var taken = 0;
      shots.forEach(function (shot) {
        for (var e = 0; e < shot[1]; e++) {
          var done = taken < o.survey.taken; taken++;
          s += '<rect x="' + (X(shot[0]) - 1.5).toFixed(1) + '" y="' + (lane - 5 + e * 6) + '" width="3" height="4" fill="' + (done ? c.plane : "none") + '" stroke="' + (done ? "none" : c.ink3) + '" stroke-width="1"/>';
        }
      });
    }
    /* how far the glints go, by depth, from the survey's short frames */
    if (o.glints) {
      var gp = "", dots = "", m = o.glints.length;
      o.glints.forEach(function (g, idx) {
        var gx = X(o.subject[0] + (o.subject[1] - o.subject[0]) * idx / (m - 1)), gy = base - g * hgt * 0.94;
        gp += (idx ? "L" : "M") + gx.toFixed(1) + " " + gy.toFixed(1);
        dots += '<rect x="' + (gx - 2).toFixed(1) + '" y="' + (gy - 2).toFixed(1) + '" width="4" height="4" transform="rotate(45 ' + gx.toFixed(1) + " " + gy.toFixed(1) + ')"/>';
      });
      s += '<path d="' + gp + '" fill="none" stroke="' + c.warn + '" stroke-width="1.3" stroke-dasharray="4 3"/><g fill="' + c.warn + '">' + dots + "</g>";
    }
    /* the scale */
    s += '<line x1="' + pad + '" x2="' + (W - pad) + '" y1="' + base + '" y2="' + base + '" stroke="' + c.line2 + '"/>';
    for (var t = Math.ceil(lo / 20) * 20; t <= hi; t += 20) {
      var major = t % 100 === 0;
      s += '<line x1="' + X(t) + '" x2="' + X(t) + '" y1="' + base + '" y2="' + (base + (major ? 6 : 3)) + '" stroke="' + (major ? c.ink3 : c.line2) + '"/>';
      if (major && X(t) > pad + 60 && X(t) < W - pad - 50) { s += '<text x="' + X(t) + '" y="' + (H - 3) + '" text-anchor="middle">' + fmt(t) + "</text>"; }
    }
    s += '<text x="' + pad + '" y="' + (H - 3) + '" style="letter-spacing:.12em">NEAR</text><text x="' + (W - pad) + '" y="' + (H - 3) + '" text-anchor="end" style="letter-spacing:.12em">FAR</text>';
    [["START", a, -1], ["END", b, 1]].forEach(function (mk) {
      if (mk[1] === undefined) { return; }
      var x = X(mk[1]);
      s += '<line x1="' + x + '" x2="' + x + '" y1="2" y2="' + base + '" stroke="' + c.acc + '" stroke-width="1.5"/>';
      s += '<path d="M' + x + " 2h" + 6 * -mk[2] + "l" + 6 * mk[2] + ' 7z" fill="' + c.acc + '"/>';
      s += '<text x="' + (x + 9 * mk[2]) + '" y="11" text-anchor="' + (mk[2] < 0 ? "end" : "start") + '" style="fill:' + c.acc + ';letter-spacing:.1em">' + mk[0] + " " + fmt(mk[1]) + "</text>";
    });
    if (o.lens) {
      var lx = X(o.lens);
      s += '<line x1="' + lx + '" x2="' + lx + '" y1="' + top + '" y2="' + base + '" stroke="' + c.ink + '"/><path d="M' + (lx - 5) + " " + (base + 7) + 'h10l-5 -7z" fill="' + c.ink + '"/>';
      var label = "LENS " + fmt(o.lens);
      if (o.sharp) {
        /* the sharp depth as a ruler at the lens: count the plane ticks under it */
        var r0 = X(o.lens - o.sharp / 2), r1 = X(o.lens + o.sharp / 2), ry = top + 16;
        s += '<path d="M' + r0 + " " + (ry - 4) + "v8M" + r1 + " " + (ry - 4) + "v8M" + r0 + " " + ry + "H" + r1 + '" stroke="' + c.ink + '" fill="none"/>';
        label += " · SHARP OVER " + o.sharp;
      }
      s += '<text x="' + (lx + 7) + '" y="' + (top + 9) + '" style="fill:' + c.ink + ';letter-spacing:.1em">' + label + "</text>";
    }
    host.innerHTML = s + "</svg>";
  }
  /* the core sample's curve: one tile's contrast against focus, the three frames marked */
  function core(el) {
    var d = window.CPF && window.CPF.core, app = el.closest(".app");
    var w = el.clientWidth || 240, h = 46;
    if (!d) { el.innerHTML = ""; return; }
    var lo = 32500, hi = 33000, top = Math.max.apply(null, d.curve), pts = [];
    d.curve.forEach(function (v, k) {
      var p = d.curve_from + k * d.curve_step;
      if (p >= lo && p <= hi) { pts.push(((p - lo) / (hi - lo) * w).toFixed(1) + "," + (h - 6 - v / top * (h - 12)).toFixed(1)); }
    });
    var s = '<svg width="' + w + '" height="' + h + '"><line x1="0" x2="' + w + '" y1="' + (h - 5.5) + '" y2="' + (h - 5.5) + '" stroke="' + css(app, "--line-2") + '"/>';
    d.frames.forEach(function (p) { var x = (p - lo) / (hi - lo) * w; s += '<line x1="' + x + '" x2="' + x + '" y1="4" y2="' + (h - 5) + '" stroke="' + css(app, "--ink-3") + '" stroke-dasharray="2 3"/>'; });
    s += '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + css(app, "--plane") + '" stroke-width="1.4"/></svg>';
    el.innerHTML = s;
  }
  function all() {
    Array.prototype.forEach.call(document.querySelectorAll(".rail[data-flowrail]"), draw);
    Array.prototype.forEach.call(document.querySelectorAll(".corecurve"), core);
  }
  all();
  window.addEventListener("resize", all);
  document.addEventListener("click", function () { setTimeout(all, 0); });
})();
