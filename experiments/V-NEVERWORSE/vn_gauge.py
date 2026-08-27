r"""V-NEVERWORSE / GAUGE COMMISSIONING -- is the ratio measuring what it says?

This runs BEFORE the instrument is commissioned and long before any subject is
scored, because it asks a prior question: are the two sides of a master/source
ratio even on the same scale?

The sharpness lane (`orch_sharp1to1.py`) was found unsound earlier tonight for
exactly this: a `--srgb --auto-exposure` numerator against a `rawpy
no_auto_bright` denominator, a statistic linear in gain, and a headline 4.767x
that became 0.9314x on a matched gauge -- a sign flip. That defect was
invisible to its commissioning because commissioning tested the ESTIMATOR, not
the GAUGE. So the gauge is commissioned first here, separately, with its own
pass/fail table.

ARMS
  G1 BINARY          all 26 SHIP-V4 masters name the pin I hold
  G2 REPRODUCTION    this pin + this environment re-render a shipped master
                     BYTE-IDENTICALLY -- which is what licenses re-developing
                     the same merge into a measurable space
  G3 THE DEFECT      `--exposure`, the documented common-mode defence, is a
                     PIXEL NO-OP under `--srgb`. 40x of gain, zero pixels moved.
  G4 NOT COMMON MODE the tone rendering is derived per-image from the image's
                     own luminance percentiles, so master and source frame get
                     different curves. Measured on real renders.
  G5 CLEAN PATH      `--linear-srgb --demosaic` carries no tone clause at all,
                     and both arms normalise by the SAME camera levels.

A FAIL on G1, G2 or G5 stops the lane. G3 and G4 are the finding: they PASS by
DEMONSTRATING the defect, and each states what result would have refuted it.

  python vn_gauge.py
"""
import hashlib
import os
import re
import subprocess
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402

GDIR = os.path.join(L.OUT, "gauge")
PROBES = ["coffee-bubbles", "wrapped-text-1"]   # 19 frames and 130 frames;
                                                # -0.26 stops and +2.27 stops


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rows_ok(rows):
    return all(r["verdict"] == "PASS" for r in rows)


def table(name, rows):
    print("\n%s" % name)
    w = max(len(r["arm"]) for r in rows)
    for r in rows:
        print("  %-*s  %-4s  %s" % (w, r["arm"], r["verdict"], r["note"]))


# --------------------------------------------------------------------------
def g1_binary():
    got = L.check_pin()
    bad, gains = [], []
    for s in L.subjects():
        if L.master_pin(s) != got:
            bad.append(s)
        gains.append(L.master_gain(s)[1])
    n = len(L.subjects())
    rows = [dict(arm="G1a pin named by all masters",
                 verdict="PASS" if not bad and n == 26 else "FAIL",
                 note="%d/%d masters name %s..%s" % (n - len(bad), n, got[:8], got[-4:]))]
    # If a per-image gain exists anywhere, a ratio statistic can silently
    # measure exposure. State the spread rather than assume it is small.
    rows.append(dict(arm="G1b per-image gain spread", verdict="PASS",
                     note="%.3fx .. %.3fx = %.1fx across the corpus -- a ratio "
                          "on a gain-sensitive statistic MUST be matched"
                          % (min(gains), max(gains), max(gains) / min(gains))))
    return rows


def g2_reproduction():
    """Re-render a shipped master with the shipping command. Byte-identical?"""
    s = "coffee-bubbles"
    out = os.path.join(GDIR, "%s--REPRO.tiff" % s)
    os.makedirs(GDIR, exist_ok=True)
    if not os.path.exists(out):
        # The provenance's own "reproduce this exact file with --exposure=N".
        # --auto-exposure is what SHIP-V4 ran; --exposure=N is what it resolved
        # to, and the two cannot be passed together.
        L.render(s, out, flags=["--srgb", "--exposure=" + L.master_exposure(s)])
    a, b = sha(L.ship_master_path(s)), sha(out)
    return [dict(arm="G2 shipped master reproduced",
                 verdict="PASS" if a == b else "FAIL",
                 note="%s: shipped %s vs re-rendered %s -- %s"
                      % (s, a[:12], b[:12],
                         "IDENTICAL, so this pin+env IS the shipping pipeline "
                         "and re-developing the same merge changes only the "
                         "develop" if a == b else "DIFFER"))]


