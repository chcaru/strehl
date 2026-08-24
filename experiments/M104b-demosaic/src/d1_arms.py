"""M104b step 1 -- decode one frame many ways and score real vs manufactured detail.

Bars are in docs/research/M104b-demosaic-lever.md, committed at f40dbf1 before
this file produced a number.

SEEDING IS DEMOSAIC-NEUTRAL BY CONSTRUCTION.  The comb is located on a
HALF-SIZE decode -- a pure 2x2 bin with no demosaic at all -- and the resulting
frequencies are halved to address the full-resolution grid.  If the seed came
from any candidate arm, that arm would choose which ROIs count as live, which
is the INERT selection and would be a thumb on the scale.

WHY THE GREEN PLANE.  Green is half the photosites and carries the luminance
detail; the bands below are quoted in full-resolution cyc/px.

ON "DO NOT MEASURE RESOLUTION ON IT".  `strehl stack --demosaic` prints that
warning and M85 means it: the demosaiced file's colour is interpolated, so a
pipeline resolution claim read off it would be inflated by interpolation.  That
caution is aimed at using the file to claim the SYSTEM's resolution.  Here the
demosaic IS the object of study, so it must be measured on exactly this file --
and the whole point of R_alias is to catch the inflation the warning is about
rather than to inherit it.  No claim about strehl's resolution is made here.
"""

import json
import pathlib
import sys

import numpy as np
import rawpy
import tifffile

sys.path.insert(
    0,
    str(pathlib.Path(__file__).resolve().parents[2] / "M104-resample-verify" / "src"),
)
import m104lib as L  # noqa: E402

FRAME = pathlib.Path(r"D:\personal\macro\flat-on-ruler-cpl\DSC00049.ARW")
MHC = pathlib.Path(r"C:\dev\strehl-out\M104b\arms\mhc-strehl.tif")
MERGED = pathlib.Path(
    r"C:\dev\strehl-out\M104\renders\flat-on-ruler-cpl-PRE-A0-g0.tif"
)
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"

# Bands in FULL-RESOLUTION cyc/px.  The split is physical, not invented:
# M5 measured the diffraction knee at 0.2762 cyc/px and the a-priori bellows
# factor predicts 0.2821 (facts 27, 123).  Nothing above it can be real.
SIG_LO, SIG_HI = 0.15, 0.2762
ALI_LO, ALI_HI = 0.30, 0.48

COLS, ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 8, \
    int(sys.argv[2]) if len(sys.argv) > 2 else 5
# ROI side in px.  The first run used the M104 default of 768 on an 8x5 grid
# and the single frame was in focus at only 2 of 40 ROIs, so D5 (>= 8 live)
# was unmet and nothing was admissible.  The grid is re-chosen ONLY against
# the demosaic-free binned decode, which is the same neutral path that already
# decides liveness; no arm comparison was consulted, and every arm is re-run
# from scratch afterwards.  See the report for the ordering.
ROI_PX = int(sys.argv[3]) if len(sys.argv) > 3 else 768
L.ROI = ROI_PX

ALGOS = [
    "LINEAR", "VNG", "PPG", "AHD", "DHT", "AAHD", "DCB",
    "LMMSE", "AMAZE", "VCD", "MODIFIED_AHD", "VCD_MODIFIED_AHD", "AFD",
]


def snapshot(d):
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in d.iterdir()}


def decode(algo, half=False):
    with rawpy.imread(str(FRAME)) as raw:
        return raw.postprocess(
            demosaic_algorithm=getattr(rawpy.DemosaicAlgorithm, algo),
            half_size=half,
            output_bps=16,
            gamma=(1, 1),
            no_auto_bright=True,
            use_camera_wb=True,
            # raw colour space: no colour matrix, so channels are NOT mixed.
            # A matrix would smear green detail into R and B and destroy the
            # chroma null, which is the one quantity here with a known answer.
            output_color=rawpy.ColorSpace.raw,
            user_flip=0,
            median_filter_passes=0,
            fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
        )


