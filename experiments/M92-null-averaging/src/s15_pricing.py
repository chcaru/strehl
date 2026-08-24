"""M92b S15 -- exact pricing of every contaminated number.

S12 priced at a nominal 250 DN. This prices at each site's OWN level, because
the sigma ratio is level-dependent and a nominal number is not a finding.
Each row also carries the direction: whether the corrected value makes the
milestone's own claim easier or harder to sustain, which is what decides
retraction versus footnote.

Run:
  python experiments/M92-null-averaging/src/s15_pricing.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as M57  # noqa: E402


def sd(level, g, rn):
    return (g * max(level, 0.0) + (rn * g) ** 2) ** 0.5


def half(level, g, rn):
    """The 0.5* form M55/m41 use: sd of a 2-way half-merge difference."""
    return (0.5 * (g * max(level, 0.0) + (rn * g) ** 2)) ** 0.5


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    rows = []

    def price(site, level, wrong, right, form=half, note=""):
        a, b = form(level, *wrong), form(level, *right)
        r = a / b
        rows.append(dict(site=site, level_dn=level, wrong=list(wrong),
                         right=list(right), sd_wrong=a, sd_right=b,
                         ratio=r, note=note))
        log(f"  {site}")
        log(f"      level {level:8.2f} DN   g/rn used ({wrong[0]:.5f},"
            f" {wrong[1]:g})  correct ({right[0]:.5f}, {right[1]:g})")
        log(f"      modelled sd {a:8.4f} vs {b:8.4f} DN"
            f"   ratio {r:.4f}x  ({(r - 1) * 100:+.2f}%)")
        if note:
            log(f"      {note}")
        log("")

    log("=" * 78)
    log("M92b S15 -- exact pricing at each site's own level")
    log("=" * 78)
    log("")

    g500, rn500 = M57.gain_dn_per_e(500), M57.read_noise_e(500)
    g160, rn160 = M57.gain_dn_per_e(160), M57.read_noise_e(160)
    g100, rn100 = M57.gain_dn_per_e(100), M57.read_noise_e(100)
    g50, rn50 = M57.gain_dn_per_e(50), M57.read_noise_e(50)

    log("-- 1. M57 S5/S6/S7: ISO 500 declared, 109MSDCF is ISO 160")
    for lvl in (106.34, 250.0, 500.0):
        price(f"m57 noise model on 109MSDCF @ {lvl:g} DN", lvl,
              (g500, rn500), (g160, rn160), form=sd)

    log("-- 2. M55 e1_dark_rho: RN_E 1.47 (pre-M48) on the ISO-500 arm")
    log("   G = 1.14469 is EXACTLY correct for ISO 500. The scanner flagged")
    log("   it only because the file opens darks 118-128 in string literals;")
    log("   the constant is scoped to res['iso'][500]. False positive on G.")
    log("")
    for nm, lvl in (("M46 flat ROI", 106.34375), ("M46 detail ROI",
                                                  203.11111)):
        price(f"M55 e1 {nm}", lvl, (g500, 1.47), (g500, rn500),
              note="conclusion is a shortfall of 100s-x in VARIANCE")

    log("-- 3. M55 e2_real_halfstacks: the DUAL-ROLE assignment")
    log("   `G, RN_E = 1.14469, 1.47` at line 56 feeds BOTH the longhand")
    log("   sigma at line 160 (sensor model) AND focus_fields at line 165")
    log("   (frozen operator, rule 15). One name, two contracts.")
    log("")
    price("M55 e2 sigma on 112MSDCF", 250.0, (g500, 1.47), (g500, rn500),
          note="correcting the sensor use in place would unfreeze the "
               "operator")

    log("-- 4. m41 a11_metric_power: M25's ISO-50 gain bug on real planes")
    log("   G = 0.11446886 is ISO/436.8; the corrected model is")
    log("   max(ISO,100)/436.8 = 0.22894 because Sony ISO 50 is an extended")
    log("   pull reading out at base-ISO gain (AGENTS M25 row, fixed 2a4f5c5).")
    log("")
    for lvl in (250.0, 1200.0):
        price(f"m41 a11 sigma_map on 119MSDCF @ {lvl:g} DN", lvl,
              (0.11446886446886446, 4.2), (g50, rn50),
              note="injected noise is 1/ratio too SMALL -> every detection "
                   "claim is anti-conservative, every failure-to-detect "
                   "claim is conservative and survives")

    log("-- 5. SYNTHESIS fact 130's ISO-50 temporal-sigma cap")
    log("   Fact 130 rules fact 88's 43.2-53.1 DN impossible because the")
    log("   model caps temporal sigma at 22.9 DN. That 22.9 was computed")
    log("   with the superseded g = 0.1145.")
    log("")
    lvl130 = 4585.0
    cap_old = sd(lvl130, 0.11446886446886446, 4.2)
    cap_new = sd(lvl130, g50, rn50)
    log(f"      level {lvl130:g} DN (fact 130's stated ROI-mean ceiling)")
    log(f"      cap with superseded g = 0.11447 : {cap_old:.2f} DN"
        f"   (fact 130 says 22.9)")
    log(f"      cap with corrected  g = {g50:.5f} : {cap_new:.2f} DN")
    log(f"      fact 88's range 43.2-53.1 DN is still ABOVE the corrected"
        f" cap by {43.2 / cap_new:.2f}x-{53.1 / cap_new:.2f}x")
    log("      -> the digits move 1.41x; the CONCLUSION survives. FOOTNOTE.")
    log("")
    rows.append(dict(site="SYNTHESIS fact 130 cap", level_dn=lvl130,
                     cap_old=cap_old, cap_new=cap_new,
                     ratio=cap_new / cap_old,
                     fact88_lo_over_cap=43.2 / cap_new,
                     fact88_hi_over_cap=53.1 / cap_new,
                     note="conclusion survives"))

    log("-- 6. Is m41's fact 478 (the (1-rho) law) exposed?")
    log("   DERIVED: a11 scales both the shared and the independent noise")
    log("   draw by the same sigma_map. A global amplitude scalar therefore")
    log("   multiplies numerator and denominator of the recovery ratio")
    log("   alike and cancels -- the same algebra as facts 617/708, where a")
    log("   linear post-filter scales C and U by |H|^2 and ring FRC cannot")
    log("   move. So the (1-rho) SCALING is invariant to the gain error.")
    log("   The absolute recovery ratios of fact 477 are NOT protected by")
    log("   that argument and were not re-measured here.")
    log("")

    with open(os.path.join(M92.OUT, "s15_pricing.json"), "w",
              encoding="utf-8") as fh:
        json.dump(dict(rows=rows), fh, indent=1)
    with open(os.path.join(M92.OUT, "s15_pricing.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("wrote out/s15_pricing.{json,log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
