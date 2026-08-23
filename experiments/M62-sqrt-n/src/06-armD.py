"""Arm D -- the same harness, on noise the sensor actually made.

The corpus already holds real static repeat bursts: `D:\\macro-dark-frames` is
11 ISO groups of 22 frames, and within a group nothing moves and nothing
refocuses. The latent is the dark field and the exposure is 1/100 s, so this is
NOT the §12 capture and does NOT close fact 808 -- but the noise is the
sensor's, not the model's, and that is the one thing Arm A structurally cannot
offer.

Everything expected here was written down in PREREGISTRATION-D.md and committed
(dea34ad) before this script ran.

D1  Python, on the real ARWs, per CFA plane. Held-out truth, `v/M` corrected.
D2  the shipped CLI, on the same frames re-encoded with a constant pedestal.

Corpus is READ-ONLY.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402
from dngwrite import write_cfa_dng  # noqa: E402

GROUP = pathlib.Path(r"D:\macro-dark-frames\118MSDCF")
EXPECTED = 22
DARK_ISO = 100
SKIP = 2
NA = 10          # merged set
NB = 10          # held-out truth set
CROP = 2048
PEDESTAL = 1230  # DN; constant in every frame, so no temporal statistic moves
LADDER = [1, 2, 3, 5, 10]
BLACK = 512.0
Q_TIFF = (15360.0 - 512.0) / 65535.0 / np.sqrt(12.0)


def load_group():
    paths = sorted(GROUP.glob("*.ARW"))
    assert len(paths) == EXPECTED, f"{GROUP}: {len(paths)} frames, expected {EXPECTED}"
    use = paths[SKIP: SKIP + NA + NB]
    assert len(use) == NA + NB

    phase = None
    frames = []
    for p in use:
        with rawpy.imread(str(p)) as raw:
            cfa = raw.raw_image_visible.astype(np.float64)  # rule 32: copy inside the `with`
            if phase is None:
                colors = raw.raw_colors_visible.astype(np.uint8).copy()
                for dy in (0, 1):
                    for dx in (0, 1):
                        q = colors[dy:dy + 2, dx:dx + 2]
                        if q[0, 0] == 0 and q[1, 1] == 2 and q[0, 1] in (1, 3) and q[1, 0] in (1, 3):
                            phase = (dy, dx)
                assert phase is not None
                y0 = phase[0] + 1024
                x0 = phase[1] + 2048
        frames.append(cfa[y0:y0 + CROP, x0:x0 + CROP].copy())
    return [str(p) for p in use], np.stack(frames), (y0, x0), phase


def planes(cfa):
    return {
        "R": cfa[..., 0::2, 0::2],
        "G1": cfa[..., 0::2, 1::2],
        "G2": cfa[..., 1::2, 0::2],
        "B": cfa[..., 1::2, 1::2],
        "green": 0.5 * (cfa[..., 0::2, 1::2] + cfa[..., 1::2, 0::2]),
    }


def corrected_ratio(A, truth, v_hat, m_truth, q2=0.0):
    """sqrt of (single-frame MS - v/M) over (merged MS - v/M - q^2), pooled.

    `A` is (n, h, w) of the merged set; `truth` is the held-out mean of `m_truth`
    frames. `v_hat` is the pooled within-`A` temporal variance.
    """
    out = {}
    corr = v_hat / m_truth
    for k in LADDER:
        if k > A.shape[0]:
            continue
        merged = A[:k].mean(axis=0)
        ms_m = float(((merged - truth) ** 2).mean()) - corr - q2
        ms_s = float(((A - truth) ** 2).mean()) - corr
        out[k] = dict(ms_single_raw=float(((A - truth) ** 2).mean()),
                      ms_merged_raw=float(((merged - truth) ** 2).mean()),
                      truth_var_correction=corr,
                      tiff_q2=q2,
                      ratio=float(np.sqrt(ms_s / ms_m)),
                      expected=float(np.sqrt(k)))
    return out


def main():
    paths, cube, crop_yx, phase = load_group()
    A, B = cube[:NA], cube[NA:]

    kD = H.constants(iso=DARK_ISO)
    model_sigma_sample = kD["read_noise_dn"]

    # ---- D1-drift: is the latent actually static?
    lvl = [float(f.mean()) for f in cube]
    drift = dict(per_frame_mean_dn=lvl,
                 first=lvl[0], last=lvl[-1],
                 span_dn=max(lvl) - min(lvl),
                 slope_dn_per_frame=float(np.polyfit(np.arange(len(lvl)), lvl, 1)[0]))

    # ---- D1-sigma and D1-k, per plane
    pA, pB = planes(A), planes(B)
    d1 = {}
    for name in ("R", "G1", "G2", "B", "green"):
        a, b = H.roi(pA[name].transpose(1, 2, 0)).transpose(2, 0, 1), \
               H.roi(pB[name].transpose(1, 2, 0)).transpose(2, 0, 1)
        v_hat = float(a.var(axis=0, ddof=1).mean())
        truth = b.mean(axis=0)
        model = model_sigma_sample / np.sqrt(2.0) if name == "green" else model_sigma_sample
        d1[name] = dict(
            temporal_sd_dn=float(np.sqrt(v_hat)),
            model_sigma_dn=float(model),
            measured_over_model=float(np.sqrt(v_hat) / model),
            mean_level_dn=float(a.mean()),
            ladder=corrected_ratio(a, truth, v_hat, NB),
        )

    # ---- D2: the shipped merge, on the same 10 frames, pedestalled
    dd = H.DATA / "armD"
    dd.mkdir(parents=True, exist_ok=True)
    for old in dd.glob("*.arw"):
        old.unlink()
    for i in range(NA):
        y = np.clip(np.rint(A[i] + PEDESTAL), 0, H.CONTAINER_MAX).astype(np.uint16)
        write_cfa_dng(dd / f"dark{i:04d}.arw", y, iso=DARK_ISO, exposure_s=0.01)

    # truth for D2 lives in the same encoded domain: pedestal is a constant, so
    # the held-out mean shifts by exactly PEDESTAL and nothing else.
    gB = H.roi(planes(B)["green"].transpose(1, 2, 0)).transpose(2, 0, 1)
    gA = H.roi(planes(A)["green"].transpose(1, 2, 0)).transpose(2, 0, 1)
    v_hat_g = float(gA.var(axis=0, ddof=1).mean())
    truth_g = gB.mean(axis=0) + PEDESTAL
    single_ms = ((gA + PEDESTAL - truth_g) ** 2).mean()

    d2 = {}
    for gate in (0.0, 16.0):
        out = dd.parent / f"armD-merged-g{gate}.tif"
        log = H.EVID / f"06-armD-merge-g{gate}.log"
        H.run_cli(["merge", str(dd), "--gate", gate, "--out", str(out)], log)
        m = H.roi(H.read_tiff_green(out, kD))
        assert m.shape == truth_g.shape, (m.shape, truth_g.shape)
        ms_m = float(((m - truth_g) ** 2).mean()) - v_hat_g / NB - Q_TIFF ** 2
        ms_s = float(single_ms) - v_hat_g / NB
        d2[f"gate{gate}"] = dict(
            ratio=float(np.sqrt(ms_s / ms_m)),
            ms_merged_raw=float(((m - truth_g) ** 2).mean()),
            ms_single_raw=float(single_ms),
            truth_var_correction=v_hat_g / NB,
            tiff_q2=float(Q_TIFF ** 2),
            expected="1.0 (selector)" if gate == 0.0 else "3.1623 = sqrt(10)",
        )
        out.unlink()

    rec = dict(
        group=str(GROUP), iso=DARK_ISO, exposure_s=0.01,
        frames_used=paths, skipped=SKIP,
        crop=dict(y0=crop_yx[0], x0=crop_yx[1], size=CROP, rggb_phase=list(phase)),
        pedestal_dn=PEDESTAL,
        constants=kD,
        drift=drift, D1=d1, D2=d2,
    )
    H.dump("06-armD.json", rec)


if __name__ == "__main__":
    main()
