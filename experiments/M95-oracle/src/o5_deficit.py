"""O5 -- the measurement. Does the election pick the sharpest frame available?

B1 passed at 81.9 % (o4), so the modelled elector is admissible as a stand-in
for the shipped one and an election offset may be reported.

THE STATISTIC, pre-registered in docs/research/M95-election-quality.md B4:

    D = 1 - mean_p O_G2( e1(p), p ) / mean_p O_G2( o1(p), p )

  e1 = argmax_f  elector_score(G1)     rectified magnitude / sigma  (the product's rule)
  o1 = argmax_f  oracle_score(G1)      noise-subtracted gradient ENERGY
  both scored on G2, which neither used to choose.

Sign convention is not assumed: o3's P1s control read it off a forced offset and
found POSITIVE D = worse choice. That control is repeated here on the real
capture as P1r, because a control that only ever ran on synthetic data has not
been shown to work on the thing being measured.

Two passes to keep memory bounded. Pass 1 takes running argmaxes over 299 frames
so no full score cube is ever held. Pass 2 recomputes O_G2 frame by frame and
gathers it at whichever frame each rule chose.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "M95-merge-vs-frame", "src"))
import m95lib as L  # noqa: E402
import o2lib as O  # noqa: E402
from o3_commission import CUBE, OUTD  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROIS = ["ROI-LOWDRIFT", "ROI-MIDDRIFT", "ROI-HIGHDRIFT", "ROI-FLAT"]
FORCED = [1, 2, 5, 10, 25]
PLANE_PITCH_UM = 10.2162


def argmaxes(cube, noise, n):
    """Running argmax of both rules over the whole stack. No score cube retained."""
    be = bo = None
    ae = ao = None
    for f in range(n):
        img = cube[f].astype(np.float64)
        se = O.elector_score(img, noise)
        so = O.oracle_score(img, noise)
        if be is None:
            be, bo = se.copy(), so.copy()
            ae = np.zeros(se.shape, dtype=np.int32)
            ao = np.zeros(so.shape, dtype=np.int32)
        else:
            m = se > be
            be[m] = se[m]
            ae[m] = f
            m = so > bo
            bo[m] = so[m]
            ao[m] = f
    return ae, ao


def gather(cube_ev, noise, n, picks):
    """One pass over G2, gathering the oracle score at each rule's chosen frame."""
    out = {k: np.zeros(next(iter(picks.values())).shape, dtype=np.float64) for k in picks}
    for f in range(n):
        s = O.oracle_score(cube_ev[f].astype(np.float64), noise)
        for k, idxmap in picks.items():
            m = idxmap == f
            if m.any():
                out[k][m] = s[m]
    return out


def gather_pixels(cube_ev, n, picks, k):
    """Gather raw G2 pixel values at each rule's chosen frame, for the mosaics."""
    out = {kk: np.zeros(next(iter(picks.values())).shape, dtype=np.float64) for kk in picks}
    for f in range(n):
        img = cube_ev[f].astype(np.float64)[k:, k:]
        for kk, idxmap in picks.items():
            m = idxmap == f
            if m.any():
                sub = img[:idxmap.shape[0], :idxmap.shape[1]]
                out[kk][m] = sub[m]
    return out


