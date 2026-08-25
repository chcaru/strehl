"""M118 arm 5 -- ORCH's N4 criterion, on a split that has power.

N4 (docs/research/ORCH-kernel-decision.md section 5) is a pre-registered NO-GO
trigger: "the election-agreement stratification REVERSES on a second subject --
i.e. gain becomes larger where the election disagrees."

My pre-registration (B2) implemented it at M113's own 0.95 threshold. On
wrapped-text-1 that threshold has NO POWER: lanczos3's election agrees with
catmull-rom's on 98.20% of quads and ALL 117 tiles land above 0.95, so the
"disagree" cell is empty and the bar cannot fail. Rule 20 -- an input that would
make the test fail has to exist, and here it does not.

The registered bar is reported as UNEVALUABLE, not narrowed (rule 30). This adds
two splits that always have power, and reports the EFFECT SIZE beside the sign,
because a correlation over a range of 0.95-1.00 can be statistically real and
numerically meaningless.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\M118")
HERE = Path(__file__).parent.parent
ARMS = ["nearest", "bilinear", "lanczos2", "lanczos3"]
BASELINE = "catmull-rom"
TILE = 128
BAND = (0.30, 0.48)

sys.path.insert(0, str(Path(__file__).parent))
from a1_metrics import tile_bandpowers, tile_origins, green  # noqa: E402


def run(subject: str) -> dict:
    rec = json.loads((HERE / "out" / f"r1_{subject}.json").read_text())
    base_img = green(Path(rec["arms"][BASELINE]["measure"]))
    h, w = base_img.shape
    origins = tile_origins(h, w)
    base = tile_bandpowers(base_img, origins)
    idx_cr = tifffile.imread(str(rec["arms"][BASELINE]["index"])).astype(np.int32)

    print(f"\n=== {subject}  ({len(origins)} tiles)")
    res = {"subject": subject, "arms": {}}
    for a in ARMS:
        img = green(Path(rec["arms"][a]["measure"]))
        gain = np.log10(tile_bandpowers(img, origins) / base)
        idx_a = tifffile.imread(str(rec["arms"][a]["index"])).astype(np.int32)
        agree_map = (idx_a == idx_cr)
        agree = np.array([agree_map[y:y + TILE, x:x + TILE].mean() for y, x in origins])

        med = np.median(agree)
        hi, lo = agree > med, agree <= med
        q = np.quantile(agree, [0.2, 0.8])
        dhi, dlo = agree >= q[1], agree <= q[0]
        corr = float(np.corrcoef(agree, gain)[0, 1]) if agree.std() > 0 else None

        e = {
            "agree_whole": float(agree_map.mean()),
            "agree_tile_min": float(agree.min()), "agree_tile_max": float(agree.max()),
            "median_split_hi": float(gain[hi].mean()) if hi.any() else None,
            "median_split_lo": float(gain[lo].mean()) if lo.any() else None,
            "decile_split_hi": float(gain[dhi].mean()) if dhi.any() else None,
            "decile_split_lo": float(gain[dlo].mean()) if dlo.any() else None,
            "corr": corr,
            "gain_mean": float(gain.mean()), "gain_sd": float(gain.std(ddof=1)),
        }
        e["median_delta"] = (e["median_split_hi"] - e["median_split_lo"]
                             if hi.any() and lo.any() else None)
        e["decile_delta"] = (e["decile_split_hi"] - e["decile_split_lo"]
                             if dhi.any() and dlo.any() else None)
        # N4 fires when the gain is LARGER where the election DISAGREES.
        e["N4_reversed"] = bool(e["median_delta"] is not None and e["median_delta"] < 0)
        # ... but only meaningfully if the reversal is a material fraction of the effect.
        e["reversal_frac_of_effect"] = (abs(e["median_delta"]) / abs(e["gain_mean"])
                                        if e["gain_mean"] else None)
        res["arms"][a] = e
        print(f"  {a:<12} agree {e['agree_whole']*100:6.2f}%  tile range "
              f"[{e['agree_tile_min']:.3f},{e['agree_tile_max']:.3f}]")
        print(f"               median split  hi {e['median_split_hi']:+.4f}  "
              f"lo {e['median_split_lo']:+.4f}  delta {e['median_delta']:+.4f}")
        print(f"               20/80 split   hi {e['decile_split_hi']:+.4f}  "
              f"lo {e['decile_split_lo']:+.4f}  delta {e['decile_delta']:+.4f}")
        print(f"               corr {corr:+.4f}   gain {e['gain_mean']:+.4f} "
              f"(tile sd {e['gain_sd']:.4f})   N4 reversed: {e['N4_reversed']}  "
              f"({100*e['reversal_frac_of_effect']:.1f}% of the effect)")
    (HERE / "out" / f"a3_n4_{subject}.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["flat-on-ruler-cpl", "wrapped-text-1", "bee-3-cpl"]):
        run(s)
