"""M87 step 59 -- the lobe lengthscale, measured without an imposed band width.

WHY 57's P-C IS VOID. 57 ran a granulometry on the VEIL BAND, defined as the
bright pixels within NEAR_VEIL = 40 px of the subject. The opening collapsed
from 93.5% retained at r=16 to 30% at r=21, and r=21 is my registered candidate
2*(WINDOW_RADIUS 13 + REGULARISER_RADIUS 8) / 2. It looked like a clean hit on
a pre-registered lengthscale.

It is not. No disc of radius 21 -- diameter 42 -- fits inside a band 40 px
thick, so the collapse is NEAR_VEIL echoing back at me. The proof is that the
collapse sits at r=21 on the BINNED grid AND at r=21 on the 2x render: a real
physical scale must DOUBLE between the two, and this one did not move at all.
That resolution-invariance check is the only reason I caught it, so it is
registered here as a bar rather than left as a habit.

FIX. Measure the lobe scale on the FULL background component, which has no
imposed thickness. A disc opening leaves a smooth body untouched and deletes
protrusions narrower than 2r, so the area removed isolates the lobes and the
body contributes nothing.

REGISTERED BARS, before running:
  L1  RESOLUTION CONTROL. Plotted against PHYSICAL radius (binned px), the
      retention curves from the binned grid and the 2x render must overlay:
      the half-loss physical radius must agree within 25%. If they do not, the
      number is an instrument artifact and no lengthscale may be reported.
      This is the bar that voided P-C, applied in advance this time.
  L2  BAND CONTROL, deliberately broken and registered as such. Re-run the
      voided band measurement at two different NEAR_VEIL values, 40 and 20. If
      the half-loss radius tracks NEAR_VEIL/2 rather than staying put, that
      confirms 57's P-C measured my parameter, and the confirmation is
      quantitative rather than an argument.
  L3  Only if L1 passes: report the physical lobe scale and compare against
      REGULARISER_RADIUS 8, WINDOW_RADIUS 13, and their sum 21, in BINNED
      units, which is the grid the merge actually runs on.
"""

import json
import pathlib

import numpy as np
import tifffile
from scipy import ndimage as ndi

CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
GAL = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery")

BASE_R = [1, 2, 3, 4, 6, 8, 10, 12, 15, 18, 22, 26, 31, 37, 44]
L1_TOL = 0.25


