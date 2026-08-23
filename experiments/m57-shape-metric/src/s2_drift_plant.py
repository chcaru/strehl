"""M57 S2 -- PR5: a plant whose two half-merges deliver DIFFERENT LATENTS.

Discipline 340 / rule 34: every plant in `m46lib` draws both half-images from
ONE latent object, so latent drift is exactly 0 and swap asymmetry exactly 1 by
construction.  Such a plant cannot validate a metric whose largest real-data
confound is latent drift.  This one can, because it is an actual focus stack:

    depth map z(x) -> per-frame, per-pixel blur sigma_k(x) = rate*|z(x) - z_k|
    Y_k = blur_sigma_k(x)(L) + FPN + N_k
    the merge is m41lib's arm A, so each half-stack ELECTS ITS OWN WINNERS and
    delivers its own latent.

Ground truth exists here and is used ONLY as an oracle positive control, never
as an input to any candidate:

    sigma_true(M) = the equivalent-Gaussian width of the transfer from L to M,
    fitted as the WLS slope of log[ Re<M conj L>_ring / <|L|^2>_ring ] on
    -2 pi^2 f^2.   (One power of H, not two, because this is a
    signal-to-truth cross-power rather than a pair cross-power.)

RULE 20 -- what makes this gate FAIL.  If the plant produced no drift, the
oracle's two half-merge latents would be identical and `drift_frc` would read
1.0; it is printed so that "the plant can express the failure" is checked
rather than asserted.  If dsig reported a blur where truth says none, PR5
kills K1.

RULE 13 -- can the plant express an interior failure?  The depth map contains
a TILT and a STEP, so different halves elect different winners at the step and
the delivered latent genuinely differs between halves.  A fronto-parallel plant
could not.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m57lib as K  # noqa: E402

N = 512
PAD = 32
NF = 32
SIG_GRID = np.linspace(0.0, 6.0, 25)


def blur_stack(img):
    return np.stack([K.M.blur(img, float(s)) for s in SIG_GRID])


def varblur(stack, sig_map):
    """Spatially varying Gaussian blur by interpolation on a sigma grid."""
    idx = np.clip(np.searchsorted(SIG_GRID, sig_map) - 1, 0, len(SIG_GRID) - 2)
    s0 = SIG_GRID[idx]
    s1 = SIG_GRID[idx + 1]
    t = np.clip((sig_map - s0) / (s1 - s0), 0.0, 1.0)
    lo = np.take_along_axis(stack, idx[None], 0)[0]
    hi = np.take_along_axis(stack, (idx + 1)[None], 0)[0]
    return ((1.0 - t) * lo + t * hi).astype(np.float32)


def make_stack(latent, depth, fpn, sigma_n, rate, seed, nf=NF):
    """A focus bracket over the depth map.  Each frame blurs every pixel by
    rate*|z(x) - z_k|, so no two frames share a latent and no half-stack can."""
    rng = np.random.default_rng(seed)
    zs = np.linspace(0.0, 1.0, nf)
    stack = blur_stack(latent)
    cube = np.empty((nf, latent.shape[0], latent.shape[1]), np.float32)
    for k, zk in enumerate(zs):
        cube[k] = varblur(stack, rate * np.abs(depth - zk)) + fpn \
            + rng.standard_normal(latent.shape).astype(np.float32) * sigma_n
    return cube


def oracle_sigma(m, latent):
    """Equivalent-Gaussian width of the transfer L -> m, in px.  ORACLE."""
    A, B = K.spectra(m, latent)
    lab, f, cnt_s, nr = K.ring_grid(m.shape[0])
    sel = lab >= 0
    ll = lab[sel]
    nz = nr * K.N_SECT
    x = (A.real * B.real + A.imag * B.imag)[sel]
    p = (np.abs(B) ** 2)[sel]
    num = np.bincount(ll, weights=x, minlength=nz).reshape(nr, -1).sum(1)
    den = np.bincount(ll, weights=p, minlength=nz).reshape(nr, -1).sum(1)
    t = num / den
    idx = K.band_index(f)
    if np.any(t[idx] <= 0):
        return np.nan
    y = np.log(t[idx])
    xx = -2.0 * np.pi ** 2 * f[idx] ** 2
    xm = xx - xx.mean()
    b = float((xm * y).sum() / (xm * xm).sum())
    return float(np.sign(b) * np.sqrt(abs(b)))


def main():
    t0 = time.time()
    m46out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "m46-detail-metric", "out")
    z = np.load(os.path.join(m46out, "b1_merges.npz"))
    b1 = json.load(open(os.path.join(m46out, "b1_results.json")))
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
    ne_f = b1["n_eff"]["112_flat"]
    rho = b1["twocap"]["flat"]["at_fsig"] / (1 - b1["twocap"]["flat"]["at_fsig"]) / ne_f

    full = z["d112"].astype(np.float32)                 # 576x576, includes pad
    latent = full[:N + 2 * PAD, :N + 2 * PAD] if full.shape[0] >= N + 2 * PAD \
        else np.pad(full, ((0, N + 2 * PAD - full.shape[0]),) * 2, mode="reflect")
    h = latent.shape[0]
    yy, xx = np.mgrid[0:h, 0:h]
    # RULE 13: a TILT plus a STEP.  A fronto-parallel plant would give every
    # half the same winners and could not express drift.
    depth = (xx / (h - 1.0)).astype(np.float32) * 0.8
    depth[yy > h // 2] += 0.2
    depth = np.clip(depth, 0.0, 1.0)

    lvl = float(np.median(latent))
    sig1 = float(np.sqrt(K.M.noise_var_dn(lvl, g, rn_e)))
    fpn = K.M.make_fpn(latent.shape, 20260823, np.sqrt(rho) * sig1)

    print("=" * 78)
    print("M57 S2 -- PR5: LATENT-DRIFT PLANT (discipline 340 / rule 34)")
    print("=" * 78)
    print(f"  latent {latent.shape}, depth = tilt 0..0.8 + a 0.2 step at y = h/2")
    print(f"  {NF} frames, single-frame sigma {sig1:.3f} DN, rho {rho:.4f}")
    res = {"rho": rho, "nf": NF, "sig1": sig1}

    for rate in (0.0, 1.5, 3.0, 6.0):
        cube = make_stack(latent, depth, fpn, sig1, rate, seed=808)
        fine, coarse, reg = K.L1.focus_fields(cube, g, rn_e)
        q = K.quads(NF)
        pa = np.sort(np.concatenate([q[0], q[2]]))
        pb = np.sort(np.concatenate([q[1], q[3]]))
        na = np.sort(np.concatenate([q[0], q[3]]))
        nb = np.sort(np.concatenate([q[1], q[2]]))
        ma, nea = K.merge_subset(cube, coarse, reg, pa, pad=PAD)
        mb, neb = K.merge_subset(cube, coarse, reg, pb, pad=PAD)
        n_a, _ = K.merge_subset(cube, coarse, reg, na, pad=PAD)
        n_b, _ = K.merge_subset(cube, coarse, reg, nb, pad=PAD)
        lat_c = latent[PAD:-PAD, PAD:-PAD]

        # can the plant express the failure?  (rule 20)
        drift = float(np.sqrt(np.mean((ma - mb) ** 2)))
        rs_pair = K.RingStats(ma, mb)
        frc_pair = float(rs_pair.frc()[rs_pair.at(K.F_SIG)[1]])
        sa, sb_ = oracle_sigma(ma, lat_c), oracle_sigma(mb, lat_c)
        pa_p = float(np.mean(np.abs(K.spectra(ma, mb)[0]) ** 2))
        pb_p = float(np.mean(np.abs(K.spectra(ma, mb)[1]) ** 2))
        print(f"\n  --- blur rate {rate:.2f} px per unit depth "
              f"(max defocus {rate:.2f} px) ---")
        print(f"    half-merge RMS difference {drift:8.4f} DN "
              f"(a fixed-latent plant gives only the noise term)")
        print(f"    FRC(f_sig) between halves {frc_pair:+.6f}   "
              f"P_a/P_b = {pa_p/pb_p:.5f}  (fact 701 measures 1.30 on real data)")
        print(f"    ORACLE sigma of half A vs truth {sa:+.5f} px, "
              f"half B {sb_:+.5f} px, |difference| {abs(sa-sb_):.5f} px")

        # ---- PR5 proper: no planted blur, only the pairing changes ---------
        rs1 = K.RingStats(ma, mb)
        rs_null = K.RingStats(n_a, n_b)
        dnull = K.dsig(rs1, rs_null)
        # Is that a NULL, or a real difference?  The oracle decides.  A
        # four-way re-pairing keeps every frame but changes the DEPTH
        # SAMPLING of each half (fact 641's mechanism), so truth need not be
        # zero and dsig must not be blamed for reporting it.
        # DERIVED: C = T_a T_b S, so dsig^2 estimates the change in the PAIR
        # width (sig_a^2 + sig_b^2)/2, not one half's.  The oracle must use
        # both halves or it is measuring a different quantity.
        o_na, o_nb = oracle_sigma(n_a, lat_c), oracle_sigma(n_b, lat_c)
        pair1 = 0.5 * (sa ** 2 + sb_ ** 2)
        pair2 = 0.5 * (o_na ** 2 + o_nb ** 2)
        o_null = float(np.sign(pair2 - pair1) * np.sqrt(abs(pair2 - pair1)))
        # A null that CAN fail (rule 39): the SAME merge pair, read on two
        # disjoint 256-px sub-ROIs.  Truth is 0 only if the field is
        # stationary, so a non-zero reading is informative rather than a bug.
        hh = ma.shape[0] // 2
        dtrue = K.dsig(K.RingStats(ma[:hh, :hh], mb[:hh, :hh]),
                       K.RingStats(ma[hh:, hh:], mb[hh:, hh:]))
        # ---- positive control: plant a known blur on config 2 --------------
        rows = {}
        print("    planted sb   dsig px    se(jack)   ORACLE d-sigma px   error px")
        for sb in (0.0, 0.05, 0.10, 0.25):
            t_a, t_b = K.M.blur(ma, sb), K.M.blur(mb, sb)
            d = K.dsig(rs1, K.RingStats(t_a, t_b))
            o = oracle_sigma(t_a, lat_c)
            # oracle delta in equivalent-Gaussian px, quadrature-free because
            # the fit is linear in sigma^2
            od = float(np.sign(o ** 2 - sa ** 2) * np.sqrt(abs(o ** 2 - sa ** 2)))
            print(f"    {sb:10.3f}   {d['px']:+8.5f}   {d['se_px']:8.2e}   "
                  f"{od:+16.5f}   {d['px'] - od:+8.5f}")
            rows[f"{sb}"] = dict(dsig=d["px"], se=d["se_px"], oracle=od)
        print(f"    RE-PAIRING (four-way, all frames, truth NOT guaranteed 0):"
              f"  dsig {dnull['px']:+.5f} +- {dnull['se_px']:.2e}   "
              f"ORACLE says {o_null:+.5f}   error {dnull['px'] - o_null:+.5f}")
        print(f"    TRUE NULL (same merge pair, two disjoint sub-ROIs):      "
              f"  dsig {dtrue['px']:+.5f} +- {dtrue['se_px']:.2e}   "
              f"-> {abs(dtrue['px'])/max(dtrue['se_px'],1e-12):5.1f} se from zero")
        res[f"rate_{rate}"] = dict(drift=drift, frc=frc_pair, oracle_a=sa,
                                   oracle_b=sb_, pa_over_pb=pa_p / pb_p,
                                   repair=dnull, repair_oracle=o_null,
                                   true_null=dtrue, planted=rows)

    # ------------------------------------------------------------------
    # PR5's sharpest case: the merge CONFIGURATION changes the drift.
    # Two gates on the same stack -- a wide gate averages frames at different
    # depths (real blur) and a narrow gate selects (no averaging blur, more
    # noise).  Truth from the oracle; dsig must track truth, not the drift.
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("PR5b -- the configuration itself changes the delivered latent.")
    print("        gate sweep on the drift plant, dsig vs the ORACLE.")
    print("=" * 78)
    cube = make_stack(latent, depth, fpn, sig1, 3.0, seed=808)
    fine, coarse, reg = K.L1.focus_fields(cube, g, rn_e)
    q = K.quads(NF)
    pa = np.sort(np.concatenate([q[0], q[2]]))
    pb = np.sort(np.concatenate([q[1], q[3]]))
    lat_c = latent[PAD:-PAD, PAD:-PAD]
    ref = None
    print("     gate   n_eff    ORACLE sigma px   dsig vs gate 0.50 px   se(jack)"
          "   ORACLE delta px")
    gates = {}
    for gate in (0.0, 0.25, 0.50, 0.75, 0.90, 0.99):
        ma, nea = K.merge_subset(cube, coarse, reg, pa, pad=PAD, gate=gate)
        mb, _ = K.merge_subset(cube, coarse, reg, pb, pad=PAD, gate=gate)
        rs = K.RingStats(ma, mb)
        o = oracle_sigma(ma, lat_c)
        if abs(gate - 0.50) < 1e-9:
            ref = (rs, o)
        gates[f"{gate}"] = dict(n_eff=nea, oracle=o, rs=rs)
    for gate in (0.0, 0.25, 0.50, 0.75, 0.90, 0.99):
        e = gates[f"{gate}"]
        d = K.dsig(ref[0], e["rs"])
        od = float(np.sign(e["oracle"] ** 2 - ref[1] ** 2)
                   * np.sqrt(abs(e["oracle"] ** 2 - ref[1] ** 2)))
        print(f"     {gate:5.2f}  {e['n_eff']:6.3f}   {e['oracle']:+15.5f}   "
              f"{d['px']:+21.5f}   {d['se_px']:8.2e}   {od:+15.5f}")
        e.pop("rs")
        e["dsig"] = d["px"]
        e["se"] = d["se_px"]
        e["oracle_delta"] = od
    res["pr5b_gate"] = gates

    with open(os.path.join(K.OUT, "s2_drift.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/s2_drift.json  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
