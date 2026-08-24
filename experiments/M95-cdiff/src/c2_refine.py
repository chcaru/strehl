"""M95 arm 7, stage 2 -- one linear green refinement on top of CDIFF.

Registered in ../PRE-REGISTRATION.md ADDENDUM 1 section A1.3 before this file
produced a number. Bars B10/B11/B12 and the K11 hard gate are stated there.

CDIFF leaves green exactly as MHC computes it, so its per-channel green gain is
+0.0000 and its luma gain is structurally capped -- luma is 71.5% green. This
stage refines green using the *exact* R and B samples, which CDIFF already
guarantees are preserved, and then redoes the chroma against the better green.

Every step is a convolution or a masked subtraction, so the result is still
linear and shift-invariant within a CFA phase.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "M95-demosaic" / "src"))
sys.path.insert(0, str(HERE.parent))

import m95dem as M  # noqa: E402
from c1_ladder import K_LATTICE, demosaic_cdiff  # noqa: E402

TRUTH = Path(r"C:\dev\strehl-out\M95-demosaic\scratch\truth_AHD.npy")
OUT = HERE.parents[1] / "out" / "c2_refine.json"
TXT = HERE.parents[1] / "out" / "c2_refine.txt"

TILE, NTILES = 64, 400
LO, HI = 0.30, 0.48

# Reconstruct from the GREEN quincunx (half the pixels) onto the R and B sites:
# the four nearest green neighbours, which is the only 3x3 kernel that is exact
# on that lattice. Taps landing on live sites sum to 1 at an R or B site.
K_QUINCUNX = np.array([[0.0, 1.0, 0.0],
                       [1.0, 0.0, 1.0],
                       [0.0, 1.0, 0.0]], dtype=np.float32) * 0.25


def demosaic_cdiff2(mosaic):
    mo = np.ascontiguousarray(mosaic, dtype=np.float32)
    h, w = mo.shape
    m = M.rggb_masks(h, w)
    R, B = m["R"], m["B"]
    G = m["G1"] | m["G2"]

    # ---- stage 1: CDIFF, verbatim
    g = np.where(G, mo, M._corr(mo, M.F_G)).astype(np.float32)
    dR = np.where(R, mo - g, np.float32(0.0)).astype(np.float32)
    dB = np.where(B, mo - g, np.float32(0.0)).astype(np.float32)
    r1 = g + ndimage.correlate(dR, K_LATTICE, mode="mirror")
    b1 = g + ndimage.correlate(dB, K_LATTICE, mode="mirror")

    # ---- stage 2: refine green at R and B sites.
    # At a green site the green sample is EXACT and the chroma is interpolated,
    # so (chroma - green) there carries only the chroma's error. Carry that
    # difference onto the R/B sites and subtract it from the EXACT R/B sample:
    # the green estimate then inherits the chroma's error instead of its own.
    er = np.where(G, r1 - mo, np.float32(0.0)).astype(np.float32)
    eb = np.where(G, b1 - mo, np.float32(0.0)).astype(np.float32)
    eri = ndimage.correlate(er, K_QUINCUNX, mode="mirror")
    ebi = ndimage.correlate(eb, K_QUINCUNX, mode="mirror")
    g2 = np.where(R, mo - eri, np.where(B, mo - ebi, mo)).astype(np.float32)

    # ---- stage 3: redo the chroma against the refined green
    dR2 = np.where(R, mo - g2, np.float32(0.0)).astype(np.float32)
    dB2 = np.where(B, mo - g2, np.float32(0.0)).astype(np.float32)
    out = np.empty((h, w, 3), dtype=np.float32)
    out[..., 0] = g2 + ndimage.correlate(dR2, K_LATTICE, mode="mirror")
    out[..., 1] = g2
    out[..., 2] = g2 + ndimage.correlate(dB2, K_LATTICE, mode="mirror")
    return out


def demosaic_cdiff2_badnorm(mosaic):
    """K11 discriminator: green-refinement kernel scaled off unity."""
    saved = K_QUINCUNX.copy()
    try:
        K_QUINCUNX[:] = saved * 1.25
        return demosaic_cdiff2(mosaic)
    finally:
        K_QUINCUNX[:] = saved


def k11_known_samples(fns):
    """Exact samples must survive: R at R sites, G at G sites, B at B sites."""
    rng = np.random.default_rng(5)
    mo = rng.random((64, 64), dtype=np.float32)
    m = M.rggb_masks(64, 64)
    G = m["G1"] | m["G2"]
    rows = []
    for name, f in fns.items():
        d = f(mo)
        e = max(float(np.abs(d[..., 0][m["R"]] - mo[m["R"]]).max()),
                float(np.abs(d[..., 1][G] - mo[G]).max()),
                float(np.abs(d[..., 2][m["B"]] - mo[m["B"]]).max()))
        rows.append((name, e, e < 1e-6))
    return rows


def k9_linearity(fns):
    rng = np.random.default_rng(11)
    m1 = rng.random((64, 64), dtype=np.float32)
    m2 = rng.random((64, 64), dtype=np.float32)
    a, b = np.float32(0.3), np.float32(-1.7)
    rows = []
    for name, f in fns.items():
        lhs = f((a * m1 + b * m2).astype(np.float32))
        rhs = a * f(m1) + b * f(m2)
        scale = max(float(np.abs(rhs).max()), 1e-6)
        e = float(np.abs(lhs - rhs).max()) / scale
        rows.append((name, e, e < 1e-5))
    return rows


def main():
    if not TRUTH.exists():
        sys.exit(f"missing truth {TRUTH}")
    T = np.load(TRUTH).astype(np.float32)
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    arms = {"MHC": M.demosaic_mhc, "CDIFF": demosaic_cdiff,
            "CDIFF2": demosaic_cdiff2}
    gated = dict(arms)
    gated["CDIFF2_BADNORM"] = demosaic_cdiff2_badnorm

    res = {"truth": str(TRUTH), "tile": TILE, "n_tiles": NTILES,
           "band": [LO, HI]}

    out("=" * 74)
    out("K11  KNOWN-SAMPLE PRESERVATION   (hard gate, registered in A1.3)")
    out("=" * 74)
    k11 = k11_known_samples(gated)
    for n, e, p in k11:
        tag = "  <- broken variant" if "BADNORM" in n else ""
        out(f"    {n:<16} err {e:.3e}   {'PASS' if p else 'FAIL'}{tag}")
    res["K11"] = {n: {"err": e, "pass": bool(p)} for n, e, p in k11}
    rejected = [n for n, _, p in k11 if not p]
    out(f"    discrimination: rejects {rejected or 'NONE -- non-discriminating'}")

    out("\n" + "=" * 74)
    out("K9  LINEARITY   (the licence and noise argument depends on it)")
    out("=" * 74)
    k9 = k9_linearity(arms)
    for n, e, p in k9:
        out(f"    {n:<16} err {e:.3e}   {'PASS' if p else 'FAIL'}")
    res["K9"] = {n: {"err": e, "pass": bool(p)} for n, e, p in k9}

    gate_ok = all(p for n, _, p in k11 if n in arms) and all(p for _, _, p in k9)
    if not gate_ok:
        out("\nHARD GATE FAILED -- refusing to print the ladder.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        TXT.write_text("\n".join(lines), encoding="utf-8")
        return 1

    mo = M.mosaic_rggb(T)
    tiles = M.pick_tiles(T, TILE, NTILES, LO, HI)
    Tl = M.luma(T)

    out("\n" + "=" * 74)
    out(f"LADDER   truth AHD, {len(tiles)} tiles of {TILE}x{TILE}, "
        f"band {LO}-{HI} cyc/px")
    out("=" * 74)
    out(f"  {'arm':<10}{'ch':<4}{'power':>10}{'signal':>10}"
        f"{'artifact':>10}{'share':>9}")
    lad = {}
    for name, f in arms.items():
        d = f(mo)
        lad[name] = {"luma": M.decompose(M.luma(d), Tl, tiles, TILE, LO, HI)}
        s = lad[name]["luma"]
        out(f"  {name:<10}{'Y':<4}{s['power']:>+10.4f}{s['signal']:>+10.4f}"
            f"{s['artifact']:>+10.4f}{s['artifact_share']:>9.4f}")
        for ci, cn in enumerate("RGB"):
            s = M.decompose(d[..., ci], T[..., ci], tiles, TILE, LO, HI)
            lad[name][cn] = s
            out(f"  {name:<10}{cn:<4}{s['power']:>+10.4f}{s['signal']:>+10.4f}"
                f"{s['artifact']:>+10.4f}{s['artifact_share']:>9.4f}")
        out("")
    res["ladder"] = lad

    def gain(a, key):
        return lad[a][key]["signal"] - lad["MHC"][key]["signal"]

    g2 = gain("CDIFF2", "luma")
    ds2 = (lad["CDIFF2"]["luma"]["artifact_share"]
           - lad["MHC"]["luma"]["artifact_share"])
    ch2 = {c: gain("CDIFF2", c) for c in "RGB"}
    worst2 = min(ch2.values())

    b10 = bool(g2 >= 0.03 and ds2 <= 0.02)
    b11 = bool(worst2 >= -0.005)
    b12 = bool(ch2["G"] > 0.005)

    out("=" * 74)
    out("PRE-REGISTERED BARS  (A1.3)")
    out("=" * 74)
    out(f"  CDIFF  luma signal gain over MHC : {gain('CDIFF', 'luma'):+.4f} dex")
    out(f"  CDIFF2 luma signal gain over MHC : {g2:+.4f} dex")
    out(f"  CDIFF2 artifact-share change     : {ds2:+.4f}")
    out("  CDIFF2 per-channel signal gain   : " +
        "  ".join(f"{c} {ch2[c]:+.4f}" for c in "RGB"))
    out("")
    out(f"  B10 SHIP  gain >= 0.03 AND dshare <= 0.02   : {b10}")
    out(f"  B11 NO CHANNEL REGRESSION  worst >= -0.005  : {b11}"
        f"   (worst {worst2:+.4f})")
    out(f"  B12 GREEN MUST MOVE  G gain > 0.005         : {b12}"
        f"   (G {ch2['G']:+.4f})")
    verdict = "SHIP" if (b10 and b11 and b12) else "DO NOT SHIP"
    out(f"\n  VERDICT : {verdict}")
    res["bars"] = {"cdiff_gain": gain("CDIFF", "luma"), "cdiff2_gain": g2,
                   "dshare": ds2, "channel_gain": ch2, "worst": worst2,
                   "B10_ship": b10, "B11_no_regression": b11,
                   "B12_green_moved": b12, "verdict": verdict}

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    TXT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
