r"""V-NEVERWORSE library -- the merge-attributable ratio, on a gauge that is proved.

THE QUESTION
    Is the strehl merge ever WORSE than the frames it was built from?
    `orch_printready.py` computes that ratio for 9 of 26 subjects -- only the
    ones that tripped an absolute threshold. This lane computes it for all 26.

THE GAUGE FINDING THAT REBUILT THIS LANE (see vn_gauge.py for the evidence)

    Every existing master/source ratio in this project -- including the nine
    wired into `orch_printready.py` through `V-REVIEW/vr_baseline.json`, and
    including the `master/best-source blotch 1.258x` on `lead-1-cpl` that
    created this lane -- is computed on `--srgb` renders.

    `--srgb` applies a PER-IMAGE, CONTENT-DERIVED tone rendering
    (`crates/strehl-cli/src/image_out.rs`, `Tone::from_luminance`):

        black = p0.1(luminance) * 0.85
        white = black + (p99.9(luminance) - black) / 0.90
        placement, soft toe (TONE_TOE 0.004), sRGB encode, S-curve 0.55

    Both percentiles are measured FROM THE IMAGE ITSELF. A 123-frame master and
    a single defocused frame therefore get DIFFERENT black points, DIFFERENT
    white points and different positions on the S-curve. `blotch = band/mean`
    is invariant to a linear gain; it is not invariant to a black subtraction,
    a transfer curve or an S-curve.

    `vr_lib.py`'s docstring names the defence: force `--exposure` to the
    master's own stops so "exposure gain and the sRGB curve are COMMON MODE".
    MEASURED, THAT DEFENCE DOES NOT REACH THE PIXELS. Rendering the same frame
    at `--exposure=-0.26` and `--exposure=+5.00` -- a 40x gain difference --
    produces files that differ in NINE BYTES, all of them inside the
    ImageDescription string. The tone stage renormalises the gain away. So the
    forced exposure pins the reported number and nothing else, and the two arms
    of every existing ratio sit on two different content-derived nonlinear
    gauges.

    The project already knew this and said so in three places:
      - each master's provenance: "sRGB, TONE CURVE APPLIED -- DO NOT MEASURE
        NUMERICALLY"
      - `strehl stack --help` on `--linear-srgb`: "THIS IS THE MODE TO MEASURE
        IN. ... quality is never judged on an --srgb render ... more than one
        result in this project has been retracted for exactly that."
      - `image_out.rs`'s own unit test
        `tone_rides_with_the_viewing_render_and_never_with_a_measurement`

THE GAUGE THIS LANE USES INSTEAD
    Both arms are rendered `--linear-srgb --demosaic`: camera colour matrix to
    BT.709/D65 and STOP -- no transfer curve, no tone rendering, no exposure
    flag (`--exposure` refuses to run without `--srgb`). The only normalisation
    is by the camera's own black/white levels, which are per-camera constants
    (512 / 15360 at ISO 100) and identical on both arms. `band/mean` is then a
    dimensionless contrast on a linear signal, which is the thing it was
    defined to be.

    The masters are re-rendered into that space FROM THE SAME PIN. That is
    licensed, not assumed: `vn_gauge.py` arm G2 re-renders a shipped master
    with the shipping command and gets a BYTE-IDENTICAL file, so the merge my
    linear master carries is provably the merge SHIP-V4 shipped. Develop is
    downstream of the merge.

STATISTICS ARE IMPORTED, NEVER RE-TYPED
    orch_blotch.blotch_ratio/flattest/lum_of and orch_chroma.chroma_blotch/
    pick_window, unmodified.

WHAT "BEST SOURCE FRAME" MEANS, STATED BEFORE ANY NUMBER
    `vr_baseline.json` records `source_baseline: "max over registered source
    frames"` and `orch_printready.py:223` prints that ratio under the label
    "master/best-source". Those are two different quantities: for a statistic
    where low is good, the max is the WORST frame. This module reports the full
    order statistic -- min (best frame), median (typical frame), max (worst
    frame) -- and labels each by what it is.
"""
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
import tifffile

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
VREVIEW = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW"
for _p in (ORCH, VREVIEW):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from orch_blotch import blotch_ratio, flattest, lum_of      # noqa: E402
from orch_blotch import WIN as BWIN                         # noqa: E402
from orch_chroma import chroma_blotch, pick_window          # noqa: E402
from orch_chroma import WIN as CWIN                         # noqa: E402

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
ARM = "SHIP-V4"
OUT = r"C:\dev\strehl-out\V-NEVERWORSE"
SRC = r"D:\personal\macro"          # READ-ONLY. Nothing here ever writes to D:.

