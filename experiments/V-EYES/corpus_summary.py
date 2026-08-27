"""Summarise the corpus softness run, and separate the thesis from the confound.

Two questions, and they are not the same question.

THE THESIS. The estimation account predicts the master's advantage is LARGEST
where the merge averages many frames into each coefficient and SMALLEST where it
degenerates to selecting one, because a selector is bounded above by the frame it
picked and an estimator is not. That predicts a positive relationship between the
ratio and `avg_index`, the mean averaged-fraction across the non-base pyramid
bands.

THE CONFOUND, which was visible in the first six rows and would otherwise be
reported as the thesis. The reference is the best of a SAMPLED bracket, not the
best of the whole bracket. A 299-frame stack sampled 13 times covers 4.3% of the
focus sweep; a 22-frame stack sampled 13 times covers 59%. The sparse case very
often has NO sampled frame in focus at a given site, so its ceiling is weak and
the ratio inflates. Sampling fraction is therefore a rival explanation for every
number here, and it happens to correlate with stack depth, which correlates with
everything else about a subject.

Both are reported, along with a partial correlation that asks whether the thesis
survives once sampling fraction is held constant. If it does not, the honest
answer is that this corpus cannot separate them and the mechanism is unproven --
which is a result, not a failure. The instrument is not permitted to launder a
sampling artifact into a physical claim about the merge.

The partition is printed first and must sum to the corpus. A refusal is printed
with its reason and is never averaged into the headline.

Usage:
  python corpus_summary.py <rows.tsv> [density.tsv]
"""

import sys
import pathlib
import numpy as np


def read(p):
    lines = pathlib.Path(p).read_text(encoding="utf-8").splitlines()
    cols = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        if ln.strip():
            rows.append(dict(zip(cols, ln.split("\t"))))
    return rows


def f(row, k):
    try:
        return float(row[k])
    except (ValueError, KeyError):
        return float("nan")


def spearman(a, b):
    """Rank correlation: the relationships here are monotone, not linear."""
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def partial_spearman(a, b, c):
    """Correlation of a and b with c held constant, on ranks."""
    ra, rb, rc = (np.argsort(np.argsort(v)).astype(float) for v in (a, b, c))
    def resid(y, x):
        A = np.vstack([x, np.ones_like(x)]).T
        return y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
    return float(np.corrcoef(resid(ra, rc), resid(rb, rc))[0, 1])


