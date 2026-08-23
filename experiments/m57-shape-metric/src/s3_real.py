"""M57 S3 -- the candidates on REAL macro stacks.

Covers PR4 (split leverage), PR6 (planted-blur recovery against a null that can
fail), PR7 (one-sided photometric gain as it actually arises), and the gate
sweep that is the shipped question.

RULE 9: the flat ROI of every stack is run FIRST, before its detail ROI.
PR24 of M55 fixes the ROIs in advance and they are reused unchanged here so
that no ROI is chosen on its result.

RULE 39 -- the null.  A four-way re-pairing is NOT a null: S2 measured truth
moving +0.062 px under one, and the oracle agreed with dsig to 0.00035 px.  The
null used here is the DISJOINT-SUBSET null: config 1 merges frames = 0,1 mod 4
split (0 mod 4 | 1 mod 4); config 2 merges frames = 2,3 mod 4 split
(2 mod 4 | 3 mod 4).  Both configurations use half the frames, both halves have
identical depth spacing (period 4) and identical within-config offset (1
frame), so truth is zero up to a depth translation.  It CAN fail -- and it
fails loudly if the stack is not depth-stationary, which is information.

RULE 20 -- what makes this gate FAIL.  A planted 0.10 px blur must be recovered
to within 30% on every stack and both ROIs, the null must sit within 3 SE of
zero, and the spread across split rules must be smaller than the planted
signal.  Any one of those failing kills K1 on real data.
"""
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m57lib as K  # noqa: E402

ROOT = r"D:\personal\macro"
PAD = 32
G, RN_E = 1.14469, 1.47          # m41lib's frozen pair, kept for comparability
PLANT_SB = 0.10                  # PR6's planted blur, fixed before any run

STACKS = {
    "112MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "detail": (1671, 1373, 512, 512)}, lo=6, hi=68),
    "113MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=63),
    "foam":     dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=62),
    "109MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=22),
}


def mod4_null(nf):
    """Two configurations with identical depth spacing and identical
    within-configuration offset.  Truth is zero up to a depth translation."""
    i = np.arange(nf)
    return (i[0::4], i[1::4]), (i[2::4], i[3::4])