def g3_exposure_is_a_noop():
    """The documented common-mode defence, tested on pixels instead of on logs.

    A LADDER, not a single pair: the commanded gain is swept over ~64x and the
    gain that actually lands on the pixels is measured against it. The arm
    fails -- and the existing ratios become defensible -- if the delivered gain
    tracks the commanded one.
    """
    s = "coffee-bubbles"
    base = "-0.26"                       # the master's own stops
    stops = [base, "-1.26", "-2.26", "+1.74", "+5.00"]
    px, cmd = {}, {}
    for st in stops:
        p = os.path.join(GDIR, "%s--exp%s.tiff" % (s, st))
        lg = p[:-5] + ".log"
        if not os.path.exists(lg) or not os.path.exists(p):
            log = L.render(s, p, flags=["--srgb", "--exposure=" + st], only_frame=0)
            open(lg, "w", encoding="utf-8").write(log)
        cmd[st] = float(re.search(r"gain ([0-9.]+)x",
                                  open(lg, encoding="utf-8").read()).group(1))
        px[st] = tifffile.imread(p).astype(np.float64)
    A = px[base]
    lad = []
    for st in stops:
        B = px[st]
        # delivered gain: least-squares slope through the origin, on every pixel
        slope = float((A * B).sum() / max((A * A).sum(), 1e-9))
        lad.append((st, cmd[st] / cmd[base], slope,
                    float(np.abs(B - A).max()),
                    bool(np.array_equal(A, B))))
    span = max(t[1] for t in lad) / min(t[1] for t in lad)
    worst = max(abs(t[2] - 1.0) for t in lad)
    ident = [t[0] for t in lad if t[4]]
    ba = open(os.path.join(GDIR, "%s--exp-1.26.tiff" % s), "rb").read()
    bb = open(os.path.join(GDIR, "%s--exp%s.tiff" % (s, base)), "rb").read()
    diff = [i for i in range(min(len(ba), len(bb))) if ba[i] != bb[i]]
    first_strip = tifffile.TiffFile(
        os.path.join(GDIR, "%s--exp%s.tiff" % (s, base))).pages[0].dataoffsets[0]
    rows = [dict(arm="G3a commanded gain sweep", verdict="PASS" if span > 30 else "FAIL",
                 note="  ".join("%s:%.1fx" % (t[0], t[1]) for t in lad)
                      + "  = %.0fx of commanded range" % span),
            dict(arm="G3b delivered pixel gain",
                 verdict="PASS" if worst < 0.01 else "FAIL",
                 note="  ".join("%s:%.5fx" % (t[0], t[2]) for t in lad)
                      + "  | worst departure from unity %.3f%%, max |dDN| %.0f "
                        "-- the defence DOES NOT REACH THE PIXELS"
                      % (100 * worst, max(t[3] for t in lad))),
            dict(arm="G3c byte-identical arms",
                 verdict="PASS" if (ident and all(d < first_strip for d in diff))
                 else "FAIL",
                 note="a 2x commanded gain (%s vs -1.26) changes %d bytes, all at "
                      "offsets %d..%d, below the first strip at %d -- i.e. inside "
                      "ImageDescription and nowhere else. Pixel-identical arms: %s"
                      % (base, len(diff), diff[0] if diff else -1,
                         diff[-1] if diff else -1, first_strip, ", ".join(ident)))]
    return rows


def g4_tone_is_per_image():
    """Master and source frame are developed against DIFFERENT curves."""
    rows, seen = [], []
    for s in PROBES:
        mb, mw, mc = L.master_tone(s)
        p = os.path.join(GDIR, "%s--srgbframe.tiff" % s)
        lg = p[:-5] + ".log"
        if not os.path.exists(lg):
            log = L.render(s, p, flags=["--srgb", "--exposure=" + L.master_exposure(s)],
                           only_frame=0)
            open(lg, "w", encoding="utf-8").write(log)
            try:
                os.remove(p)
            except OSError:
                pass
        t = L.tone_of(open(lg, encoding="utf-8").read())
        if t is None:
            rows.append(dict(arm="G4 %s" % s, verdict="FAIL", note="no tone line"))
            continue
        sb, sw, _ = t
        span_m, span_s = mw - mb, sw - sb
        seen.append((s, mb, mw, sb, sw))
        rows.append(dict(
            arm="G4 %s tone m-vs-src" % s,
            verdict="PASS" if abs(span_s / span_m - 1.0) > 0.02 or abs(sb - mb) > 1e-4
            else "FAIL",
            note="master black %.6f white %.6f | frame black %.6f white %.6f "
                 "| span %.4f vs %.4f = %.3fx  (SAME --exposure=%s on both)"
                 % (mb, mw, sb, sw, span_m, span_s, span_s / span_m,
                    L.master_exposure(s))))
    rows.append(dict(arm="G4 consequence", verdict="PASS" if seen else "FAIL",
                     note="blotch=band/mean survives a linear gain but NOT a "
                          "black subtraction, a transfer curve or an S-curve; "
                          "the two arms of every existing ratio sit on two "
                          "different content-derived nonlinear curves"))
    return rows


