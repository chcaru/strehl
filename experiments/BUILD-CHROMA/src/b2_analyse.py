"""B2 -- analyse the through-focus curves. The headline number and the
LoCA-vs-lateral discrimination.

Statistics policy, stated up front because it is the part most easily fudged:

* **The independent unit is the TILE, not the sample point.** The focus
  operator has a 27-plane-px box support and sample points are 10 px apart, so
  points inside a tile are heavily correlated. Pooling 12 150 points and
  quoting sqrt(n) would understate the uncertainty by roughly an order of
  magnitude. Every headline uncertainty here is between-tile scatter over
  ~54 tiles. The pooled-over-points figure is printed BESIDE it so the reader
  can see the difference rather than take my word for it.

* **The raw statistic is reported beside every excess-over-control, in the
  same table** (rule 3). `null` is the G1-G2 difference: the same wavelength on
  a different lattice with independent noise, carrying every estimator, SNR and
  lattice bias the instrument has and none of the axial signal.

* **The control is evaluated in the SAME radial bins as the treatment**
  (rule 4). A control that itself trends with radius would be no control on the
  radius axis, which is the axis the whole LoCA-vs-lateral discrimination turns
  on.

* **The confidence gate is reported as a LADDER, not as a chosen threshold**
  (rule 5). If the answer depends on where the gate sits, that is a finding and
  it will be visible.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, PLANES, parabola_peak, dump


def load(stack, tag="main"):
    return np.load(os.path.join(OUT, "json", f"b1_{stack}_{tag}.npz"),
                   allow_pickle=True)


def peaks(z):
    """Per-point sub-frame peak index for each of the four CFA planes."""
    nk, nt, npt = z["R"].shape
    res = {}
    for c in PLANES:
        F = z[c].reshape(nk, nt * npt).astype(np.float64)
        kh, pk, prom, interior, uni = parabola_peak(F)
        res[c] = {"k": kh, "peak": pk, "prom": prom, "ok": interior & uni, "F": F}
    return res, nt, npt


def hwhm(F, kh):
    """Through-focus half-width at half maximum, in frames, per point."""
    nk, n = F.shape
    lo = F.min(axis=0)
    pk = F.max(axis=0)
    half = lo + 0.5 * (pk - lo)
    above = F > half[None, :]
    cnt = above.sum(axis=0).astype(float)
    return 0.5 * cnt          # full width -> half width


def interp_at(F, k):
    """Linear interpolation of each column of F at its own fractional index k."""
    nk, n = F.shape
    kc = np.clip(k, 0, nk - 1.001)
    i0 = np.floor(kc).astype(int)
    t = kc - i0
    idx = np.arange(n)
    return F[i0, idx] * (1 - t) + F[i0 + 1, idx] * t


def gate(res, thr, track_ok):
    conf = np.ones(res["R"]["k"].shape, bool)
    for c in PLANES:
        conf &= res[c]["ok"] & (res[c]["prom"] >= thr)
    return conf & track_ok


def tilewise(values, conf, nt, npt, minpts=12):
    """Median per tile over its confident points; tiles with too few are dropped."""
    v = values.reshape(nt, npt)
    c = conf.reshape(nt, npt)
    out, keep = np.full(nt, np.nan), np.zeros(nt, bool)
    for t in range(nt):
        if c[t].sum() >= minpts:
            out[t] = np.median(v[t][c[t]])
            keep[t] = True
    return out, keep


def summarise(stack, tag="main", thr=1.5, nbin=5):
    z = load(stack, tag)
    res, nt, npt = peaks(z)
    rad = z["rad"].ravel()
    track_res = z["track_res"]
    track_ok = np.repeat(track_res <= 2.0, npt)
    nk = int(z["nk"])

    kG = 0.5 * (res["G1"]["k"] + res["G2"]["k"])
    dR = res["R"]["k"] - kG
    dB = res["B"]["k"] - kG
    null = res["G1"]["k"] - res["G2"]["k"]

    out = {"stack": stack, "tag": tag, "nframes": nk, "ntiles": int(nt),
           "npts_per_tile": int(npt), "gate_thr": thr,
           "tiles_reg_rejected": int((track_res > 2.0).sum())}

    # ---- gate ladder ------------------------------------------------------
    ladder = []
    for t in (1.1, 1.2, 1.5, 2.0, 3.0, 5.0):
        c = gate(res, t, track_ok)
        ladder.append({
            "thr": t, "n": int(c.sum()), "frac": float(c.mean()),
            "dR": float(np.median(dR[c])) if c.any() else None,
            "dB": float(np.median(dB[c])) if c.any() else None,
            "null": float(np.median(null[c])) if c.any() else None,
            "sign_dR": float((dR[c] < 0).mean()) if c.any() else None,
            "sign_null": float((null[c] < 0).mean()) if c.any() else None})
    out["gate_ladder"] = ladder

    conf = gate(res, thr, track_ok)
    out["confident_pts"] = int(conf.sum())
    out["confident_frac"] = float(conf.mean())
    if conf.sum() < 200:
        out["verdict"] = "INSUFFICIENT CONFIDENT POINTS"
        return out, None

    # ---- headline, pooled and tilewise ------------------------------------
    tR, kR_ = tilewise(dR, conf, nt, npt)
    tB, kB_ = tilewise(dB, conf, nt, npt)
    tN, kN_ = tilewise(null, conf, nt, npt)
    keep = kR_ & kB_ & kN_
    out["tiles_used"] = int(keep.sum())

    def tstat(t):
        v = t[keep]
        med = float(np.median(v))
        mad = float(np.median(np.abs(v - med))) * 1.4826
        se = mad / np.sqrt(max(len(v), 1))
        return {"median": med, "robust_sd_across_tiles": mad, "se": se,
                "n_tiles": int(len(v)),
                "p10": float(np.percentile(v, 10)),
                "p90": float(np.percentile(v, 90))}

    out["tilewise"] = {"dR": tstat(tR), "dB": tstat(tB), "null": tstat(tN)}
    out["pooled"] = {
        "dR": float(np.median(dR[conf])), "dB": float(np.median(dB[conf])),
        "null": float(np.median(null[conf])),
        "iqr_dR": [float(np.percentile(dR[conf], 25)),
                   float(np.percentile(dR[conf], 75))],
        "iqr_dB": [float(np.percentile(dB[conf], 25)),
                   float(np.percentile(dB[conf], 75))],
        "iqr_null": [float(np.percentile(null[conf], 25)),
                     float(np.percentile(null[conf], 75))]}
    out["sign"] = {
        "frac_dR_negative": float((dR[conf] < 0).mean()),
        "frac_dB_negative": float((dB[conf] < 0).mean()),
        "frac_null_negative": float((null[conf] < 0).mean()),
        "frac_tiles_dR_negative": float((tR[keep] < 0).mean()),
        "frac_tiles_dB_negative": float((tB[keep] < 0).mean()),
        "frac_tiles_null_negative": float((tN[keep] < 0).mean())}

    # ---- radial bins: the LoCA-vs-lateral discriminator -------------------
    trad = z["rad"].reshape(nt, npt).mean(axis=1)
    rk = trad[keep]
    edges = np.quantile(rk, np.linspace(0, 1, nbin + 1))
    edges[-1] += 1e-6
    bins = []
    for i in range(nbin):
        m = keep & (trad >= edges[i]) & (trad < edges[i + 1])
        if m.sum() < 2:
            continue
        pm = np.repeat(m, npt) & conf
        bins.append({
            "r_lo": float(edges[i]), "r_hi": float(edges[i + 1]),
            "r_mid": float(np.median(trad[m])),
            "n_tiles": int(m.sum()), "n_pts": int(pm.sum()),
            # RAW statistic and CONTROL side by side, same row (rule 3)
            "dR": float(np.median(tR[m])), "dB": float(np.median(tB[m])),
            "null": float(np.median(tN[m])),
            "dR_minus_null": float(np.median(tR[m]) - np.median(tN[m])),
            "dB_minus_null": float(np.median(tB[m]) - np.median(tN[m])),
            "sd_dR": float(np.median(np.abs(tR[m] - np.median(tR[m]))) * 1.4826),
            "sign_dR": float((np.repeat(m, npt) & conf).sum() and
                             (dR[pm] < 0).mean()),
            "sign_null": float((null[pm] < 0).mean())})
    out["radial_bins"] = bins

    # linear trend of dR on radius, over tiles
    if keep.sum() >= 6:
        A = np.stack([trad[keep], np.ones(keep.sum())], 1)
        for nm, arr in (("dR", tR), ("dB", tB), ("null", tN)):
            sol, *_ = np.linalg.lstsq(A, arr[keep], rcond=None)
            pred = A @ sol
            r2 = 1 - np.sum((arr[keep] - pred) ** 2) / max(
                np.sum((arr[keep] - arr[keep].mean()) ** 2), 1e-12)
            # permutation null on the slope
            rng = np.random.default_rng(7)
            obs = abs(sol[0])
            cnt = 0
            for _ in range(2000):
                p = rng.permutation(arr[keep])
                s, *_ = np.linalg.lstsq(A, p, rcond=None)
                cnt += abs(s[0]) >= obs
            out.setdefault("radial_fit", {})[nm] = {
                "slope_frames_per_planepx": float(sol[0]),
                "intercept": float(sol[1]), "r2": float(r2),
                "perm_p": float((cnt + 1) / 2001),
                "predicted_change_centre_to_corner":
                    float(sol[0] * (trad[keep].max() - trad[keep].min()))}

    # ---- what the shared election costs -----------------------------------
    loss = {}
    for c in ("R", "B", "G1"):
        F = res[c]["F"]
        at_own = interp_at(F, res[c]["k"])
        at_green = interp_at(F, kG)
        l = 1.0 - at_green / np.maximum(at_own, 1e-9)
        tl, kl = tilewise(l, conf, nt, npt)
        loss[c] = float(np.median(tl[kl & keep]))
    out["gradient_energy_forfeited"] = loss

    # ---- offsets in depth-of-field units ----------------------------------
    hw = hwhm(res["G1"]["F"], res["G1"]["k"])
    th, kh_ = tilewise(hw, conf, nt, npt)
    hwm = float(np.median(th[kh_ & keep]))
    out["through_focus_hwhm_frames"] = hwm
    out["dR_in_hwhm"] = out["tilewise"]["dR"]["median"] / hwm if hwm else None
    out["dB_in_hwhm"] = out["tilewise"]["dB"]["median"] / hwm if hwm else None

    return out, {"dR": dR, "dB": dB, "null": null, "conf": conf,
                 "rad": rad, "tR": tR, "tB": tB, "tN": tN, "keep": keep,
                 "trad": trad, "res": res, "kG": kG, "nt": nt, "npt": npt}


def show(o):
    print(f"\n===== {o['stack']} [{o['tag']}] =====")
    print(f"  {o['nframes']} frames, {o['ntiles']} tiles "
          f"({o.get('tiles_used','-')} used, {o['tiles_reg_rejected']} rejected on "
          f"registration), {o['confident_pts']} confident pts "
          f"({o['confident_frac']*100:.1f}%)")
    if "tilewise" not in o:
        print("  " + o.get("verdict", "no result"))
        return
    tw, pl = o["tilewise"], o["pooled"]
    print(f"  TILEWISE  dR = {tw['dR']['median']:+.4f} +- {tw['dR']['se']:.4f} "
          f"(sd across tiles {tw['dR']['robust_sd_across_tiles']:.4f}, "
          f"n={tw['dR']['n_tiles']})")
    print(f"            dB = {tw['dB']['median']:+.4f} +- {tw['dB']['se']:.4f}")
    print(f"            NULL(G1-G2) = {tw['null']['median']:+.4f} "
          f"+- {tw['null']['se']:.4f}")
    print(f"  POOLED    dR = {pl['dR']:+.4f}   dB = {pl['dB']:+.4f}   "
          f"NULL = {pl['null']:+.4f}")
    s = o["sign"]
    print(f"  SIGN      dR<0 {s['frac_dR_negative']*100:.1f}%   "
          f"dB<0 {s['frac_dB_negative']*100:.1f}%   "
          f"NULL<0 {s['frac_null_negative']*100:.1f}%  (null must be ~50%)")
    print(f"  LOSS      R forfeits {o['gradient_energy_forfeited']['R']*100:.2f}%  "
          f"B {o['gradient_energy_forfeited']['B']*100:.2f}%  "
          f"NULL-floor(G1) {o['gradient_energy_forfeited']['G1']*100:.2f}%")
    print(f"  HWHM {o['through_focus_hwhm_frames']:.2f} frames -> "
          f"dR = {o['dR_in_hwhm']:+.3f} HWHM, dB = {o['dB_in_hwhm']:+.3f} HWHM")
    print("  RADIAL BINS (raw beside control, same row):")
    print("    r_mid   nT   nPts     dR      dB     NULL   dR-NULL  sign_dR sign_null")
    for b in o["radial_bins"]:
        print(f"    {b['r_mid']:6.0f} {b['n_tiles']:4d} {b['n_pts']:6d} "
              f"{b['dR']:+7.4f} {b['dB']:+7.4f} {b['null']:+7.4f} "
              f"{b['dR_minus_null']:+8.4f}  {b['sign_dR']*100:5.1f}% {b['sign_null']*100:6.1f}%")
    if "radial_fit" in o:
        for nm, f in o["radial_fit"].items():
            print(f"  RADIAL FIT {nm:4s}: slope {f['slope_frames_per_planepx']:+.3e} "
                  f"frames/px, R2 {f['r2']:.4f}, perm p {f['perm_p']:.4f}, "
                  f"centre->corner {f['predicted_change_centre_to_corner']:+.4f} frames")


if __name__ == "__main__":
    stacks = sys.argv[1:] or ["lavendar-cpl", "coffee-bean",
                              "couch-fibers-cpl", "bee-2-cpl"]
    allout = []
    for s in stacks:
        try:
            o, _ = summarise(s)
        except FileNotFoundError:
            print(f"  (no data yet for {s})")
            continue
        show(o)
        allout.append(o)
    dump("b2_summary", allout)
