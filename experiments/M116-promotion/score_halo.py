"""M116-promotion — scoring for the occlusion-halo campaign (prereg-halo.txt).

Implements prereg-halo.txt section 3 verbatim. Reads ONLY the linear renders in
C:\\dev\\strehl-out\\M116\\halo\\measure. The sRGB renders under view/ are for
looking at and are never measured here.

The foreground convention matches the tool's own, read from the source at the
pinned SHA: `crates/strehl-cli/src/merge_cmd/halo.rs` builds its mask with
`luma.iter().map(|&v| v < tau)` -- the subject is the DARKER-than-Otsu class,
closed then opened with a radius-3 disc, components under 2000 px dropped.
Reproducing that convention here is what makes the containment check (HB6)
comparable to the tool's own yoke.
"""

import json
import hashlib
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

import score as S  # same directory; guarded by __main__, so importing is inert

ROOT = Path(r"C:\dev\strehl-out\M116")
HALO = ROOT / "halo"

# From halo.rs at the pinned SHA.
YOKE = 40.0        # binned px, the correction's stated reach
DISC_R = 3
MIN_COMPONENT = 2000
OTSU_BINS = 512

# The halo index bands, in binned px of distance from the silhouette.
NEAR_LO, NEAR_HI = 2.0, 40.0
FAR_LO, FAR_HI = 60.0, 100.0

