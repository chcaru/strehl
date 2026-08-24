"""M87 step 24 -- THE POLARITY FALSIFIER, on ground truth.

Registered in PREREG-ADDENDUM-3-polarity.md, commit 4e04877, BEFORE this ran.

The two-layer veiling model predicts the signed error against truth is

    E(d) = merge(d) - truth(d) ~= alpha_{k_B}(d) * (Fbar - B(d))

so it must carry the sign of (Fbar - Bbar) and REVERSE when the polarity of the
contrast reverses.  Three registered tests:

  N1 sign      -- sign(median E over d in [3,40]) == sign(Fbar - Bbar)
  N2 magnitude -- |E| within 2x of a ZERO-FREE-PARAMETER forward model built
                  from the plant's KNOWN alpha and KNOWN F, B
  N3 shape     -- Pearson r >= 0.5 between measured E(d) and forward E(d)

Arms: levels SWAPPED, not rescaled, so both scenes hold the same two luminance
levels (level-matching control C-lvl).

  P_plus  : F dark  (0.08), B bright (0.75)   -> predicted E < 0
  P_minus : F bright(0.75), B dark   (0.08)   -> predicted E > 0

Controls:
  C-sig  : repeat with a CONSTANT focus normaliser instead of green_luma_sigma,
           removing the signal-dependent nonlinearity (fact 1064) that is the
           live alternative explanation for any polarity asymmetry.
  C-gate : pure selection, so the averaging gate cannot contribute.
  C-mask : profiles taken from the KNOWN silhouette, never from Otsu.

Everything is measured on the plant because only there do alpha, F, B and the
all-in-focus truth exist.  The real-data arm is step 25.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

H, W = 384, 512
N = 121
KF, KB = 40, 90
SCALE = 0.28
LEVEL = 3000.0
READ_SD = 6.0
D_MAX = 64
BAND = (3, 40)

LO, HI = 0.08, 0.75          # the two levels, swapped between arms


def build(fg_level, bg_level, seed=87):
    """Two-layer plant.  fg_level/bg_level select which layer is bright.

    Everything else -- geometry, depths, textures, noise, compositing order --
    is identical between arms.  Only the assignment of the two levels flips.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]

    # background texture: same RELATIVE modulation whichever level it carries,
    # so the two arms have matched texture contrast, not matched absolute
    # amplitude.  Matching relative contrast is what keeps the focus measure
    # (a gradient ratio) comparable across arms.
    tex = 0.0467 * np.sin(xx / 1.6) * np.cos(yy / 1.9)
    tex = tex + 0.016 * ndi.gaussian_filter(rng.standard_normal((H, W)), 0.8)
    b = bg_level * (1.0 + tex)
    b = np.clip(b, 0.01, 1.2)

    m = ((xx > 150) & (xx < 260)).astype(np.float32)
    m *= (yy > 20) & (yy < H - 20)
    m = ndi.gaussian_filter(m, 0.6)
    m = np.clip(m, 0, 1)
    f = fg_level * (1.0 + 0.375 * np.sin(yy / 7.0))

    frames = np.empty((N, H, W), np.float32)
    alphas = np.empty((N, H, W), np.float32)
    for k in range(N):
        sf = abs(k - KF) * SCALE
        sb = abs(k - KB) * SCALE
        a = ndi.gaussian_filter(m, sf) if sf > 0.3 else m.copy()
        fb = ndi.gaussian_filter(m * f, sf) if sf > 0.3 else (m * f)
        bb = ndi.gaussian_filter(b, sb) if sb > 0.3 else b.copy()
        img = fb + bb * (1.0 - a)
        alphas[k] = a
        v = img * LEVEL
        frames[k] = v + rng.normal(0, np.sqrt(np.maximum(v, 1.0)) + READ_SD,
                                   (H, W))
    truth = (m * f + b * (1.0 - m)) * LEVEL
    return frames, alphas, m, f, b, truth


def field_signal_dependent(fr, iso=100.0):
    return L.regularised_field(fr, iso)


def field_constant_sigma(fr, iso=100.0):
    """C-sig: identical operator with the signal-dependent divisor replaced by
    a scene-constant one.  Removes the fact-1064 nonlinearity entirely."""
    f = L.clamped_box(L.sobel_mag(fr), L.WINDOW_RADIUS)
    sig = float(np.median(L.green_luma_sigma(fr, iso)))
    f = f / max(sig, L.SIGMA_EPS)
    return L.clamped_box(f, L.REGULARISER_RADIUS).astype(np.float32)


