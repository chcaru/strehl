"""Paired comparison, GALLERY-FIXED-SRGB against SHIP-V1.

BOTH ARMS ARE THE PYRAMID BACKEND. galleryfixed.ps1 states "Arm is the pyramid
merge with the hull clamp" and its per-subject logs record "merge : pyramid,
hull clamp ON, gate 4". So this compares pyramid gate 4.0 against pyramid gate
4.5 plus lateral-CA plus auto-exposure. It does NOT test estimator vs pyramid.

Both arms are read through the SAME curve.arms(), reloaded under a swapped
VBF_GAL/VBF_OUT, so the two galleries cannot be measured by different code. The
path override was itself commissioned: ctrl_patch.py re-measured 109MSDCF with
the patched instrument and reproduced all 8 pre-patch arrays bit-for-bit.

Validity gates carry over from rank3.py with one change forced by the data:
SHIP-V1 was rendered with --auto-exposure, applying per-subject gains from
0.807x to 13.548x, so an ABSOLUTE floor band in DN is not comparable across
galleries. The band is therefore taken relative to each gallery's own median
floor. That is a change to a reporting gate, not to the measurement.
"""
import os, importlib, warnings
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore")
GALS = {"GAL": r"C:\dev\strehl-out\GALLERY-FIXED-SRGB",
        "SHIP": r"C:\dev\strehl-out\SHIP-V1"}
OUTS = {"GAL": r"C:\dev\strehl-out\V-BESTFRAME",
        "SHIP": r"C:\dev\strehl-out\V-BESTFRAME-SHIP"}
RAW = Path(r"D:\personal\macro")
GATE, FM_TOL, SNR_MIN, MIN_DETAIL, FLOOR_FACTOR = 0.80, 1.5, 3.0, 20, 8.0
CALLED_OUT = {"highly-angled-ruler-mm-cpl", "lead-1-cpl", "flowers-cpl", "bee-1-cpl"}


def measure(tag):
    """Every subject in this gallery, through curve.arms reloaded under its env."""
    os.environ["VBF_GAL"] = GALS[tag]; os.environ["VBF_OUT"] = OUTS[tag]
    import paircov, peaks, curve
    importlib.reload(paircov); importlib.reload(peaks); importlib.reload(curve)
    assert str(curve.GAL) == GALS[tag], (curve.GAL, GALS[tag])
    assert str(curve.OUT) == OUTS[tag], (curve.OUT, OUTS[tag])
    res = {}
    for p in sorted(Path(GALS[tag]).glob("*.tiff")):
        s = p.stem
        if not (RAW / s).is_dir():
            res[s] = dict(bad="no source directory"); continue
        try:
            a = curve.arms(s, peak_min=GATE)
        except Exception as e:
            res[s] = dict(bad=f"arms() raised {type(e).__name__}: {e}"); continue
        fl = (float(np.sqrt(np.nanmedian(a["F"])))
              if np.any(np.isfinite(a["F"])) else np.nan)
        pk = peaks.peaks_for(s, a["z"]["anchors"])
        # arms() abandons the gate when fewer than 2 pairs would survive, so
        # ngate=0 means EITHER "nothing to remove" OR "too much to remove".
        # Those must not print the same way.
        nbelow = int(np.sum(np.isfinite(pk) & (pk < GATE)))
        res[s] = dict(a=a, fl=fl, frm=int(a["nd"]), rd=2 * len(a["z"]["anchors"]),
                      gt=a["ngate"], nbelow=nbelow,
                      gate_skipped=(nbelow > 0 and a["ngate"] == 0),
                      pk=float(np.nanmin(pk)) if np.any(np.isfinite(pk)) else np.nan)
    return res


