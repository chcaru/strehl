"""M70 s12 - VOID condition 4: patch-size sensitivity.

Pre-registered in PREREGISTRATION.md sec 5.4:

    The whole measurement is repeated at 128 GQ samples on a subset. A patch
    mixes depths within its footprint, which broadens the apparent
    through-focus response and is therefore *generous* to the proposal. If
    halving the patch changes the stack-median n_eff_MF by more than 1.5x, the
    256-sample numbers are reported as an upper bound only.

Subset chosen to span both axes the corpus offers, and chosen BEFORE the run:
the two extremes of frame count (19 and 299) and one stack at each of the three
marked apertures.

  coffee-bubbles   K= 19  f/8     shallowest stack
  109MSDCF         K= 22  f/11    the aperture where fact 27 put the cutoff
  wrapped-text-1   K=130  f/5.6
  bee-3            K=299  f/5.6   deepest stack

Halving the patch to 128 GQ samples (255 sensor px) also halves the Welch tile
to 64, because a tile cannot exceed its patch. Frequency resolution therefore
halves: bins land every 1/64 = 0.0156 sensor cyc/px instead of every 0.0078.
The mid bands (0.100-0.2762) still carry 3-5 bins each; b1_low (0.025-0.050)
carries 1-2 and is used only for the textured/flat classification. That
resolution loss is a property of the test, not of the corpus, and is stated
here rather than in the result.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
import s04_through_focus as S4  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402

OUT = A5.OUT
SUBSET = ["coffee-bubbles", "109MSDCF", "wrapped-text-1", "bee-3"]
SMALL_PATCH = 128
SMALL_TILE = 64
TAG = "-p128"


def measure() -> None:
    with open(os.path.join(OUT, "exif-census.json"), encoding="utf-8") as fh:
        census = {c["stack"]: c for c in json.load(fh)}
    S4.CENTRES = S4.patch_centres(SMALL_PATCH)
    print(f"patch={SMALL_PATCH} GQ samples ({2 * SMALL_PATCH - 1} sensor px), "
          f"tile={SMALL_TILE}, {len(S4.CENTRES)} patches/frame", flush=True)
    for st in SUBSET:
        if os.path.exists(os.path.join(OUT, f"tfs-{st}{TAG}.npz")):
            print(f"  {st:16s} already measured", flush=True)
            continue
        hist = census[st]["iso"]
        assert len(hist) == 1, (st, hist)
        S4.run_stack(st, float(max(hist, key=lambda k: hist[k])),
                     patch=SMALL_PATCH, tile=SMALL_TILE, tag=TAG)


def stats(stack: str, tag: str) -> dict:
    d = A5.load(stack, tag)
    s, nvar = A5.signal(d)
    tex, _ = A5.classify(d, s, nvar)
    idx = [p for p in range(s.shape[1]) if tex[p]]
    acc = {"n_all": [], "n_w5": [], "relA1": [], "relA2": [], "g3": []}
    for bd in M.MID_BANDS:
        j = d["bands"].index(bd)
        v = [S7.tf_stats_uc(s[:, p, j]) for p in idx]
        acc["n_all"].append(A5.med([x["n_eff_uc"] for x in v]))
        acc["n_w5"].append(A5.med([x["n_eff_uc_window"] for x in v]))
        acc["relA1"].append(A5.med([x["rel_amp_1"] for x in v]))
        acc["relA2"].append(A5.med([x["rel_amp_2"] for x in v]))
        acc["g3"].append(A5.med([S7.gain_top_m_uc(s[:, p, j], 3) for p in idx]))
    return {"tex": len(idx), **{k: float(np.mean(v)) for k, v in acc.items()}}


def main() -> None:
    measure()
    print()
    print("=" * 108)
    print("VOID CONDITION 4 - stack-median mid-band statistics at 256 vs 128 GQ samples")
    print("=" * 108)
    print(f"{'stack':16s} {'K':>4s} {'F':>5s} | {'tex256':>6s} {'tex128':>6s} | "
          f"{'n_eff(all) 256':>14s} {'128':>8s} {'ratio':>7s} | "
          f"{'n_eff(+-5) 256':>14s} {'128':>8s} {'ratio':>7s} | "
          f"{'relA1 256':>9s} {'128':>7s}")
    rows = []
    for st in SUBSET:
        a, b = stats(st, ""), stats(st, TAG)
        r = {"stack": st, "F": S7.APERTURE[st], "p256": a, "p128": b,
             "ratio_all": b["n_all"] / a["n_all"],
             "ratio_w5": b["n_w5"] / a["n_w5"],
             "d_relA1": b["relA1"] - a["relA1"]}
        rows.append(r)
        k = A5.load(st)["power"].shape[0]
        print(f"{st:16s} {k:4d} {r['F']:5.1f} | {a['tex']:6d} {b['tex']:6d} | "
              f"{a['n_all']:14.3f} {b['n_all']:8.3f} {r['ratio_all']:7.3f} | "
              f"{a['n_w5']:14.3f} {b['n_w5']:8.3f} {r['ratio_w5']:7.3f} | "
              f"{a['relA1']:9.3f} {b['relA1']:7.3f}")

    ra = [r["ratio_all"] for r in rows]
    rw = [r["ratio_w5"] for r in rows]
    dr = [abs(r["d_relA1"]) for r in rows]
    print()
    print(f"  n_eff(all)  ratio 128/256: min {min(ra):.3f}  median "
          f"{np.median(ra):.3f}  max {max(ra):.3f}")
    print(f"  n_eff(+-5)  ratio 128/256: min {min(rw):.3f}  median "
          f"{np.median(rw):.3f}  max {max(rw):.3f}")
    print(f"  |d rel_amp_1|              max {max(dr):.4f}")
    worst = max(max(ra), max(rw), 1 / min(ra), 1 / min(rw))
    print()
    print(f"  Pre-registered trigger: any stack-median n_eff changing by > 1.50x.")
    print(f"  Largest change observed: {worst:.3f}x  ->  "
          f"{'VOID CONDITION 4 FIRES' if worst > 1.5 else 'PASSES; the 256-sample numbers stand'}")

    with open(os.path.join(OUT, "s12_patchsize.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "worst": worst}, fh, indent=1)
    print("\nwrote out/s12_patchsize.json")


if __name__ == "__main__":
    main()
