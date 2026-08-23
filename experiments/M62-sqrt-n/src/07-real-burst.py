"""Arm C -- the harness path for the real §12 static burst. Written, not run.

There is no real burst yet. This file is what runs the moment there is one:

    python src/07-real-burst.py D:\\personal\\macro\\<burst-dir> --n 30

`--smoke` runs the identical code path over a synthetic Arm A burst instead, so
the path is demonstrated to execute and the photon-transfer fitter is
demonstrated to recover constants that were injected on purpose. That is a test
of the *fitter*, not of the sensor: on synthetic data it must recover `g` and
`RN` because `g` and `RN` are what generated the data. Its value is that a
fitter which cannot recover a known answer cannot be trusted with an unknown
one.

Three measurements, and only the first is one Arm A can also make:

  C1  noise reduction against held-out truth. Split the burst in half, merge one
      half, score against the mean of the other. Expected sqrt(N/2), with the
      truth set's own `v/M` subtracted.

  C2  in-situ photon transfer at working exposure. A static burst gives a
      per-pixel temporal variance and a per-pixel mean over a scene that spans a
      real signal range, so `var = g*S + (RN*g)^2` can be REGRESSED rather than
      assumed. This is the measurement that Arm A structurally cannot make and
      the one that answers fact 808: the shipped `g` and read noise were fitted
      at 1/100 s in the dark, and this checks them at 1/8-2.5 s on a scene.

  C3  defect census at working exposure. Temporal variance in excess of the
      model, per pixel, at working exposure -- the population fact 808 says the
      1/100 s dark map misses (~5 of ~839). Reported per plane, because of the
      68x odd/even asymmetry (R 101, G1 98, G2 7757, B 5674).

Everything stays in DN. Facts 783-808 record a 2.174x dark-signal step at ISO
400 that is a labelling failure in the gain/read-noise split; DN-domain
predictions are unaffected, so nothing here is exposed to it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

CROP = 2048
BLACK = 512.0


def read_stack(paths, crop=CROP, expect_iso=None):
    """Decode `paths` to a (n, CROP, CROP) RGGB-phased float64 cube."""
    import rawpy

    cube, phase, y0, x0 = [], None, None, None
    for p in paths:
        with rawpy.imread(str(p)) as raw:
            cfa = raw.raw_image_visible.astype(np.float64)  # rule 32
            if phase is None:
                colors = raw.raw_colors_visible.astype(np.uint8).copy()
                for dy in (0, 1):
                    for dx in (0, 1):
                        q = colors[dy:dy + 2, dx:dx + 2]
                        if q[0, 0] == 0 and q[1, 1] == 2 and q[0, 1] in (1, 3) and q[1, 0] in (1, 3):
                            phase = (dy, dx)
                assert phase is not None, "no RGGB phase"
                h, w = cfa.shape
                y0 = phase[0] + ((h - crop) // 4) * 2
                x0 = phase[1] + ((w - crop) // 4) * 2
        cube.append(cfa[y0:y0 + crop, x0:x0 + crop].copy())
    return np.stack(cube), (y0, x0), phase


def split_planes(cube):
    return {"R": cube[..., 0::2, 0::2], "G1": cube[..., 0::2, 1::2],
            "G2": cube[..., 1::2, 0::2], "B": cube[..., 1::2, 1::2]}


def c1_noise_reduction(cube, k, workdir, gate=16.0):
    """Merge half the burst, score against the mean of the other half."""
    from dngwrite import write_cfa_dng

    n = cube.shape[0]
    na = n // 2
    A, B = cube[:na], cube[na:]
    workdir.mkdir(parents=True, exist_ok=True)
    for old in workdir.glob("*.arw"):
        old.unlink()
    for i in range(na):
        write_cfa_dng(workdir / f"f{i:04d}.arw",
                      np.clip(np.rint(A[i]), 0, H.CONTAINER_MAX).astype(np.uint16),
                      iso=int(k["iso"]), exposure_s=1.0)

    gA = H.roi(np.stack([H.green(f) for f in A]).transpose(1, 2, 0)).transpose(2, 0, 1)
    gB = H.roi(np.stack([H.green(f) for f in B]).transpose(1, 2, 0)).transpose(2, 0, 1)
    v_hat = float(gA.var(axis=0, ddof=1).mean())
    truth = gB.mean(axis=0)
    corr = v_hat / gB.shape[0]
    q2 = ((k["white"] - k["black"]) / 65535.0 / np.sqrt(12.0)) ** 2

    out = workdir.parent / "armC-merged.tif"
    H.run_cli(["merge", str(workdir), "--gate", gate, "--out", str(out)],
              H.EVID / "07-armC-merge.log")
    m = H.roi(H.read_tiff_green(out, k))
    ms_s = float(((gA - truth) ** 2).mean()) - corr
    ms_m = float(((m - truth) ** 2).mean()) - corr - q2

    ladder = {}
    for kk in (1, 2, 5, na):
        merged = gA[:kk].mean(axis=0)
        ladder[kk] = dict(ratio=float(np.sqrt(ms_s / (float(((merged - truth) ** 2).mean()) - corr))),
                          expected=float(np.sqrt(kk)))
    out.unlink()
    return dict(n_merged=na, n_truth=int(B.shape[0]), gate=gate,
                cli_ratio=float(np.sqrt(ms_s / ms_m)),
                cli_expected=float(np.sqrt(na)),
                truth_var_correction=corr, tiff_q2=float(q2),
                python_ladder=ladder)


def c2_photon_transfer(cube, k, bins=48, min_px=500):
    """Regress temporal variance on mean signal, per plane. In DN throughout.

    The burst is static, so per-pixel temporal variance across frames is the
    sensor's variance at that pixel's signal, with fixed-pattern noise, defects
    and scene structure all held constant and therefore invisible. That is what
    makes a static burst -- and nothing else in this corpus -- a photon-transfer
    measurement at working exposure.
    """
    out = {}
    n = cube.shape[0]
    for name, pl in split_planes(cube).items():
        mean = H.roi(pl.mean(axis=0))
        var = H.roi(pl.var(axis=0, ddof=1))
        s = mean - k["black"]
        ok = (mean < k["white"] - 64) & (s > -32)
        s, var = s[ok], var[ok]
        if s.size < min_px:
            out[name] = dict(error="too few usable pixels", n=int(s.size))
            continue
        edges = np.quantile(s, np.linspace(0.0, 1.0, bins + 1))
        edges = np.unique(edges)
        idx = np.clip(np.digitize(s, edges[1:-1]), 0, len(edges) - 2)
        xs, ys, ns = [], [], []
        for b in range(len(edges) - 1):
            m = idx == b
            c = int(m.sum())
            if c < min_px:
                continue
            # median of the per-pixel variances is robust to defects; scale it
            # back to a mean for a chi-square_(n-1) variate.
            chi_med = float(np.median(np.random.default_rng(0).chisquare(n - 1, 200000))) / (n - 1)
            xs.append(float(np.median(s[m])))
            ys.append(float(np.median(var[m])) / chi_med)
            ns.append(c)
        xs, ys = np.asarray(xs), np.asarray(ys)
        w = np.asarray(ns, float)
        A = np.stack([xs, np.ones_like(xs)], axis=1)
        coef, *_ = np.linalg.lstsq(A * w[:, None] ** 0.5, ys * w ** 0.5, rcond=None)
        g_hat, c_hat = float(coef[0]), float(coef[1])
        rn_dn_hat = float(np.sqrt(max(c_hat, 0.0)))
        out[name] = dict(
            n_bins=len(xs), signal_span_dn=[float(xs.min()), float(xs.max())],
            g_hat_dn_per_e=g_hat, g_profile_dn_per_e=k["gain_dn_per_e"],
            g_ratio=g_hat / k["gain_dn_per_e"],
            read_noise_dn_hat=rn_dn_hat, read_noise_dn_profile=k["read_noise_dn"],
            read_noise_ratio=rn_dn_hat / k["read_noise_dn"],
            read_noise_e_hat=rn_dn_hat / g_hat if g_hat > 0 else None,
            bins=dict(signal_dn=xs.tolist(), var_dn2=ys.tolist(), count=ns),
        )
    return out


def c3_defects(cube, k, thresh=4.0):
    """Pixels whose temporal variance exceeds the model by `thresh`x, per plane."""
    out = {}
    n = cube.shape[0]
    for name, pl in split_planes(cube).items():
        mean = H.roi(pl.mean(axis=0))
        var = H.roi(pl.var(axis=0, ddof=1))
        model = H.sigma_dn(mean - k["black"], k) ** 2
        r = var / model
        out[name] = dict(
            px=int(r.size), n_frames=n,
            excess_gt_thresh=int((r > thresh).sum()),
            rate_per_million=float((r > thresh).sum() / r.size * 1e6),
            r_median=float(np.median(r)), r_p999=float(np.percentile(r, 99.9)),
            r_max=float(r.max()),
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("burst", nargs="?", help="directory of the real static burst")
    ap.add_argument("--n", type=int, default=30, help="expected frame count (discipline 388)")
    ap.add_argument("--iso", type=float, default=None)
    ap.add_argument("--smoke", action="store_true",
                    help="run the identical path over a synthetic Arm A burst")
    a = ap.parse_args()

    if a.smoke:
        k = H.constants()
        latent = np.load(H.DATA / "latent.npy")
        d = H.DATA / "armC-smoke"
        H.make_burst(latent, a.n, 99, d, k)
        cube = np.stack([H.read_cfa(p, latent.shape) for p in sorted(d.glob("*.arw"))])
        assert cube.shape[0] == a.n
        rec = dict(mode="SMOKE -- synthetic, circular by construction (rule 34)",
                   n=a.n, iso=k["iso"],
                   C1=c1_noise_reduction(cube, k, H.DATA / "armC-work"),
                   C2=c2_photon_transfer(cube, k),
                   C3=c3_defects(cube, k))
        H.dump("07-armC-smoke.json", rec)
        return

    assert a.burst, "give a burst directory, or --smoke"
    src = pathlib.Path(a.burst)
    paths = sorted(src.glob("*.ARW"))
    assert len(paths) == a.n, f"{src}: {len(paths)} frames, expected {a.n}"  # discipline 388
    k = H.constants(iso=a.iso) if a.iso else H.constants()
    cube, crop, phase = read_stack(paths)
    rec = dict(mode="REAL", burst=str(src), n=len(paths), iso=k["iso"],
               crop=dict(y0=crop[0], x0=crop[1], size=CROP, phase=list(phase)),
               constants=k,
               drift=dict(per_frame_mean_dn=[float(f.mean()) for f in cube]),
               C1=c1_noise_reduction(cube, k, H.DATA / "armC-work"),
               C2=c2_photon_transfer(cube, k),
               C3=c3_defects(cube, k))
    H.dump("07-armC-real.json", rec)
    print(json.dumps(rec["C2"], indent=2)[:2000])


if __name__ == "__main__":
    main()