def main():
    t0 = time.time()
    res = {}
    print("=" * 78)
    print("M57 S3 -- real macro stacks.  Flat ROI first (rule 9).")
    print(f"  band [{K.F_LO}, {K.F_HI:.4f}] cyc/px, nbin {K.NBIN}, "
          f"planted blur {PLANT_SB} px -- all fixed before this ran (PR11)")
    print("=" * 78)

    for sname, cfg in STACKS.items():
        files = sorted(glob.glob(os.path.join(ROOT, sname, "*.ARW")))
        files = files[cfg["lo"]:cfg["hi"]]
        for rname, roi in cfg["rois"].items():
            cube = K.load_cube(files, roi, pad=PAD)
            nf = cube.shape[0]
            fine, coarse, reg = K.L1.focus_fields(cube, G, RN_E)
            key = f"{sname}/{rname}"
            print("\n" + "=" * 78)
            print(f"{key}   {nf} frames   ROI {roi}   "
                  f"level {np.median(cube):.1f} DN   ({time.time()-t0:.0f}s)")
            print("=" * 78)
            r = {}

            # -- rule 24 / A.3: the merge really is m41lib's arm A ----------
            if rname == list(cfg["rois"])[0]:
                a_ref = K.L1.arm_A(cube, coarse, reg)[0][PAD:-PAD, PAD:-PAD]
                a_mine, _ = K.merge_subset(cube, coarse, reg, np.arange(nf),
                                           pad=PAD, gate=0.5)
                same = float(np.max(np.abs(a_ref - a_mine)))
                print(f"  merge_subset(all, gate=0.5) vs m41lib.arm_A: "
                      f"max |diff| {same:.3e} DN")
                r["arm_a_maxdiff"] = same

            # ---------------------------------------------- PR4 split table
            print(f"\n  PR4 -- SPLIT LEVERAGE.  The split is held COMMON to both"
                  f" configurations;\n         config 2 is config 1 with a"
                  f" {PLANT_SB} px Gaussian planted on both halves.\n"
                  f"         Truth is {PLANT_SB:.3f} px for EVERY row.")
            print("     split         n_A  n_B     P_a/P_b   FRC(f_sig)"
                  "     dsig px    se(jack)    err %      gof    sigpow ratio")
            rows, base_par = {}, None
            for k, (ia, ib) in K.splits(nf).items():
                ma, _ = K.merge_subset(cube, coarse, reg, ia, pad=PAD)
                mb, _ = K.merge_subset(cube, coarse, reg, ib, pad=PAD)
                rs1 = K.RingStats(ma, mb)
                rs2 = K.RingStats(K.M.blur(ma, PLANT_SB), K.M.blur(mb, PLANT_SB))
                d = K.dsig(rs1, rs2)
                A, B = K.spectra(ma, mb)
                pab = float(np.mean(np.abs(A) ** 2) / np.mean(np.abs(B) ** 2))
                frc = float(rs1.frc()[rs1.at(K.F_SIG)[1]])
                sp = K.sigpow(rs2) / K.sigpow(rs1)
                err = 100.0 * (d["px"] - PLANT_SB) / PLANT_SB
                print(f"     {k:12s} {len(ia):4d} {len(ib):4d}   {pab:9.5f}"
                      f"   {frc:+.6f}   {K.fmt(d['px'])}   {d['se_px']:8.2e}"
                      f"  {err:+7.2f}  {K.fmt(d['gof'],7,4)}    {sp:9.5f}")
                rows[k] = dict(n_a=len(ia), n_b=len(ib), pa_over_pb=pab, frc=frc,
                               dsig=d["px"], se=d["se_px"], err_pct=err,
                               gof=d["gof"], sigpow_ratio=sp)
                if k == "parity":
                    base_par = (rs1, ma, mb)
            vals = np.array([rows[k]["dsig"] for k in rows], float)
            noc = np.array([rows[k]["dsig"] for k in rows if k != "contiguous"],
                           float)
            nfin = int(np.isfinite(vals).sum())
            sp_all = float(np.nanmax(vals) - np.nanmin(vals)) if nfin else np.nan
            sp_noc = float(np.nanmax(noc) - np.nanmin(noc)) \
                if np.isfinite(noc).any() else np.nan
            print(f"     MEASURABLE in {nfin} of {len(vals)} split rules -- dsig"
                  f" returns NaN, not a number, when a ring's common power goes\n"
                  f"     non-positive.  Contrast fact 706: sigpow returned a"
                  f" NEGATIVE reference and an undefined sign rule.")
            print(f"     spread across MEASURABLE split rules  {sp_all:.5f} px"
                  f"   ({100*sp_all/PLANT_SB:.2f}% of the planted signal)")
            r["pr4"] = dict(rows=rows, spread_all=sp_all, spread_no_contig=sp_noc,
                            n_finite=nfin, n_rules=len(vals))

            # The fact-705 comparison: how far does dsig move if the OPERATOR
            # changes the split rule and nothing else?  Truth is not zero (S2
            # measured a real change), so this is a USAGE bound, not a bug.
            sp_pairs = {}
            for k, (ia, ib) in K.splits(nf).items():
                if k == "parity":
                    continue
                ma, _ = K.merge_subset(cube, coarse, reg, ia, pad=PAD)
                mb, _ = K.merge_subset(cube, coarse, reg, ib, pad=PAD)
                d = K.dsig(base_par[0], K.RingStats(ma, mb))
                sp_pairs[k] = dict(dsig=d["px"], se=d["se_px"])
            print("     changing the SPLIT RULE itself, vs parity "
                  "(truth is NOT zero -- S2 measured a real change):")
            for k, v in sp_pairs.items():
                print(f"        {k:12s} {K.fmt(v['dsig'])} px  "
                      f"+- {v['se']:8.2e}   = {abs(v['dsig'])/PLANT_SB:7.2f}x"
                      f" the planted signal")
            r["split_rule_change"] = sp_pairs

            # ------------------------------------------------- PR6 the null
            (a1, b1), (a2, b2) = mod4_null(nf)
            n = min(len(a1), len(b1), len(a2), len(b2))
            m11, _ = K.merge_subset(cube, coarse, reg, a1[:n], pad=PAD)
            m12, _ = K.merge_subset(cube, coarse, reg, b1[:n], pad=PAD)
            m21, _ = K.merge_subset(cube, coarse, reg, a2[:n], pad=PAD)
            m22, _ = K.merge_subset(cube, coarse, reg, b2[:n], pad=PAD)
            rn1, rn2 = K.RingStats(m11, m12), K.RingStats(m21, m22)
            dn = K.dsig(rn1, rn2)
            dsig_par = K.dsig(base_par[0], K.RingStats(
                K.M.blur(base_par[1], PLANT_SB), K.M.blur(base_par[2], PLANT_SB)))
            # planted wrong answer (rule 39)
            for wrong in (0.0, 2 * PLANT_SB):
                z = abs(dsig_par["px"] - wrong) / max(dsig_par["se_px"], 1e-12)
                print(f"  RULE 39 planted wrong answer {wrong:.3f} px: "
                      f"rejected at {z:.1f} se")
            print(f"  PR6 NULL (disjoint mod-4 subsets, matched depth spacing, "
                  f"{n}+{n} frames each):\n"
                  f"        dsig {K.fmt(dn['px'])} px  +- {dn['se_px']:.2e}  "
                  f"-> {abs(dn['px'])/max(dn['se_px'],1e-12):.1f} se from zero"
                  f"   = {100*abs(dn['px'])/PLANT_SB:.1f}% of the planted signal")
            r["pr6_null"] = dn
            r["pr6_signal"] = dsig_par

            # --------------------------------------------- PR7 one-sided gain
            lam = 1.30                      # fact 701's measured real ratio
            g1 = K.dsig(K.RingStats(base_par[1] * lam, base_par[2]),
                        K.RingStats(K.M.blur(base_par[1], PLANT_SB) * lam,
                                    K.M.blur(base_par[2], PLANT_SB)))
            print(f"  PR7 one-sided gain x{lam} on half A only: dsig "
                  f"{g1['px']:+.5f} px vs {dsig_par['px']:+.5f} px unscaled, "
                  f"move {abs(g1['px']-dsig_par['px']):.2e} px")
            r["pr7_onesided"] = dict(dsig=g1["px"],
                                     move=abs(g1["px"] - dsig_par["px"]))

            # ------------------------------------------------- gate sweep
            print(f"\n  GATE SWEEP (parity split).  dsig is relative to gate"
                  f" 0.50; negative = SHARPER.")
            print("      gate   n_eff      dsig px    se(jack)      gof"
                  "     sigpow/base     FRC(f_sig)")
            gates, ref = {}, None
            store = {}
            for gate in (0.0, 0.25, 0.50, 0.75, 0.90, 0.99):
                ia, ib = K.splits(nf)["parity"]
                ma, nea = K.merge_subset(cube, coarse, reg, ia, pad=PAD, gate=gate)
                mb, _ = K.merge_subset(cube, coarse, reg, ib, pad=PAD, gate=gate)
                rs = K.RingStats(ma, mb)
                store[gate] = (rs, nea)
                if abs(gate - 0.5) < 1e-9:
                    ref = rs
            for gate in (0.0, 0.25, 0.50, 0.75, 0.90, 0.99):
                rs, nea = store[gate]
                d = K.dsig(ref, rs)
                print(f"      {gate:5.2f}  {nea:6.3f}   {K.fmt(d['px'])}"
                      f"   {d['se_px']:8.2e}  {K.fmt(d['gof'],8,4)}"
                      f"    {K.sigpow(rs)/K.sigpow(ref):9.5f}"
                      f"     {rs.frc()[rs.at(K.F_SIG)[1]]:+.6f}")
                gates[f"{gate}"] = dict(n_eff=nea, dsig=d["px"], se=d["se_px"],
                                        gof=d["gof"],
                                        sigpow_ratio=K.sigpow(rs) / K.sigpow(ref))
            r["gate"] = gates
            res[key] = r
            del cube, fine, coarse, reg

    with open(os.path.join(K.OUT, "s3_real.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/s3_real.json  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
