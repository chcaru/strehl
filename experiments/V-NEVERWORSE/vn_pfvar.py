"""Why the shipping binary does NOT reproduce the rogue-frame capture.

`vn_shipfr.py` put source frame 46 of bee-2-cpl through the pinned binary --
`--limit 46` against `--limit 47`, one frame apart on the real stack -- and the
L5 band shape moved 1.011x against nulls of 1.008x and 1.014x. The capture that
section 9.25 measured at 0.62336 of L5 does not happen in the product.

So the defect is in my model. This finds which difference does it.

THE CANDIDATE, AND I HAD ITS SIGN BACKWARDS. Section 9.25 carries a fidelity
note saying my model shares one `var0` across frames while `pyramid.rs` fits
`variance` per frame, and reasons that a dark frame has a lower fitted variance,
hence a lower floor, hence a LARGER `r` -- concluding the shipping concentration
is "at least as large as I measure". That reasoning is wrong. Frame 46 carries
2.058x the per-frame noise of the stack median (measured, `rogue.json`). Higher
noise means a HIGHER fitted variance, a HIGHER floor, and a SMALLER `r`. The
per-frame variance is not a gap that understates the defect; it is the defence
my model omitted.

THE ARMS.

  shared    one `var0` from frame 0, broadcast to every frame -- section 9.25
  perframe  `fit_variance` per frame, which is what pyramid.rs does

If the per-frame fit is the defence, frame 46's share collapses from `shared` to
`perframe` while an ordinary frame's share stays near its 1/N entitlement.

THE CONTROL THAT MAKES IT MEAN SOMETHING. Reporting only that the rogue's share
falls would be satisfied by any change that flattens every weight -- including
one that simply broke the selection. So an ORDINARY frame's share is carried
through both arms too. The claim is differential: the rogue's share must fall
while the ordinary frame's does not, and a fall in both is a broken arm rather
than a defence.
"""
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_gbundle as GB  # noqa: E402
import vn_pyr as VP  # noqa: E402
import vn_subgate as SG  # noqa: E402

NB = SG.NB
ROGUE = 46
ORDINARY = 100
BANDS = [0, 3, 4, 5, 6]


def shares(frames, varps, k):
    """Mean share of band k taken by each frame, under the shipping law.

    `varps[j]` is the variance pyramid used for frame j, so the shared and
    per-frame arms differ in exactly one thing.
    """
    ws = []
    for j, f in enumerate(frames):
        floor = np.maximum(SG.GATE * SG.BETA[k]
                           * np.maximum(varps[j][k], 0.0), 1.0)
        lap, _ = VP.lap_pyr(np.asarray(f, dtype=np.float64), NB)
        ex = VP.smooth5(lap[k] ** 2) - floor
        r = np.where(ex > 0.0, ex / floor / VP.SNR_REF, 0.0)
        ws.append(np.where(ex > 0.0, r ** SG.EXPO[k], 0.0))
    tot = np.zeros_like(ws[0])
    for w in ws:
        tot += w
    live = tot > 0.0
    if not live.any():
        return [0.0] * len(ws), 0.0
    den = np.where(live, tot, 1.0)
    return ([float((np.where(live, w / den, 0.0))[live].mean()) for w in ws],
            float(live.mean()))


def main():
    frames, kept, meta = GB.load("bee-2-cpl", rule="registered")
    n = len(frames)
    j46 = [j for j in range(n) if int(kept[j]) == ROGUE][0]
    jord = [j for j in range(n) if int(kept[j]) == ORDINARY][0]
    ent = 1.0 / n

    shared_v = VP.gauss_pyr(VP.fit_variance(frames[0])[0], NB)
    v_shared = [shared_v] * n
    per = [VP.fit_variance(np.asarray(f, dtype=np.float64))[0]
           for f in frames]
    v_per = [VP.gauss_pyr(v, NB) for v in per]

    v46 = float(np.median(per[j46]))
    vord = float(np.median(per[jord]))
    vmed = float(np.median([float(np.median(x)) for x in per]))
    print("bee-2-cpl: %d frames, entitlement 1/N = %.5f" % (n, ent))
    print("fitted variance   frame %d %.1f   frame %d %.1f   median %.1f"
          % (ROGUE, v46, ORDINARY, vord, vmed))
    print("  the rogue's fitted variance is %.2fx the stack median"
          % (v46 / vmed))
    if v46 <= vmed:
        print("  NOTE: the rogue does NOT fit a higher variance; the "
              "hypothesis under test is already in trouble")

    rows = []
    print("\n band   rogue shared  rogue perframe   ord shared  ord perframe")
    for k in BANDS:
        ss, lv_s = shares(frames, v_shared, k)
        sp, lv_p = shares(frames, v_per, k)
        rows.append(dict(band=k, rogue_shared=ss[j46], rogue_perframe=sp[j46],
                         ord_shared=ss[jord], ord_perframe=sp[jord],
                         live_shared=lv_s, live_perframe=lv_p,
                         rogue_ratio=(sp[j46] / ss[j46]) if ss[j46] else None))
        print("  L%d %12.5f %15.5f %12.5f %13.5f"
              % (k, ss[j46], sp[j46], ss[jord], sp[jord]))

    hot = [x for x in rows if x["rogue_shared"] > 10 * ent]
    if not hot:
        print("\nREFUSED: no band shows the rogue above 10x entitlement under "
              "the shared arm, so there is nothing for the per-frame arm to "
              "defend against. This does not reproduce section 9.25.")
        return 2
    fell = [x for x in hot if x["rogue_ratio"] is not None
            and x["rogue_ratio"] < 0.5]
    ordmove = max(abs(np.log(max(x["ord_perframe"], 1e-12)
                              / max(x["ord_shared"], 1e-12)))
                  for x in hot)
    ordmove = float(np.exp(ordmove))
    print("\n  bands where the rogue captures under the shared arm : %d"
          % len(hot))
    print("  of those, bands where the per-frame fit halves it    : %d"
          % len(fell))
    print("  largest move in the ORDINARY frame's share           : %.3fx"
          % ordmove)

    if ordmove > 3.0:
        verdict = ("UNDECIDED: the per-frame fit moved an ordinary frame's "
                   "share by %.2fx, so it is not acting selectively on the "
                   "rogue and this arm cannot be read as a defence" % ordmove)
    elif len(fell) == len(hot):
        verdict = ("THE PER-FRAME VARIANCE IS THE DEFENCE: it cuts the rogue's "
                   "share by more than half at all %d captured bands while "
                   "moving an ordinary frame's share by %.2fx"
                   % (len(hot), ordmove))
    elif fell:
        verdict = ("PARTIAL: the per-frame fit halves the rogue's share at %d "
                   "of %d captured bands; something else accounts for the rest"
                   % (len(fell), len(hot)))
    else:
        verdict = ("NOT THE DEFENCE: the per-frame fit does not halve the "
                   "rogue's share at any captured band, so the gap between my "
                   "model and the binary lies elsewhere")
    print("\nVERDICT: %s" % verdict)

    res = dict(subject="bee-2-cpl", n=n, entitlement=ent,
               rogue_source_index=ROGUE, ordinary_source_index=ORDINARY,
               var_rogue=v46, var_ordinary=vord, var_median=vmed,
               var_rogue_over_median=v46 / vmed, rows=rows,
               n_captured=len(hot), n_halved=len(fell),
               ordinary_move=ordmove, verdict=verdict)
    p = os.path.join(SG.OUT, "pfvar.json")
    json.dump(res, io.open(p, "w", encoding="utf-8"), default=float, indent=1)
    print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
