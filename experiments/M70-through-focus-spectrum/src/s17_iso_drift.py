"""M70 s17 - two post hoc checks the pre-registration did not anticipate.

(1) Does the sign of the measured asymmetry track ISO rather than optics?
    s15/s16 showed the three 299-frame bee captures and the two wrapped-text
    captures split in sign. Those splits line up with ISO. If the whole corpus
    does, the residual asymmetry is an artefact of the noise subtraction, not a
    property of the PSF - which would be a stronger statement than "scene-like".

(2) Level drift through the sweep - the candidate mechanism for (1).

This is UNRULED. It was not pre-registered, it is post hoc, and it is reported
as such.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
STACKS = list(S7.APERTURE.keys())


def main() -> None:
    cen = {e["stack"]: e for e in json.load(open(os.path.join(OUT, "exif-census.json")))
           if isinstance(e, dict) and "stack" in e}
    S = json.load(open(os.path.join(OUT, "s15_asym_corpus.json")))["stacks"]
    NB = json.load(open(os.path.join(OUT, "s16_null_band.json")))

    print("=" * 118)
    print("POST HOC (1) - does the asymmetry SIGN track ISO?")
    print("=" * 118)
    hdr = ("stack", "ISO", "f/", "K", "A50", "A25", "A10", "powered")
    print("{:<16}{:>6}{:>6}{:>5}{:>9}{:>9}{:>9}{:>9}".format(*hdr))
    rows = []
    for st in STACKS:
        e = S[st]
        iso = float(max(cen[st]["iso"], key=lambda k: cen[st]["iso"][k]))
        pw = NB[st]["A50"]["outside"]
        print(f"{st:<16}{int(iso):>6}{e['aperture']:>6.1f}{e['K']:>5}"
              f"{e['A50']:>+9.4f}{e['A25']:>+9.4f}{e['A10']:>+9.4f}"
              f"{('YES' if pw else 'no'):>9}")
        rows.append((st, iso, e["A50"], e["A25"], e["A10"], pw))

    iso = np.array([r[1] for r in rows])
    res = {"iso": {}, "drift": {}}
    for key, col in (("A50", 2), ("A25", 3), ("A10", 4)):
        a = np.array([r[col] for r in rows])
        for lab, keep in (("all 12", np.ones(12, bool)),
                          ("powered only", np.array([r[5] for r in rows]))):
            i, x = iso[keep], a[keep]
            r = float(np.corrcoef(np.log(i), x)[0, 1])
            ent = {"n": int(keep.sum()), "corr_logISO": r, "by_iso": {}}
            print(f"\n  {key} / {lab}: n={keep.sum()}  corr(log ISO, {key}) = {r:+.3f}")
            for lv in sorted(set(i)):
                m = i == lv
                ent["by_iso"][int(lv)] = {
                    "n": int(m.sum()), "median": float(np.median(x[m])),
                    "n_pos": int((x[m] > 0).sum()), "n_neg": int((x[m] < 0).sum())}
                print(f"      ISO {int(lv):>4}: n={m.sum()}  median {np.median(x[m]):+.4f}"
                      f"  signs +{int((x[m] > 0).sum())}/-{int((x[m] < 0).sum())}")
            res["iso"][f"{key}|{lab}"] = ent

    print("\n" + "=" * 118)
    print("POST HOC (2) - LEVEL DRIFT through the sweep (the candidate mechanism)")
    print("  If patch level drifts monotonically, a mis-scaled noise floor biases the")
    print("  curve tails asymmetrically. Slope is per-frame fractional change in the")
    print("  w^2-weighted patch level, median over textured patches.")
    print("=" * 118)
    print(f"{'stack':<16}{'ISO':>6}{'K':>5}{'drift %/frame':>15}{'total %':>10}{'A50':>9}")
    dr = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d, 1.0)
        tex, _ = A5.classify(d, s, nvar)
        K = d["level"].shape[0]
        x = np.arange(K, dtype=np.float64)
        sl = []
        for p in np.where(tex)[0]:
            y = d["level"][:, p].astype(np.float64)
            if y.mean() > 0:
                sl.append(np.polyfit(x, y, 1)[0] / y.mean())
        m = float(np.median(sl))
        dr.append(m)
        print(f"{st:<16}{int(max(cen[st]['iso'], key=lambda k: cen[st]['iso'][k])):>6}"
              f"{K:>5}{100 * m:>15.4f}{100 * m * K:>10.2f}{S[st]['A50']:>+9.4f}")
        res["drift"][st] = {"slope_frac_per_frame": m, "total_frac": m * K,
                            "A50": S[st]["A50"]}
    dr = np.array(dr)
    a50 = np.array([S[st]["A50"] for st in STACKS])
    tot = dr * np.array([S[st]["K"] for st in STACKS], dtype=np.float64)
    print(f"\n  corr(drift %/frame, A50)  = {np.corrcoef(dr, a50)[0, 1]:+.3f}")
    print(f"  corr(total drift,   A50)  = {np.corrcoef(tot, a50)[0, 1]:+.3f}")
    res["drift_corr"] = {"per_frame": float(np.corrcoef(dr, a50)[0, 1]),
                         "total": float(np.corrcoef(tot, a50)[0, 1])}

    with open(os.path.join(OUT, "s17_iso_drift.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s17_iso_drift.json")


if __name__ == "__main__":
    main()
