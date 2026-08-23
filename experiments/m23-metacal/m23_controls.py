"""M23 control arms: what does R < 1 at small delta actually measure?

The premise of R4 is that the per-edge response R is small BECAUSE of the
defocus asymmetry between the two frames.  These arms hold that story to
account by removing, one at a time, everything that is not defocus.

  cb           real coffee-bean pairs, spans 1-2       defocus present
  cb-self      the SAME frame against itself           defocus REMOVED
  cb-self-ped  same frame, pair pushed off zero        defocus REMOVED, no lock
  cb-ped       real pairs, pair pushed off zero        defocus present, no lock
  field-p0     synthetic band-limited field, no warp   NO defocus, NO resampler
  112          real pairs on the placebo stack         no defocus asymmetry

FAILURE DIRECTION OF R (registered): R is a slope, unbiased at 1.000.  R < 1
means the estimator under-reports the planted increment; R > 1 over-reports.  A
response that moves when the defocus is REMOVED is not a defocus response, and
the whole of R4 rests on it being one.

Run:  python m23_controls.py > out\\controls.txt
"""

from __future__ import annotations

import numpy as np

from m23_mc import by_delta, by_span, read_metacal

DELTAS = [1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3]

ARMS = [
    ("cb spans 1-2  (real, defocus)", "data/coffee-bean-metacal.csv", (1, 2), 0.0),
    ("cb-ped        (real, +4e-3 ped)", "data/cb-ped-metacal.csv", (1,), 4e-3),
    ("cb-self       (self, no defocus)", "data/cb-self-metacal.csv", (0,), 0.0),
    ("cb-self-ped   (self, +4e-3 ped)", "data/cb-self-ped-metacal.csv", (0,), 4e-3),
    ("field-p0      (no resampler at all)", "data/cb-field-metacal.csv", (0,), 0.0),
    ("112 spans 1-2 (placebo stack)", "data/stack-112-metacal.csv", (1, 2), 0.0),
]


def rows_for(path, spans, cfg="m10"):
    mc = read_metacal(path, cfg=cfg)
    if spans == (0,):
        return mc
    out = []
    for s in spans:
        out += by_span(mc, s)
    return out


def med(v):
    v = np.asarray(list(v), float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else float("nan")


def main() -> int:
    print("=" * 104)
    print("CONTROL ARMS - is the small-delta response deficit caused by DEFOCUS?")
    print("  median two-sided R = (l+ - l-) / (log(1+d) - log(1-d)).  Unbiased => 1.000")
    print("  FAILURE DIRECTION: R < 1 = under-response.  A deficit that survives the")
    print("  removal of defocus is not a defocus response.")
    print("=" * 104)
    print(f"  {'arm':<37} {'n':>5} " + "".join(f"{d:>10.1e}" for d in DELTAS))
    table = {}
    for name, path, spans, _ped in ARMS:
        rs = rows_for(path, spans)
        vals = [med(x.r_two for x in by_delta(rs, d)) for d in DELTAS]
        n = len(by_delta(rs, DELTAS[0]))
        table[name] = vals
        print(f"  {name:<37} {n:>5} " + "".join(f"{v:>10.4f}" for v in vals))

    print("\n  SPREAD (p25-p75) of R, same arms")
    for name, path, spans, _ped in ARMS:
        rs = rows_for(path, spans)
        cells = []
        for d in DELTAS:
            v = np.array([x.r_two for x in by_delta(rs, d)], float)
            v = v[np.isfinite(v)]
            cells.append(f"[{np.percentile(v, 25):.3f},{np.percentile(v, 75):.3f}]"
                         if v.size else "-")
        print(f"  {name:<37} " + " ".join(f"{c:>16}" for c in cells))

    print("\n" + "=" * 104)
    print("N4b  THE DECISIVE COMPARISON")
    print("=" * 104)
    cb = table["cb spans 1-2  (real, defocus)"]
    sf = table["cb-self       (self, no defocus)"]
    fp = table["field-p0      (no resampler at all)"]
    pd = table["cb-ped        (real, +4e-3 ped)"]
    sp = table["cb-self-ped   (self, +4e-3 ped)"]
    for k, d in enumerate(DELTAS):
        print(f"\n  delta = {d:.1e}")
        print(f"    real defocus pair, bilinear plant about zero   R = {cb[k]:.4f}")
        print(f"    SELF pair (zero defocus), bilinear plant       R = {sf[k]:.4f}"
              f"   <- defocus removed, deficit {'SURVIVES' if sf[k] < 0.9 else 'gone'}")
        print(f"    synthetic field, NO resampler anywhere         R = {fp[k]:.4f}"
              f"   <- resampler removed, deficit "
              f"{'SURVIVES' if fp[k] < 0.9 else 'gone'}")
        print(f"    real pair, plant composed off a 4e-3 pedestal  R = {pd[k]:.4f}")
        print(f"    self pair, plant composed off a 4e-3 pedestal  R = {sp[k]:.4f}")

    print("\n" + "=" * 104)
    print("ATTRIBUTION (DERIVED from the rows above)")
    print("=" * 104)
    print("  If R measured defocus-induced shrinkage, then removing the defocus")
    print("  (cb -> cb-self) would send R to 1.000 and removing the resampler")
    print("  (cb -> field-p0) would leave it alone.  Read the signs:")
    print(f"    {'delta':>9} {'cb':>9} {'self':>9} {'field':>9} "
          f"{'self - cb':>10} {'field - cb':>11}")
    for k, d in enumerate(DELTAS):
        print(f"    {d:>9.1e} {cb[k]:>9.4f} {sf[k]:>9.4f} {fp[k]:>9.4f} "
              f"{sf[k] - cb[k]:>+10.4f} {fp[k] - cb[k]:>+11.4f}")

    print("\n  PEDESTAL ARM - the same plant, measured about a 4e-3 operating point")
    print("  (a ~4.8 plane px differential displacement, so no tile sits in the")
    print("  sub-pixel locking zone).  CONFOUND, stated: the pedestal also moves")
    print("  the operating point, so this arm changes two things at once.")
    print(f"    {'delta':>9} {'cb':>9} {'cb-ped':>9} {'self':>9} {'self-ped':>9}")
    for k, d in enumerate(DELTAS):
        print(f"    {d:>9.1e} {cb[k]:>9.4f} {pd[k]:>9.4f} {sf[k]:>9.4f} "
              f"{sp[k]:>9.4f}")

    print("\n" + "=" * 104)
    print("FIELD ARM REPEATABILITY (12 independent noise realisations)")
    print("=" * 104)
    mc = read_metacal("data/cb-field-metacal.csv", cfg="m10")
    print(f"  {'delta':>9} {'reps':>5} {'median R':>9} {'sd':>9} {'min':>9} {'max':>9}")
    for d in DELTAS:
        v = np.array([x.r_two for x in by_delta(mc, d)], float)
        v = v[np.isfinite(v)]
        print(f"  {d:>9.1e} {v.size:>5} {np.median(v):>9.4f} {v.std(ddof=1):>9.4f} "
              f"{v.min():>9.4f} {v.max():>9.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
