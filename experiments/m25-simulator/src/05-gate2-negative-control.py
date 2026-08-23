"""05 -- Gate 2: the negative control ON THE SIMULATOR ITSELF.

A validation suite that cannot fail is not a validation suite.  This
deliberately mis-specifies the physics and asks whether Gate 1's statistics
move outside the tolerance Gate 1 passed at.  Every outcome is reported --
especially the mis-specifications Gate 1 turns out to be *blind* to, because
those delimit exactly what Gate 1 is evidence for.

The baseline uses the MEASURED scene placement from
`06-gate1b-measured-placement.py` (focus peak frame, per-frame level series,
level, sd) on m9's ROI `2272,1344`, so that the baseline passes and the
control is interpretable.

Mis-specifications:

  NC-A  gain 2x.  The DN level is held at the real ROI's and the electron
        budget re-derived from the MIS-STATED gain -- exactly the error a
        mis-calibrated `g` causes in practice: you believe you have half the
        electrons you have, so you model 1.41x too much shot noise and the
        render produces it.
  NC-B  no diffraction.  Drop the term that dominates at fine scales on this
        rig (N_eff = 33).
  NC-C  spatially correlated noise: the same per-pixel variance, passed
        through a 3x3 binomial within each Bayer plane.  The right amount of
        noise with the wrong independence structure -- aimed squarely at
        fact 35's mechanism, which is that a pixel's OWN noise votes for its
        own selection.
  NC-D  no noise at all.  The floor: excess must vanish.

Every variant is re-calibrated so the rendered ROI's sd still matches the real
ROI's.  That is the hard version of the control: wrong physics that has been
tuned to look right on the summary statistics.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/05-gate2-negative-control.py
"""

from __future__ import annotations

import collections
import csv
import os
import sys
import time

import numpy as np
from scipy import ndimage, stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.render import render_stack                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "gate2-negative-control.txt")
M9CSV = os.path.join(HERE, "..", "..", "m9-support", "data",
                     "sweep-109MSDCF-coupled.csv")
REAL = r"C:\dev\macro\test\109MSDCF"
ROI = "2272,1344"
ROI_HW = 256
WIDTHS = [1, 3, 5, 7, 9, 13, 17, 21, 25, 33, 41, 49, 65, 81, 97]
SUPERSAMPLE = 3
COC = 1.5                     # fitted in 06 against the through-focus sd curve
SEED = 1

TOL_RHO_PHI = 0.70
TOL_TEN_W0 = 0.02
TOL_EXCESS_MAD = 0.05         # median |sim - real| over the 16 measures
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def real_single_roi():
    by = collections.defaultdict(dict)
    for r in csv.DictReader(open(M9CSV)):
        if r["roi"] != f"{ROI},{ROI_HW},{ROI_HW}":
            continue
        by[r["measure"]][int(r["width"])] = float(r["ratio"])
    out = {}
    for m, d in by.items():
        fl = min(v for w, v in d.items() if w <= max(WIDTHS))
        out[m] = dict(c1=d[1], floor=fl, excess=d[1] - fl, w17=d[17])
    return out


def correlate_noise(noisy, clean):
    """Same per-pixel variance, 3x3-binomial correlated, per Bayer plane.
    Correlating across the Bayer grid would mix colour planes and be a
    different (and duller) error."""
    out = noisy.astype(np.float64).copy()
    k = np.outer([1.0, 2.0, 1.0], [1.0, 2.0, 1.0])
    k /= k.sum()
    scale = 1.0 / np.sqrt((k ** 2).sum())
    for dy in (0, 1):
        for dx in (0, 1):
            r = noisy[dy::2, dx::2].astype(np.float64) - clean[dy::2, dx::2]
            f = ndimage.convolve(r, k, mode="reflect") * scale
            out[dy::2, dx::2] = clean[dy::2, dx::2] + f
    return np.clip(np.rint(out), 0, 15360).astype(np.uint16)


