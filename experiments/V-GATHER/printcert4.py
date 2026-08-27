r"""The print certificate on FOUR axes.

The committed certificate measured one axis -- mid-scale mottling -- and said so
in its own closing paragraph: "a PASS here is silence on those, not a clean bill.
Anyone reading these counts as print-ready is reading roughly a third of what
ruins a print." This closes the three named gaps: halo, sharpness, and sensor
defect trails.

THE BLOTCH AXIS IS NOT RE-IMPLEMENTED. Its constants, its coverage gate, its
focus-qualified best-frame rule and its label derivation are imported from
printcert.py and used unchanged, so extending the certificate cannot silently
weaken the axis that already worked.

EACH AXIS PARTITIONS ALL 26 SEPARATELY. An axis that examined 9 subjects must say
so as 9 + 17 NOT EXAMINED, not as 9 PASS. A REFUSED never reads as a PASS, and
each column is checked to sum to the seal census independently.
"""
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import printcert as pc                                             # noqa: E402
import rimaxis                                                     # noqa: E402
import sharpaxis as sa                                             # noqa: E402
import dustaxis as da                                              # noqa: E402

# Measured in rimsubsample.py: drawing random subsets of one subject's OWN edges
# down to n=72 moved the reading by at most +1.315 points (bee-1-cpl, +3.126% ->
# +4.441%), while 119MSDCF moved by 0.003 points. The allowance is the measured
# worst case rounded up, applied only where the sample is small enough for it to
# matter. It is not a safety factor; it is the size of a measured bias.
RIM_SMALLN_N = 200
RIM_SMALLN_ALLOW = 0.015
AXES = ("blotch", "rim", "sharp", "dust")
ORDER = ("PASS", "FAIL", "SUBJECT", "REFUSED", "NOT EXAMINED")


def load(name):
    p = os.path.join(HERE, name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


def finite(*vals):
    """True only if every supplied value is a real, finite number.

    NaN compares False against EVERY relational operator, so an absent
    measurement flowing into `if x > threshold` produces a PASS. One NaN
    already reached cert.json (bee-2-cpl frame 11, an unbounded chroma
    window). The upstream hole is fixed; this is the second line, because a
    verdict function must never be the place where a missing number becomes a
    clean one.
    """
    for v in vals:
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v):
            return False
    return True


def blotch_verdict(s, deliv, cert, margin):
    if s not in deliv:
        return "NOT EXAMINED", "no delivered-file measurement"
    d = deliv[s]
    vis = []
    if d["blotch"] > pc.VIS_BLOTCH:
        vis.append("blotch %.4f" % d["blotch"])
    if d["chroma"] > pc.VIS_CHROMA:
        vis.append("chroma %.4f" % d["chroma"])
    if d["clip"] > pc.CLIP_MAX:
        vis.append("clip %.4f%%" % (d["clip"] * 100))
    rb, cov_note = None, None
    v = cert.get(s)
    if v and v.get("done"):
        uf, sf, used, samp = pc.coverage(v)
        if uf < pc.COVERAGE_MIN or sf < pc.COVERAGE_MIN:
            cov_note = ("coverage %.0f%%/%.0f%% (%d of %d) below %.0f%%"
                        % (100 * uf, 100 * sf, used, samp, 100 * pc.COVERAGE_MIN))
            v = None
    if v and v.get("done"):
        src = [x for x in v["sources"] if "blotch" in x]
        if src:
            b = [x["blotch"] for x in src]
            f = [x["focus_win"] for x in src]
            i_b, _ = pc.best_index(b, f)
            if i_b is not None:
                rb = v["master"]["blotch"] / b[i_b]
    if not vis:
        return "PASS", "below visibility on the delivered file"
    if rb is not None and not finite(rb):
        return "REFUSED", ("visible (%s) but the master/best-source ratio is "
                           "not a finite number" % "; ".join(vis))
    if rb is None:
        return "REFUSED", "visible (%s) but %s" % (
            "; ".join(vis), cov_note or "no matched-gauge attribution")
    if rb > margin:
        return "FAIL", "visible (%s) and ratio %.3f > %.3f" % ("; ".join(vis), rb, margin)
    return "SUBJECT", "visible (%s) but ratio %.3f -- sources carry it" % (
        "; ".join(vis), rb)


