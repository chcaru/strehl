"""Pre-registration inputs -- plant properties only, computed BEFORE any arm runs.

Nothing here touches a merge output. It emits the numbers the predictions in
`PREREGISTRATION.md` are built from: the model sigma of the binned green at this
crop, and the high-pass sd of the latent itself, which is what sets the ceiling
on the CLI's own flat-ROI invariant under a shared-latent plant.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

N = 30
HP_SIDE = 9
HP_NOISE_GAIN = np.sqrt(1.0 - 1.0 / HP_SIDE**2)  # matches flat_ratio.rs HP_NOISE_GAIN


def hp_sd(a, side=HP_SIDE):
    r = a - uniform_filter(a, side, mode="nearest")
    k = side // 2
    return float(r[k:-k, k:-k].std())


def main():
    k = H.constants()
    latent = np.load(H.DATA / "latent.npy")
    lg = H.green(latent)  # raw DN, plane resolution
    sig_g1 = H.sigma_dn(latent[0::2, 1::2] - k["black"], k)
    sig_g2 = H.sigma_dn(latent[1::2, 0::2] - k["black"], k)
    var_green = 0.25 * (sig_g1**2 + sig_g2**2)  # NoiseModel::green_luma_sigma, squared

    r_var = H.roi(var_green)
    r_lg = H.roi(lg)
    v = float(r_var.mean())
    hp_l = hp_sd(r_lg)

    g2 = HP_NOISE_GAIN**2
    trap_predicted = float(np.sqrt((hp_l**2 + g2 * v) / (hp_l**2 + g2 * v / N)))
    trap_ceiling = float(np.sqrt(2 * N / (N + 1)))

    rec = dict(
        N=N,
        sqrt_N=float(np.sqrt(N)),
        constants=k,
        roi=dict(inset=H.INSET, shape=list(r_lg.shape), pixels=int(r_lg.size)),
        latent_green=dict(
            mean_raw_dn=float(r_lg.mean()),
            mean_signal_dn=float(r_lg.mean() - k["black"]),
            min_raw_dn=float(r_lg.min()),
            max_raw_dn=float(r_lg.max()),
        ),
        binned_green_noise=dict(
            model_var_dn2=v,
            model_sigma_dn=float(np.sqrt(v)),
            note="Var((G1+G2)/2) = (sigma_G1^2 + sigma_G2^2)/4, NoiseModel::green_luma_sigma",
        ),
        trap=dict(
            hp_box_side=HP_SIDE,
            hp_noise_gain=float(HP_NOISE_GAIN),
            latent_hp_sd_dn=hp_l,
            predicted_flat_roi_hp_ratio=trap_predicted,
            ceiling_texture_free_scene=trap_ceiling,
        ),
        ladder=[dict(k=int(kk), expected=float(np.sqrt(kk))) for kk in (1, 2, 3, 5, 10, 20, 30)],
    )
    H.dump("03-prereg-inputs.json", rec)


if __name__ == "__main__":
    main()
