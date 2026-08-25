"""M126-default-audit — the scorer.

Computes exactly the metrics registered in PREREG.md sections 3, 3b and 3c
(commit b77d67c4f0563fa029a73073fbde89aac79ee2d6), and nothing else.

The pooled N/D/Q core is M116-promotion/score.py unchanged, deliberately: this
milestone re-asks M116's question on more arms and more subjects, and a metric
that moved between the two would make the comparison meaningless. What is new
here is section 3b (per-tile dispersion, discipline 866) and section 3c (the
chromatic metric, which exists because the green-plane metric is provably blind
to the CA gate).

Every mask comes from the M0 arm (`--gate 0`), which is never compared, so no
mask is derived from an arm under test.

HAZARD: `PIL.Image.open()` silently downconverts 16-bit RGB TIFFs to 8-bit and
has corrupted 241 measurements in this project. This file uses `tifffile` only.

    python experiments\\M126-default-audit\\score.py
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

ROOT = Path(r"C:\dev\strehl-out\M126")
MEASURE = ROOT / "measure"

# Fixed in PREREG section 3. Identical to M116-promotion/score.py.
FLAT_FRAC = 0.20
DET_FRAC = 0.20
HP_BOX = 5
STRUCT_DOWN = 4
STRUCT_WIN = 33
# PREREG section 3b.
TILE = 64
# PREREG section 3c.
OUTER_R = 0.6
INNER_R = 0.3

SUBJECTS = ["bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl"]

# Aligned arms, scored against A0 with M0's masks. Order is report order.
# (file tag as written by run.ps1, display name as registered in PREREG s4).
ALIGNED_ARMS = [
    ("A0", "A0-default"),
    ("M0", "M0-gate0"),
    ("G1", "G1-ca"), ("G2", "G2-robust"), ("G3", "G3-smooth"),
    ("G4", "G4-softgate"), ("G5", "G5-photometric"), ("G6", "G6-halo"),
    ("ALL", "ALL-on"),
    ("D1", "D1-noca"), ("D2", "D2-norobust"), ("D3", "D3-nosmooth"),
    ("D4", "D4-nosoftgate"), ("D5", "D5-nophotometric"),
    ("N1", "N1-rerun"), ("P1", "P1-placebo"), ("P2", "P2-ungated"),
    ("PC", "PC-nearest"), ("PC2", "PC2-nearest-solved"),
]
# Unaligned arms, scored against each other with M0u's masks.
UNALIGNED_ARMS = [("B1u", "B1u-noalign"), ("B0", "B0-single")]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def rgb(path: Path) -> np.ndarray:
    """The merge's three planes as f64. tifffile, never PIL."""
    a = tifffile.imread(path)
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} is {a.shape}, want HxWx3"
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, want uint16 (PIL hazard)"
    return a.astype(np.float64)


def green(path: Path) -> np.ndarray:
    return rgb(path)[:, :, 1]


def highpass(g: np.ndarray) -> np.ndarray:
    """L - box5(L). `g` is 2-D by assertion, so no non-spatial axis can be
    smoothed (AGENTS.md rule 23)."""
    assert g.ndim == 2
    return g - uniform_filter(g, size=HP_BOX, mode="nearest")


def structure(g: np.ndarray) -> np.ndarray:
    """Local sd of the mask arm at a coarse scale. Downsampled 4x FIRST so the
    ranking is driven by scene structure, not by the mask arm's own noise."""
    h, w = g.shape
    hh, ww = h // STRUCT_DOWN, w // STRUCT_DOWN
    blocks = g[: hh * STRUCT_DOWN, : ww * STRUCT_DOWN]
    small = blocks.reshape(hh, STRUCT_DOWN, ww, STRUCT_DOWN).mean(axis=(1, 3))
    m1 = uniform_filter(small, size=STRUCT_WIN, mode="nearest")
    m2 = uniform_filter(small * small, size=STRUCT_WIN, mode="nearest")
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, STRUCT_DOWN, axis=0), STRUCT_DOWN, axis=1)
    out = np.zeros((h, w), dtype=np.float64)
    out[: up.shape[0], : up.shape[1]] = up[:h, :w]
    if up.shape[0] < h:
        out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < w:
        out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