def rim_verdict(s, rim):
    v = rim.get(s)
    if v is None:
        return "NOT EXAMINED", "not measured"
    if "refused" in v:
        return "REFUSED", v["refused"]
    c = v["corrected_bright"]
    ci = v["master"].get("ci_bright")
    off = v["master"]["null_bright"] + v["floor"]["resid_bright"]
    lo = (ci[0] - off) if ci else None
    allow = RIM_SMALLN_ALLOW if v["n_sel"] < RIM_SMALLN_N else 0.0
    thr = rimaxis.RIM_MAX + allow
    tail = ("%+.2f%% of the edge step over %d isolated edges (%.0f%% of the "
            "high-contrast features present; the rest never plateau by t=+7px "
            "and this axis cannot speak to them)"
            % (100 * c, v["n_sel"], 100 * v["isolated_frac"]))
    if lo is None:
        return "REFUSED", "no bootstrap interval; " + tail
    if not finite(c, lo):
        return "REFUSED", "rim statistic is not a finite number; " + tail
    if c > thr and lo > thr:
        return "FAIL", ("overshoot %s; 95%% interval lower bound %+.2f%% also "
                        "exceeds %.1f%%" % (tail, 100 * lo, 100 * thr))
    if c > thr:
        return "REFUSED", ("overshoot %s but its 95%% interval reaches down to "
                           "%+.2f%%, below the %.1f%% threshold -- not resolved"
                           % (tail, 100 * lo, 100 * thr))
    return "PASS", "overshoot %s" % tail


def sharp_verdict(s, sharp):
    v = sharp.get(s)
    if v is None:
        return "NOT EXAMINED", "not measured"
    if "refused" in v:
        return "REFUSED", v["refused"]
    d = v["deficit_median"]
    tail = ("median %+.1f%% below the per-site focus ceiling over %d qualifying "
            "sites of %d offered (%d frames)"
            % (100 * d, v["n_qualified"], v["n_sites_offered"], v["n_frames_used"]))
    if not finite(d):
        return "REFUSED", "softness statistic is not a finite number; " + tail
    if d > sa.SHARP_MAX:
        return "FAIL", "softness %s, above %.1f%%" % (tail, 100 * sa.SHARP_MAX)
    return "PASS", "softness %s" % tail


def dust_verdict(s, dust):
    v = dust.get(s)
    if v is None:
        return "NOT EXAMINED", "not measured"
    if "refused" in v:
        return "REFUSED", v["refused"]
    r = v["ratio"]
    tail = ("defect-site response %.4f x matched controls over %d mapped sites "
            "and %d controls" % (r, v["n_sites_used"], v["n_control"]))
    if not finite(r):
        return "REFUSED", "trail statistic is not a finite number; " + tail
    if r > da.DUST_MAX:
        return "FAIL", "trails present: %s" % tail
    return "PASS", "no trails at or above this axis's power limit: %s" % tail