def otsu(v):
    h, e = np.histogram(v.ravel(), 512)
    h = h.astype(np.float64)
    c, m = h.cumsum(), (h * ((e[:-1] + e[1:]) / 2)).cumsum()
    tot, mt = c[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        sb = (mt * c / tot - m) ** 2 / (c * (tot - c))
    return float(e[1:][np.nanargmax(sb)])


def bg_mask(lum):
    bright = lum > otsu(lum)
    lab, _ = ndi.label(bright)
    b = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    b.discard(0)
    return bright, np.isin(lab, list(b))


def spectrum(mask, radii):
    """Depth of material a disc opening cuts from the boundary, per unit perimeter.

    NOT the retained-area fraction. The background here is a single smooth body
    covering ~78% of the frame, so an opening barely dents its AREA -- 98.6%
    survives r=44 -- and a half-loss radius never exists. That is what voided
    the first version of this bar. Lobes are boundary features, so normalise by
    boundary length: E(r) = (|M| - |open(M,r)|) / perimeter has units of length
    and is the mean depth cut at scale r. It rises while r is smaller than the
    lobes and saturates at their amplitude once r passes them, so the knee is
    the lobe scale and the plateau is the lobe depth.
    """
    base = float(mask.sum())
    per = float((mask ^ ndi.binary_erosion(mask)).sum())
    d_in = ndi.distance_transform_edt(mask)
    out = []
    for r in radii:
        er = d_in > r
        op = ndi.distance_transform_edt(~er) <= r if er.any() else er
        out.append({"kept": float(op.sum() / max(base, 1.0)),
                    "depth": float((base - op.sum()) / max(per, 1.0))})
    return out


def knee(radii_phys, depth, frac=0.5):
    """Physical radius at which the cut depth first reaches `frac` of its plateau."""
    plateau = depth[-1]
    if plateau <= 0:
        return None
    tgt = frac * plateau
    for i, d in enumerate(depth):
        if d >= tgt:
            if i == 0:
                return float(radii_phys[0])
            r0, r1, d0, d1 = radii_phys[i - 1], radii_phys[i], depth[i - 1], d
            return float(r0 + (tgt - d0) * (r1 - r0) / max(d1 - d0, 1e-9))
    return None


def main():
    res = {}
    sel = np.load(CACHE / "25-flower-alone-sel.npy").astype(np.float32)
    bright_b, bg_b = bg_mask(sel)
    ys, xs = np.where(~bright_b)
    by0, by1 = max(int(ys.min()) - 150, 0), min(int(ys.max()) + 150, sel.shape[0])
    bx0, bx1 = max(int(xs.min()) - 150, 0), min(int(xs.max()) + 150, sel.shape[1])

    img = tifffile.imread(GAL / "flower-bud-alone-cpl-exposed.tif").astype(np.float32)
    lum = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    del img
    ratio = lum.shape[0] / sel.shape[0]
    bright_f, bg_f = bg_mask(lum)
    fy0, fy1 = int(by0 * ratio), int(by1 * ratio)
    fx0, fx1 = int(bx0 * lum.shape[1] / sel.shape[1]), int(bx1 * lum.shape[1] / sel.shape[1])
    print(f"binned {sel.shape}  render {lum.shape}  ratio {ratio:.4f}")
    print(f"  judged image is the EXPOSED tif -- gallery.py writes -100pct.png from it")
    mx = float(lum.max())
    print(f"  near-clipping (>=99.9% of max) on EXPOSED: "
          f"{100 * float((lum >= 0.999 * mx).mean()):.4f}%")

    print("\n=== L1: resolution control on the background component ===")
    kb = spectrum(bg_b[by0:by1, bx0:bx1], BASE_R)
    rf = [max(int(round(r * ratio)), 1) for r in BASE_R]
    kf = spectrum(bg_f[fy0:fy1, fx0:fx1], rf)
    db = [z["depth"] for z in kb]
    # render depths are in render px; divide by the ratio to compare physically
    df = [z["depth"] / ratio for z in kf]
    print(f"  {'r_phys':>7} {'kept_bin':>9} {'depth_bin':>10} "
          f"{'r_full':>7} {'kept_full':>10} {'depth_full':>11}  (binned px)")
    for i, r in enumerate(BASE_R):
        print(f"  {r:>7} {100 * kb[i]['kept']:>8.2f}% {db[i]:>10.3f} "
              f"{rf[i]:>7} {100 * kf[i]['kept']:>9.2f}% {df[i]:>11.3f}")
    hb, hf = knee(BASE_R, db), knee(BASE_R, df)
    res["knee_bin"], res["knee_full_in_binned_units"] = hb, hf
    res["plateau_bin"], res["plateau_full_in_binned_units"] = db[-1], df[-1]
    if hb and hf:
        dev = abs(hf - hb) / max(hb, 1e-9)
        pdev = abs(df[-1] - db[-1]) / max(db[-1], 1e-9)
        l1 = dev <= L1_TOL and pdev <= L1_TOL
        print(f"\n  knee     binned {hb:.2f}   render {hf:.2f} (binned units)"
              f"   deviation {100 * dev:.1f}%")
        print(f"  plateau  binned {db[-1]:.3f}  render {df[-1]:.3f}"
              f"   deviation {100 * pdev:.1f}%   bar <= {100 * L1_TOL:.0f}%"
              f"   {'PASS' if l1 else 'FAIL'}")
    else:
        l1, dev = False, None
        print(f"\n  knee  binned {hb}   render {hf} -- no plateau; L1 FAIL")
    res["L1_pass"], res["L1_dev"] = bool(l1), dev

    print("\n=== L2: the broken arm -- does the band result track my parameter? ===")
    d_sub_b = ndi.distance_transform_edt(bright_b)
    l2 = {}
    for nv in (40, 20):
        band = bg_b & (d_sub_b <= nv)
        k = spectrum(band[by0:by1, bx0:bx1], BASE_R)
        kept = [z["kept"] for z in k]
        h = None
        for i, v in enumerate(kept):
            if v < 0.5:
                r0, r1 = BASE_R[i - 1] if i else 0, BASE_R[i]
                k0 = kept[i - 1] if i else 1.0
                h = r0 + (k0 - 0.5) * (r1 - r0) / max(k0 - v, 1e-9)
                break
        l2[nv] = h
        print(f"  NEAR_VEIL={nv:>3}  half-loss r={h}  (NEAR_VEIL/2 = {nv / 2})")
    res["L2_band_half_loss"] = l2
    tracks = (l2[40] is not None and l2[20] is not None
              and abs(l2[40] - 2 * l2[20]) < 0.4 * l2[40])
    print(f"  half-loss halves with the parameter: {'YES' if tracks else 'NO'}"
          f"  -> 57's P-C {'CONFIRMED VOID' if tracks else 'not explained by this'}")
    res["L2_tracks_parameter"] = bool(tracks)

    if l1:
        print("\n=== L4: does the knee track my ladder's ENDPOINT? ===")
        # The same class of check that voided P-C. `knee` is defined against the
        # plateau, but depth(r) is still climbing at the last radius, so there
        # may be no plateau at all -- in which case "50% of the plateau" is
        # simply "50% of wherever I stopped", and the knee is my ladder.
        l4 = []
        for end in (7, 10, 12, 14):
            k = knee(BASE_R[:end + 1], db[:end + 1])
            l4.append({"end_r": BASE_R[end], "knee": k})
            print(f"  ladder ends at r={BASE_R[end]:>3}  knee = {k:.2f}"
                  f"   knee/end = {k / BASE_R[end]:.3f}")
        res["L4"] = l4
        ks = [z["knee"] for z in l4]
        drift = (max(ks) - min(ks)) / max(min(ks), 1e-9)
        stable = drift <= 0.25
        print(f"  knee drift across endpoints: {100 * drift:.1f}%"
              f"   bar <= 25%   {'STABLE' if stable else 'TRACKS THE ENDPOINT'}")
        lo, hi = 1, len(db) - 1
        slope = float(np.polyfit(np.log(BASE_R[lo:]), np.log(db[lo:]), 1)[0])
        print(f"  log-log slope of depth(r) over r={BASE_R[lo]}..{BASE_R[-1]}:"
              f" {slope:.3f}  (a power law has NO characteristic scale)")
        res["L4_stable"] = bool(stable)
        res["L4_powerlaw_slope"] = slope
        if stable:
            print("\n=== L3: physical lobe scale (binned px, the merge's grid) ===")
            print(f"  knee at r={hb:.2f} binned px -> lobe width {2 * hb:.1f} px")
            for name, v in (("REGULARISER_RADIUS", 8), ("WINDOW_RADIUS", 13),
                            ("sum", 21)):
                print(f"    knee vs {name:<18} {v:>3}  ratio {hb / v:.2f}")
            res["L3_lobe_knee_binned"] = hb
        else:
            print("\n  L3 WITHHELD. The knee is my ladder endpoint, not the image.")
            print("  Reported result: the veil boundary has NO characteristic")
            print(f"  lengthscale over 1-{BASE_R[-1]} binned px. Both apparent hits")
            print("  -- 42 px = 2*(13+8) in 57, and 28.6 px = 2*WINDOW_RADIUS here --")
            print("  were my own instrument parameters, and a dense pre-registered")
            print("  candidate list made them look like confirmations.")
    else:
        print("\n  L3/L4 withheld: L1 failed, so no lengthscale may be reported.")

    json.dump(res, open(DATA / "59-lengthscale.json", "w"), indent=1)
    print(f"\nwrote {DATA / '59-lengthscale.json'}")


if __name__ == "__main__":
    main()