def score(res):
    """Apply validity gates, then the acceptance invariant on detail tiles."""
    fls = [d["fl"] for d in res.values() if "bad" not in d and np.isfinite(d["fl"])]
    med = float(np.median(fls)) if fls else np.nan
    lo, hi = med / FLOOR_FACTOR, med * FLOOR_FACTOR
    for s, d in res.items():
        if "bad" in d:
            continue
        if not np.isfinite(d["fl"]):
            d["bad"] = ("fixed-pattern floor undefined: no tile reached 20 px scene "
                        "displacement (merge is unregistered)"); continue
        if not (lo <= d["fl"] <= hi):
            d["bad"] = (f"floor {d['fl']:.2f} DN is {d['fl']/med:.3f}x this "
                        f"gallery's median floor {med:.2f} DN, outside the "
                        f"{1/FLOOR_FACTOR:.3f}-{FLOOR_FACTOR:.0f}x family"); continue
        a = d["a"]
        real = np.isfinite(a["snr"]) & (a["snr"] >= SNR_MIN)
        d["nd_tiles"] = int(real.sum())
        if d["nd_tiles"] < MIN_DETAIL:
            d["bad"] = f"only {d['nd_tiles']} detail tiles < {MIN_DETAIL}"; continue
        fm = float(np.sqrt(a["Fm"]))
        d["fm"] = fm
        d["strict_ok"] = fm <= FM_TOL * d["fl"]
        Smt = np.maximum(a["Em"] - np.minimum(a["Fm"], a["F"]), 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            rc = np.sqrt(Smt) / np.sqrt(np.maximum(a["Sft"], 1e-12))
        r = rc[real]
        d["w"] = float(np.mean(r >= 1.0) * 100)
        d["med"] = float(np.nanmedian(r))
        d["p05"] = float(np.nanpercentile(r, 5))
        d["nb"] = int(np.sum(r < 0.80))
        d["ws"] = float(np.mean(a["ratio"][real] >= 1.0) * 100)
    return res, med


def table(res, title):
    ok = {s: d for s, d in res.items() if "bad" not in d}
    print(f"\n{title}\n")
    h = (f"{'subject':36s} {'frm':>4} {'rd':>3} {'gt':>5} {'pkMin':>6} {'floor':>7} "
         f"{'detail':>7} {'merge>=frm':>10} {'medR':>6} {'p05':>6} {'<0.8':>5}")
    print(h); print("-" * len(h))
    for s, d in sorted(ok.items(), key=lambda kv: kv[1]["w"]):
        mark = " *" if s in CALLED_OUT else ""
        gt = f"SKIP{d['nbelow']}" if d["gate_skipped"] else f"{d['gt']:d}"
        print(f"{s+mark:36s} {d['frm']:4d} {d['rd']:3d} {gt:>5} {d['pk']:6.3f} "
              f"{d['fl']:7.2f} {d['nd_tiles']:3d}/352 {d['w']:9.1f}% {d['med']:6.2f} "
              f"{d['p05']:6.3f} {d['nb']:5d}")
    print("-" * len(h))
    bad = {s: d for s, d in res.items() if "bad" in d}
    print(f"\n  rendered on disk        {len(res):3d}")
    print(f"  measured and ranked     {len(ok):3d}")
    print(f"  NOT MEASURABLE          {len(bad):3d}")
    for s, d in sorted(bad.items()):
        print(f"      {s:36s} {d['bad']}")
    tot = len(ok) + len(bad)
    print(f"  partition sums to       {tot:3d}   "
          f"{'OK' if tot == len(res) else 'MISMATCH -- DO NOT TRUST'}")
    sk = [s for s, d in ok.items() if d["gate_skipped"]]
    print(f"  gate ABANDONED (>2 pairs would be lost)  {len(sk):3d}   "
          f"{', '.join(sk) if sk else '-'}")
    return ok


if __name__ == "__main__":
    g, gmed = score(measure("GAL"))
    s, smed = score(measure("SHIP"))
    print(f"median fixed-pattern floor: GALLERY {gmed:.2f} DN, SHIP-V1 {smed:.2f} DN")
    gok = table(g, "A. GALLERY-FIXED-SRGB -- pyramid backend, hull clamp, gate 4.0 "
                   "(blend-render.exe; NOT the estimator), worst first")
    sok = table(s, "B. SHIP-V1 -- pyramid backend, gate 4.5, auto-exposure, "
                   "lateral-CA on, worst first")

    print("\n\nC. PAIRED DIFF, GALLERY-FIXED-SRGB -> SHIP-V1, by GALLERY rank\n")
    h = (f"{'subject':36s} {'detail G':>8} {'detail S':>8} {'>=frm G':>8} "
         f"{'>=frm S':>8} {'delta':>8} {'medR G':>7} {'medR S':>7} "
         f"{'<0.8 G':>7} {'<0.8 S':>7}")
    print(h); print("-" * len(h))
    both = [k for k in sorted(gok, key=lambda k: gok[k]["w"]) if k in sok]
    for k in both:
        a, b = gok[k], sok[k]
        mark = " *" if k in CALLED_OUT else ""
        print(f"{k+mark:36s} {a['nd_tiles']:8d} {b['nd_tiles']:8d} {a['w']:7.1f}% "
              f"{b['w']:7.1f}% {b['w']-a['w']:+7.1f} {a['med']:7.2f} {b['med']:7.2f} "
              f"{a['nb']:7d} {b['nb']:7d}")
    print("-" * len(h))
    only_g = sorted(set(gok) - set(sok)); only_s = sorted(set(sok) - set(gok))
    print(f"\n  ranked in BOTH galleries      {len(both):3d}")
    print(f"  ranked in GALLERY only        {len(only_g):3d}   "
          f"{', '.join(only_g) if only_g else '-'}")
    print(f"  ranked in SHIP-V1 only        {len(only_s):3d}   "
          f"{', '.join(only_s) if only_s else '-'}")
    nm = sorted(set(g) - set(gok) - set(only_s))
    nm = sorted(s_ for s_ in g if s_ not in gok and s_ not in sok)
    print(f"  NOT MEASURABLE in either      {len(nm):3d}   "
          f"{', '.join(nm) if nm else '-'}")
    tot = len(both) + len(only_g) + len(only_s) + len(nm)
    print(f"  partition sums to             {tot:3d}   "
          f"{'OK' if tot == len(g) else 'MISMATCH -- DO NOT TRUST'}")

    if both:
        dl = np.array([sok[k]["w"] - gok[k]["w"] for k in both])
        print(f"\n  delta merge>=frame: median {np.median(dl):+.1f} pp, "
              f"min {dl.min():+.1f}, max {dl.max():+.1f}, "
              f"improved {int((dl > 0).sum())}/{len(dl)}, "
              f"worsened {int((dl < 0).sum())}/{len(dl)}")
        nbg = sum(gok[k]["nb"] for k in both); nbs = sum(sok[k]["nb"] for k in both)
        print(f"  tiles below 0.8, summed over ranked subjects: "
              f"GALLERY {nbg}  ->  SHIP-V1 {nbs}")