def merge(frames, fieldfn):
    best = np.full(frames.shape[1:], -np.inf, np.float32)
    arg = np.zeros(frames.shape[1:], np.int32)
    for k in range(len(frames)):
        fl = fieldfn(frames[k].astype(np.float64))
        better = fl > best
        best[better] = fl[better]
        arg[better] = k
    sel = np.take_along_axis(frames, arg[None], 0)[0]
    return sel, arg


def normals_from_mask(m, thr=0.5):
    """Outward unit normals and exterior distance, from the KNOWN silhouette."""
    solid = m > thr
    edt = ndi.distance_transform_edt(~solid)
    s = ndi.gaussian_filter(edt.astype(np.float64), 4.0)
    gy, gx = np.gradient(s)
    n = np.hypot(gy, gx)
    return solid, edt, gy / np.maximum(n, 1e-9), gx / np.maximum(n, 1e-9)


def sample_profiles(imgs, m, roi_pad=48, step=2):
    """Return (P, d) where P[i] is a stack of profiles, one row per boundary
    point, sampled outward along the normal at d = 0..D_MAX."""
    solid, edt, ny, nx = normals_from_mask(m)
    # boundary points: exterior pixels at distance ~1 from the silhouette
    band = (edt > 0.5) & (edt < 1.5)
    ys, xs = np.nonzero(band)
    keep = ((ys > roi_pad) & (ys < H - roi_pad)
            & (xs > roi_pad) & (xs < W - roi_pad))
    ys, xs = ys[keep][::step], xs[keep][::step]
    ds = np.arange(D_MAX + 1, dtype=np.float64)
    out = []
    for img in imgs:
        prof = np.empty((len(ys), D_MAX + 1), np.float64)
        for j, (y, x) in enumerate(zip(ys, xs)):
            py = y + ny[y, x] * ds
            px = x + nx[y, x] * ds
            prof[j] = ndi.map_coordinates(img, [py, px], order=1, mode="nearest")
        out.append(prof)
    return out, ds, ys, xs, ny, nx


def forward_veil(alphas, arg, f, b, m, ys, xs, ny, nx):
    """ZERO-FREE-PARAMETER forward prediction: at each sampled point take the
    alpha of the ACTUALLY ELECTED frame and multiply by the known (F - B)."""
    ds = np.arange(D_MAX + 1, dtype=np.float64)
    fbar = float(np.mean(f))
    pred = np.empty((len(ys), D_MAX + 1), np.float64)
    # alpha of the elected frame, as an image
    a_elect = np.take_along_axis(alphas, arg[None], 0)[0].astype(np.float64)
    diff = (fbar - b) * LEVEL
    for j, (y, x) in enumerate(zip(ys, xs)):
        py = y + ny[y, x] * ds
        px = x + nx[y, x] * ds
        av = ndi.map_coordinates(a_elect, [py, px], order=1, mode="nearest")
        dv = ndi.map_coordinates(diff, [py, px], order=1, mode="nearest")
        pred[j] = av * dv
    return pred


