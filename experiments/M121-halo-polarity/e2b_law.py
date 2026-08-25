"""E2b -- what the rim ACTUALLY is, once P-POLARITY has a number.

E2 measured, on the shipped gate-4 arm:

    dark object / bright surround   rim = +0.0634  (surround pushed BRIGHTER)
    bright object / dark surround   rim = +0.0009  (surround not moved at all)

Both are in units of the edge amplitude A = hi - lo.  ORCH's mechanism predicts
+0.063 in BOTH rows, because the veiling it removes scales with A on both
sides.  So the second row is where the mechanism has to be paid for, and this
script asks what else could produce it.

Three candidate laws, all fitted to the FIRST row and then PREDICTING the
second, so the second row is a genuine out-of-sample test:

  CONTRAST   the rim is a fixed fraction of A, pushed outward on both sides.
             predicts  dark-row = +0.0634.
  ADDITIVE   the rim adds a fixed number of DN to whichever side it is on.
             predicts  dark-row = -0.0634  (the dark surround gets LIFTED).
  MULTIPLICATIVE
             the rim scales the surround by a fixed factor (1 + g).
             g is fixed by row one: g = 0.0634 * A / hi.
             on a DARK surround the same factor moves g * lo DN, so
             predicts  dark-row = -g * lo / A = -0.0634 * lo / hi.
             Because lo << hi at a silhouette, this is NEARLY ZERO.

That third law is not in the brief.  It came out of the measurement, and it is
the one that fits, so it has to be stated and then attacked.

The obvious attack, which this script also runs: maybe the bright-object row is
not made of SILHOUETTES at all.  On a bee, "bright thing on a dark background"
is usually a pale hair lying ON the dark body -- same depth, no occlusion, no
defocus discontinuity -- and then every mechanism predicts nothing and the row
tests nothing.  `depth_split` measures, for each accepted edge, how different
the two sides' best-focus depths are, using the same 5-frame focus field the
classifier uses, and re-reads both rows restricted to edges that really do
straddle a depth discontinuity.

Run:  python experiments/M121-halo-polarity/e2b_law.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from e2_polarity import (  # noqa: E402
    FLAT_TOL, GRAD_PCT, ISO, MAX_EDGES, MIN_AMPLITUDE, NEAR_MAX, WINDOW_RADIUS,
    commissioned_max_rise, focus_field, make_classifier, polarity_table,
)
from m121_io import FRAMES, OUT, arm_path, load_u16, luma  # noqa: E402
from runner import _boot_ci, scan  # noqa: E402


def side_rows(r, band):
    """Per-edge rim value, plateau levels and amplitude, per class."""
    lo, hi = band
    dist = r["dist"]
    m = (dist >= lo) & (dist <= hi)
    rows = {}
    for cls, side, want in (("dark_object_bright_surround", "bright", -1),
                            ("bright_object_dark_surround", "dark", +1)):
        s = r.get(side)
        if s is None or not m.any():
            rows[cls] = None
            continue
        sel = s["obj"] == want
        if sel.sum() < 8:
            rows[cls] = {"n": int(sel.sum())}
            continue
        rows[cls] = {
            "n": int(sel.sum()),
            "rim": s["stack"][sel][:, m].mean(axis=1),
            "A": np.asarray(s["amps"])[sel] if "amps" in s else None,
            "lo": np.asarray(s["lo"])[sel] if "lo" in s else None,
            "hi": np.asarray(s["hi"])[sel] if "hi" in s else None,
            "dz": np.asarray(s["dz"])[sel] if "dz" in s else None,
        }
    return rows


def main():
    max_rise = commissioned_max_rise()
    merged = luma(load_u16(arm_path("armM4-gate4-binlin")))
    frames = {n: luma(load_u16(arm_path(n))) for n in FRAMES}
    fields = np.stack([focus_field(f) for f in frames.values()])
    fmax = fields.max(axis=0)
    fbest = fields.argmax(axis=0).astype(np.float32)
    classify = make_classifier(fmax)

    # per-edge depth split: how far apart are the two sides' best frames?
    def probe(e):
        y, x = e["y"], e["x"]
        nx, ny = e["nx"], e["ny"]
        h, w = fbest.shape
        out = []
        for s in (+1, -1):
            yy = int(round(y + s * 20 * ny))
            xx = int(round(x + s * 20 * nx))
            yy = min(max(yy, 0), h - 1)
            xx = min(max(xx, 0), w - 1)
            out.append(fbest[yy, xx])
        return abs(out[0] - out[1])

    r = scan(merged, label="E2b shipped", grad_percentile=GRAD_PCT,
             max_edges=MAX_EDGES, isolation_frac=ISO, flat_tol=FLAT_TOL,
             classify=classify, max_rise=max_rise, min_amplitude=MIN_AMPLITUDE,
             extra=probe, verbose=True)
    pt = polarity_table(r)
    band = pt["read_band"]
    rows = side_rows(r, band)

    res = {"read_band": band, "window_radius_focus_rs": WINDOW_RADIUS,
           "max_rise": max_rise}

    print(f"\nread band {band[0]:.2f}-{band[1]:.2f} px\n")
    print("=== observed rows ===")
    obs = {}
    for cls, d in rows.items():
        if not d or d.get("rim") is None:
            print(f"  {cls:30s} n={d.get('n', 0) if d else 0} -- no reading")
            continue
        m, lo, hi = _boot_ci(d["rim"])
        obs[cls] = (m, lo, hi, d)
        print(f"  {cls:30s} n={d['n']:4d}  rim={m:+.4f} [{lo:+.4f},{hi:+.4f}]")

    A_key = "dark_object_bright_surround"
    B_key = "bright_object_dark_surround"
    if A_key in obs and B_key in obs:
        mA, _, _, dA = obs[A_key]
        mB, lB, hB, dB = obs[B_key]
        # ratio lo/hi on the BRIGHT-OBJECT edges: the surround is the dark side
        ratio = float(np.median(dB["lo"] / dB["hi"])) if dB["lo"] is not None else np.nan
        pred = {"CONTRAST": +mA, "ADDITIVE": -mA, "MULTIPLICATIVE": -mA * ratio}
        print("\n=== out-of-sample test: fit row one, predict row two ===")
        print(f"  median lo/hi on the bright-object edges = {ratio:.4f}")
        print(f"  {'law':18s} {'predicted':>10s} {'observed':>10s} {'95% CI':>20s}  verdict")
        res["ratio_lo_over_hi"] = ratio
        res["predictions"] = {}
        for law, p in pred.items():
            inside = (lB <= p <= hB)
            res["predictions"][law] = {"predicted": p, "inside_CI": bool(inside)}
            print(f"  {law:18s} {p:+10.4f} {mB:+10.4f} [{lB:+.4f},{hB:+.4f}]  "
                  f"{'SURVIVES' if inside else 'REJECTED'}")

    # --- the attack: restrict to edges that really straddle a depth step ---
    print("\n=== restricted to edges that STRADDLE A DEPTH DISCONTINUITY ===")
    print("    (|best-frame index difference| across the edge, 5-frame field)")
    res["depth_split"] = {}
    for thresh in (0, 1, 2, 3):
        line = []
        for cls, side, want in ((A_key, "bright", -1), (B_key, "dark", +1)):
            s = r.get(side)
            if s is None or "dz" not in s:
                line.append((cls, 0, np.nan, np.nan, np.nan))
                continue
            sel = (s["obj"] == want) & (np.asarray(s["dz"]) >= thresh)
            n = int(sel.sum())
            if n < 8:
                line.append((cls, n, np.nan, np.nan, np.nan))
                continue
            dist = r["dist"]
            m = (dist >= band[0]) & (dist <= band[1])
            v = s["stack"][sel][:, m].mean(axis=1)
            line.append((cls, n) + _boot_ci(v))
        res["depth_split"][str(thresh)] = [
            {"class": c, "n": n, "rim": a, "lo95": b, "hi95": cc} for c, n, a, b, cc in line]
        txt = "  ".join(f"{c.split('_')[0]}-obj n={n:3d} rim="
                        + (f"{a:+.4f}[{b:+.4f},{cc:+.4f}]" if np.isfinite(a) else "  --   ")
                        for c, n, a, b, cc in line)
        print(f"  dz>={thresh}:  {txt}")

    (OUT / "e2b-law.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT / 'e2b-law.json'}")


if __name__ == "__main__":
    main()
