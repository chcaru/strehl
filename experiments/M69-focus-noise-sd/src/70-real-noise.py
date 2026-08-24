"""M69 -- two real-noise arms that need no capture the corpus does not have.

A2b / K8  THE GREEN HALF-SPLIT.
    Every RGGB quad carries two green photosites. The shipped luma is their mean,
    so G1 and G2 are two INDEPENDENT noisy observations of nearly the same scene
    in the SAME exposure. Running the operator on each half separately gives a
    difference field whose scatter is real sensor noise on real texture with a
    CLEAN latent -- the one thing every synthetic-noise arm in this project,
    including M66's K7 and M69's own A2, cannot have.

    Two known contaminants inflate it: the halves sit half a plane pixel apart
    (a deterministic scene difference) and their gains differ slightly (PRNU).
    Both are FIXED PATTERN, so a matched synthetic pair on the same latent at
    the same noise scale isolates them. That comparison is control K8.

    The halves carry sqrt(2) times the luma noise, so the half-split measures
    sigma_F at nu/s divided by sqrt(2), not at nu/s. P2 transports it.

A4  DARK FRAMES.
    22 darks per ISO group, first two discarded as stabilisation. Their temporal
    per-pixel scatter is a direct test of the read-noise half of the sensor model
    at each ISO, and their response scatter is the crate's own zero-signal plant
    realised with real sensor noise instead of a random number generator.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a2 = __import__("importlib").import_module("20-a2-m66-replication")
p2m = __import__("importlib").import_module("40-p2-predictor")

CROP = 2048
S_SOBEL = 0.125 * np.sqrt(12.0)


def halves(raw):
    h = (raw.shape[0] // 2) * 2
    w = (raw.shape[1] // 2) * 2
    g1 = np.maximum(raw[0:h:2, 1:w:2] - m69.BLACK, 0.0)
    g2 = np.maximum(raw[1:h:2, 0:w:2] - m69.BLACK, 0.0)
    return g1, g2


def half_sigma(h, iso):
    g = m69.gain(iso)
    rn = m69.read_noise_e(iso) * g
    return np.sqrt(g * np.maximum(h, 0.0) + rn * rn)


def half_response(h, iso):
    f = m69.box_clamped(m69.sobel_mag(h), m69.WINDOW_RADIUS)
    f /= np.maximum(half_sigma(h, iso), m69.SIGMA_EPS)
    return m69.box_clamped(f, m69.REGULARISER_RADIUS)


def rms(a):
    return float(np.sqrt(np.mean(np.asarray(a, dtype=np.float64) ** 2)))


def half_split(tag, stack, name, y, x, seeds=6):
    lat, path, y, x = a2.read_latent(stack, name, y, x)
    iso = m69.iso_of(path)
    g1, g2 = halves(lat)
    d_real = m69.interior(half_response(g1, iso) - half_response(g2, iso))
    sd_real = rms(d_real) / np.sqrt(2.0)

    latent = 0.5 * (g1 + g2)
    sig = half_sigma(latent, iso)
    sds = []
    for s in range(seeds):
        rng = np.random.default_rng(8800 + s)
        a = latent + sig * rng.standard_normal(latent.shape)
        b = latent + sig * rng.standard_normal(latent.shape)
        sds.append(rms(m69.interior(half_response(a, iso) - half_response(b, iso))) / np.sqrt(2.0))
    sd_syn = float(np.mean(sds))

    pred_half = float(m69.interior(p2m.p2(latent, sig)).mean())

    luma = m69.luma_from_raw(lat)
    sig_l = m69.green_luma_sigma(luma, iso)
    pred_full = float(m69.interior(p2m.p2(luma, sig_l)).mean())

    excess2 = sd_real**2 - sd_syn**2
    excess = float(np.sign(excess2) * np.sqrt(abs(excess2)))
    transported = sd_real * pred_full / pred_half
    transported_clean = sd_syn * pred_full / pred_half
    print(
        f"  {tag:<16} ISO {iso:>4.0f}   half-split {sd_real:.6f}  matched-synthetic"
        f" {sd_syn:.6f}   fixed-pattern excess {excess:+.6f}"
    )
    print(
        f"  {'':<16} P2 at half scale {pred_half:.6f}  P2 at luma scale {pred_full:.6f}"
        f"   -> rho transported {transported / m69.FOCUS_NOISE_SD:.4f}"
        f"  (synthetic-only {transported_clean / m69.FOCUS_NOISE_SD:.4f})"
    )
    return {
        "path": path,
        "iso": iso,
        "sd_half_split": sd_real,
        "sd_matched_synthetic": sd_syn,
        "fixed_pattern_excess": excess,
        "p2_half_scale": pred_half,
        "p2_luma_scale": pred_full,
        "rho_transported": float(transported / m69.FOCUS_NOISE_SD),
        "rho_transported_synthetic_only": float(transported_clean / m69.FOCUS_NOISE_SD),
        "ratio_real_over_synthetic": float(sd_real / sd_syn),
    }


def darks():
    m69.banner("A4 -- dark frames: read-noise model and the zero-signal plant")
    root = pathlib.Path(m69.DARKS)
    groups = sorted(p for p in root.iterdir() if p.is_dir())
    print(f"  {'group':<12} {'ISO':>5} {'used':>5} {'emp read DN':>12} {'model RN*g':>11}"
          f" {'ratio':>7} {'rho_dark':>9} {'clipped %':>10}")
    print("  " + "-" * 78)
    rows = {}
    for gdir in groups:
        files = sorted(str(p) for p in gdir.iterdir() if p.suffix.upper() == ".ARW")
        if len(files) < 5:
            continue
        files = files[2:]
        iso = m69.iso_of(files[0])
        acc_raw = None
        acc_resp = None
        for f in files:
            v = m69.raw_visible(f)
            y = (v.shape[0] - CROP) // 2
            x = (v.shape[1] - CROP) // 2
            y -= y % 2
            x -= x % 2
            sub = v[y : y + CROP, x : x + CROP].copy()
            luma = m69.luma_from_raw(sub)
            reg = m69.regularised(luma, iso)
            if acc_raw is None:
                acc_raw = m69.Welford(sub.shape)
                acc_resp = m69.Welford(reg.shape)
            acc_raw.push(sub)
            acc_resp.push(reg)
        emp = float(np.median(acc_raw.sd()))
        model = m69.read_noise_e(iso) * m69.gain(iso)
        sd = m69.interior(acc_resp.sd())
        rho = float(sd.mean() / m69.FOCUS_NOISE_SD)
        clipped = float(np.mean(acc_raw.mean < m69.BLACK) * 100.0)
        print(f"  {gdir.name:<12} {iso:>5.0f} {len(files):>5} {emp:>12.4f} {model:>11.4f}"
              f" {emp / model:>7.4f} {rho:>9.4f} {clipped:>9.1f}%")
        rows[gdir.name] = {
            "iso": iso,
            "frames_used": len(files),
            "empirical_read_dn": emp,
            "model_read_dn": model,
            "ratio": float(emp / model),
            "rho_dark": rho,
            "pct_below_black": clipped,
        }
    return rows


def main():
    m69.banner("M69 -- real-noise arms: green half-split (K8) and dark frames (A4)")
    m69.dump_constants()
    m69.banner("A2b / K8 -- green half-split on real texture")
    print("  sd is per-half response scatter: RMS(X_G1 - X_G2) / sqrt(2).\n")
    hs = {}
    for tag, stack, name, y, x in (
        ("M62", "109MSDCF", "DSC00020.ARW", 1024, 4096),
        ("coffee-bean", "coffee-bean", None, None, None),
        ("wrapped-text-1", "wrapped-text-1", None, None, None),
        ("bee-1", "bee-1", None, None, None),
    ):
        hs[tag] = half_split(tag, stack, name, y, x)
    ratios = np.array([v["ratio_real_over_synthetic"] for v in hs.values()])
    ok = bool(np.all(np.abs(ratios - 1.0) <= 0.10))
    print(f"\n  K8 real/synthetic ratio {np.round(ratios, 4).tolist()}   bar +-10%"
          f"  ->  {'MET' if ok else 'NOT MET'}")
    dk = darks()
    (m69.OUT / "70-real-noise.json").write_text(
        json.dumps({"half_split": hs, "k8_met": ok, "darks": dk}, indent=2), encoding="utf-8"
    )
    print("\n  wrote out/70-real-noise.json")


if __name__ == "__main__":
    main()
