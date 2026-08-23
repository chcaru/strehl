"""B4 -- how much of the selector's penalty is scene structure?

Arm B3 (`strehl merge --gate 0`, the shipped estimator configured to admit only
the winner) scored 0.9768 on a textured crop and 0.9277 on the real dark field.
The pre-registered Arm D bound was 1.00 +/- 0.05 and 0.9277 is outside it, so the
difference has to be explained by measurement rather than by argument.

The mechanism on offer: the argmax picks the frame with the largest regularised
focus response, and the focus response is scene structure plus noise. Where
structure dominates, the winner is decided by structure and the pick is nearly
independent of that pixel's noise. Where structure is absent, the winner is
decided *by the noise*, and the selector systematically returns the frame whose
noise happened to point the right way.

The test: run the identical selector over a latent with NO structure at all --
a constant field at the same 1230 DN of signal, so the noise is identical and
only the structure is removed. The prediction, if the mechanism is right, is a
larger penalty than the textured crop's.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

N = 30
SIZE = 2048
SIGNAL = 1230.0
SEEDS = (0, 1, 2)


def main():
    k = H.constants()
    latent = np.full((SIZE, SIZE), k["black"] + SIGNAL, dtype=np.float64)
    out = {}
    for seed in SEEDS:
        d = H.DATA / f"flat-s{seed}"
        H.make_burst(latent, N, 5000 + seed, d, k)
        cube = np.stack([H.read_cfa(p, latent.shape) for p in sorted(d.glob("*.arw"))])
        g = np.stack([H.green(f) for f in cube])
        truth = H.roi(H.green(latent))
        gr = H.roi(g.transpose(1, 2, 0)).transpose(2, 0, 1)
        single_ms = ((gr - truth) ** 2).mean(axis=0)

        for gate in (0.0, 16.0):
            tif = H.DATA / f"flat-s{seed}-g{gate}.tif"
            log = H.EVID / f"08-flat-s{seed}-g{gate}.log"
            txt = H.run_cli(["merge", str(d), "--gate", gate, "--out", str(tif)], log)
            m = H.roi(H.read_tiff_green(tif, k))
            r, se = H.ratio_and_se(m, truth, single_ms)
            out.setdefault(f"gate{gate}", {})[seed] = dict(
                ratio=r, boot_se=se,
                mean_n_eff=H.grep1(txt, rf"\n\s*{gate:.2f}\s+[0-9.]+\s+([0-9.]+)", float),
            )
            tif.unlink()
        for p in d.glob("*.arw"):
            p.unlink()
        d.rmdir()

    summ = {}
    for gate, per in out.items():
        v = [per[s]["ratio"] for s in SEEDS]
        summ[gate] = dict(ratio_mean=float(np.mean(v)),
                          ratio_sd_between_seeds=float(np.std(v, ddof=1)),
                          boot_se_seed0=per[SEEDS[0]]["boot_se"],
                          mean_n_eff=per[SEEDS[0]]["mean_n_eff"],
                          per_seed=v)
    sel = summ["gate0.0"]["ratio_mean"]
    summ["selection_penalty_pct"] = float((1.0 / sel - 1.0) * 100.0)
    summ["comparison"] = dict(
        textured_synthetic_crop=0.976815,
        flat_synthetic_field=sel,
        real_dark_field=0.9277221816789586,
        note="all three are `strehl merge --gate 0`, n_eff == 1 at every pixel",
    )
    H.dump("08-flat-selector.json", dict(summary=summ, per_seed=out,
                                         latent="constant 512+1230 DN, no structure",
                                         n=N, seeds=list(SEEDS)))


if __name__ == "__main__":
    main()
