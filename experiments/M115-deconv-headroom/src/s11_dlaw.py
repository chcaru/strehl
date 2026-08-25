r"""M115 -- s11: does cancellation protection track D = max/min of the terms?

ORCH's addendum retracts the "it is a ratio of two arms, so it cancels"
protection and replaces it with a graded law: the protection is a property of
how UNEQUAL the two terms are, indexed by D = max/min, measured on M111 at
1547 tiles with median |shift| rising 0.68% -> 8.04% across D bins, Spearman
+0.530.

M115 supplied the -1.0% that ORCH originally generalised into the retracted
rule, so M115 owes ORCH the D that goes with it.  But the same machinery can
test the replacement law rather than merely comply with it -- ORCH's triage
output has now needed correcting three times, and the D law currently rests on
one milestone.  This is a second instrument, on different subjects, with a
different statistic.

REGISTERED PREDICTIONS, recorded before the sweep is run
--------------------------------------------------------
  Q1  |shift| under the real PIL narrowing rises monotonically across ORCH's
      exact D bins, and Spearman rho(D, |shift|) > 0.
  Q2  M115's headline ratio lands at low D and low |shift|, consistent with the
      -1.0% it reported.
  Q3  The relationship is NOT merely an artefact of pairs involving a
      degenerate arm.  BEST1 and FRAME* are the same estimator in this
      instrument (identical P_sig and P_noise), so that pair contributes a
      free D=1, shift=0 point that would prop up a monotone result without
      evidence.  IT IS EXCLUDED, and the law must survive the exclusion.

Support counts are reported per bin.  ORCH's table has none, and the extreme
bins are always the least-supported ones; a median over five points is not
comparable to a median over three hundred.
"""
import os, sys, json, itertools
import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner
from negctl_bitdepth import narrow8

STACKS = ["109MSDCF", "119MSDCF"]
DF = 0.01
ARMS = ["BEST1", "FRAME*", "GATE", "MEAN", "MF", "WIENER", "WIENER_UNG"]
EXCLUDE = {("BEST1", "FRAME*")}          # Q3: the degenerate pair
EDGES = [1.0, 1.25, 1.50, 2.0, 3.0, 5.0, 8.0, np.inf]
LABELS = ["[1.00,1.25)", "[1.25,1.50)", "[1.50,2)", "[2,3)",
          "[3,5)", "[5,8)", "[8,inf)"]


def snr_per_bin(cube, g, rn_e, crop, rb, mid, s_fixed=None):
    """Amplitude SNR per frequency bin, per arm, through the split channel."""
    if s_fixed is None:
        s_fixed, _, _ = L.calibrate_s(cube, L.focus_fields(cube, g, rn_e)[1])
    sp = L.split_channel(cube, g, rn_e, s_fixed, crop, want=ARMS)
    out = {}
    for a in ARMS:
        st = L.split_stats(rb, *sp[a])
        out[a] = np.sqrt(np.maximum(st[2][mid], 0.0))
    return out, s_fixed


