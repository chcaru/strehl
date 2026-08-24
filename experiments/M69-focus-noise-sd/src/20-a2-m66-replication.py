"""M69 arm A2 -- independent replication of M66's post-hoc control K7.

M66 measured the temporal SD of the regularised response across replicates of a
frozen latent plus fresh sensor noise, and reported

    FLAT 1.0018    SMOOTH 1.0690    REAL 1.1921

against the crate's FOCUS_NOISE_SD. This script rebuilds that measurement from
M69's own operator (summed-area box, own Sobel, own noise model, constants
parsed from `crates/` at run time) on M66's exact plant, and then repeats it on
three further latents from other stacks so the number is not a property of one
2048^2 crop of one frame.

K1b is checked first: on the crate's own zero-signal plant the temporal
estimator used here must agree with the spatial estimator K1 used.
"""

import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

NREP = 64
NREP_EXTRA = 32
CROP = 2048

# M62's plant, quoted from experiments/M66-gate-n-dependence/src/04-burst.py.
M62_PLANT = ("109MSDCF", "DSC00020.ARW", 1024, 4096)

EXTRA = [
    ("coffee-bean", None, None, None),
    ("wrapped-text-1", None, None, None),
    ("bee-1", None, None, None),
]


def read_latent(stack, name=None, y=None, x=None):
    files = m69.stack_files(stack)
    path = None
    if name is not None:
        for f in files:
            if f.endswith(name):
                path = f
                break
        if path is None:
            raise SystemExit(f"{name} not in {stack}")
    else:
        path = files[len(files) // 2]
    v = m69.raw_visible(path)
    if y is None:
        y = (v.shape[0] - CROP) // 2
        y -= y % 2
    if x is None:
        x = (v.shape[1] - CROP) // 2
        x -= x % 2
    lat = v[y : y + CROP, x : x + CROP].copy()
    return lat, path, y, x


def raw_noise_sd(latent, iso):
    """Per-raw-pixel sensor sigma from the crate model (noise.rs / profile.rs)."""
    g = m69.gain(iso)
    read_dn = m69.read_noise_e(iso) * g
    var = g * np.maximum(latent - m69.BLACK, 0.0) + read_dn * read_dn
    return np.sqrt(var)


def temporal_sd(latent, iso, nrep, seed):
    sd_dn = raw_noise_sd(latent, iso)
    rng = np.random.default_rng(seed)
    acc = None
    for _ in range(nrep):
        frame = latent + sd_dn * rng.standard_normal(latent.shape)
        luma = m69.luma_from_raw(frame)
        reg = m69.regularised(luma, iso)
        if acc is None:
            acc = m69.Welford(reg.shape)
        acc.push(reg)
    return m69.interior(acc.sd()), m69.interior(acc.mean)


def box4(a):
    """4x4 mean with 'nearest' edge handling -- M66's SMOOTH latent smoother.

    scipy's uniform_filter with an even size puts the extra tap on the leading
    side; reproduced here directly rather than imported, so the two
    implementations are independent.
    """
    p = np.pad(a, ((2, 1), (2, 1)), mode="edge")
    s = np.zeros((p.shape[0] + 1, p.shape[1] + 1))
    np.cumsum(p, axis=0, out=s[1:, 1:])
    np.cumsum(s[1:, 1:], axis=1, out=s[1:, 1:])
    h, w = a.shape
    ys = np.arange(h)
    xs = np.arange(w)
    tot = (
        s[np.ix_(ys + 4, xs + 4)]
        - s[np.ix_(ys, xs + 4)]
        - s[np.ix_(ys + 4, xs)]
        + s[np.ix_(ys, xs)]
    )
    return tot / 16.0


def grad_stats(latent, iso):
    """Observed gradient budget of the latent, and the noise floor 2 s^2."""
    luma = m69.luma_from_raw(latent)
    gx, gy = m69.sobel_components(luma)
    g2 = m69.interior(gx * gx + gy * gy)
    sig = m69.interior(m69.green_luma_sigma(luma, iso))
    s = 0.125 * np.sqrt(12.0) * sig
    return float(np.mean(g2)), float(np.mean(2.0 * s * s)), float(np.mean(sig))


def k1b():
    m69.banner("M69 / K1b -- temporal estimator on the crate's zero-signal plant")
    rn = np.sqrt(2.0) / 1e-4
    sds = []
    for rep_seed in range(4):
        rng = np.random.default_rng(9100 + rep_seed)
        acc = None
        for _ in range(48):
            luma = rng.standard_normal((512, 512))
            v = 1e-4 * np.maximum(luma, 0.0) + (rn * 1e-4) ** 2
            reg = m69.regularised(luma, sigma=np.sqrt(0.25 * (v + v)))
            if acc is None:
                acc = m69.Welford(reg.shape)
            acc.push(reg)
        sds.append(float(m69.interior(acc.sd(), 22).mean()))
    sds = np.array(sds)
    rho = sds.mean() / m69.FOCUS_NOISE_SD
    ok = abs(rho - 1.0) <= 0.02
    print(f"  temporal SD mean over 4 x 48 reps = {sds.mean():.6e}   rho = {rho:.4f}")
    print(f"  K1b |rho - 1| = {abs(rho - 1.0):.4f}  bar 0.02  ->  {'MET' if ok else 'NOT MET'}")
    return {"rho": float(rho), "sd": float(sds.mean()), "met": bool(ok)}


def run_latent(tag, stack, name, y, x, nrep, seed):
    lat, path, y, x = read_latent(stack, name, y, x)
    iso = m69.iso_of(path)
    flat = np.full_like(lat, float(lat.mean()))
    smooth = box4(lat)
    g2, floor, sig = grad_stats(lat, iso)
    z2 = max(g2 - floor, 0.0) / (floor / 2.0)
    print(f"\n  {tag}: {pathlib.Path(path).name}  ISO {iso:.0f}  crop ({y},{x})")
    print(
        f"    latent raw mean {lat.mean():8.1f} DN   green luma sigma {sig:6.3f} DN"
        f"   E|grad|^2 {g2:9.4f}   noise floor 2s^2 {floor:9.4f}"
        f"   debiased (nu/s)^2 {z2:8.3f}  nu/s {np.sqrt(z2):6.3f}"
    )
    rows = {}
    m69.print_header()
    for plant, latent in (("FLAT", flat), ("SMOOTH", smooth), ("REAL", lat)):
        t0 = time.time()
        sd, mean = temporal_sd(latent, iso, nrep, seed)
        s = m69.summarise(sd, f"{tag}/{plant}")
        s["response_mean"] = float(mean.mean())
        s["secs"] = round(time.time() - t0, 1)
        m69.print_row(s)
        rows[plant] = s
    rows["_meta"] = {
        "path": path,
        "iso": iso,
        "crop": [y, x, CROP],
        "nrep": nrep,
        "grad_sq": g2,
        "noise_floor_2s2": floor,
        "sigma_luma_dn": sig,
        "z_debiased": float(np.sqrt(z2)),
    }
    return rows


def main():
    m69.banner("M69 arm A2 -- replication of M66 control K7")
    m69.dump_constants()
    out = {"K1b": k1b(), "latents": {}}

    m69.banner("A2.1 -- M62's exact plant (M66's K7 numbers)")
    out["latents"]["M62"] = run_latent("M62", *M62_PLANT, NREP, 7)
    r = out["latents"]["M62"]
    print("\n  M66 reported   FLAT 1.0018   SMOOTH 1.0690   REAL 1.1921")
    print(
        f"  M69 measures   FLAT {r['FLAT']['rho']:.4f}   SMOOTH {r['SMOOTH']['rho']:.4f}"
        f"   REAL {r['REAL']['rho']:.4f}"
    )
    d = abs(r["REAL"]["rho"] - 1.1921)
    print(f"\n  D1 |rho_REAL - 1.1921| = {d:.4f}  bar 0.02  ->  {'REPRODUCED' if d <= 0.02 else 'NOT REPRODUCED'}")

    m69.banner("A2.2 -- the same measurement on three further latents")
    for stack, name, y, x in EXTRA:
        out["latents"][stack] = run_latent(stack, stack, name, y, x, NREP_EXTRA, 11)

    (m69.OUT / "20-a2.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n  wrote out/20-a2.json")


if __name__ == "__main__":
    main()