def build_seed():
    """Comb location from the merged render; liveness from a demosaic-free bin.

    FIRST ATTEMPT, AND WHY IT FAILED.  The seed was taken from a half-size
    decode of the single frame itself.  That frame is one exposure from a FOCUS
    BRACKET, so it is sharp only in a band; across most ROIs `find_comb` found
    no mm comb and locked onto coarse structure at f0 ~ 0.016 cyc/px instead of
    the ruler's 0.140 (binned).  Every arm then scored S/B 1.3-2.0, under the
    INERT floor of 3, and the shipped arm returned zero live ROIs.  Diagnosed
    with `dbg_mhc.py`, which showed strehl and rawpy agreeing to 3 decimals on
    the WRONG feature -- the arms were fine, the seed was not.

    The repair keeps the two roles separate and each one neutral:
      * WHERE the comb is, in frequency, comes from the 79-frame merge, which
        is in focus everywhere and knows the real tick spacing.  A frequency is
        a property of the ruler, not of any demosaic.
      * WHICH ROIs count as live comes from a half-size 2x2 bin of the single
        frame -- no demosaic has run -- so no candidate arm chooses its own
        sample.
    """
    merged = tifffile.imread(str(MERGED))
    if merged.ndim == 3:
        merged = merged[..., 1]
    s = L.seed_combs(merged.astype(np.float64), cols=COLS, rows=ROWS)
    print(f"  merged render: {len(s)} ROIs with a comb")

    gh = decode("LINEAR", half=True)[..., 1].astype(np.float64)
    grid = L.roi_grid(*gh.shape, cols=COLS, rows=ROWS)
    live = {}
    for i, v in s.items():
        if i >= len(grid):
            continue
        P, _ = L.power(L.crop(gh, grid[i]))
        c = L.find_comb_near(P, v["fy"], v["fx"])
        if c is None:
            continue
        fy, fx, f0 = c
        S, B, _ = L.probe(P, fy, fx)
        if B <= 0 or S / B < L.INERT_MIN:
            continue
        # Half-size and binned share a scale; full resolution is twice it.
        live[i] = dict(fy=fy / 2.0, fx=fx / 2.0, f0=f0 / 2.0, sb=S / B)
    print(f"  single frame in focus at {len(live)} of those ROIs")
    return live


def score(rgb, seed, label):
    """R_sig, R_alias, Phi, chroma X and comb modulations for one arm."""
    R = rgb[..., 0].astype(np.float64)
    G = rgb[..., 1].astype(np.float64)
    B = rgb[..., 2].astype(np.float64)
    grid = L.roi_grid(*G.shape, cols=COLS, rows=ROWS)
    rows = []
    for i, s in seed.items():
        if i >= len(grid):
            continue
        xy = grid[i]
        gp = L.crop(G, xy)
        P, _ = L.power(gp)
        c = L.find_comb_near(P, s["fy"], s["fx"])
        if c is None:
            continue
        fy, fx, f0 = c
        S, Bg, M1 = L.probe(P, fy, fx)
        # NO per-arm INERT gate here, deliberately.  Liveness is decided ONCE,
        # on the demosaic-free binned decode, and every arm then measures
        # exactly that set.  Re-gating per arm would let each candidate choose
        # its own sample, so a demosaic that merely raised local contrast would
        # admit ROIs the others were denied and the arms would no longer be
        # compared on the same object.  M104's symmetric INERT exists for this
        # reason; the first version of this file broke it and reported n = 1.
        _, _, M2 = L.probe(P, 2 * fy, 2 * fx)
        rs = L.band_power_abs(P, SIG_LO, SIG_HI)
        ra = L.band_power_abs(P, ALI_LO, ALI_HI)
        if rs is None or ra is None:
            continue
        # Chroma: ruler is grey, so the true comb modulation here is ZERO.
        cr = L.crop(R, xy) / max(R.mean(), 1e-9) - gp / max(G.mean(), 1e-9)
        cb = L.crop(B, xy) / max(B.mean(), 1e-9) - gp / max(G.mean(), 1e-9)
        Pcr, _ = L.power(cr, normalise=False)
        Pcb, _ = L.power(cb, normalise=False)
        _, _, xr = L.probe(Pcr, fy, fx)
        _, _, xb = L.probe(Pcb, fy, fx)
        rows.append(dict(i=i, f0=f0, sb=S / Bg, m1=M1, m2=M2,
                         r_sig=rs, r_alias=ra, x=float(xr + xb)))
    return rows


def agg(rows, key):
    v = np.array([r[key] for r in rows], dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None, None
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(v.size)) if v.size > 1 else 0.0