# The binary under test, and the hash that pins it. Overridable by environment
# so a second arm can be run against a newer build WITHOUT editing this file --
# but the defaults are the original pin, so every script that does not set the
# environment measures exactly what it measured before. Both must be overridden
# together or `check_pin` refuses: a new exe against an old hash is the failure
# mode this pin exists to catch.
EXE = os.environ.get("VN_EXE", os.path.join(OUT, "bin", "strehl.exe"))
PIN_SHA = os.environ.get(
    "VN_PIN_SHA",
    "44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490")

# The measurement space. Not a preference -- the CLI's own help calls it
# "THE MODE TO MEASURE IN" and forbids judging quality on --srgb.
MEASURE_FLAGS = ["--linear-srgb", "--demosaic"]
SHIP_FLAGS = ["--srgb", "--auto-exposure"]      # what SHIP-V4 actually ran

NCC_MIN = 0.75                      # V-REVIEW's registration floor, adopted verbatim

_COVER = re.compile(r"field of view scaled to ([0-9.]+)")
_REPRO = re.compile(r"reproduce this exact file with --exposure=([-+]?[0-9.]+)")
_SHA = re.compile(r"^sha256\s*:\s*([0-9A-Fa-f]{64})\s*$", re.M)
_GAIN = re.compile(r"exposure\s*:\s*([-+]?[0-9.]+) stops \(gain ([0-9.]+)x\)")
_LEVELS = re.compile(r"levels\s*:\s*black (\d+), white (\d+)")
_TONE = re.compile(r"tone\s*:\s*black ([0-9.]+), white ([0-9.]+) \(linear\), "
                   r"contrast ([0-9.]+)")


def subjects():
    """Every subject with a SHIP-V4 master, from the filesystem. 26 expected."""
    return sorted(f[:-len("--%s.tiff" % ARM)] for f in os.listdir(SHIP)
                  if f.endswith("--%s.tiff" % ARM))


def ship_master_path(subj):
    return os.path.join(SHIP, "%s--%s.tiff" % (subj, ARM))


def lin_master_path(subj):
    return os.path.join(OUT, "masters", "%s--LIN.tiff" % subj)


def provenance_text(subj):
    with open(ship_master_path(subj) + ".provenance.txt",
              encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _need(rx, text, what, subj):
    m = rx.search(text)
    if not m:
        raise RuntimeError("no %s in provenance/log for %s" % (what, subj))
    return m


def master_pin(subj):
    return _need(_SHA, provenance_text(subj), "sha256 line", subj).group(1).upper()


def master_exposure(subj):
    """Stops the master's own provenance says reproduce it. Parsed, never typed."""
    return _need(_REPRO, provenance_text(subj),
                 "'reproduce ... --exposure='", subj).group(1)


def master_gain(subj):
    m = _need(_GAIN, provenance_text(subj), "exposure/gain line", subj)
    return float(m.group(1)), float(m.group(2))


def master_tone(subj):
    """The per-image tone the shipped --srgb master was developed against."""
    m = _need(_TONE, provenance_text(subj), "tone line", subj)
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def levels_of(text):
    m = _LEVELS.search(text)
    return [int(m.group(1)), int(m.group(2))] if m else None


def tone_of(text):
    m = _TONE.search(text)
    return [float(m.group(1)), float(m.group(2)), float(m.group(3))] if m else None


def cover_of_log(text):
    m = _COVER.search(text)
    if m:
        return float(m.group(1))
    return 1.0 if "no crop needed" in text else None


def master_cover(subj):
    with open(lin_master_path(subj)[:-5] + ".log",
              encoding="utf-8", errors="replace") as fh:
        return cover_of_log(fh.read())


def frames_of(subj):
    d = os.path.join(SRC, subj)
    return sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))


def n_frames(subj):
    return len(frames_of(subj))


def check_pin():
    import hashlib
    if ("VN_EXE" in os.environ) != ("VN_PIN_SHA" in os.environ):
        raise RuntimeError(
            "VN_EXE and VN_PIN_SHA must be set together; got VN_EXE=%r "
            "VN_PIN_SHA=%r. A new binary measured against the old hash is "
            "exactly what this pin exists to catch."
            % (os.environ.get("VN_EXE"), os.environ.get("VN_PIN_SHA")))
    h = hashlib.sha256(open(EXE, "rb").read()).hexdigest().upper()
    if h != PIN_SHA:
        raise RuntimeError("pinned copy %s is sha %s, expected %s" % (EXE, h, PIN_SHA))
    return h


def read_rgb(path):
    a = tifffile.imread(path)          # tifffile, never PIL
    if a.dtype != np.uint16:
        raise RuntimeError("%s is %s, expected uint16" % (path, a.dtype))
    return a[:, :, :3].astype(np.float32)