def main():
    banner("s11 -- cancellation protection vs D = max/min of the terms")
    pts_D, pts_shift, prov = [], [], []
    headline = {}

    for stack in STACKS:
        cube, g, rn_e, B = load_detail(stack)
        crop = L.crop_fn(L.PAD, B)
        rb = L.RadialBins(B, DF)
        mid = rb.band_mask(*L.MIDBAND)
        intact, s0 = snr_per_bin(cube, g, rn_e, crop, rb, mid)
        # s is pinned to the intact value so that D and shift describe the
        # SAME estimator; s09 showed re-calibration is a separate effect worth
        # 0.0071 in slope, and mixing the two would confound this law.
        narrowed, _ = snr_per_bin(narrow8(cube), g, rn_e, crop, rb, mid,
                                  s_fixed=s0)
        nb = intact[ARMS[0]].size
        print(f"  {stack}: s={s0:.4f}, {nb} mid-band bins")

        for a, b in itertools.combinations(ARMS, 2):
            if (a, b) in EXCLUDE or (b, a) in EXCLUDE:
                continue
            ia, ib = intact[a], intact[b]
            na, nbn = narrowed[a], narrowed[b]
            ok = (ia > 1e-9) & (ib > 1e-9) & (na > 1e-9) & (nbn > 1e-9)
            D = np.maximum(ia, ib) / np.minimum(ia, ib)
            shift = ((na / nbn) / (ia / ib)) - 1.0
            for k in np.where(ok)[0]:
                pts_D.append(float(D[k]))
                pts_shift.append(float(shift[k]))
                prov.append(f"{stack}:{a}/{b}:bin{k}")
            if {a, b} == {"WIENER", "GATE"}:
                headline[stack] = dict(
                    D_mean=float(np.mean(D[ok])),
                    D_min=float(np.min(D[ok])), D_max=float(np.max(D[ok])),
                    shift_mean=float(np.mean(shift[ok])))

    D = np.array(pts_D)
    S = np.abs(np.array(pts_shift))
    print(f"\n  {D.size} points, D range [{D.min():.2f}, {D.max():.2f}], "
          f"{len(STACKS)} stacks, {len(list(itertools.combinations(ARMS,2)))-1} "
          f"arm pairs (degenerate pair excluded)")

    # ---- ORCH's exact bins, with the support counts her table omits -------
    print(f"\n  {'D bin':14s} {'n':>6s} {'median |shift|':>15s} {'IQR':>16s}")
    med, cnt = [], []
    for i, lab in enumerate(LABELS):
        m = (D >= EDGES[i]) & (D < EDGES[i + 1])
        n = int(m.sum())
        cnt.append(n)
        if n == 0:
            med.append(np.nan)
            print(f"  {lab:14s} {n:6d} {'--':>15s}")
            continue
        v = S[m]
        med.append(float(np.median(v)))
        q1, q3 = np.percentile(v, [25, 75])
        print(f"  {lab:14s} {n:6d} {100*med[-1]:14.2f}% "
              f"[{100*q1:6.2f}, {100*q3:6.2f}]%")

    ok = [i for i, c in enumerate(cnt) if c >= 10]
    mono = all(med[ok[i]] <= med[ok[i + 1]] + 1e-12 for i in range(len(ok) - 1))
    rho, p = spearmanr(D, S)
    print(f"\n  monotone across bins with n>=10: {mono}")
    print(f"  Spearman rho(D, |shift|) = {rho:+.3f}  (p = {p:.3g}, n = {D.size})")
    q1 = (rho > 0)
    print(f"  Q1 {'PASS' if q1 and mono else 'PARTIAL' if q1 else 'FAIL'}  "
          f"(ORCH measured +0.530 on M111)")

    print("\n  Q2 -- M115's headline ratio, R_SNR(WIENER)/R_SNR(GATE)")
    for stack, h in headline.items():
        print(f"     {stack}: D = {h['D_mean']:.3f} "
              f"(range {h['D_min']:.2f}-{h['D_max']:.2f}), "
              f"mean shift {100*h['shift_mean']:+.2f}%")
    dmean = float(np.mean([h["D_mean"] for h in headline.values()]))
    band = next(LABELS[i] for i in range(len(LABELS))
                if EDGES[i] <= dmean < EDGES[i + 1])
    print(f"     -> pooled D = {dmean:.3f}, which is ORCH's {band} bin")

    res = dict(n=int(D.size), bins=LABELS, counts=cnt,
               median_abs_shift=med, spearman=float(rho), p=float(p),
               monotone=bool(mono), headline=headline, D_pooled=dmean,
               D_band=band, excluded_pair=sorted(list(EXCLUDE)[0]),
               D_max_global=float(D.max()), D_min_global=float(D.min()))
    json.dump(res, open(os.path.join(L.OUT, "s11_dlaw.json"), "w"), indent=2)
    print("\n  -> s11_dlaw.json")


if __name__ == "__main__":
    main()
