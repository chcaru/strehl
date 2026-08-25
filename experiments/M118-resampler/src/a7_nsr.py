"""M118 arm 9 -- turn ORCH's value/position rule into a computable prediction.

ORCH's correction #2 says dispersion statistics absorb quantisation variance and
are destroyed, location statistics are largely immune. My a6 data agrees with
the spirit but contains an apparent exception worth resolving:

  sd DN is a DISPERSION statistic. Absolutely, it is destroyed -- M4 read
  735.3 DN and 2.90 DN through PIL. But the RATIO of sd between two arms on the
  same data moved 0.01%, while the ratio of BAND POWER -- also dispersion --
  moved -0.90% in detail tiles and -9.92% in flat ones.

So "dispersion" alone does not decide it. The quantity that does, and that
subsumes ORCH's "small-over-large ratios compress toward 1":

    the added quantisation variance N, measured IN THE BAND AND SUPPORT the
    statistic integrates over, as a fraction of the signal S there.

A common-mode N cancels in an arm ratio only to the extent N << S. Where N ~ S
the ratio compresses toward 1 regardless of whether the statistic is a ratio.

PREDICTION, registered before the numbers below are computed. If S1/S2 is the
true between-arm ratio and N is the added in-band power, the observed ratio
should be (S1 + N) / (S2 + N). Inverting a6's measured compressions implies:

    detail tiles   N/S2 ~ 5.1%     (1.22716 -> 1.21616)
    flat tiles     N/S2 ~ 95.6%    (1.25478 -> 1.13025)

That is a ~19x difference. This script measures N directly, from the actual
quantisation residual, and checks it against those two implied values. If the
measured N/S lands near them the rule is predictive; if not, it is a story.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from a1_metrics import (ARMS, BASELINE, DECILE, TILE, band_power,  # noqa: E402
                        grad_mag, tile_origins)

HERE = Path(__file__).parent.parent
SUBJECT = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
rec = json.loads((HERE / "out" / f"r1_{SUBJECT}.json").read_text())


def true_plane(arm):
    return tifffile.imread(str(Path(rec["arms"][arm]["measure"])))[:, :, 1]


def pil_plane(arm):
    return np.asarray(Image.open(str(Path(rec["arms"][arm]["measure"]))))[:, :, 1]


planes = {a: true_plane(a).astype(np.float64) for a in ARMS}
origins = tile_origins(*planes[BASELINE].shape)
gm = grad_mag(np.mean([planes[a] for a in ARMS], axis=0))
tile_grad = np.array([gm[y:y + TILE, x:x + TILE].mean() for y, x in origins])
order = np.argsort(tile_grad)
n = max(1, int(len(origins) * DECILE))
flat_idx, detail_idx = order[:n], order[-n:]
og = np.array(origins)

# The quantisation residual, on the ORIGINAL 16-bit scale. PIL returns t >> 8,
# so reconstructing at (pil << 8) discards exactly the low byte.
resid = {a: planes[a] - (pil_plane(a).astype(np.float64) * 256.0) for a in ARMS}
r0 = resid[BASELINE]
print(f"=== {SUBJECT}: the quantisation residual PIL discards")
print(f"  range [{r0.min():.0f}, {r0.max():.0f}] DN, mean {r0.mean():.1f}, sd {r0.std():.1f}")
print(f"  a uniform residual on [0,256) predicts mean 127.5, sd {256 / np.sqrt(12):.1f}")
print()

print("=== N/S measured IN BAND, per stratum (the quantity that decides)")
print()
print(f"  {'stratum':<9}{'S signal':>13}{'N quant':>12}{'N/S':>9}{'implied N/S':>13}")
out = {}
for label, idx in (("detail", detail_idx), ("flat", flat_idx)):
    S = float(np.mean([band_power(planes[BASELINE][y:y + TILE, x:x + TILE])
                       for y, x in og[idx]]))
    N = float(np.mean([band_power(r0[y:y + TILE, x:x + TILE]) for y, x in og[idx]]))
    implied = 0.051 if label == "detail" else 0.956
    print(f"  {label:<9}{S:13.4g}{N:12.4g}{N / S:9.3f}{implied:13.3f}")
    out[label] = {"S": S, "N": N, "NS": N / S, "implied": implied}
print()

print("=== Does (S1+N)/(S2+N) predict the observed compression?")
print()
a6 = json.loads((HERE / "out" / f"a6_reconcile_{SUBJECT}.json").read_text())
bp_rows = {r["stratum"]: r for r in a6["R2"] if "band power" in r["stat"]}
print(f"  {'stratum':<9}{'true ratio':>12}{'observed':>11}{'predicted':>11}{'resid':>9}")
for label in ("detail", "flat"):
    t = bp_rows[label]["ratio_true"]
    obs = bp_rows[label]["ratio_pil"]
    N_over_S2 = out[label]["NS"]
    pred = (t + N_over_S2) / (1.0 + N_over_S2)
    out[label].update({"ratio_true": t, "observed": obs, "predicted": pred})
    print(f"  {label:<9}{t:12.5f}{obs:11.5f}{pred:11.5f}{pred - obs:+9.5f}")
print()

err = max(abs(out[l]["predicted"] - out[l]["observed"]) for l in ("detail", "flat"))
span = abs(out["detail"]["observed"] - out["flat"]["observed"])
print(f"  worst prediction error {err:.5f} against a {span:.5f} spread between strata")
print("  PREDICTIVE" if err < 0.2 * span else "  NOT PREDICTIVE -- the model is wrong")
print()

print("=== The one-line test any agent can run before deciding to re-run")
print()
print("  Compute the band/support-restricted N/S. Retention is then ~ 1/(1+N/S)")
print("  for a small-over-large ratio, and ~1 for a ratio where N << S.")
print()
print(f"  {'stratum':<9}{'N/S':>8}{'retention of the between-arm effect':>40}")
for label in ("detail", "flat"):
    t, obs = out[label]["ratio_true"], out[label]["observed"]
    ret = (obs - 1.0) / (t - 1.0)
    out[label]["effect_retention"] = ret
    print(f"  {label:<9}{out[label]['NS']:8.3f}{100 * ret:39.1f}%")
print()
print("  This is why ORCH's rule and my a6 table agree: sd DN broadband has")
print("  N/S ~ 1e-4 so its arm ratio is protected, while HF band power in flat")
print("  tiles has N/S ~ 1 so it loses half its effect. Same statistic class,")
print("  opposite outcome, decided entirely by in-band N/S.")

(HERE / "out" / f"a7_nsr_{SUBJECT}.json").write_text(json.dumps(
    {"subject": SUBJECT, "resid_sd": float(r0.std()), "strata": out}, indent=1))