def render(subj, out_tiff, flags=None, only_frame=None, timeout=3600, extra=()):
    """One strehl render through the pinned binary.

    Every STREHL_* variable is CLEARED so a neighbouring lane's environment
    cannot leak in (rule 47: the environment is part of the pipeline).
    """
    use = list(MEASURE_FLAGS if flags is None else flags)
    env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}
    if only_frame is not None:
        env["STREHL_ONLY_FRAME"] = str(only_frame)
    cmd = [EXE, "stack", os.path.join(SRC, subj), "--out", out_tiff] + use + list(extra)
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout)
    log = p.stderr.decode("utf-8", "replace")
    if p.returncode != 0:
        raise RuntimeError("render rc=%d\n%s" % (p.returncode, log[-3000:]))
    if not os.path.exists(out_tiff):
        # Never trust an exit code without the artifact it claims to have made.
        raise RuntimeError("rc=0 but no artifact at %s\n%s" % (out_tiff, log[-2000:]))
    if "--linear-srgb" in use and _TONE.search(log):
        raise RuntimeError("TONE LEAKED ONTO THE MEASUREMENT PATH for %s" % subj)
    return log


def ensure_linear_master(subj, force=False):
    """The SHIP-V4 merge, developed into the measurement space.

    Licensed by vn_gauge G2: the same pin and environment re-render a shipped
    --srgb master BYTE-IDENTICALLY, so changing only the output space changes
    only the develop, which is downstream of the merge.
    """
    p = lin_master_path(subj)
    lg = p[:-5] + ".log"
    if os.path.exists(p) and os.path.exists(lg) and not force:
        return p
    os.makedirs(os.path.dirname(p), exist_ok=True)
    log = render(subj, p)
    with open(lg, "w", encoding="utf-8") as fh:
        fh.write(log)
    return p


# ---------------------------------------------------------------------------
# The two statistics, computed the way orch_printready computes them.

# A window that has run into the top of the 16-bit range has no chroma left:
# clipping drives R, G and B to the same value, so (R-Y)/Y goes to zero and the
# statistic reads PERFECT. `coffee-bean` found this the hard way -- three source
# frames clipped 79-99.97% of the chroma window, read chroma ~5e-7, and produced
# a master/source ratio of 638x that was entirely an artefact of the denominator
# being destroyed. A degenerate denominator is not a good score; it is not a
# measurement, and it is dropped and counted rather than divided by.
SAT_DN = 64000          # 97.7% of full scale on the uint16 linear render
SAT_MAX = 0.02          # fraction of the window allowed to sit there


def sat_frac(win):
    return float((win >= SAT_DN).mean())


def stats_at(rgb, bw, cw):
    """blotch at window bw, chroma at window cw, on an already-loaded image."""
    lum = lum_of(rgb)
    r, bd, nd, md = blotch_ratio(lum[bw[0]:bw[0] + BWIN, bw[1]:bw[1] + BWIN])
    cb = chroma_blotch(rgb, (cw[0], cw[1]))
    return dict(blotch=float(r), band=float(bd), noise=float(nd), mean=float(md),
                relhf=float(nd / max(md, 1e-9)),
                chroma=float(cb[0]), a_rms=float(cb[1]), b_rms=float(cb[2]),
                chr_std=float(cb[3]),
                sat_b=sat_frac(rgb[bw[0]:bw[0] + BWIN, bw[1]:bw[1] + BWIN]),
                sat_c=sat_frac(rgb[cw[0]:cw[0] + CWIN, cw[1]:cw[1] + CWIN]))


def choose_windows(rgb):
    lum = lum_of(rgb)
    by, bx = flattest(lum)
    cw = pick_window(rgb, "chroma")
    return (int(by), int(bx)), (int(cw[0]), int(cw[1]))


def master_stats(subj, path=None):
    rgb = read_rgb(path or lin_master_path(subj))
    bw, cw = choose_windows(rgb)
    s = stats_at(rgb, bw, cw)
    s.update(bw=list(bw), cw=list(cw),
             shape=[int(rgb.shape[0]), int(rgb.shape[1])])
    return s


def window_stats(win_b_rgb, win_c_rgb):
    r, bd, nd, md = blotch_ratio(lum_of(win_b_rgb))
    cb = chroma_blotch(win_c_rgb, (0, 0))
    return dict(blotch=float(r), band=float(bd), noise=float(nd), mean=float(md),
                relhf=float(nd / max(md, 1e-9)),
                chroma=float(cb[0]), chr_std=float(cb[3]),
                sat_b=sat_frac(win_b_rgb), sat_c=sat_frac(win_c_rgb))


# ---------------------------------------------------------------------------
# Geometry. Imported from V-REVIEW, which commissioned it (vr_commission ARM B:
# a planted similarity recovered to 3.5e-4 in scale and 0.5 px in shift).
# Registration is gauge-neutral: it correlates blurred, mean-removed,
# variance-normalised luminance, so it does not care which space either arm is
# in. Only the STATISTICS care, and those are what this lane moved to linear.

