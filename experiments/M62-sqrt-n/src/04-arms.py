"""M62 arms A0, A1, B1, B2, B3 -- the deciding run.

Expected values are fixed in `PREREGISTRATION.md`, committed at 906688c before
this script produced a single ratio.

Every arm is scored by ONE statistic, on ONE ROI, against ONE denominator:

    R = sqrt( mean_over_frames_and_px (Y_i - L)^2 / mean_over_px (O - L)^2 )

with `L` the latent crop, `Y_i` the 30 written frames read back off disk, and
`O` the arm's output. `L` is truth by definition, so the frozen noise inside it
cancels out of both residuals identically -- see PREREGISTRATION.md 3.
"""

from __future__ import annotations

import pathlib
import re
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

N = 30
SEEDS = (0, 1, 2)
GATES = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
LADDER = (1, 2, 3, 5, 10, 20, 30)


def parse_gate_row(txt):
    m = re.search(
        r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)x\s*$",
        txt,
        re.M,
    )
    assert m, "gate calibration row not found"
    return dict(
        gate=float(m.group(1)),
        tolerance=float(m.group(2)),
        mean_n_eff=float(m.group(3)),
        n_eff_1_pct=float(m.group(4)),
        boundary_pct=float(m.group(5)),
        pred_sigma_gain=float(m.group(6)),
    )


def parse_hp_row(txt):
    m = re.search(r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)x\s+\[\s*([0-9.]+)x\s*\.\.\s*([0-9.]+)x\]", txt, re.M)
    assert m, "hp ratio row not found"
    return dict(hp_sd_dn=float(m.group(2)), hp_ratio=float(m.group(3)),
                hp_ratio_min=float(m.group(4)), hp_ratio_max=float(m.group(5)))


def run_seed(seed, k, latent, shape):
    t0 = time.time()
    burst = H.DATA / f"burst-s{seed}"
    rep = H.make_burst(latent, N, seed=seed, outdir=burst, k=k)

    paths = sorted(burst.glob("*.arw"))
    assert len(paths) == N, f"{burst}: {len(paths)} frames, expected {N}"

    truth_g = H.green(latent)
    frames_g = np.stack([H.green(H.read_cfa(p, shape)) for p in paths]).astype(np.float32)

    tr = H.roi(truth_g)
    fr = frames_g[:, H.INSET : -H.INSET, H.INSET : -H.INSET]
    # Pooled single-frame mean square against truth, over ALL N frames (fact 441:
    # never let one frame be the denominator).
    single_ms = ((fr.astype(np.float64) - tr[None]) ** 2).mean(axis=0)

    def score(out_g_roi):
        return H.ratio_and_se(out_g_roi, tr, single_ms)

    results = {}

    # ---- A0: the ideal-average ladder. Arithmetic; expected exactly sqrt(k).
    for kk in LADDER:
        m = fr[:kk].astype(np.float64).mean(axis=0)
        r, se = score(m)
        results[f"A0-{kk}"] = dict(arm="A0", k=kk, expected=float(np.sqrt(kk)), ratio=r, se=se)

    # ---- B1a: constant selector. Copy frame 0 everywhere.
    r, se = score(fr[0].astype(np.float64))
    results["B1a"] = dict(arm="B1a", expected=1.0, ratio=r, se=se)

    # ---- B1b: random per-pixel selector, full winner histogram, no noise coupling.
    rng = np.random.default_rng([seed, 424242])
    pick = rng.integers(0, N, size=fr.shape[1:])
    sel = np.take_along_axis(fr.astype(np.float64), pick[None], axis=0)[0]
    r, se = score(sel)
    results["B1b"] = dict(arm="B1b", expected=1.0, ratio=r, se=se)

    # ---- A1 / B3: the shipped merge across the gate ladder. gate 0 IS a selector.
    roi_arg = f"{H.INSET},{H.INSET},{fr.shape[2]},{fr.shape[1]}"
    for gate in GATES:
        tif = H.EVID / f"04-merge-s{seed}-g{gate}.tif"
        txt = H.run_cli(
            ["merge", burst, "--gate", gate, "--flat-roi", roi_arg, "--out", tif],
            H.EVID / f"04-merge-s{seed}-g{gate}.log",
        )
        g = H.roi(H.read_tiff_green(tif, k))
        r, se = score(g)
        row = parse_gate_row(txt)
        hp = parse_hp_row(txt)
        tif.unlink()
        results[f"A1-g{gate}"] = dict(
            arm="B3" if gate == 0.0 else "A1", gate=gate, ratio=r, se=se,
            cli_mean_n_eff=row["mean_n_eff"], cli_pred_sigma_gain=row["pred_sigma_gain"],
            cli_n_eff_1_pct=row["n_eff_1_pct"],
            sqrt_mean_n_eff=float(np.sqrt(row["mean_n_eff"])),
            efficiency=r / float(np.sqrt(row["mean_n_eff"])),
            cli_flat_roi_hp_ratio=hp["hp_ratio"], cli_flat_roi_hp_sd_dn=hp["hp_sd_dn"],
        )

    # ---- B2: the shipped unregularised argmax selector.
    tif = H.EVID / f"04-stack-s{seed}.tif"
    txt = H.run_cli(
        ["stack", burst, "--flat-roi", roi_arg, "--out", tif],
        H.EVID / f"04-stack-s{seed}.log",
    )
    g = H.roi(H.read_tiff_green(tif, k))
    r, se = score(g)
    tif.unlink()
    results["B2"] = dict(arm="B2", expected_max=1.0, ratio=r, se=se)

    for p in paths:
        p.unlink()
    burst.rmdir()
    return dict(seed=seed, burst=rep, elapsed_s=time.time() - t0, results=results)


def main():
    k = H.constants()
    latent = np.load(H.DATA / "latent.npy")
    shape = latent.shape
    out = []
    for seed in SEEDS:
        r = run_seed(seed, k, latent, shape)
        print(f"seed {seed} done in {r['elapsed_s']:.1f} s")
        out.append(r)

    keys = list(out[0]["results"].keys())
    summary = {}
    for key in keys:
        vals = np.array([o["results"][key]["ratio"] for o in out])
        base = dict(out[0]["results"][key])
        base.pop("ratio")
        base.pop("se")
        summary[key] = dict(
            base,
            ratio_mean=float(vals.mean()),
            ratio_sd_between_seeds=float(vals.std(ddof=1)),
            ratio_per_seed=[float(v) for v in vals],
            bootstrap_se_seed0=out[0]["results"][key]["se"],
        )
    H.dump("04-arms.json", dict(N=N, seeds=list(SEEDS), per_seed=out, summary=summary))


if __name__ == "__main__":
    main()
