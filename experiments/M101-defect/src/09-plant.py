"""M101 script 09 - the positive control: does the instrument see a defect that
DOES matter?

The real arm read a flat null: H_value at the base rate, enrichment 0.987x,
no trail. A null is only evidence if the instrument could have seen the
alternative, and the corpus carries three separate incidents this week where a
null passed and the instrument was blind (disciplines 611, 615, 616).

So: 320 synthetic hot pixels are planted at coordinates absent from the defect
map, 40 at each of eight amplitudes spanning 2 to 500 DN, and the identical
election and identical statistics are run. The real defect amplitude measured
in-situ is ~1.5 DN, so the ladder brackets it by more than two decades.

Per discipline 615 the plant runs in its OWN arm. It cannot perturb the
mechanism the real measurement runs through, because the real arm's numbers come
from a run in which nothing was planted.

The pre-registered prediction, derived before the run from the shipped
arithmetic: an isolated spike of green-luma amplitude A raises box_mean_27(|Sobel|)
by 2.118*A/729 DN/px, so it moves the regularised focus by
  dF = 0.002905 * A / sigma_L
and it can only win where dF is comparable to FOCUS_NOISE_SD = 0.015214. At the
stack's typical sigma_L ~ 14.6 DN that needs A ~ 76 DN of luma, i.e. ~153 DN on
one green plane. The ladder should therefore turn on between 100 and 250 DN and
stay flat below it.

Reads  : C:\\dev\\strehl-out\\M101\\election-*-plant.npz, plant-*.npz
Writes : C:\\dev\\strehl-out\\M101\\09-plant-<stack>.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location(
    "e07", Path(__file__).with_name("07-election.py"))
_e07 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_e07)
parse_warpmap = _e07.parse_warpmap

OUT = Path(r"C:\dev\strehl-out\M101")
REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
SEED = 101

# shipped constants, for the derived prediction
FOCUS_NOISE_SD = 0.015214
SOBEL_DELTA_SUM = 2.118          # sum of |Sobel|/8 response to a unit delta
WINDOW_PX = 27 * 27


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", default="bee-3-cpl")
    ap.add_argument("--warpmap", default=str(
        REPO / "experiments/M86-alignment/out/warpmap-bee-3-cpl.txt"))
    a = ap.parse_args()

    zp = np.load(OUT / f"election-{a.stack}-plant.npz")
    zw = np.load(OUT / f"election-{a.stack}-warped.npz")
    pl = np.load(OUT / f"plant-{a.stack}.npz")
    win_p, win_w = zp["winner"].astype(np.int32), zw["winner"].astype(np.int32)
    luma = zw["luma"]
    H, W = win_p.shape
    cx, cy = W * 0.5, H * 0.5
    hdr, warps = parse_warpmap(Path(a.warpmap))
    nf = json.loads(str(zp["meta"][0]))["n_frames"]
    rng = np.random.default_rng(SEED)

    py, px, amp = pl["y"].astype(np.float64), pl["x"].astype(np.float64), pl["amp"]
    # unplanted control sites, matched in count, drawn the same way
    cy_, cx_ = (rng.integers(200, H - 200, size=py.size).astype(np.float64),
                rng.integers(200, W - 200, size=px.size).astype(np.float64))

    def events(win, qy, qx):
        hit = np.zeros(qy.size, dtype=np.int32)
        vis = np.zeros(qy.size, dtype=np.int32)
        for k in range(nf):
            sim = warps.get(k)
            if sim is None:
                continue
            z = ((qx - cx) + 1j * (qy - cy) - sim[1]) / sim[0]
            gx, gy = z.real + cx, z.imag + cy
            ok = (gx >= 0) & (gx < W) & (gy >= 0) & (gy < H)
            ix = np.clip(np.rint(gx).astype(np.int32), 0, W - 1)
            iy = np.clip(np.rint(gy).astype(np.int32), 0, H - 1)
            vis += ok
            hit += ok & (win[iy, ix] == k)
        return hit, vis

    h_plant, v_plant = events(win_p, py, px)      # planted sites, planted run
    h_same, v_same = events(win_w, py, px)        # SAME sites, UNPLANTED run
    h_ctrl, v_ctrl = events(win_p, cy_, cx_)      # unplanted sites, planted run

    sigma_typ = float(np.median(np.sqrt(
        0.5 * ((100 / 436.8) * np.maximum(luma, 0) + (4.20 * 100 / 436.8) ** 2))))

    res = {"stack": a.stack, "n_planted": int(py.size), "n_frames": nf,
           "sigma_luma_median_dn": round(sigma_typ, 4),
           "uniform_chance": 1.0 / nf, "ladder": []}
    for A in sorted(set(amp.tolist())):
        sel = amp == A
        rp = float(h_plant[sel].sum() / max(v_plant[sel].sum(), 1))
        rs = float(h_same[sel].sum() / max(v_same[sel].sum(), 1))
        # derived prediction for this amplitude
        d_focus = SOBEL_DELTA_SUM * (0.5 * A) / WINDOW_PX / sigma_typ
        res["ladder"].append({
            "plane_amplitude_dn": float(A),
            "luma_amplitude_dn": float(0.5 * A),
            "n_sites": int(sel.sum()),
            "elected_px_mean_planted": float(h_plant[sel].mean()),
            "elected_px_mean_same_sites_unplanted": float(h_same[sel].mean()),
            "rate_planted": rp, "rate_same_sites_unplanted": rs,
            "enrichment": rp / rs if rs else None,
            "predicted_dfocus": d_focus,
            "predicted_dfocus_in_focus_noise_sd": d_focus / FOCUS_NOISE_SD,
        })
    rc = float(h_ctrl.sum() / max(v_ctrl.sum(), 1))
    res["unplanted_control_in_planted_run"] = {
        "n_sites": int(cy_.size), "rate": rc,
        "elected_px_mean": float(h_ctrl.mean())}
    res["placebo_arm_integrity"] = {
        "note": "discipline 615: the plant must not perturb the mechanism it "
                "measures through. These two agree only if planting 320 pixels "
                "left the rest of the election alone.",
        "winner_map_disagreement_frac": float((win_p != win_w).mean()),
    }

    print(f"  sigma_L median = {sigma_typ:.2f} DN, uniform chance = "
          f"{1.0/nf:.5f}", flush=True)
    for r in res["ladder"]:
        print(f"  plant {r['plane_amplitude_dn']:6.1f} DN -> elected "
              f"{r['elected_px_mean_planted']:8.2f} px (same sites unplanted "
              f"{r['elected_px_mean_same_sites_unplanted']:6.2f}) "
              f"enrich {r['enrichment']:7.2f}x  predicted dF = "
              f"{r['predicted_dfocus_in_focus_noise_sd']:.3f} sd", flush=True)
    print(f"  unplanted control in planted run: {rc:.5f} "
          f"({res['unplanted_control_in_planted_run']['elected_px_mean']:.2f} px)",
          flush=True)
    print(f"  winner-map disagreement planted vs clean: "
          f"{res['placebo_arm_integrity']['winner_map_disagreement_frac']:.3e}",
          flush=True)

    with open(OUT / f"09-plant-{a.stack}.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote 09-plant-{a.stack}.json", flush=True)


if __name__ == "__main__":
    main()