def score_plane(g: np.ndarray, mflat: np.ndarray, mdet: np.ndarray) -> dict:
    hp = highpass(g)
    sd_flat = float(hp[mflat].std())
    sd_det = float(hp[mdet].std())
    return {
        "sd_flat": sd_flat,
        "sd_det": sd_det,
        "N": float(np.log10(sd_flat)),
        "D": float(np.log10(sd_det)),
        "Q": float(np.log10(sd_det)) - float(np.log10(sd_flat)),
    }


def tile_sd(hp: np.ndarray) -> np.ndarray:
    """sd of `hp` within each TILExTILE tile, as a (rows, cols) grid."""
    h, w = hp.shape
    hh, ww = h // TILE, w // TILE
    b = hp[: hh * TILE, : ww * TILE].reshape(hh, TILE, ww, TILE)
    m1 = b.mean(axis=(1, 3))
    m2 = (b * b).mean(axis=(1, 3))
    return np.sqrt(np.maximum(m2 - m1 * m1, 0.0))


def tile_class(struct: np.ndarray, flat_cut: float, det_cut: float):
    """Per-tile detail/flat classification from the MASK ARM's structure field.
    Registered in PREREG 3b: mean struct at or above the detail cut => detail
    tile; at or below the flat cut => flat tile."""
    h, w = struct.shape
    hh, ww = h // TILE, w // TILE
    b = struct[: hh * TILE, : ww * TILE].reshape(hh, TILE, ww, TILE)
    m = b.mean(axis=(1, 3))
    return m <= flat_cut, m >= det_cut


def dispersion(sd_arm: np.ndarray, sd_ref: np.ndarray, sel: np.ndarray,
               improved_when_positive: bool) -> dict:
    """Per-tile delta in dex over the selected tiles, plus improved fraction."""
    a, r = sd_arm[sel], sd_ref[sel]
    ok = (a > 0) & (r > 0)
    d = np.log10(a[ok]) - np.log10(r[ok])
    if d.size == 0:
        return {"n_tiles": 0}
    imp = float((d > 0).mean()) if improved_when_positive else float((d < 0).mean())
    return {
        "n_tiles": int(d.size),
        "median": float(np.median(d)),
        "sd": float(d.std()),
        "p10": float(np.quantile(d, 0.10)),
        "p90": float(np.quantile(d, 0.90)),
        "improved_frac": imp,
    }


def chromatic(a: np.ndarray, mdet: np.ndarray) -> dict:
    """PREREG 3c. corr(hp_R, hp_G) and corr(hp_B, hp_G) over detail pixels,
    split by field radius. Blue is a free placebo (eps_b is None) and the inner
    disc is a second free placebo (a radial term has ~0 lever there)."""
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.sqrt(((yy - cy) / (h / 2.0)) ** 2 + ((xx - cx) / (w / 2.0)) ** 2)
    r = r / r.max()
    hp_r = highpass(a[:, :, 0])
    hp_g = highpass(a[:, :, 1])
    hp_b = highpass(a[:, :, 2])
    out = {}
    for name, sel in (("outer", mdet & (r > OUTER_R)),
                      ("inner", mdet & (r < INNER_R))):
        if sel.sum() < 1000:
            out[name] = {"n_px": int(sel.sum())}
            continue
        out[name] = {
            "n_px": int(sel.sum()),
            "X_R": float(np.corrcoef(hp_r[sel], hp_g[sel])[0, 1]),
            "X_B": float(np.corrcoef(hp_b[sel], hp_g[sel])[0, 1]),
        }
    return out