SUBJECTS = [
    "bee-3-cpl",
    "flower-bud-with-background-fern-cpl",
    "flower-bud-alone-cpl",
    "tweezers-cpl",
]
ARMS = ["H0", "H1", "H2", "H3"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def otsu(a: np.ndarray) -> float:
    """The tool's own Otsu: 512 bins over the finite range, bin centres."""
    v = a[np.isfinite(a)]
    lo, hi = float(v.min()), float(v.max())
    if not hi > lo:
        return lo
    scale = OTSU_BINS / (hi - lo)
    idx = np.clip(((v - lo) * scale).astype(np.int64), 0, OTSU_BINS - 1)
    hist = np.bincount(idx, minlength=OTSU_BINS).astype(np.float64)
    centre = lo + (np.arange(OTSU_BINS) + 0.5) / scale
    total = hist.sum()
    grand = float((hist * centre).sum())
    w0 = np.cumsum(hist)
    cw = np.cumsum(hist * centre)
    w1 = total - w0
    ok = (w0 > 0) & (w1 > 0)
    mu0 = np.divide(cw, w0, out=np.zeros_like(cw), where=w0 > 0)
    mu1 = np.divide(grand - cw, w1, out=np.zeros_like(cw), where=w1 > 0)
    scoreb = np.where(ok, w0 * w1 * (mu0 - mu1) ** 2, -np.inf)
    return float(centre[int(np.argmax(scoreb))])


def disc(r: int) -> np.ndarray:
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return (y * y + x * x) <= r * r


def foreground_mask(luma: np.ndarray):
    """Darker-than-Otsu, closed, opened, de-speckled. Mirrors halo.rs."""
    tau = otsu(luma)
    m = luma < tau
    se = disc(DISC_R)
    m = ndimage.binary_closing(m, structure=se)
    m = ndimage.binary_opening(m, structure=se)
    lab, n = ndimage.label(m)  # 4-connectivity is the tool's; 8 is scipy's
    if n:
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        keep = sizes >= MIN_COMPONENT
        m = keep[lab]
    return m, float(tau)


def halo_index(g: np.ndarray, fg: np.ndarray, keep: np.ndarray = None):
    """H = mean over background pixels 2<=d<=40 of (L / L_far - 1).

    A ratio, so it is invariant to the exposure constant and to any global
    gain: an absolute DN tolerance is what produced the 'waxy blob' (fact 1470).

    `keep`, when given, restricts the whole statistic to a subset of the frame.
    That is the POST-HOC bright-background variant described in
    docs/research/M116-promotion.md; the registered index passes keep=None.
    """
    d = ndimage.distance_transform_edt(~fg)
    bg = ~fg
    if keep is not None:
        bg = bg & keep
    near = bg & (d >= NEAR_LO) & (d <= NEAR_HI)
    far = bg & (d >= FAR_LO) & (d <= FAR_HI)
    if near.sum() < 1000 or far.sum() < 1000:
        return None
    l_far = float(np.median(g[far]))
    if not np.isfinite(l_far) or l_far <= 0:
        return None
    h = float(np.mean(g[near] / l_far - 1.0))
    # Radial profile, for the report's figure and for reading the rim's shape.
    prof = []
    for r0 in range(0, 100, 4):
        band = bg & (d >= r0) & (d < r0 + 4)
        if band.sum() > 200:
            prof.append([r0 + 2, float(np.mean(g[band]) / l_far - 1.0),
                         int(band.sum())])
    return {
        "H": h,
        "L_far": l_far,
        "near_px": int(near.sum()),
        "far_px": int(far.sum()),
        "profile": prof,
    }


def yoke_noise(g: np.ndarray, fg: np.ndarray):
    """Local high-pass std inside the yoke band against outside it."""
    hp = S.highpass(g)
    d = ndimage.distance_transform_edt(~fg)
    bg = ~fg
    near = bg & (d >= NEAR_LO) & (d <= NEAR_HI)
    far = bg & (d >= FAR_LO) & (d <= FAR_HI)
    if near.sum() < 1000 or far.sum() < 1000:
        return None
    sn, sf = float(hp[near].std()), float(hp[far].std())
    return {"sd_yoke": sn, "sd_outside": sf,
            "ratio": sn / sf if sf > 0 else float("nan")}


def containment(a: np.ndarray, b: np.ndarray, fg: np.ndarray):
    """Where do H0 and H1 differ, relative to the stated 40 px yoke?"""
    diff = np.any(a != b, axis=2)
    n = int(diff.sum())
    if n == 0:
        return {"changed_px": 0, "changed_pct": 0.0, "beyond_yoke_px": 0,
                "beyond_yoke_pct": 0.0, "max_d": 0.0, "p99_9_d": 0.0}
    d = ndimage.distance_transform_edt(~fg)
    dd = d[diff]
    beyond = int((dd > YOKE).sum())
    return {
        "changed_px": n,
        "changed_pct": 100.0 * n / diff.size,
        "beyond_yoke_px": beyond,
        "beyond_yoke_pct": 100.0 * beyond / n,
        "max_d": float(dd.max()),
        "p99_9_d": float(np.percentile(dd, 99.9)),
        "in_fg_px": int((dd == 0).sum()),
    }


def bright_edge_mask(g: np.ndarray, fg: np.ndarray, tile: int = 128):
    """POST-HOC. Tiles that straddle a silhouette AND whose background side is
    bright, which is the only place M87's stated mechanism can produce a rim:
    "a bright rim around a dark subject that meets a bright out-of-focus
    background". The registered global index averages over the WHOLE silhouette,
    including the large part of it that meets dark background, which dilutes any
    rim that exists only at bright edges. This variant is not registered and is
    reported separately and as post-hoc.
    """
    h, w = g.shape
    ty, tx = h // tile, w // tile
    fgt = fg[:ty * tile, :tx * tile].reshape(ty, tile, tx, tile).mean(axis=(1, 3))
    gt = np.where(fg, np.nan, g)[:ty * tile, :tx * tile]
    gt = gt.reshape(ty, tile, tx, tile)
    with np.errstate(all="ignore"):
        bgm = np.nanmedian(gt, axis=(1, 3))
    straddle = (fgt > 0.10) & (fgt < 0.90) & np.isfinite(bgm)
    if straddle.sum() < 8:
        return None, {}
    cut = float(np.nanquantile(bgm[straddle], 0.75))
    sel = straddle & (bgm >= cut)
    keep = np.zeros((h, w), dtype=bool)
    big = np.repeat(np.repeat(sel, tile, axis=0), tile, axis=1)
    keep[:big.shape[0], :big.shape[1]] = big
    return keep, {"tiles_straddling": int(straddle.sum()),
                  "tiles_kept": int(sel.sum()),
                  "bg_median_cut": cut,
                  "keep_pct": 100.0 * float(keep.mean())}


def fine_structure(g: np.ndarray, treated: np.ndarray, control: np.ndarray, window):
    """Detail amplitude inside a window, split by whether the correction
    touched the pixel.

    The REGISTERED HB3 statistic was Q = D - N evaluated with the same mask
    passed for both the flat and the detail set, which makes D and N the same
    number and Q identically zero for every arm. That is a dead probe in the
    sense of fact 1548, and the prereg's own vacuity clause is what caught it.
    The replacement is stated post-hoc: D over treated pixels, with D over
    untreated pixels in the SAME window as an internal control that must not
    move. Softening shows as a fall in D_treated.

    `control` is NOT simply ~treated. highpass() is a 5 px box, so an untouched
    pixel within 2 px of a touched one still changes value, and a naive control
    read +0.101 dex on an arm whose control pixels are byte-identical. The
    control set is therefore the untreated set ERODED by the filter's support,
    which is the algebraic expansion of the control in the terms it combines.
    """
    hp = S.highpass(g)[window]
    t = treated[window]
    c = control[window]
    out = {"treated_px": int(t.sum()), "control_px": int(c.sum())}
    for name, m in (("D_treated", t), ("D_untreated", c)):
        if m.sum() > 5000:
            sd = float(hp[m].std())
            out[name] = float(np.log10(sd)) if sd > 0 else float("nan")
            out[name + "_sd"] = sd
        else:
            out[name] = float("nan")
    return out


def main() -> None:
    out = {"pinned_sha": "4beac7300e318f6f0aaf10b6a88e57f311b9e814",
           "subjects": {}}

    for subj in SUBJECTS:
        print(f"==== {subj} ====", flush=True)
        rec = {"arms": {}}
        mdir = HALO / "measure"
        paths = {a: mdir / f"{subj}__{a}.tif" for a in ARMS}
        missing = [a for a, p in paths.items() if not p.exists()]
        if missing:
            print(f"  SKIP, missing arms: {missing}")
            continue

        # ---- hashes, and the cross-campaign replicate check ---------------
        for a in ARMS:
            rec["arms"][a] = {"sha256": sha256(paths[a])[:12]}
        old_a0 = ROOT / "measure" / f"{subj}__A0.tif"
        if old_a0.exists():
            rec["A0_replicate"] = {
                "old_A0": sha256(old_a0)[:12],
                "new_H0": rec["arms"]["H0"]["sha256"],
                "identical": sha256(old_a0)[:12] == rec["arms"]["H0"]["sha256"],
            }
        rec["HB5_trap_halo0_identical_to_H0"] = (
            rec["arms"]["H3"]["sha256"] == rec["arms"]["H0"]["sha256"])

        # ---- the mask is built ONCE, on H0, and reused for every arm ------
        # Building it per-arm would let the correction move its own ruler.
        g0 = S.green(paths["H0"])
        fg, tau = foreground_mask(g0)
        rec["mask"] = {"tau": tau, "fg_px": int(fg.sum()),
                       "fg_pct": 100.0 * float(fg.sum()) / fg.size,
                       "shape": list(g0.shape)}
        print(f"  tau {tau:.1f}  fg {rec['mask']['fg_pct']:.2f}%")

        # ---- halo index per arm -------------------------------------------
        for a in ARMS:
            g = g0 if a == "H0" else S.green(paths[a])
            hi = halo_index(g, fg)
            yn = yoke_noise(g, fg)
            if hi is None:
                rec["arms"][a]["halo"] = None
                continue
            rec["arms"][a]["halo"] = {k: v for k, v in hi.items()
                                      if k != "profile"}
            rec["arms"][a]["profile"] = hi["profile"]
            rec["arms"][a]["yoke_noise"] = yn
            print(f"  {a}: H={hi['H']:+.5f}  yoke/out={yn['ratio']:.4f}")

        h0 = rec["arms"]["H0"]["halo"]
        if h0 and h0["H"] != 0:
            for a in ["H1", "H2", "H3"]:
                ha = rec["arms"][a]["halo"]
                if ha:
                    rec["arms"][a]["dHALO_pct"] = 100.0 * (ha["H"] - h0["H"]) / h0["H"]
            for a in ["H1", "H2"]:
                r0 = rec["arms"]["H0"]["yoke_noise"]["ratio"]
                ra = rec["arms"][a]["yoke_noise"]["ratio"]
                rec["arms"][a]["yoke_noise_rise_pct"] = 100.0 * (ra - r0) / r0

        # ---- fine structure (HB3): treated vs untreated, in one window ----
        # The window must CONTAIN treated pixels or it cannot express softening.
        a0 = tifffile.imread(paths["H0"])
        a1 = tifffile.imread(paths["H1"])
        a2 = tifffile.imread(paths["H2"])
        t1 = np.any(a0 != a1, axis=2)
        t2 = np.any(a0 != a2, axis=2)
        rec["HB6_containment"] = containment(a0, a1, fg)
        del a0, a1, a2
        # Compare every arm on the pixels BOTH deltas touched, so delta 40 and
        # delta 80 are not scored over different populations.
        treated = t1 & t2
        control = ~ndimage.binary_dilation(
            t1 | t2, structure=np.ones((S.HP_BOX + 2, S.HP_BOX + 2), bool))
        rec["treated_sets"] = {
            "d40_px": int(t1.sum()), "d80_px": int(t2.sum()),
            "common_px": int(treated.sum()),
            "control_px": int(control.sum()),
        }

        st = S.structure(g0)
        x, y = S.best_window(st, want_high=True)  # returns (x, y), not (y, x)
        win = (slice(y, y + S.CROP), slice(x, x + S.CROP))
        rec["fine_window"] = {
            "y": int(y), "x": int(x), "size": S.CROP,
            "treated_pct_of_window": 100.0 * float(treated[win].mean()),
        }
        for a in ARMS:
            g = g0 if a == "H0" else S.green(paths[a])
            rec["arms"][a]["fine"] = fine_structure(g, treated, control, win)
            rec["arms"][a]["fine_global"] = fine_structure(
                g, treated, control, (slice(None), slice(None)))
        ref = rec["arms"]["H0"]["fine"]
        gref = rec["arms"]["H0"]["fine_global"]
        for a in ["H1", "H2", "H3"]:
            f = rec["arms"][a]["fine"]
            gf = rec["arms"][a]["fine_global"]
            rec["arms"][a]["dD_treated"] = f["D_treated"] - ref["D_treated"]
            rec["arms"][a]["dD_untreated"] = f["D_untreated"] - ref["D_untreated"]
            rec["arms"][a]["dD_treated_global"] = (
                gf["D_treated"] - gref["D_treated"])
            rec["arms"][a]["dD_untreated_global"] = (
                gf["D_untreated"] - gref["D_untreated"])
            print(f"  {a}: dD_treated={rec['arms'][a]['dD_treated']:+.5f}  "
                  f"global={rec['arms'][a]['dD_treated_global']:+.5f}  "
                  f"ctrl={rec['arms'][a]['dD_untreated_global']:+.5f}")

        # ---- POST-HOC: the bright-background-only halo index ---------------
        keep, kinfo = bright_edge_mask(g0, fg)
        if keep is not None:
            rec["bright_edge"] = kinfo
            hb0 = halo_index(g0, fg, keep)
            if hb0 and hb0["H"] != 0:
                rec["arms"]["H0"]["halo_bright"] = {
                    k: v for k, v in hb0.items() if k != "profile"}
                rec["arms"]["H0"]["profile_bright"] = hb0["profile"]
                for a in ["H1", "H2"]:
                    hb = halo_index(S.green(paths[a]), fg, keep)
                    if hb:
                        rec["arms"][a]["halo_bright"] = {
                            k: v for k, v in hb.items() if k != "profile"}
                        rec["arms"][a]["profile_bright"] = hb["profile"]
                        rec["arms"][a]["dHALO_bright_pct"] = (
                            100.0 * (hb["H"] - hb0["H"]) / hb0["H"])
                print(f"  bright-edge H0={hb0['H']:+.5f}  "
                      f"dHALO_bright(H1)="
                      f"{rec['arms']['H1'].get('dHALO_bright_pct', float('nan')):+.2f}%")

        out["subjects"][subj] = rec

    # ---- bee gate-0 pair, M87's own terms ---------------------------------
    g0p = HALO / "measure" / "bee-3-cpl__G0.tif"
    g1p = HALO / "measure" / "bee-3-cpl__G1.tif"
    if g0p.exists() and g1p.exists():
        gg0 = S.green(g0p)
        fg0, tau0 = foreground_mask(gg0)
        h_off = halo_index(gg0, fg0)
        h_on = halo_index(S.green(g1p), fg0)
        out["bee_gate0"] = {
            "tau": tau0,
            "H_off": h_off["H"], "H_on": h_on["H"],
            "dHALO_pct": 100.0 * (h_on["H"] - h_off["H"]) / h_off["H"],
            "profile_off": h_off["profile"], "profile_on": h_on["profile"],
        }
        print(f"  bee gate0: dHALO% = {out['bee_gate0']['dHALO_pct']:+.2f}")

    # ---- HB2, the deciding bar --------------------------------------------
    fern = out["subjects"].get("flower-bud-with-background-fern-cpl", {})
    alone = out["subjects"].get("flower-bud-alone-cpl", {})
    d_fern = fern.get("arms", {}).get("H1", {}).get("dHALO_pct")
    d_alone = alone.get("arms", {}).get("H1", {}).get("dHALO_pct")
    if d_fern is not None and d_alone is not None and d_fern != 0:
        out["HB2_selectivity"] = {
            "dHALO_pct_fern": d_fern,
            "dHALO_pct_alone": d_alone,
            "R": d_alone / d_fern,
            "bar": "R <= 0.50",
            "pass": (d_alone / d_fern) <= 0.50,
        }

    (HALO / "scores-halo.json").write_text(json.dumps(out, indent=2))
    print("\nwrote", HALO / "scores-halo.json")


if __name__ == "__main__":
    main()
