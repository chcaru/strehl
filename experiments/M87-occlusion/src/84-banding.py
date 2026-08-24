"""M87 s31 -- separate the veil (real) from the banding (suspected display).

ORCH's BLOB.png shows two things and asks me to separate them:
  1. a bright veil hugging the silhouette   -- claimed real
  2. concentric banding near the claw        -- "veil falling off in steps",
                                                "quantisation in the stretch",
                                                or a separate defect

blob.py reads the 16-bit render, so 8-bit SOURCE quantisation is excluded.
But it casts the stretched field to uint8 with

    stretched = (g - med) / span * 127 + 127,   span = (p99 - p1) * 0.35

so ONE OUTPUT CODE IS span/127 DN.  Measured here: 115.7 DN.  A field whose
gradient is gentler than that per pixel MUST posterise into contours, and a
field carrying noise near a code boundary must speckle there.  That pair --
flat plateaus separated by speckled transition zones -- is what the pocket
enclosed by the claw actually looks like at 100%.

THREE REGISTERED BARS.  Written with three branches each (discipline 676:
a two-branch ratio bar scored a 7.8x effect as a null in this project today).

  B1 DITHER.  Quantisation introduced by a uint8 cast is removed by dithering
     BEFORE the cast; real structure in the 16-bit data is not.
       ratio = transitions(dithered) / transitions(undithered)
       ratio >= 4.0 and 16-bit is smooth -> DISPLAY
       ratio <= 1.5, or 16-bit is not smooth -> REAL
       otherwise -> MIXED

  B2 PHASE.  If the speckle is quantisation, it sits at code boundaries: the
     local variance of the uint8 image peaks where the pre-cast float value
     v is near a half-integer, and vanishes where v is near an integer.  A
     real defect has no reason to know about the cast's phase.
       corr(local sd, triangular phase) >= +0.30 -> DISPLAY
       corr <= -0.30                             -> anti-phased, REAL
       otherwise                                 -> NO PHASE LOCK

  B3 CONTROL.  The same two statistics on a far-background box with no
     reported banding.  If B1/B2 fire there too, they are measuring the
     stretch and not the claw, which is the point -- but if they fire ONLY
     in the pocket, banding is local and the display reading is wrong.

Also settles a factual claim in the covering message -- "the step is a few
DN and invisible at normal display gamma".  Veil amplitude is measured as a
FALLOFF CURVE against distance from the silhouette (discipline 677: render
the map, do not trust a region average), not as a box mean.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage

SRC = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl.tif")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

X0, Y0, W, H = 700, 3150, 1100, 900          # ORCH's exact region
SEED = 8731

# Boxes read off the coordinate grid in 85-grid.py, in crop coords (y0,y1,x0,x1).
POCKET = (690, 790, 720, 890)     # inside the claw's hook -- ORCH's banding
FAR = (200, 400, 830, 1070)       # far background, no banding reported
BG_MAX_DARK = 0.02                # subject-pixel fraction tolerated in a box

B1_DISPLAY, B1_REAL = 4.0, 1.5
B2_DISPLAY, B2_REAL = 0.30, -0.30
SMOOTH16_RUN = 2.0                # median 16-bit run length, px


def transitions_per_row(img):
    """Median number of value changes along a row -- low = posterised."""
    return float(np.median([1 + np.count_nonzero(np.diff(r) != 0) for r in img]))


def median_run(img):
    runs = []
    for r in img:
        d = np.flatnonzero(np.diff(r) != 0)
        runs.extend(np.diff(np.concatenate([[-1], d, [r.size - 1]])))
    return float(np.median(runs)) if runs else float(img.shape[1])


def stretch(x, med, span, rng=None):
    v = (x - med) / span * 127.0 + 127.0
    if rng is not None:
        v = v + rng.triangular(-1.0, 0.0, 1.0, size=v.shape)
    return np.clip(v, 0, 255).astype(np.uint8)


def local_sd(u8, k=5):
    f = u8.astype(np.float32)
    m = ndimage.uniform_filter(f, k)
    m2 = ndimage.uniform_filter(f * f, k)
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def analyse_box(name, g, box, med, span, dark_thr, rng, out):
    y0, y1, x0, x1 = box
    b = g[y0:y1, x0:x1]
    dark = float((b < dark_thr).mean())
    print(f"\n--- {name} box y {y0}:{y1} x {x0}:{x1}"
          f"  dark {100*dark:.3f}% (bar {100*BG_MAX_DARK:.0f}%)")
    assert dark < BG_MAX_DARK, f"{name} box contains subject pixels; move it"

    u_plain = stretch(b, med, span)
    u_dith = stretch(b, med, span, rng=rng)
    t1, r1 = transitions_per_row(u_plain), median_run(u_plain)
    t2, r2 = transitions_per_row(u_dith), median_run(u_dith)
    t3, r3 = transitions_per_row(b.astype(np.int32)), median_run(b.astype(np.int32))
    ratio = t2 / max(t1, 1e-9)
    print(f"  B1  undithered uint8 {t1:8.1f} transitions/row, run {r1:6.1f} px,"
          f" {np.unique(u_plain).size:3d} codes")
    print(f"      dithered   uint8 {t2:8.1f} transitions/row, run {r2:6.1f} px")
    print(f"      raw 16-bit       {t3:8.1f} transitions/row, run {r3:6.1f} px,"
          f" {np.unique(b.astype(np.int32)).size:5d} DN values")
    print(f"      ratio {ratio:.1f}x   (DISPLAY >= {B1_DISPLAY}, REAL <= {B1_REAL})")

    v = (b - med) / span * 127.0 + 127.0
    phase = 1.0 - 2.0 * np.abs(np.mod(v, 1.0) - 0.5)     # 0 at integer, 1 at .5
    sd = local_sd(u_plain)
    ph = ndimage.uniform_filter(phase.astype(np.float32), 5)
    corr = float(np.corrcoef(sd.ravel(), ph.ravel())[0, 1])
    print(f"  B2  corr(local sd of uint8, code-boundary phase) = {corr:+.4f}"
          f"   (DISPLAY >= {B2_DISPLAY:+.2f}, REAL <= {B2_REAL:+.2f})")

    smooth16 = r3 <= SMOOTH16_RUN
    if ratio >= B1_DISPLAY and smooth16:
        v1 = "DISPLAY"
    elif ratio <= B1_REAL or not smooth16:
        v1 = "REAL"
    else:
        v1 = "MIXED"
    v2 = "DISPLAY" if corr >= B2_DISPLAY else ("REAL" if corr <= B2_REAL
                                               else "NO PHASE LOCK")
    print(f"  verdicts: B1 {v1}   B2 {v2}")
    out[name] = {"box": list(box), "dark": dark,
                 "t_plain": t1, "t_dither": t2, "t_raw16": t3,
                 "run_plain": r1, "run_dither": r2, "run_raw16": r3,
                 "codes": int(np.unique(u_plain).size),
                 "dn_values": int(np.unique(b.astype(np.int32)).size),
                 "ratio": ratio, "phase_corr": corr,
                 "B1": v1, "B2": v2}
    return v1, v2


def main():
    a = tifffile.imread(SRC)
    print(f"render {a.shape} {a.dtype}  <- {SRC}")
    r = a[Y0:Y0 + H, X0:X0 + W].astype(np.float32)
    g = r[:, :, 1]

    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    dn_per_code = span / 127.0
    print("\n=== the diagnostic stretch, reconstructed from blob.py ===")
    print(f"  p1 {lo:.0f}  p99 {hi:.0f}  median {med:.0f}")
    print(f"  span {span:.0f} DN   panel label reads x{65535/span:.0f}")
    print(f"  ONE OUTPUT CODE = {dn_per_code:.1f} DN")
    print(f"  a 3 DN step is {3.0/dn_per_code:.4f} of one code -> "
          f"{'INVISIBLE in this figure' if 3.0 < dn_per_code else 'visible'}")
    out = {"region": [X0, Y0, W, H], "p1": lo, "p99": hi, "median": med,
           "span": span, "dn_per_code": dn_per_code}

    dark_thr = med - span
    subj = ndimage.binary_closing(g < dark_thr, np.ones((5, 5)))
    subj = ndimage.binary_opening(subj, np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subj)
    print(f"\n=== veil amplitude vs distance from silhouette ==="
          f"  (subject = {100*subj.mean():.1f}% of crop)")
    prof = []
    for d in range(1, 121):
        m = (dist >= d) & (dist < d + 1)
        if m.sum() >= 200:
            prof.append((d, float(np.median(g[m])), int(m.sum())))
    asym = float(np.median([p[1] for p in prof if p[0] >= 90]))
    peak_d, peak_v = max(((d, v) for d, v, _ in prof), key=lambda t: t[1])
    print(f"  d= 1 {prof[0][1]:7.0f} DN   d= 5 {prof[4][1]:7.0f}"
          f"   d=10 {prof[9][1]:7.0f}   d=20 {prof[19][1]:7.0f}"
          f"   d=40 {prof[39][1]:7.0f}   d>=90 asymptote {asym:7.0f}")
    print(f"  peak at d={peak_d} px, {peak_v:.0f} DN"
          f"  ->  veil amplitude {peak_v - asym:+.0f} DN over background")
    print(f"  in units of the figure's own quantum: "
          f"{(peak_v - asym)/dn_per_code:+.1f} output codes")
    out["profile"] = prof
    out["asymptote"] = asym
    out["peak_d"] = peak_d
    out["peak_dn"] = peak_v
    out["veil_amplitude_dn"] = peak_v - asym
    out["veil_amplitude_codes"] = (peak_v - asym) / dn_per_code

    print("\n=== banding discriminator ===")
    rng = np.random.default_rng(SEED)
    p1v, p2v = analyse_box("POCKET", g, POCKET, med, span, dark_thr, rng, out)
    f1v, f2v = analyse_box("FAR", g, FAR, med, span, dark_thr, rng, out)

    print("\n=== B3 control: is the effect local to the claw? ===")
    local = (p1v == "DISPLAY") and (f1v != "DISPLAY")
    print(f"  pocket B1 {p1v} / far B1 {f1v}  ->"
          f" {'LOCAL to the claw' if local else 'GLOBAL to the stretch'}")
    out["B3_local"] = local
    out["FAR_B2"] = f2v

    if p1v == "DISPLAY" and p2v == "DISPLAY":
        verdict = "DISPLAY: the banding is posterisation in the diagnostic cast"
    elif p1v == "REAL" or p2v == "REAL":
        verdict = "REAL: the banding survives dithering / is anti-phased"
    else:
        verdict = "UNRESOLVED"
    print(f"\nVERDICT: {verdict}")
    out["verdict"] = verdict

    DATA.mkdir(exist_ok=True)
    (DATA / "84-banding.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"wrote {DATA / '84-banding.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