def dex(rows, key):
    v = np.array([r[key] for r in rows], dtype=np.float64)
    v = np.log10(v[np.isfinite(v) & (v > 0)])
    if v.size == 0:
        return None, None
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(v.size)) if v.size > 1 else 0.0


def main():
    d = FRAME.parent
    before = snapshot(d)
    seed = build_seed()
    print(f"seed: {len(seed)} ROIs located on the demosaic-free binned decode\n")

    arms = {}
    # The shipped arm, from strehl itself -- MHC as it actually ships.
    mhc = tifffile.imread(str(MHC))
    arms["MHC-strehl"] = score(mhc, seed, "MHC-strehl")

    # NCD, the negative control, made to go red EXACTLY (rule 39).
    # An unsharp mask of amount 0.500000, radius 1.0 px manufactures detail by
    # construction.  It MUST be caught by D2: R_sig up, R_alias up more, Phi
    # down.  If a planted sharpener is scored a REAL WIN, the discriminator is
    # blind and every arm above it is void.
    from scipy.ndimage import gaussian_filter

    ncd = np.empty_like(mhc)
    for ch in range(3):
        f = mhc[..., ch].astype(np.float32)
        ncd[..., ch] = np.clip(f + 0.500000 * (f - gaussian_filter(f, 1.0)),
                               0, 65535).astype(np.uint16)
    arms["NCD-unsharp-0.5"] = score(ncd, seed, "NCD")
    del ncd, mhc

    unavailable = []
    for a in ALGOS:
        try:
            rgb = decode(a)
        except Exception as e:  # LibRaw ships some algorithms only in GPL packs
            unavailable.append((a, str(e)[:60]))
            continue
        arms[a] = score(rgb, seed, a)
        del rgb

    # PLD, placebo: the same algorithm decoded twice must agree to machine
    # precision, not "closely".
    pld = score(decode("AHD"), seed, "PLD")
    worst = 0.0
    m = {r["i"]: r for r in arms["AHD"]}
    for r in pld:
        o = m.get(r["i"])
        if o:
            for kk in ("r_sig", "r_alias", "m1", "x"):
                worst = max(worst, abs(r[kk] - o[kk]))
    print(f"PLD placebo: worst deviation {worst:.3e} "
          f"({'PASS' if worst < 1e-12 else 'FAIL'}; bar < 1e-12)\n")

    assert snapshot(d) == before, "READ-ONLY ASSERTION FAILED on D:"
    print("read-only assertion: PASS\n")
    if unavailable:
        print("UNAVAILABLE in this LibRaw build:")
        for a, e in unavailable:
            print(f"  {a}: {e}")
        print()

    base = arms["MHC-strehl"]
    if not base:
        print("MHC-strehl has no live ROI -- D5 unmet, no comparison is possible.")
        json.dump({"aborted": "no live ROI on shipped arm", "unavailable": unavailable},
                  open(OUT / "d1_arms.json", "w"), indent=2)
        return
    bs, _ = dex(base, "r_sig")
    ba, _ = dex(base, "r_alias")
    print(f"{'arm':<20} {'n':>3} {'R_sig':>9} {'R_alias':>9} {'Phi':>8} "
          f"{'dR_sig':>8} {'dPhi':>8} {'X':>10}")
    out = {}
    for k, rows in arms.items():
        if not rows:
            print(f"{k:<20}   0   -- no live ROI --")
            continue
        s, ss = dex(rows, "r_sig")
        a, sa = dex(rows, "r_alias")
        x, sx = agg(rows, "x")
        phi = s - a
        print(f"{k:<20} {len(rows):>3} {s:>9.4f} {a:>9.4f} {phi:>8.4f} "
              f"{s - bs:>8.4f} {phi - (bs - ba):>8.4f} {x:>10.3e}")
        out[k] = dict(n=len(rows), r_sig=s, r_sig_se=ss, r_alias=a, r_alias_se=sa,
                      phi=phi, d_r_sig=s - bs, d_phi=phi - (bs - ba), x=x, x_se=sx,
                      rows=rows)

    # --- score the registered bars -------------------------------------------
    n_live = out["MHC-strehl"]["n"]
    print(f"\nD5 INERT: {n_live} live ROIs, bar >= 8 -> "
          f"{'PASS' if n_live >= 8 else 'FAIL (no evidence; nothing below is admissible)'}")

    def paired(rows_a, rows_b, key, log=True):
        """SE of a PAIRED difference, ROI by ROI.

        Every arm measures the SAME ROIs, so the arms are paired and the
        ROI-to-ROI variance is common-mode.  Differencing per ROI first
        cancels it.  The first version of this scoring took each arm's mean
        and combined the two independent SEs, which carries the whole spread
        of "how much ruler is in this crop" into the error bar on a quantity
        that spread cannot affect: SEs came out near 0.18 dex, an order above
        the effects, and every arm was declared inconclusive by construction.
        """
        m = {r["i"]: r for r in rows_b}
        d = []
        for r in rows_a:
            o = m.get(r["i"])
            if o is None:
                continue
            va, vb = r[key], o[key]
            if log:
                if va <= 0 or vb <= 0:
                    continue
                d.append(np.log10(va) - np.log10(vb))
            else:
                d.append(va - vb)
        d = np.array([x for x in d if np.isfinite(x)], dtype=np.float64)
        if d.size == 0:
            return None, None, 0
        se = float(d.std(ddof=1) / np.sqrt(d.size)) if d.size > 1 else 0.0
        return float(d.mean()), se, d.size

    b = out["MHC-strehl"]
    print(f"\nPAIRED against MHC-strehl (same ROIs, differenced per ROI)")
    print(f"{'arm':<20} {'dR_sig':>9} {'SE':>7} {'sigma':>7} "
          f"{'dPhi':>9} {'SE':>7} {'sigma':>7}  verdict")
    for k, v in out.items():
        if k == "MHC-strehl":
            continue
        ds, se_s, _ = paired(v["rows"], b["rows"], "r_sig")
        da, se_a, _ = paired(v["rows"], b["rows"], "r_alias")
        # Phi = R_sig / R_alias, so d(log Phi) = d(log R_sig) - d(log R_alias),
        # itself a per-ROI paired quantity.
        m = {r["i"]: r for r in b["rows"]}
        dp = []
        for r in v["rows"]:
            o = m.get(r["i"])
            if o and r["r_sig"] > 0 and r["r_alias"] > 0 and o["r_sig"] > 0 and o["r_alias"] > 0:
                dp.append((np.log10(r["r_sig"]) - np.log10(r["r_alias"]))
                          - (np.log10(o["r_sig"]) - np.log10(o["r_alias"])))
        dp = np.array(dp)
        dpm = float(dp.mean())
        se_p = float(dp.std(ddof=1) / np.sqrt(dp.size)) if dp.size > 1 else 0.0
        dx, se_x, _ = paired(v["rows"], b["rows"], "x", log=False)
        if ds < 0.02:
            verd = "no win (D1 unmet)"
        elif dpm < -2 * se_p:
            verd = "MANUFACTURED (D2)"
        else:
            verd = "REAL WIN (D1)"
        sg_s = abs(ds) / se_s if se_s else float("inf")
        sg_p = abs(dpm) / se_p if se_p else float("inf")
        print(f"{k:<20} {ds:>9.4f} {se_s:>7.4f} {sg_s:>7.2f} "
              f"{dpm:>9.4f} {se_p:>7.4f} {sg_p:>7.2f}  {verd}")
        v.update(d_r_sig_paired=ds, se_d_r_sig=se_s, sigma_r_sig=sg_s,
                 d_phi_paired=dpm, se_d_phi=se_p, sigma_phi=sg_p,
                 d_x_paired=dx, se_d_x=se_x, verdict=verd)

    # CUT: is the band split physically where facts 27/123 say?
    cut = out["MHC-strehl"]["r_alias"] - out["MHC-strehl"]["r_sig"]
    print(f"\nCUT control: R_alias - R_sig on MHC = {cut:+.4f} dex "
          f"({'PASS' if cut < -0.3 else 'FAIL'}; bar < -0.30)")

    json.dump({"bands": [SIG_LO, SIG_HI, ALI_LO, ALI_HI], "frame": FRAME.name,
               "unavailable": unavailable, "cut_dex": cut, "arms": out},
              open(OUT / "d1_arms.json", "w"), indent=2)


if __name__ == "__main__":
    main()
