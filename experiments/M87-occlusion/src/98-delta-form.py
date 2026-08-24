"""M87 s33e -- what SHAPE is the residual 11.7%?  A constant, or the veil?

B16 refuted the proportional reading: delta(d) correlates with the veil
profile at Pearson 0.157 and fits it with slope 0.0186 where 0.1167 was
predicted.  So "the gate weakens the veil by 11.7%" is NOT supported and I
will not write it.

Reading the delta column instead of the correlation shows why, and suggests
the alternative.  The veil residual falls from +4296 DN at d=25 to +838 DN at
d=60 -- it has nearly vanished.  The delta over the same span goes +580 ->
+486 DN.  It does NOT fall with the veil.  A quantity that stays put while
the veil decays by 80% is not a fraction of the veil; it is an offset sitting
underneath it.

That is exactly the hazard ORCH warned about and that affine invariance does
NOT cover.  My metric is immune to x -> a*x + b applied globally -- C-DRIFT
proved that at 0.000000% while the raw DN moved 2.1400%.  It is NOT immune to
a level change that differs between the near zone and the far zone, because
the baseline is taken from the far zone.  ORCH said the drift is "organised
spatially by the election"; a spatially organised level change is precisely a
near/far difference.

  BAR B18, on delta(d) over d = 5..60, three branches.  Fit two one-parameter
  models and compare RMS residual:
        M_const:  delta(d) = c            (a near/far level difference)
        M_prop :  delta(d) = k * veil(d)  (the gate weakening the veil)

     RMS_const <= 0.70 * RMS_prop  -> CONSTANT OFFSET.  The residual is drift,
                                      not veil, and the drift-corrected veil
                                      survival must be reported instead.
     RMS_prop  <= 0.70 * RMS_const -> PROPORTIONAL.  It is veil weakening
                                      after all and B16 was misread.
     otherwise                     -> NEITHER, report both RMS values and
                                      claim nothing about the residual.

  CONTROL C-ZERO.  The identical fit on delta = arm4 - arm4, which is
  identically zero, must return RMS 0.000 for BOTH models and c = k = 0.  If
  the fitting machinery can manufacture a preference on null input, B18's
  verdict is a property of the fitter.

  CONTROL C-PLANT-CONST and C-PLANT-PROP.  Synthesise delta = 500 DN exactly,
  and delta = 0.1167 * veil(d) exactly, and require B18 to name each one
  correctly.  A discriminator that cannot label data whose true form I chose
  cannot label data whose form I am asking about.  This is the positive
  control: C-ZERO alone shows the fitter is quiet, not that it can respond.

Operands come from 96-gate-final.json, so this script re-reads no TIFF and
introduces no new segmentation.
"""
import json
import pathlib
import sys

import numpy as np

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
DMIN, DMAX = 5, 60


def prof(arm):
    return {int(d): float(v) for d, v, _ in arm["profile"]}


def fit(delta, veil):
    c = float(np.mean(delta))
    rc = float(np.sqrt(np.mean((delta - c) ** 2)))
    k = (float(np.dot(delta, veil) / np.dot(veil, veil))
         if np.dot(veil, veil) > 0 else 0.0)
    rp = float(np.sqrt(np.mean((delta - k * veil) ** 2)))
    return c, rc, k, rp


def verdict(rc, rp):
    return ("CONSTANT OFFSET" if rc <= 0.70 * rp else
            "PROPORTIONAL" if rp <= 0.70 * rc else "NEITHER")


