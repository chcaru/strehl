"""
M71 step 15 — cross-check M72 fact 32 (the B-plane gain/offset limbs).

No pixels are read. This is arithmetic over two already-committed measurements:
M71's own photon-transfer gains (data/03-ptc.json, ISO 100, illuminated flats)
and M72's per-plane dark fit as quoted in docs/research/M72-green-plane-
correlation.md section 9.

M72 fits, on 220 darks across ISO:      var(ISO) = alpha * G^2 + delta
  alpha_B / alpha_green = 0.8418        delta_B / delta_green = 0.5966
A single pre-ADC scale s predicts       alpha ratio = s^2 = 0.7049 (s = 0.8396)
                                        delta ratio = 1  (quantisation is
                                        added AFTER the scale)
Neither is met. M72 did not rule; the orchestrator routed it as evidence.

WHAT A GAIN LIMB ADDS. Let the B channel differ from green by a single
multiplicative factor c applied at ONE point in the analog chain, before the ADC.

  signal        S_B = c*g0*e
  shot noise    var = c^2 g0^2 e = (c*g0) * S_B      -> PTC slope ratio = c
  read noise generated UPSTREAM of that point (input-referred, electrons):
                var scales as c^2                    -> alpha ratio c^2
  read noise generated DOWNSTREAM of that point:
                var unchanged                        -> alpha ratio 1

So with a fraction f of the green plane's ISO-scaling noise POWER upstream:

  alpha_ratio = f*c^2 + (1-f)  =  1 - f*(1 - c^2)
  =>  f = (1 - alpha_ratio) / (1 - c^2)

f is where in the chain the attenuation sits, measured in noise power rather
than argued. M68 stated a photon-transfer RATIO could not settle this; that is
correct in isolation, and it stops being correct once an alpha ratio from darks
is available to combine with it. c comes from MY flats, independent of M61.

PRE-REGISTERED, written before evaluating:

  PR-10a  PHYSICALITY. The model is falsifiable in exactly one place: f must
          lie in [0, 1]. f > 1 requires c^2 > alpha_ratio, i.e. c > 0.9175.
          If my measured c exceeds 0.9175 the single-point model is REFUTED
          and I report that instead of a localisation.
  PR-10b  I rule on the gain limb ONLY IF my c and M61's c give f values that
          agree to within 0.25 in absolute f. If they disagree by more, the
          localisation is dominated by which gain you believe and I decline.
  PR-10c  DELTA LIMB. I rule on delta only if my PTC intercept ratio
          discriminates 0.5966 from 1.0 at better than 2 sigma. My intercepts
          are negative and were already flagged unruled in section 6.4, so I
          expect this to fail; pre-registering it means I cannot quietly claim
          the delta limb later.
"""
import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = HERE / "data"
OUT = DATA / "15-m72-gain-limb.json"

# ---- M72, docs/research/M72-green-plane-correlation.md section 9 (read directly)
ALPHA_RATIO = 0.8418
DELTA_RATIO = 0.5966
S_M61 = 0.8396          # M61's pre-ADC scale, = fact 921's gain factor
S_M61_ERR = 0.0112


def f_of(c):
    return (1.0 - ALPHA_RATIO) / (1.0 - c * c)


