"""M95 arm 7 -- score colour-difference chroma against the shipped MHC.

Bars, controls and predictions are in ../PRE-REGISTRATION.md and were on disk
before this file produced a number.

The instrument is arm 6's: mosaic a known truth, demosaic it, and split the
emitted in-band power into the part a per-frequency linear filter can explain
from the truth (`signal`) and the part no such filter can (`artifact`). Arm 6's
whole result is that total power ranks loudness rather than detail, so nothing
here is decided on `power`.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "M95-demosaic" / "src"))

import m95dem as M  # noqa: E402

TRUTH = Path(r"C:\dev\strehl-out\M95-demosaic\scratch\truth_AHD.npy")
OUT = HERE.parents[1] / "out" / "c1_ladder.json"
TXT = HERE.parents[1] / "out" / "c1_ladder.txt"

TILE, NTILES = 64, 400
LO, HI = 0.30, 0.48

# Bilinear reconstruction on a 2x-spaced lattice, applied to a sparse plane that
# is zero away from its own CFA sites. Normalisation is exact for all four
# phases: the taps landing on live sites sum to 1 at an R site (centre alone),
# at a G site (two half-weights) and at a B site (four quarter-weights). K8
# checks that claim rather than trusting it.
K_LATTICE = np.array([[1.0, 2.0, 1.0],
                      [2.0, 4.0, 2.0],
                      [1.0, 2.0, 1.0]], dtype=np.float32) * 0.25


def _cdiff(mosaic, lattice, mask_shift=0):
    """Colour-difference chroma over an MHC green plane. Linear in `mosaic`."""
    mo = np.ascontiguousarray(mosaic, dtype=np.float32)
    h, w = mo.shape
    m = M.rggb_masks(h, w)
    R, B = m["R"], m["B"]
    if mask_shift:
        # deliberately wrong Bayer phase, for control discrimination only
        R = np.roll(R, mask_shift, axis=1)
        B = np.roll(B, mask_shift, axis=1)
    G = m["G1"] | m["G2"]
    if mask_shift:
        G = ~(R | B)

    # 1. green everywhere: known at G sites, MHC's F_G stencil at R/B sites
    g = np.where(G, mo, M._corr(mo, M.F_G)).astype(np.float32)
    # 2. colour differences, live only at their own sites
    dR = np.where(R, mo - g, np.float32(0.0)).astype(np.float32)
    dB = np.where(B, mo - g, np.float32(0.0)).astype(np.float32)
    # 3. reconstruct each difference across the full grid
    dRi = ndimage.correlate(dR, lattice, mode="mirror")
    dBi = ndimage.correlate(dB, lattice, mode="mirror")

    out = np.empty((h, w, 3), dtype=np.float32)
    out[..., 0] = g + dRi
    out[..., 1] = g
    out[..., 2] = g + dBi
    return out


def demosaic_cdiff(mosaic):
    return _cdiff(mosaic, K_LATTICE)


def demosaic_cdiff_badnorm(mosaic):
    """K8 discriminator: the lattice kernel scaled off unity."""
    return _cdiff(mosaic, K_LATTICE * np.float32(1.2))


def demosaic_cdiff_badparity(mosaic):
    """K10 discriminator as registered: the wrong Bayer phase."""
    return _cdiff(mosaic, K_LATTICE, mask_shift=1)


ARMS = {
    "MHC": M.demosaic_mhc,
    "CDIFF": demosaic_cdiff,
    "BILINEAR": M.demosaic_bilinear,
    "NEAREST": M.demosaic_nearest,
}
BROKEN = {
    "CDIFF_BADNORM": demosaic_cdiff_badnorm,
    "CDIFF_BADPARITY": demosaic_cdiff_badparity,
}


# --------------------------------------------------------------------- controls


def k8_constant(fns):
    """A constant mosaic must demosaic to that exact constant, all channels."""
    rows = []
    mo = np.full((64, 64), 0.37, dtype=np.float32)
    for name, f in fns.items():
        d = f(mo)
        err = float(np.abs(d - 0.37).max())
        rows.append((name, err, err < 1e-6))
    return rows


def k9_linearity(fns):
    """f(a*M1 + b*M2) == a*f(M1) + b*f(M2)."""
    rng = np.random.default_rng(11)
    m1 = rng.random((64, 64), dtype=np.float32)
    m2 = rng.random((64, 64), dtype=np.float32)
    a, b = np.float32(0.3), np.float32(-1.7)
    rows = []
    for name, f in fns.items():
        lhs = f((a * m1 + b * m2).astype(np.float32))
        rhs = a * f(m1) + b * f(m2)
        scale = max(float(np.abs(rhs).max()), 1e-6)
        err = float(np.abs(lhs - rhs).max()) / scale
        rows.append((name, err, err < 1e-5))
    return rows


def k10_shift(fns):
    """Shifting the mosaic by (2,2) must shift the output by (2,2) inside."""
    rng = np.random.default_rng(23)
    mo = rng.random((72, 72), dtype=np.float32)
    rows = []
    for name, f in fns.items():
        a = f(mo)[8:-8, 8:-8]
        b = f(np.roll(np.roll(mo, 2, 0), 2, 1))[10:-6, 10:-6]
        err = float(np.abs(a - b).max())
        rows.append((name, err, err < 1e-6))
    return rows


def k11_known_samples(fns):
    """POST-HOC, see ADDENDUM 1 section A1.2.

    Added after K8, K9 and K10 all turned out to reject nothing. An exact
    sample must survive the demosaic: R at an R site, G at a G site, B at a B
    site. CDIFF guarantees it by construction since R = G + (M - G) = M there.
    This is the only control in the arm that rejects either broken variant.
    """
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


def main():
    if not TRUTH.exists():
        sys.exit(f"missing truth {TRUTH}")
    T = np.load(TRUTH).astype(np.float32)
    res = {"truth": str(TRUTH), "tile": TILE, "n_tiles": NTILES,
           "band": [LO, HI]}
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    all_fns = dict(ARMS)
    all_fns.update(BROKEN)

    out("=" * 74)
    out("CONTROLS  (predictions registered in ../PRE-REGISTRATION.md)")
    out("=" * 74)

    ctl = {}
    for tag, fn, want in (("K8  CONSTANT ", k8_constant, "exact"),
                          ("K9  LINEARITY", k9_linearity, "linear"),
                          ("K10 SHIFT(2,2)", k10_shift, "invariant"),
                          ("K11 KNOWNSAMP", k11_known_samples, "post-hoc, A1.2")):
        rows = fn(all_fns)
        ctl[tag.split()[0]] = {n: {"err": e, "pass": bool(p)} for n, e, p in rows}
        out(f"\n{tag}  ({want})")
        for n, e, p in rows:
            mark = "PASS" if p else "FAIL"
            note = "  <- broken variant" if n in BROKEN else ""
            out(f"    {n:<16} err {e:.3e}   {mark}{note}")

    # A control that cannot fail is not evidence. Report discrimination
    # explicitly for each, including where my registered prediction was wrong.
    disc = {}
    for key in ("K8", "K9", "K10", "K11"):
        good = all(ctl[key][n]["pass"] for n in ("MHC", "CDIFF"))
        broke = [n for n in all_fns if not ctl[key][n]["pass"]]
        disc[key] = {"shipping_arms_pass": bool(good), "failed_arms": broke}
    out("\n  discrimination:")
    for key in ("K8", "K9", "K10", "K11"):
        d = disc[key]
        out(f"    {key:<4} MHC+CDIFF pass {d['shipping_arms_pass']}   "
            f"arms it rejects: {d['failed_arms'] or 'NONE -- non-discriminating'}")
    res["controls"] = ctl
    res["discrimination"] = disc

    if not all(disc[k]["shipping_arms_pass"] for k in ("K8", "K9", "K10", "K11")):
        out("\nCONTROL FAILED on a shipping arm -- refusing to print the ladder.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        TXT.write_text("\n".join(lines), encoding="utf-8")
        return 1

    # ------------------------------------------------------------- the ladder
    mo = M.mosaic_rggb(T)
    tiles = M.pick_tiles(T, TILE, NTILES, LO, HI)
    out("\n" + "=" * 74)
    out(f"THE LADDER   truth AHD {T.shape[1]}x{T.shape[0]}, "
        f"{len(tiles)} tiles of {TILE}x{TILE}, band {LO}-{HI} cyc/px")
    out("=" * 74)
    out(f"  {'arm':<16}{'power':>10}{'signal':>10}{'artifact':>10}{'share':>9}")

    lad = {}
    Tl = M.luma(T)
    for name, f in all_fns.items():
        d = f(mo)
        s = M.decompose(M.luma(d), Tl, tiles, TILE, LO, HI)
        lad[name] = s
        tag = "  <- broken" if name in BROKEN else ""
        out(f"  {name:<16}{s['power']:>+10.4f}{s['signal']:>+10.4f}"
            f"{s['artifact']:>+10.4f}{s['artifact_share']:>9.4f}{tag}")
    res["ladder_luma"] = lad

    out("\n  per channel")
    out(f"  {'arm':<10}{'ch':<4}{'power':>10}{'signal':>10}"
        f"{'artifact':>10}{'share':>9}")
    perch = {}
    for name in ("MHC", "CDIFF"):
        d = all_fns[name](mo)
        perch[name] = {}
        for ci, cn in enumerate("RGB"):
            s = M.decompose(d[..., ci], T[..., ci], tiles, TILE, LO, HI)
            perch[name][cn] = s
            out(f"  {name:<10}{cn:<4}{s['power']:>+10.4f}{s['signal']:>+10.4f}"
                f"{s['artifact']:>+10.4f}{s['artifact_share']:>9.4f}")
    res["per_channel"] = perch

    # ---------------------------------------------------------------- the bars
    gain = lad["CDIFF"]["signal"] - lad["MHC"]["signal"]
    dshare = lad["CDIFF"]["artifact_share"] - lad["MHC"]["artifact_share"]
    ch_gain = {c: perch["CDIFF"][c]["signal"] - perch["MHC"][c]["signal"]
               for c in "RGB"}
    worst_ch = min(ch_gain.values())

    b7 = bool(gain >= 0.03 and dshare <= 0.02)
    b8 = bool(gain < 0.01)
    b9 = bool(worst_ch >= -0.005)

    out("\n" + "=" * 74)
    out("PRE-REGISTERED BARS")
    out("=" * 74)
    out(f"  CDIFF luma signal gain over MHC   : {gain:+.4f} dex")
    out(f"  CDIFF artifact-share change       : {dshare:+.4f}")
    out("  per-channel signal gain           : " +
        "  ".join(f"{c} {ch_gain[c]:+.4f}" for c in "RGB"))
    out("")
    out(f"  B7 SHIP  gain >= 0.03 AND dshare <= 0.02      : {b7}")
    out(f"  B8 DEAD  gain < 0.01                          : {b8}")
    out(f"  B9 NO CHANNEL REGRESSION  worst >= -0.005     : {b9}"
        f"   (worst {worst_ch:+.4f})")
    if not b7 and not b8:
        out("  -> registered middle band: real but below the ship bar.")
    verdict = "SHIP" if (b7 and b9) else ("DEAD" if b8 else "BELOW BAR")
    out(f"\n  VERDICT : {verdict}")

    res["bars"] = {"gain_dex": gain, "dshare": dshare,
                   "channel_gain": ch_gain, "worst_channel": worst_ch,
                   "B7_ship": b7, "B8_dead": b8, "B9_no_regression": b9,
                   "verdict": verdict}

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    TXT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