def main():
    deliv, cert = load("delivered.json"), load("cert.json")
    rim, sharp, dust = load("rim.json"), load("sharp.json"), load("dust.json")

    seals = sorted(f[:-len("--SHIP-V4.tiff")] for f in os.listdir(pc.SEAL_DIR)
                   if f.endswith("--SHIP-V4.tiff"))
    n = len(seals)
    print("seal census: %d masters carry a --SHIP-V4.tiff in %s\n" % (n, pc.SEAL_DIR))

    # SAME CROSS-CHECK AS THE SINGLE-AXIS CERTIFICATE. "total == len(population)"
    # is self-consistent and proves nothing; a population truncated to twenty
    # sums to twenty. The .ok seals are a second, independently produced census.
    okseals = [f for f in os.listdir(pc.SEAL_DIR) if f.endswith(".tiff.ok")]
    if len(okseals) != n:
        raise SystemExit("POPULATION DISAGREES WITH SEALS: %d masters, %d seals"
                         % (n, len(okseals)))
    margin, _bias_rows = pc.price_sampling_bias(cert)
    print("sampling-bias margin priced from exhaustive subjects: %.4f" % margin)
    res = {}
    for s in seals:
        res[s] = {"blotch": blotch_verdict(s, deliv, cert, margin),
                  "rim": rim_verdict(s, rim),
                  "sharp": sharp_verdict(s, sharp),
                  "dust": dust_verdict(s, dust)}

    print("%-38s %-12s %-12s %-12s %-12s" % ("subject", "BLOTCH", "RIM", "SHARP", "DUST"))
    print("-" * 90)
    for s in seals:
        print("%-38s %-12s %-12s %-12s %-12s"
              % (s, res[s]["blotch"][0], res[s]["rim"][0], res[s]["sharp"][0],
                 res[s]["dust"][0]))

    print("\nPER-AXIS PARTITION -- each column independently sums to the seal census")
    print("%-14s %6s %6s %6s %6s" % ("", "BLOTCH", "RIM", "SHARP", "DUST"))
    for k in ORDER:
        print("  %-12s %6d %6d %6d %6d"
              % (k, *[sum(1 for s in seals if res[s][a][0] == k) for a in AXES]))
    tot = [sum(sum(1 for s in seals if res[s][a][0] == k) for k in ORDER) for a in AXES]
    print("  %-12s %6d %6d %6d %6d  (each must equal %d)" % ("TOTAL", *tot, n))
    for a, t in zip(AXES, tot):
        if t != n:
            raise SystemExit("AXIS %s DOES NOT SUM: %d != %d" % (a, t, n))

    fails = {s: [a for a in AXES if res[s][a][0] == "FAIL"] for s in seals}
    anyfail = [s for s in seals if fails[s]]
    allpass = [s for s in seals if all(res[s][a][0] == "PASS" for a in AXES)]
    refused = [s for s in seals
               if not fails[s] and any(res[s][a][0] in ("REFUSED", "NOT EXAMINED")
                                       for a in AXES)]
    subj = [s for s in seals if s not in anyfail and s not in allpass and s not in refused]
    print("\nCOMBINED -- a print is only as good as its worst axis")
    print("  clean on all four axes      %3d" % len(allpass))
    print("  FAIL on at least one axis   %3d" % len(anyfail))
    print("  no FAIL, some axis silent   %3d" % len(refused))
    print("  no FAIL, source-attributed  %3d" % len(subj))
    print("  TOTAL                       %3d  (must equal %d)"
          % (len(allpass) + len(anyfail) + len(refused) + len(subj), n))
    if len(allpass) + len(anyfail) + len(refused) + len(subj) != n:
        raise SystemExit("COMBINED PARTITION DOES NOT SUM")

    print("\nFAILING SUBJECTS, and on what")
    for s in anyfail:
        print("\n  %s  -- FAIL on: %s" % (s, ", ".join(fails[s])))
        for a in fails[s]:
            print("      %-7s %s" % (a, res[s][a][1]))

    print("\nVERDICT CHANGE versus the single-axis certificate")
    changed = [s for s in anyfail if res[s]["blotch"][0] != "FAIL"]
    print("  newly failing because of the three new axes: %d" % len(changed))
    for s in changed:
        print("    %-38s now FAIL on %s" % (s, ", ".join(fails[s])))

    print("""
WHAT A PASS STILL DOES NOT COVER
  RIM   speaks only to edges isolated enough to plateau within 7px. The
        isolated fraction is printed per subject above and runs from 12% to 72%.
  SHARP resolves softness down to about blur sigma 0.6; below that it is silent.
        Its ceiling is a max over sampled frames, so every deficit is a LOWER
        bound, and subjects whose ceiling did not converge are REFUSED.
  DUST  detected planted single-pixel defects at 2000 DN and missed them at 500.
        The darks say this sensor's worst site carries 331 DN of mean excess, so
        this axis speaks confidently only about the strongest defects.
  None of the four measures colour accuracy, tonal rendering or composition.""")


if __name__ == "__main__":
    main()