def analyse(frames, iso, margin, sweep_margin, phi_margin, reach, real):
    roi = S.Roi(margin, margin, ROI_HW, ROI_HW)
    luma, val = S.tiles(frames, roi, margin)
    nm = F.NoiseModel.for_iso(iso)
    o = margin - sweep_margin
    sl = luma[:, o:luma.shape[1] - o, o:luma.shape[2] - o]
    o2 = margin - phi_margin
    pl = luma[:, o2:luma.shape[1] - o2, o2:luma.shape[2] - o2]
    single = val[val.shape[0] // 2]
    phis, exc, sup, dex = [], [], [], []
    tenw0 = None
    for m in F.design(False):
        _, _, phi, _ = F.phi_for(m, pl, nm, reach)
        rows = F.sweep_measure(m, sl, val, single, nm, sweep_margin, WIDTHS)
        rr = np.array([r["ratio"] for r in rows])
        e = float(rr[0] - rr.min())
        phis.append(phi)
        exc.append(e)
        sup.append(m.support_radius)
        dex.append(abs(e - real[m.name]["excess"]))
        if m.name == "tenengrad-w0":
            tenw0 = (float(rr[0]), e)
    rp = stats.spearmanr(phis, exc)
    rs = stats.spearmanr(sup, exc)
    er = np.array([real[m.name]["excess"] for m in F.design(False)])
    return dict(rho_phi=float(rp.statistic), p_phi=float(rp.pvalue),
                rho_sup=float(rs.statistic), p_sup=float(rs.pvalue),
                ten_c1=tenw0[0], ten_exc=tenw0[1],
                excess_mad=float(np.median(dex)),
                excess_slope=float(np.polyfit(er, np.array(exc), 1)[0]),
                sd=float(single.std()), mean=float(single.mean()))


def score(r):
    return (r["rho_phi"] >= TOL_RHO_PHI and r["p_phi"] < 0.05,
            r["ten_exc"] < TOL_TEN_W0,
            r["excess_mad"] <= TOL_EXCESS_MAD)


def main():
    t0 = time.time()
    say("Gate 2 -- negative control on the simulator itself")
    say()
    reach = F.max_support(F.design(True))
    sweep_margin = max((x - 1) // 2 for x in WIDTHS) + reach
    phi_margin = 4 * reach + 2
    margin = max(sweep_margin, phi_margin)
    tile = ROI_HW + 2 * margin

    raw = S.load_real(REAL)
    iso = S.iso_of(REAL)
    K = raw.shape[0]
    nm = F.NoiseModel.for_iso(iso)
    x, y = (int(v) for v in ROI.split(","))
    luma_r, val_r = S.tiles(raw, S.Roi(x, y, ROI_HW, ROI_HW), margin)
    m13 = [m for m in F.design(False) if m.name == "ring-1-3"][0]
    fr = np.array([m13.compute(luma_r[k], nm)[margin:-margin,
                                              margin:-margin].mean()
                   for k in range(K)])
    peak = int(np.argmax(fr))
    level = np.array([val_r[k].mean() for k in range(K)])
    ref = val_r[K // 2]
    del raw, luma_r, val_r
    beta = B.fit_beta(ref)
    real = real_single_roi()
    say(f"real ROI {ROI}: mean {ref.mean():.2f} DN, sd {ref.std():.4f} DN, "
        f"focus peak frame {peak}, beta {beta:.3f}")
    say(f"gates: rho(phi,excess) >= {TOL_RHO_PHI} at p<0.05; "
        f"tenengrad-w0 excess < {TOL_TEN_W0}; "
        f"median |excess_sim - excess_real| <= {TOL_EXCESS_MAD}")
    say(f"real single-ROI excesses span "
        f"{min(v['excess'] for v in real.values()):.4f} .. "
        f"{max(v['excess'] for v in real.values()):.4f}")
    say()

    B.set_supersample(SUPERSAMPLE)
    hw = (2 * tile, 2 * tile)
    gain = level / level[K // 2]
    mean_dn = float(ref.mean())
    sd_dn = float(ref.std())

    def make(**kw):
        c = B.cfg_109(COC, n_frames=K, seed=SEED, channels="green")
        for k, v in kw.items():
            setattr(c, k, v)
        return c

    variants = {
        "baseline": make(),
        "NC-A gain 2x": make(gain_dn_per_e=2.0 * nm.gain_dn_per_e),
        "NC-B no diffraction": make(with_diffraction=False),
        "NC-C correlated noise": make(),
        "NC-D no noise": make(shot=False, read=False, fpn=False),
    }

    rows = {}
    for name, vcfg in variants.items():
        tr = time.time()
        g_eff = vcfg.gain_dn_per_e or nm.gain_dn_per_e
        b_e = mean_dn / g_eff
        nv = 0.5 * (g_eff * mean_dn + (nm.read_noise_e * g_eff) ** 2)
        ce = np.sqrt(max(sd_dn ** 2 - nv, 1.0)) / g_eff
        st = sc = None
        for _ in range(2):                     # one contrast-correcting pass
            sc = B.flat_scene(vcfg, hw, b_e, ce, beta, focus_index=float(peak),
                              seed=201)
            st = render_stack(sc, vcfg, gain_series=gain)
            got = float(S.green_value(st.frames[K // 2]).std())
            ce *= np.sqrt(max(sd_dn ** 2 - nv, 1.0)
                          / max(got ** 2 - nv, 1.0))
        frames = st.frames
        if name.startswith("NC-C"):
            cc = make(shot=False, read=False, fpn=False)
            clean = render_stack(sc, cc, gain_series=gain).frames.astype(float)
            frames = np.stack([correlate_noise(frames[k], clean[k])
                               for k in range(K)])
        r = analyse(frames, iso, margin, sweep_margin, phi_margin, reach, real)
        r["secs"] = time.time() - tr
        rows[name] = r
        aa, bb, cc_ = score(r)
        say(f"{name:<22} mean {r['mean']:7.2f} sd {r['sd']:7.4f}  "
            f"rho_phi {r['rho_phi']:+.3f} (p {r['p_phi']:.4f})  "
            f"tenw0 c(1) {r['ten_c1']:.4f} exc {r['ten_exc']:.4f}  "
            f"excess MAD {r['excess_mad']:.4f} slope {r['excess_slope']:.3f}"
            f"  [{r['secs']:.0f}s]")
        say(f"{'':<22} axes: phi {'ok' if aa else 'FIRED'}, "
            f"zero-tap {'ok' if bb else 'FIRED'}, "
            f"excess-level {'ok' if cc_ else 'FIRED'}")

    say()
    say("=" * 78)
    say(f"  {'variant':<22} {'phi':>6} {'zerotap':>8} {'exc-lvl':>8}  fired?")
    fired = {}
    for name, r in rows.items():
        aa, bb, cc_ = score(r)
        fired[name] = not (aa and bb and cc_)
        say(f"  {name:<22} {'ok' if aa else 'FIRE':>6} "
            f"{'ok' if bb else 'FIRE':>8} {'ok' if cc_ else 'FIRE':>8}  "
            f"{'YES' if fired[name] else 'no'}")
    n_nc = sum(1 for k in rows if k != "baseline")
    n_fire = sum(1 for k, v in fired.items() if k != "baseline" and v)
    say()
    say(f"{n_fire} of {n_nc} mis-specifications fired.")
    if fired["baseline"]:
        say("WARNING: the BASELINE failed its own gate -- Gate 2 is "
            "uninterpretable until that is fixed.")
    blind = [k for k, v in fired.items() if k != "baseline" and not v]
    if blind:
        say("BLIND SPOTS -- Gate 1 did NOT catch these, so Gate 1 is not "
            "evidence about them:")
        for k in blind:
            say(f"  * {k}")
    else:
        say("No blind spots among the four.")
    verdict = "PASS" if n_fire >= 1 and not fired["baseline"] else "FAIL"
    say(f"GATE 2: {verdict} ({n_fire}/{n_nc} fired)  [{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
        keys = ["mean", "sd", "rho_phi", "p_phi", "rho_sup", "p_sup",
                "ten_c1", "ten_exc", "excess_mad", "excess_slope"]
        fh.write("\ncsv\nvariant," + ",".join(keys) + "\n")
        for name, r in rows.items():
            fh.write(name + "," + ",".join(f"{r[k]}" for k in keys) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