def run_group(subject: str, mask_arm: str, arms: list, ref_arm: str, tag: str) -> dict:
    mp = MEASURE / f"{subject}__{mask_arm}.tif"
    if not mp.exists():
        print(f"  [{tag}] mask arm {mp.name} missing, skipping group")
        return {}
    struct = structure(green(mp))
    flat_cut = float(np.quantile(struct, FLAT_FRAC))
    det_cut = float(np.quantile(struct, 1.0 - DET_FRAC))
    mflat, mdet = struct <= flat_cut, struct >= det_cut
    tflat, tdet = tile_class(struct, flat_cut, det_cut)

    rp = MEASURE / f"{subject}__{ref_arm}.tif"
    if not rp.exists():
        print(f"  [{tag}] reference arm {rp.name} missing, skipping group")
        return {}
    ref_rgb = rgb(rp)
    ref_hp = highpass(ref_rgb[:, :, 1])
    ref_tsd = tile_sd(ref_hp)
    ref_sha = sha256(rp)

    out = {
        "mask_arm": mask_arm,
        "mask_source": str(mp),
        "ref_arm": ref_arm,
        "shape": list(struct.shape),
        "n_flat_px": int(mflat.sum()),
        "n_det_px": int(mdet.sum()),
        "n_flat_tiles": int(tflat.sum()),
        "n_det_tiles": int(tdet.sum()),
        "arms": {},
    }
    for file_tag, arm in arms:
        p = MEASURE / f"{subject}__{file_tag}.tif"
        if not p.exists():
            print(f"  [{tag}] {p.name} missing")
            continue
        a = rgb(p)
        if a.shape != ref_rgb.shape:
            print(f"  [{tag}] {arm} is {a.shape}, ref is {ref_rgb.shape} -- skipped")
            continue
        s = score_plane(a[:, :, 1], mflat, mdet)
        s["sha256"] = sha256(p)
        s["bytes"] = p.stat().st_size
        s["sha_equals_ref"] = (s["sha256"] == ref_sha)
        # PREREG 3c: is the GREEN plane bitwise identical to the reference?
        # For G1-ca this is a derived prediction, not a guess: optics.rs:194-199
        # returns None for Channel::Green.
        s["green_identical_to_ref"] = bool(
            np.array_equal(a[:, :, 1], ref_rgb[:, :, 1]))
        s["red_identical_to_ref"] = bool(
            np.array_equal(a[:, :, 0], ref_rgb[:, :, 0]))
        s["blue_identical_to_ref"] = bool(
            np.array_equal(a[:, :, 2], ref_rgb[:, :, 2]))
        tsd = tile_sd(highpass(a[:, :, 1]))
        s["tiles_detail"] = dispersion(tsd, ref_tsd, tdet, True)
        s["tiles_flat"] = dispersion(tsd, ref_tsd, tflat, False)
        s["chromatic"] = chromatic(a, mdet)
        out["arms"][arm] = s
    return out


def main() -> int:
    results = {}
    for subject in SUBJECTS:
        print(f"== {subject} ==")
        aligned = run_group(subject, "M0", ALIGNED_ARMS, "A0", "aligned")
        unaligned = run_group(subject, "M0u", UNALIGNED_ARMS, "B1u", "unaligned")
        results[subject] = {"aligned": aligned, "unaligned": unaligned}

        ref = aligned.get("arms", {}).get("A0-default")
        if ref:
            print(f"  power floor: Q(A0) = {ref['Q']:.4f} dex "
                  f"(bar: >= 0.50)")
            print(f"  {'arm':17s} {'N':>8s} {'D':>8s} {'Q':>8s} "
                  f"{'dN':>8s} {'dD':>8s} {'dQ':>8s} "
                  f"{'tD.med':>8s} {'tD.imp':>7s} {'G=':>3s}  sha")
            for arm, s in aligned["arms"].items():
                td = s["tiles_detail"]
                print(f"  {arm:17s} {s['N']:8.5f} {s['D']:8.5f} {s['Q']:8.5f} "
                      f"{s['N'] - ref['N']:+8.5f} {s['D'] - ref['D']:+8.5f} "
                      f"{s['Q'] - ref['Q']:+8.5f} "
                      f"{td.get('median', float('nan')):+8.5f} "
                      f"{100.0 * td.get('improved_frac', float('nan')):6.1f}% "
                      f"{'Y' if s['green_identical_to_ref'] else 'n':>3s}  "
                      f"{s['sha256'][:12]}")
            for arm in ("A0-default", "G1-ca", "ALL-on"):
                s = aligned["arms"].get(arm)
                if s:
                    c = s["chromatic"]
                    o, i = c.get("outer", {}), c.get("inner", {})
                    print(f"  chroma {arm:14s} outer X_R={o.get('X_R', float('nan')):.5f} "
                          f"X_B={o.get('X_B', float('nan')):.5f} | "
                          f"inner X_R={i.get('X_R', float('nan')):.5f} "
                          f"X_B={i.get('X_B', float('nan')):.5f}")
        u = unaligned.get("arms", {})
        if "B0-single" in u and "B1u-noalign" in u:
            print(f"  V-M116 gauge: D(merge, ALIGN=0) - D(single frame) = "
                  f"{u['B1u-noalign']['D'] - u['B0-single']['D']:+.5f} dex")

    (ROOT / "scores.json").write_text(json.dumps(results, indent=2))
    print(f"\nwrote {ROOT / 'scores.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
