"""How much shift does the flat-exponent gauge actually care about?

WHY THIS EXISTS.  flatexp.registration_shift() refused three of the first
sixteen subjects on an SSD argmin taken at ONE site.  regdiag.py showed the
refusals were not evidence of a shift: on `flowers-cpl` and
`flower-bud-alone-cpl` the argmin ran to the BOUNDARY of the +/-4 px search with
double-digit excess, which is a surface with no minimum in range rather than a
displaced one, and on `dry-erase-marker-head-cpl` every site agreed to within
one pixel at under 1.8% excess.  Both arms' own logs report the same sidecar,
the same reference frame and the same placed/refused counts, so the geometry is
shared and SSD was reading CONTENT DIFFERENCE -- exactly the quantity the
experiment exists to measure -- and calling it displacement.

THE ERROR UNDERNEATH THAT.  The guard was written as though the comparison were
per-pixel.  It is not.  blotch, sharp and grain are band-power AGGREGATES over a
400x400 crop -- MAD and p99.5 within a passband -- computed on each arm
separately and only then divided.  A one-pixel offset moves the sampled region
by 0.25% of its width and cannot move an aggregate of that kind.  What WOULD
break the comparison is a GROSS offset, where the two crops stop being the same
piece of scene -- and a +/-4 px search cannot see a gross offset at all, because
it saturates.  So the guard was simultaneously too strict for the shifts that do
not matter and blind to the ones that do.

WHAT THIS SCRIPT DOES.  It refuses to guess the threshold.  It takes real
masters, shifts a copy of each against ITSELF -- so the only difference between
the two sides is the shift, with no arm difference left to confound it -- and
measures how far each of the three ratios departs from the 1.0000 they are
obliged to show at zero shift.  The guard's threshold is then set where the
statistic it protects actually starts to move, which is the only place a
threshold can be defended from.  It also records zero-shift normalised
cross-correlation at every planted shift, because NCC is the candidate
replacement test and its numbers have to come off the same sweep rather than
off a second one that could disagree.

Run:  python regsens.py [subject ...]
"""
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recertlib as R  # noqa: E402
from flatexp import DEF_DIR, CROP, UNIT_GAIN, ZERO_OFF, content_sites  # noqa: E402

SHIFTS = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256]


def ncc(pa, pb):
    """Normalised cross-correlation at zero shift, on the green plane."""
    a = pa.astype(np.float64).ravel()
    b = pb.astype(np.float64).ravel()
    a = a - a.mean()
    b = b - b.mean()
    da = float(np.sqrt((a * a).sum()))
    db = float(np.sqrt((b * b).sum()))
    if da == 0.0 or db == 0.0:
        return float("nan")
    return float((a * b).sum() / (da * db))


def ratio_set(ma, mb):
    """The three published ratios for one crop pair, gated as flatexp gates them."""
    out = {}
    for name, band, key in (("blotch", "mottle", "floor"),
                            ("sharp", "struct", "structure"),
                            ("grain", "grain", "floor")):
        a, b = ma[band], mb[band]
        if a["degenerate"] or b["degenerate"]:
            out[name] = None
            continue
        if key == "structure" and not (a["structure_detectable"]
                                       and b["structure_detectable"]):
            out[name] = None
            continue
        base, cand = a[key], b[key]
        if base is None or cand is None or base <= 1e-12:
            out[name] = None
            continue
        r = cand / base
        out[name] = float(r) if np.isfinite(r) else None
    return out


def sweep(name):
    dp = DEF_DIR / f"{name}--DEF-2f858c62.tiff"
    if not dp.exists():
        print(f"{name}: MISSING {dp}")
        return None
    a = tifffile.imread(dp)
    sites = content_sites(a)
    if not sites:
        print(f"{name}: NO-SITES")
        return None

    lim = max(SHIFTS)
    sites = [(y, x) for (y, x) in sites
             if y - lim >= 0 and x - lim >= 0
             and y + CROP + lim <= a.shape[0] and x + CROP + lim <= a.shape[1]]
    if not sites:
        print(f"{name}: no site survives a {lim}px margin -- skipped")
        return None

    print(f"\n== {name}  shape={a.shape}  sites={len(sites)}  "
          f"(self-shift: the ONLY difference between the two sides is the shift)")
    print("  shift   blotch    sharp    grain     NCC(0)    nB nS nG")
    rows = []
    for s in SHIFTS:
        acc = {"blotch": [], "sharp": [], "grain": []}
        nc = []
        for (y, x) in sites:
            ca = R.display_crop(a, y, x, (0, 0), UNIT_GAIN, ZERO_OFF, 1.0,
                                crop=CROP, already_srgb=True)
            cb = R.display_crop(a, y + s, x, (0, 0), UNIT_GAIN, ZERO_OFF, 1.0,
                                crop=CROP, already_srgb=True)
            rs = ratio_set(R.measure_crop(ca), R.measure_crop(cb))
            for k, v in rs.items():
                if v is not None:
                    acc[k].append(v)
            nc.append(ncc(a[y:y + CROP, x:x + CROP, 1],
                          a[y + s:y + s + CROP, x:x + CROP, 1]))
        row = dict(shift=s, n_sites=len(sites),
                   ncc=float(np.median(nc)) if nc else float("nan"))
        for k in ("blotch", "sharp", "grain"):
            row[k] = float(np.median(acc[k])) if acc[k] else float("nan")
            row["n_" + k] = len(acc[k])
        rows.append(row)
        print(f"  {s:5d}  {row['blotch']:7.4f}  {row['sharp']:7.4f}  "
              f"{row['grain']:7.4f}  {row['ncc']:9.5f}   "
              f"{row['n_blotch']:2d} {row['n_sharp']:2d} {row['n_grain']:2d}")
    return rows


def main(names):
    if not names:
        names = ["coffee-bubbles", "flowers-cpl", "dry-erase-marker-head-cpl"]
    allrows = {}
    for n in names:
        r = sweep(n)
        if r:
            allrows[n] = r
    if not allrows:
        raise SystemExit("nothing swept")

    print(f"\n== worst departure from 1.0000 across {len(allrows)} subject(s): "
          f"{', '.join(allrows)}")
    print("  shift   max|blotch-1|   max|sharp-1|   max|grain-1|    min NCC(0)")
    for i, s in enumerate(SHIFTS):
        def worst(k):
            vs = [abs(allrows[n][i][k] - 1.0) for n in allrows
                  if np.isfinite(allrows[n][i][k])]
            return max(vs) if vs else float("nan")
        mn = min(allrows[n][i]["ncc"] for n in allrows)
        print(f"  {s:5d}   {worst('blotch') * 100:12.3f}%  "
              f"{worst('sharp') * 100:12.3f}%  {worst('grain') * 100:12.3f}%  "
              f"{mn:12.5f}")

    print("\nREAD THIS AS: the guard must refuse at the shift where these "
          "departures stop\nbeing small against the effect under test "
          "(flat-1 moves sharp by 15-22%), and\nmust NOT refuse below it. "
          "NCC(0) is the candidate test; its threshold is\nwhatever value "
          "separates those two regimes on this table.")


if __name__ == "__main__":
    main(sys.argv[1:])