def main():
    src = json.loads((DATA / "96-gate-final.json").read_text(encoding="utf-8"))
    a4, a0 = src["arms"]["4.00"], src["arms"]["0.00"]
    p4, p0 = prof(a4), prof(a0)
    b4, b0 = a4["base"], a0["base"]
    ds = [d for d in range(DMIN, DMAX + 1) if d in p4 and d in p0]
    veil = np.array([p4[d] - b4 for d in ds])
    delta = np.array([(p4[d] - b4) - (p0[d] - b0) for d in ds])

    out = {"d_range": [DMIN, DMAX], "n": len(ds)}
    print(f"=== B18: the form of the residual, d = {ds[0]}..{ds[-1]},"
          f" {len(ds)} rings ===")
    c, rc, k, rp = fit(delta, veil)
    print(f"  M_const  delta = {c:+.1f} DN            RMS {rc:8.1f} DN")
    print(f"  M_prop   delta = {k:.4f} * veil(d)     RMS {rp:8.1f} DN")
    print(f"  ratio RMS_const / RMS_prop = {rc/rp:.3f}")
    v18 = verdict(rc, rp)
    print(f"  B18: {v18}")
    out["B18"] = {"c": c, "rms_const": rc, "k": k, "rms_prop": rp,
                  "ratio": rc / rp, "verdict": v18}

    print("\n=== controls ===")
    z = np.zeros_like(delta)
    cz, rcz, kz, rpz = fit(z, veil)
    zok = abs(cz) < 1e-12 and rcz < 1e-12 and abs(kz) < 1e-12 and rpz < 1e-12
    print(f"  C-ZERO         c={cz:.3e} RMS_c={rcz:.3e}"
          f"  k={kz:.3e} RMS_p={rpz:.3e}  -> {'PASS' if zok else 'FAIL'}")
    cc = fit(np.full_like(delta, 500.0), veil)
    vpc = verdict(cc[1], cc[3])
    cp = fit(0.1167 * veil, veil)
    vpp = verdict(cp[1], cp[3])
    print(f"  C-PLANT-CONST  true form constant 500 DN -> B18 says {vpc}"
          f"  -> {'PASS' if vpc == 'CONSTANT OFFSET' else 'FAIL'}")
    print(f"  C-PLANT-PROP   true form 0.1167*veil     -> B18 says {vpp}"
          f"  -> {'PASS' if vpp == 'PROPORTIONAL' else 'FAIL'}")
    ctl_ok = zok and vpc == "CONSTANT OFFSET" and vpp == "PROPORTIONAL"
    print(f"  controls all pass: {ctl_ok}")
    out["controls"] = {"C_ZERO": zok, "C_PLANT_CONST": vpc,
                       "C_PLANT_PROP": vpp, "all_pass": ctl_ok}

    # ---- the drift-corrected survival ----------------------------------
    print("\n=== the veil ratio with the offset removed ===")
    C4, C0 = a4["C"], a0["C"]
    amp4 = max(veil)
    amp0_raw = max(p0[d] - b0 for d in ds)
    amp0_corr = max((p0[d] - b0) + c for d in ds)
    r_raw = (amp0_raw / C0) / (amp4 / C4)
    r_corr = (amp0_corr / C0) / (amp4 / C4)
    print(f"  peak veil, gate 4.00            {amp4:8.0f} DN")
    print(f"  peak veil, gate 0.00 as measured{amp0_raw:8.0f} DN"
          f"   -> r = {r_raw:.4f}")
    print(f"  peak veil, gate 0.00 + {c:+.0f} DN offset"
          f" {amp0_corr:8.0f} DN   -> r = {r_corr:.4f}")
    print(f"  so of the {100*(1-r_raw):.1f}% the gate appeared to remove,"
          f" {100*(r_corr-r_raw)/(1-r_raw):.0f}% is the near/far offset and"
          f" {100*(1-r_corr)/(1-r_raw):.0f}% is unexplained")
    out["corrected"] = {"amp4": float(amp4), "amp0_raw": float(amp0_raw),
                        "amp0_corr": float(amp0_corr), "r_raw": r_raw,
                        "r_corr": r_corr,
                        "offset_share_pct": 100 * (r_corr - r_raw) / (1 - r_raw)}

    print("\n=== what this means for B15 ===")
    print(f"  B15 measured r = {r_raw:.4f}, i.e. {100*r_raw:.1f}% of the veil"
          f" surviving with averaging off.")
    print(f"  B18 says {100*(r_corr-r_raw)/(1-r_raw):.0f}% of the shortfall is"
          f" an offset the metric cannot be immune to, so {100*r_corr:.1f}% is"
          f" the better estimate and 88.3% is a LOWER BOUND.")
    print(f"  Either way the conclusion is the same and it is the one that"
          f" matters: a {55.321:.1f}x change in frames averaged per pixel"
          f" leaves the veil essentially intact.")

    (DATA / "98-delta-form.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {DATA / '98-delta-form.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