def main():
    rows = read(sys.argv[1])
    by_state = {}
    for r in rows:
        by_state.setdefault(r["state"], []).append(r)
    meas = by_state.get("measured", [])

    print("=" * 78)
    print("PARTITION  (a refusal is not a pass; these sum to the corpus)")
    print("=" * 78)
    total = 0
    for st in ("measured", "refused", "failed", "not-examined"):
        rs = by_state.get(st, [])
        total += len(rs)
        print(f"  {st:<14} {len(rs):>3}")
        reasons = {}
        for r in rs:
            if r["reason"]:
                reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
        for k, v in sorted(reasons.items()):
            names = ", ".join(sorted(x["subject"] for x in rs if x["reason"] == k))
            print(f"       {k:<16} {v:>3}   {names}")
    print(f"  {'TOTAL':<14} {total:>3}")

    if not meas:
        return

    print()
    print("=" * 78)
    print("PER SUBJECT")
    print("=" * 78)
    print(f"  {'subject':<36}{'ratio':>8}{'CI':>18}{'sites':>7}"
          f"{'n/N':>10}{'avg':>7}  softer%")
    print("  " + "-" * 90)
    for r in sorted(meas, key=lambda r: -f(r, "ratio")):
        frac = f(r, "n_sampled") / max(f(r, "n_frames"), 1)
        print(f"  {r['subject']:<36}{f(r, 'ratio'):>8.3f}"
              f"  [{f(r, 'ci_lo'):>5.2f},{f(r, 'ci_hi'):>6.2f}]"
              f"{int(f(r, 'n_sites')):>7}"
              f"{int(f(r, 'n_sampled')):>5}/{int(f(r, 'n_frames')):<4}"
              f"{f(r, 'avg_index'):>7.2f}{f(r, 'softer_pct'):>8.1f}")

    ratio = np.array([f(r, "ratio") for r in meas])
    avg = np.array([f(r, "avg_index") for r in meas])
    frac = np.array([f(r, "n_sampled") / max(f(r, "n_frames"), 1) for r in meas])
    depth = np.array([f(r, "n_frames") for r in meas])
    soft = np.array([f(r, "softer_pct") for r in meas])

    print()
    print("=" * 78)
    print("HEADLINE  (measured subjects only)")
    print("=" * 78)
    n_above = int((ratio > 1).sum())
    print(f"  subjects measured                 {len(ratio)}")
    print(f"  master SHARPER than per-site best {n_above}  "
          f"({100 * n_above / len(ratio):.0f}%)")
    print(f"  master SOFTER                     {len(ratio) - n_above}  "
          f"{sorted(r['subject'] for r in meas if f(r, 'ratio') <= 1)}")
    print(f"  median ratio across subjects      {np.median(ratio):.3f}")
    print(f"  geometric mean ratio              {np.exp(np.mean(np.log(ratio))):.3f}")
    print(f"  range                             {ratio.min():.3f} .. {ratio.max():.3f}")

    print()
    print("=" * 78)
    print("THESIS vs CONFOUND")
    print("=" * 78)
    print(f"  Spearman(ratio, avg_index)        {spearman(ratio, avg):+.3f}"
          "   <- thesis predicts POSITIVE")
    print(f"  Spearman(ratio, sampling frac)    {spearman(ratio, frac):+.3f}"
          "   <- confound predicts NEGATIVE")
    print(f"  Spearman(ratio, stack depth)      {spearman(ratio, depth):+.3f}")
    print(f"  Spearman(avg_index, sampling frac){spearman(avg, frac):+.3f}"
          "   <- are they entangled?")
    print(f"  PARTIAL Spearman(ratio, avg_index | sampling frac)  "
          f"{partial_spearman(ratio, avg, frac):+.3f}")
    print(f"  PARTIAL Spearman(ratio, sampling frac | avg_index)  "
          f"{partial_spearman(ratio, frac, avg):+.3f}")
    print()
    print(f"  Spearman(softer%, sampling frac)  {spearman(soft, frac):+.3f}"
          "   <- where does the soft tail live?")
    print(f"  Spearman(softer%, avg_index)      {spearman(soft, avg):+.3f}")
    print(f"  Spearman(softer%, stack depth)    {spearman(soft, depth):+.3f}")

    if len(sys.argv) > 2 and pathlib.Path(sys.argv[2]).exists():
        print()
        print("=" * 78)
        print("SUBSAMPLE DENSITY CHECK  (does the ceiling stop moving?)")
        print("=" * 78)
        drows = read(sys.argv[2])
        for subj in sorted({r["subject"] for r in drows}):
            rs = sorted((r for r in drows if r["subject"] == subj),
                        key=lambda r: f(r, "n_sampled"))
            print(f"  {subj}  (N={int(f(rs[0], 'n_frames'))} frames)")
            prev = None
            for r in rs:
                if r["state"] != "measured":
                    print(f"      n={int(f(r, 'n_sampled')):>4}  {r['state']} "
                          f"{r['reason']}")
                    continue
                v = f(r, "ratio")
                delta = "" if prev is None else f"  ({100 * (v / prev - 1):+.1f}%)"
                print(f"      n={int(f(r, 'n_sampled')):>4}  "
                      f"frac={f(r, 'n_sampled') / f(r, 'n_frames'):>5.2f}  "
                      f"ratio={v:>7.3f}  "
                      f"CI [{f(r, 'ci_lo'):.2f},{f(r, 'ci_hi'):.2f}]{delta}")
                prev = v


if __name__ == "__main__":
    main()