def g5_clean_path():
    rows = []
    for s in PROBES:
        p = L.ensure_linear_master(s)
        log = open(p[:-5] + ".log", encoding="utf-8").read()
        lv = L.levels_of(log)
        sp = os.path.join(GDIR, "%s--linframe.tiff" % s)
        slg = sp[:-5] + ".log"
        if not os.path.exists(slg):
            open(slg, "w", encoding="utf-8").write(L.render(s, sp, only_frame=0))
            try:
                os.remove(sp)
            except OSError:
                pass
        slog = open(slg, encoding="utf-8").read()
        slv = L.levels_of(slog)
        tone = L.tone_of(log) or L.tone_of(slog)
        a = tifffile.imread(p)
        rows.append(dict(arm="G5 %s linear path" % s,
                         verdict="PASS" if tone is None and lv == slv and lv else "FAIL",
                         note="tone clause: %s | camera levels master %s frame %s "
                              "| %s %s"
                              % ("ABSENT on both arms" if tone is None else tone,
                                 lv, slv, a.shape, a.dtype)))
    # --exposure has no meaning here; prove the CLI refuses it rather than
    # silently accepting a flag that would reintroduce a per-image gain.
    env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}
    q = subprocess.run([L.EXE, "stack", os.path.join(L.SRC, PROBES[0]),
                        "--out", os.path.join(GDIR, "never.tiff"),
                        "--linear-srgb", "--demosaic", "--exposure=1.0"],
                       env=env, capture_output=True)
    refused = q.returncode != 0 and not os.path.exists(os.path.join(GDIR, "never.tiff"))
    rows.append(dict(arm="G5 no gain flag exists here",
                     verdict="PASS" if refused else "FAIL",
                     note="--exposure on --linear-srgb: rc=%d, %s"
                          % (q.returncode,
                             q.stderr.decode("utf-8", "replace").strip().splitlines()[-1][:110]
                             if q.stderr else "")))
    return rows


def main():
    os.makedirs(GDIR, exist_ok=True)
    out = {}
    for name, fn in (("G1 BINARY", g1_binary), ("G2 REPRODUCTION", g2_reproduction),
                     ("G3 THE DEFECT: --exposure is a pixel no-op", g3_exposure_is_a_noop),
                     ("G4 THE DEFECT: tone is per-image, not common mode",
                      g4_tone_is_per_image),
                     ("G5 THE CLEAN PATH", g5_clean_path)):
        rows = fn()
        table(name, rows)
        out[name] = rows
    hard = out["G1 BINARY"] + out["G2 REPRODUCTION"] + out["G5 THE CLEAN PATH"]
    ok = rows_ok(hard)
    print("\nGAUGE COMMISSIONING: %s" % ("PASS" if ok else "FAIL"))
    print("  measurement space: %s" % " ".join(L.MEASURE_FLAGS))
    print("  shipped space    : %s  (NOT measurable -- tone curve applied)"
          % " ".join(L.SHIP_FLAGS))
    L.jdump(dict(arms=out, ok=ok, measure=L.MEASURE_FLAGS, ship=L.SHIP_FLAGS),
            os.path.join(GDIR, "gauge.json"))
    # The G2 reproduction and the G3 exposure ladder are the evidence; they stay
    # on disk so the byte comparison can be re-run by hand. Everything else goes.
    for f in os.listdir(GDIR):
        if f.endswith(".tiff") and "REPRO" not in f and "--exp" not in f:
            try:
                os.remove(os.path.join(GDIR, f))
            except OSError:
                pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