def main():
    ptc = json.loads((DATA / "03-ptc.json").read_text(encoding="utf-8"))

    gB, gBe = ptc["B"]["g"], ptc["B"]["g_err"]
    gG = 0.5 * (ptc["G1"]["g"] + ptc["G2"]["g"])
    gGe = 0.5 * np.hypot(ptc["G1"]["g_err"], ptc["G2"]["g_err"])
    c = gB / gG
    c_err = c * np.hypot(gBe / gB, gGe / gG)
    print(f"M71 gain limb:  g_B = {gB:.6f}  g_green = {gG:.6f}")
    print(f"                c = g_B/g_green = {c:.4f} +- {c_err:.4f}")
    print(f"M61 gain limb:  s = {S_M61:.4f} +- {S_M61_ERR:.4f}\n")

    # ---- PR-10a physicality
    c_max = float(np.sqrt(ALPHA_RATIO))
    ok_a = c < c_max
    print(f"PR-10a  single-point model needs c < sqrt(alpha_ratio) = {c_max:.4f}")
    print(f"        measured c = {c:.4f}  ->  "
          f"{'MET (physical)' if ok_a else 'FAILED -> model REFUTED'}"
          f"   margin {100*(c_max-c)/c_max:.1f}%")
    print(f"        M61's s = {S_M61:.4f}  margin {100*(c_max-S_M61)/c_max:.1f}%\n")

    # ---- the localisation
    f_me, f_61 = f_of(c), f_of(S_M61)
    f_me_lo, f_me_hi = f_of(c - c_err), f_of(c + c_err)
    print(f"        f (M71 gain, c={c:.4f})  = {f_me:.3f}  "
          f"[{min(f_me_lo,f_me_hi):.3f}, {max(f_me_lo,f_me_hi):.3f}] from c error")
    print(f"        f (M61 gain, s={S_M61:.4f})  = {f_61:.3f}")
    ok_b = abs(f_me - f_61) <= 0.25
    print(f"PR-10b  |f_M71 - f_M61| = {abs(f_me-f_61):.3f} <= 0.25  "
          f"{'MET' if ok_b else 'FAILED -> decline'}\n")

    # ---- PR-10c delta limb, from my PTC intercepts
    bB, bBe = ptc["B"]["b"], ptc["B"]["b_err"]
    bG = 0.5 * (ptc["G1"]["b"] + ptc["G2"]["b"])
    bGe = 0.5 * np.hypot(ptc["G1"]["b_err"], ptc["G2"]["b_err"])
    dr = bB / bG
    dr_err = abs(dr) * np.hypot(bBe / bB, bGe / bG)
    z1 = abs(dr - DELTA_RATIO) / dr_err
    z2 = abs(dr - 1.0) / dr_err
    ok_c = min(z1, z2) > 2.0 and abs(z1 - z2) > 2.0
    print(f"PR-10c  my intercept ratio b_B/b_green = {dr:.4f} +- {dr_err:.4f}")
    print(f"        (both intercepts NEGATIVE and unphysical -- section 6.4)")
    print(f"        distance to M72's 0.5966: {z1:.2f} sigma;  to 1.0: {z2:.2f} sigma")
    print(f"        discriminates? {'MET' if ok_c else 'FAILED -> decline delta limb'}")

    # ---- how much of the alpha ratio would a plane-dependent input-referred
    # read noise absorb? This is the degeneracy I cannot break.
    rn_ratio_if_f1 = float(np.sqrt(ALPHA_RATIO) / c)
    print(f"\n        degeneracy: if instead ALL alpha noise were upstream (f=1),")
    print(f"        the data need RN_B/RN_green = {rn_ratio_if_f1:.4f} in electrons.")
    print(f"        I cannot exclude that; f is conditional on equal input-")
    print(f"        referred read noise between the planes.")

    out = {"inputs": {"alpha_ratio_M72": ALPHA_RATIO,
                      "delta_ratio_M72": DELTA_RATIO,
                      "s_M61": S_M61, "s_M61_err": S_M61_ERR,
                      "g_B_M71": gB, "g_green_M71": gG},
           "c_M71": c, "c_err_M71": c_err,
           "c_max_for_physicality": c_max,
           "f_M71": f_me, "f_M71_lo": min(f_me_lo, f_me_hi),
           "f_M71_hi": max(f_me_lo, f_me_hi), "f_M61": f_61,
           "intercept_ratio": dr, "intercept_ratio_err": dr_err,
           "z_to_delta_ratio": z1, "z_to_unity": z2,
           "rn_ratio_needed_if_f1": rn_ratio_if_f1,
           "PR-10a": "MET" if ok_a else "FAILED",
           "PR-10b": "MET" if ok_b else "FAILED",
           "PR-10c": "MET" if ok_c else "FAILED"}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