import vr_lib as V                                             # noqa: E402
import vr_reg2 as R                                            # noqa: E402

warp_window = V.warp_window
register_best = R.register_best
context_ncc = R.context_ncc


def _f(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def measure_source_frame(subj, k, mlum, bw, cw, km, scratch=None, keep=None,
                         flags=None):
    """Render frame k in the measurement space, register it to the linear
    master, and measure at the MASTER'S OWN windows."""
    t0 = time.time()
    d = scratch or os.path.join(OUT, "scratch")
    os.makedirs(d, exist_ok=True)
    tif = os.path.join(d, "%s--f%04d.tiff" % (subj, k))
    row = dict(frame=int(k), state="RENDER-FAILED")
    try:
        log = render(subj, tif, flags=flags, only_frame=k)
        ks = cover_of_log(log) or 1.0
        srgb = read_rgb(tif)
        slum = lum_of(srgb)
        A, dg = register_best(mlum, slum, km / ks, bw[0], bw[1], BWIN)
        row = dict(frame=int(k), how=dg.get("how"), ecc=_f(dg.get("ecc")),
                   scale=_f(dg.get("scale")), ncc_b=_f(dg.get("ncc_context")),
                   cover_src=float(ks), levels=levels_of(log))
        if A is None:
            row["state"] = "UNREGISTERED"
        else:
            row["ncc_c"] = _f(context_ncc(mlum, slum, A, cw[0], cw[1], CWIN))
            wb = warp_window(srgb, A, bw[0], bw[1], BWIN)
            wc = warp_window(srgb, A, cw[0], cw[1], CWIN)
            if wb is None or wc is None:
                row["state"] = "WINDOW-OUTSIDE-SOURCE"
            else:
                row.update(state="OK", **window_stats(wb, wc))
                if row["ncc_b"] is None or row["ncc_b"] < NCC_MIN:
                    row["state"] = "POOR-REG"
                # Per-STATISTIC admission. The two windows are in different
                # places and are registered separately, so a frame can be a
                # valid blotch reading and an invalid chroma one. Gating both
                # on the blotch window's NCC is how coffee-bean f31 -- chroma
                # window NCC 0.23, 99.97% clipped -- became a denominator.
                row["ok_b"] = (row["state"] == "OK" and row["sat_b"] <= SAT_MAX)
                row["ok_c"] = (row["state"] == "OK"
                               and row["ncc_c"] is not None
                               and row["ncc_c"] >= NCC_MIN
                               and row["sat_c"] <= SAT_MAX)
                row["why_b"] = ("" if row["ok_b"] else
                                ("reg %s" % row["state"] if row["state"] != "OK"
                                 else "blotch window %.1f%% clipped"
                                      % (100 * row["sat_b"])))
                row["why_c"] = ("" if row["ok_c"] else
                                ("reg %s" % row["state"] if row["state"] != "OK"
                                 else "chroma window %.1f%% clipped"
                                      % (100 * row["sat_c"]) if row["sat_c"] > SAT_MAX
                                 else "chroma NCC %s < %.2f"
                                      % (row["ncc_c"], NCC_MIN)))
                if keep is not None:
                    keep.append((int(k), wb, wc))
        del srgb, slum
    finally:
        try:
            os.remove(tif)
        except OSError:
            pass
    row["secs"] = round(time.time() - t0, 1)
    return row


def admits(row, key):
    """Is this frame's reading of `key` admissible as a denominator?"""
    return bool(row.get("ok_c" if key == "chroma" else "ok_b"))


def order_stats(rows, key):
    """min / median / max over ADMISSIBLE source frames, with each argframe.

    Direction, stated where it is used (rule 18): for both blotch and chroma
    LOW is good, so `min` is the BEST source frame and `max` is the WORST.
    A ratio against `min` is the strong invariant; against `max` the weak one.
    Admissibility is per statistic -- see `measure_source_frame`.
    """
    ok = [r for r in rows if admits(r, key) and r.get(key) is not None]
    if not ok:
        return None
    v = np.array([r[key] for r in ok], dtype=np.float64)
    lo, hi = int(np.argmin(v)), int(np.argmax(v))
    return dict(n=len(ok), min=float(v.min()), med=float(np.median(v)),
                max=float(v.max()),
                argmin=ok[lo]["frame"], argmax=ok[hi]["frame"],
                relhf_at_min=ok[lo].get("relhf"), relhf_at_max=ok[hi].get("relhf"),
                mean_at_min=ok[lo].get("mean"))


def jdump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, default=float)
    os.replace(tmp, path)


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