def main() -> int:
    meta = json.load(open(os.path.join(CUBE, "cube_meta.json"), encoding="utf-8"))
    n, black = meta["n"], meta["black"]

    f1 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g1.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    f2 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g2.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    noise, fit = O.fit_noise(f1.reshape(-1, f1.shape[-1]), f2.reshape(-1, f2.shape[-1]), black)
    print(f"noise model: {noise}  R^2={fit['r2']:.5f}")
    del f1, f2

    res = {"noise": dict(gain=noise.gain, floor=noise.floor, r2=fit["r2"]), "rois": {}}
    k = 1 + O.BOX_R

    for nm in ROIS:
        print("\n" + "=" * 74)
        print(nm)
        g1 = np.load(os.path.join(CUBE, f"{nm}.g1.npy"), mmap_mode="r")
        g2 = np.load(os.path.join(CUBE, f"{nm}.g2.npy"), mmap_mode="r")

        ae, ao = argmaxes(g1, noise, n)
        picks = {"elector": ae, "oracle": ao}
        for off in FORCED:
            picks[f"forced+{off}"] = np.clip(ao + off, 0, n - 1)
            picks[f"forced-{off}"] = np.clip(ao - off, 0, n - 1)
        ev = gather(g2, noise, n, picks)

        base = float(ev["oracle"].mean())
        d_el = 1.0 - float(ev["elector"].mean()) / base
        off = ae.astype(np.int32) - ao.astype(np.int32)
        same = float(np.mean(off == 0)) * 100.0
        w1 = float(np.mean(np.abs(off) <= 1)) * 100.0
        print(f"  elector == oracle        : {same:.4f} %")
        print(f"  within +/-1 frame        : {w1:.4f} %")
        print(f"  |offset| mean {np.abs(off).mean():.3f}  median "
              f"{np.median(np.abs(off)):.1f}  p90 {np.percentile(np.abs(off),90):.1f}")
        print(f"  D (elector vs oracle)    : {d_el*100:+.4f} %")

        print("  P1r  power control on the REAL capture (forced offsets):")
        prow = []
        for o2 in FORCED:
            dp = 1.0 - float(ev[f"forced+{o2}"].mean()) / base
            dm = 1.0 - float(ev[f"forced-{o2}"].mean()) / base
            prow.append(dict(offset=o2, D_plus=dp * 100.0, D_minus=dm * 100.0))
            print(f"      +/-{o2:2d} frames -> D = {dp*100:+8.4f} % / {dm*100:+8.4f} %")
        seq = [r["D_plus"] for r in prow]
        mono = all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))
        d1 = seq[0]
        print(f"      monotone: {mono}   one-frame sensitivity: {d1:+.4f} %")

        # Mosaics on the evaluation channel: what each rule would have emitted.
        px = gather_pixels(g2, n, picks, k)
        c = 512
        y0 = (px["elector"].shape[0] - c) // 2
        x0 = (px["elector"].shape[1] - c) // 2
        me = px["elector"][y0:y0 + c, x0:x0 + c]
        mo = px["oracle"][y0:y0 + c, x0:x0 + c]
        fr, pe, _ = L.radial_psd(me)
        _, po, _ = L.radial_psd(mo)
        bands = {}
        for lo, hi, lab in ((0.10, 0.20, "0.10-0.20"), (0.20, 0.30, "0.20-0.30"),
                            (0.30, 0.40, "0.30-0.40"), (0.40, 0.50, "0.40-0.50")):
            be_ = L.band_power(fr, pe, lo, hi)
            bo_ = L.band_power(fr, po, lo, hi)
            cy = 0.5 * (lo + hi) / (PLANE_PITCH_UM * 1e-3)
            bands[lab] = dict(elector=be_, oracle=bo_, ratio=be_ / bo_,
                              cy_per_mm=cy,
                              amp_pct=100.0 * (np.sqrt(be_ / bo_) - 1.0))
            print(f"  band {lab} cyc/px ({cy:5.1f} cy/mm): elector/oracle power "
                  f"{be_/bo_:.4f}  amplitude {100.0*(np.sqrt(be_/bo_)-1.0):+.2f} %")

        res["rois"][nm] = dict(
            D_pct=d_el * 100.0, same_pct=same, within1_pct=w1,
            mean_abs_off=float(np.abs(off).mean()),
            median_abs_off=float(np.median(np.abs(off))),
            p90_abs_off=float(np.percentile(np.abs(off), 90)),
            signed_mean_off=float(off.mean()),
            p1r=prow, p1r_monotone=bool(mono), one_frame_sens_pct=d1,
            bands=bands, n_px=int(off.size))
        del g1, g2, ev, px

    print("\n" + "=" * 74)
    print("SENSITIVITY: does the conclusion rest on the fitted noise model?")
    g1 = np.load(os.path.join(CUBE, "ROI-LOWDRIFT.g1.npy"), mmap_mode="r")
    g2 = np.load(os.path.join(CUBE, "ROI-LOWDRIFT.g2.npy"), mmap_mode="r")
    sens = []
    for mult in (0.8, 1.0, 1.25):
        nz = O.Noise(noise.gain * mult, noise.floor, black)
        ae, ao = argmaxes(g1, nz, n)
        ev = gather(g2, nz, n, {"e": ae, "o": ao})
        d = (1.0 - float(ev["e"].mean()) / float(ev["o"].mean())) * 100.0
        sens.append(dict(gain_mult=mult, D_pct=d))
        print(f"  gain x{mult:.2f} -> D = {d:+.4f} %")
    res["sensitivity"] = sens

    print("\n" + "=" * 74)
    det = [res["rois"][r]["D_pct"] for r in ROIS if r != "ROI-FLAT"]
    flat = res["rois"]["ROI-FLAT"]["D_pct"]
    print(f"detail ROIs D = {['%+.4f %%' % d for d in det]}")
    print(f"flat control D = {flat:+.4f} %")
    allmono = all(res["rois"][r]["p1r_monotone"] for r in ROIS if r != "ROI-FLAT")
    if all(d > 5.0 for d in det) and abs(flat) < 1.0 and allmono:
        verdict = "ELECTION IS LOSING SHARPNESS"
    elif all(d < 1.0 for d in det) and allmono:
        verdict = "ELECTION IS SOUND"
    else:
        verdict = "INCONCLUSIVE-BUT-BOUNDED"
    print(f"B4 VERDICT: {verdict}")
    res["verdict"] = verdict
    with open(os.path.join(OUTD, "o5_deficit.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"wrote {os.path.join(OUTD, 'o5_deficit.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