def png(a, path, lo, hi, gamma=2.2):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def run_arm(tag, fg, bg, fieldfn, fieldtag):
    frames, alphas, m, f, b, truth = build(fg, bg)
    sel, arg = merge(frames, fieldfn)
    (prof_sel, prof_tru), ds, ys, xs, ny, nx = sample_profiles(
        [sel.astype(np.float64), truth.astype(np.float64)], m)
    pred = forward_veil(alphas, arg, f, b, m, ys, xs, ny, nx)

    err = prof_sel - prof_tru                       # signed error, DN
    E = np.median(err, axis=0) / LEVEL              # fraction of level
    Ef = np.median(pred, axis=0) / LEVEL            # forward model

    lo_d, hi_d = BAND
    band = slice(lo_d, hi_d + 1)
    E_band = float(np.median(E[band]))
    Ef_band = float(np.median(Ef[band]))

    fbar, bbar = float(np.mean(f)), float(np.mean(b))
    exp_sign = 1.0 if fbar > bbar else -1.0

    # N3: shape correlation over the whole profile
    r = float(np.corrcoef(E, Ef)[0, 1])

    # bootstrap the band statistic over profiles (they are spatially adjacent,
    # so resample in contiguous blocks of 32 rows)
    rng = np.random.default_rng(24)
    nrow = err.shape[0]
    blocks = max(1, nrow // 32)
    boot = []
    for _ in range(400):
        idx = np.concatenate([np.arange(i * 32, min((i + 1) * 32, nrow))
                              for i in rng.integers(0, blocks, blocks)])
        boot.append(np.median(np.median(err[idx], axis=0)[band]) / LEVEL)
    ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))

    n1 = (np.sign(E_band) == exp_sign)
    ratio = abs(E_band) / max(abs(Ef_band), 1e-12)
    n2 = 0.5 <= ratio <= 2.0
    n2_soft = ratio >= 0.25
    n3 = r >= 0.5

    print(f"\n--- {tag} [{fieldtag}] : F={fbar/1.0:.3f} B={bbar:.3f} "
          f"(F-B){'>' if fbar > bbar else '<'}0 ---", flush=True)
    print(f"  profiles           : {nrow}", flush=True)
    print(f"  E  (measured, band): {E_band:+.5f} of level  "
          f"95% CI [{ci[0]:+.5f}, {ci[1]:+.5f}]", flush=True)
    print(f"  Ef (forward,  band): {Ef_band:+.5f} of level", flush=True)
    print(f"  |E|/|Ef|           : {ratio:.3f}", flush=True)
    print(f"  Pearson r (shape)  : {r:+.3f}", flush=True)
    print(f"  N1 sign      : {'PASS' if n1 else 'FAIL'} "
          f"(expected {'+' if exp_sign > 0 else '-'}, "
          f"got {'+' if E_band > 0 else '-'})", flush=True)
    print(f"  N2 magnitude : {'PASS' if n2 else ('SOFT' if n2_soft else 'FAIL')}",
          flush=True)
    print(f"  N3 shape     : {'PASS' if n3 else 'FAIL'}", flush=True)

    return dict(tag=tag, field=fieldtag, fbar=fbar, bbar=bbar,
                n_profiles=int(nrow), E_band=E_band, E_ci=list(ci),
                Ef_band=Ef_band, ratio=float(ratio), pearson_r=r,
                N1=bool(n1), N2=bool(n2), N2_soft=bool(n2_soft), N3=bool(n3),
                E_profile=[float(v) for v in E],
                Ef_profile=[float(v) for v in Ef]), (sel, truth, m)


def main():
    results = []
    keep = {}
    for fieldtag, fieldfn in (("signal-dependent", field_signal_dependent),
                              ("constant-sigma", field_constant_sigma)):
        for tag, fg, bg in (("P_plus  dark-FG/bright-BG", LO, HI),
                            ("P_minus bright-FG/dark-BG", HI, LO)):
            r, imgs = run_arm(tag, fg, bg, fieldfn, fieldtag)
            results.append(r)
            if fieldtag == "signal-dependent":
                keep[tag] = imgs

    print("\n================ REGISTERED VERDICT ================", flush=True)
    for fieldtag in ("signal-dependent", "constant-sigma"):
        sub = [r for r in results if r["field"] == fieldtag]
        signs = [np.sign(r["E_band"]) for r in sub]
        flipped = signs[0] != signs[1]
        print(f"  [{fieldtag}] E: "
              f"{sub[0]['E_band']:+.5f}  /  {sub[1]['E_band']:+.5f}   "
              f"-> sign {'FLIPS' if flipped else 'DOES NOT FLIP'}", flush=True)
        if not flipped:
            print("      => N1 FAILED: veiling REFUTED as dominant cause",
                  flush=True)

    for tag, (sel, truth, m) in keep.items():
        short = "Pplus" if "plus" in tag else "Pminus"
        lo, hi = np.percentile(truth, [0.5, 99.5])
        png(sel, OUT / f"24-{short}-merge.png", lo, hi)
        png(truth, OUT / f"24-{short}-truth.png", lo, hi)
        e = sel.astype(np.float64) - truth.astype(np.float64)
        png(e, OUT / f"24-{short}-error.png", -0.10 * LEVEL, 0.10 * LEVEL,
            gamma=1.0)
        print(f"  wrote out/24-{short}-*.png "
              f"(error map stretched +-10% of level, mid grey = 0)", flush=True)

    (DATA / "24-polarity.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    print("\n  -> data/24-polarity.json", flush=True)


if __name__ == "__main__":
    main()
