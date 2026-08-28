r"""Can the print gate's DUST axis see the defects this sensor actually has?

WHY THIS RUNS BEFORE ANY ON/OFF COMPARISON. ORCH asked whether sensor-defect
correction should ship ON, and set "no regression on the print gate" as one of
the two bars. That bar is only meaningful if the gate can read at the scale of
the thing it grades. Tonight this project retired `E*` as an accuracy gate for
the structurally identical reason: it was a ruler made of the thing it measured.
Before spending hours of render on an ON-vs-OFF arm graded by the DUST axis, the
axis itself gets measured.

WHAT IS RE-DERIVED HERE, AND WHAT IS TAKEN ON TRUST. Nothing is taken on trust.
`dustaxis.py`'s own functions are imported and called -- so this measures the
shipping axis, not a paraphrase of it -- but every threshold, every site list and
every claimed figure is PARSED OUT OF THE ARTIFACTS, never written here. The
claim under test ("detected planted single-pixel defects at 2000 DN and missed
them at 500") is lifted out of printcert4.py's own closing text by regex, so if
that text changes this script's comparison changes with it.

THE THREE ARMS, AND WHY AN IMPROVEMENT ARM IS AMONG THEM. A ladder of planted
degradations can only show that a statistic responds to damage. It cannot
distinguish a statistic that is BLIND to a defect from one that is PERVERSE on
it -- scoring the damaged image better. This project has shipped exactly that
defect: a sharpness statistic bounded below by zero that could never charge for
a halo, with every commissioning arm a degradation, so nobody noticed.

  NULL         the untouched master. The ratio must sit at or below the axis's
               own pass threshold, or the axis is failing clean images and every
               reading downstream of it is suspect.
  LADDER       planted single-pixel defects at descending amplitude. The floor
               is the smallest amplitude whose ratio clears the threshold. The
               ladder MUST BE ABLE TO RETURN NOTHING: if no rung clears, the
               floor is reported as UNRESOLVED-ABOVE-TOP, not as the top rung.
  IMPROVEMENT  the strongest planted rung, then a 3x3 median that removes it.
               The ratio must fall back toward the null. If it does not, the
               statistic cannot score a fix, only a defect, and its PASS verdicts
               mean nothing.

WHAT THE FLOOR IS COMPARED AGAINST. The largest excess this sensor's darks
actually carry, parsed from the defect map the axis itself loads. If the floor
is above that number, then every PASS this axis has issued is silence from an
instrument that could not have detected the defect -- which is what the axis's
own docstring says should produce a REFUSED.

READ-ONLY. This script imports V-GATHER's modules and reads their JSON. It
writes only into experiments/BUILD-DEFECT/out/. It never writes D:\ and never
edits another lane's files.
"""
import io
import json
import os
import re
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GATHER = os.path.join(ROOT, "experiments", "V-GATHER")
OUTDIR = os.path.join(ROOT, "experiments", "BUILD-DEFECT", "out")
sys.path.insert(0, GATHER)

import dustaxis as da                                              # noqa: E402
import rimaxis                                                     # noqa: E402

# The rungs are this script's own experimental design, not a claim about the
# axis, so they are declared here. They deliberately extend BELOW dustaxis's own
# ladder (which stopped at 120 DN) because the whole question is whether the
# floor lies under the amplitudes the darks actually carry.
RUNGS = (4000.0, 2000.0, 1000.0, 500.0, 250.0, 120.0, 60.0, 30.0)

# Subjects chosen to span the measured range of control_med in dust.json -- the
# floor of a max-over-window statistic must depend on how much local structure
# the scene already has, and a single subject cannot show that.
SPAN_KEY = "control_med"


def parse_claimed_floor():
    """Lift the axis's own published power claim out of printcert4.py.

    Parsed, never written here. A checker that compares an artifact against
    constants typed into the checker runs green while the artifact drifts;
    another lane scored 37/37 that way and then caught 5 of 13 plants.
    """
    src = io.open(os.path.join(GATHER, "printcert4.py"), encoding="utf-8").read()
    m = re.search(r"detected planted single-pixel defects at\s+(\d+)\s*DN\s+"
                  r"and missed them at\s+(\d+)", re.sub(r"\s+", " ", src))
    if not m:
        raise SystemExit("CLAIM NOT FOUND in printcert4.py -- cannot compare "
                         "against a claim that is not there")
    return float(m.group(1)), float(m.group(2))


def strip_string_literals(src):
    """Remove string and comment bodies. Retained only to detect the PROSE case.

    NOT used to decide whether the verdict consults the power arm -- see
    consults_power for why that use was wrong and how it was caught.
    """
    src = re.sub(r'"""(?:.|\n)*?"""', '""', src)
    src = re.sub(r"'''(?:.|\n)*?'''", "''", src)
    src = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', src)
    src = re.sub(r"'(?:\\.|[^'\\\n])*'", "''", src)
    src = re.sub(r"#[^\n]*", "", src)
    return src


def parse_real_amplitude():
    """The largest excess the darks actually carry, from the map the axis loads.

    `excess_dn` IS NOT THE WORST SITE. dustmap.py line 60 uses it as a selection
    threshold -- `hits += (ex > EXCESS_DN)` -- so it is the cut a site had to
    clear to be kept, and reading it as the defect amplitude understates the
    real defect by 6.9x and flatters this audit's own conclusion. The worst site
    is the maximum of the per-site `amp` list. Both are reported, labelled as
    what they are.
    """
    m = json.load(io.open(da.MAP, encoding="utf-8"))
    amps = [abs(float(a)) for a in m.get("amp", [])]
    return {"cut_excess_dn": float(m["excess_dn"]),
            "amp_max": max(amps) if amps else float("nan"),
            "amp_med": float(np.median(amps)) if amps else float("nan"),
            "n_sites_total": int(m["n_sites_total"]),
            "n_sites_kept": len(amps),
            "cut_dn": float(m["cut_dn"]),
            "n_darks": int(m["n_darks"]),
            "raw_shape": m["raw_shape"]}


def ladder_floor(g, sites, ctrl, thr):
    """Smallest planted amplitude whose ratio clears `thr`.

    RETURNS None WHEN NOTHING CLEARS. A search that cannot fail returns its
    least-bad candidate and calls it a find; this one is required to be able to
    come back empty, and the caller must handle that as UNRESOLVED rather than
    substituting the top rung.
    """
    rows, floor = [], None
    for a_dn in RUNGS:
        r = da.arm(da.plant(g, sites, a_dn), sites, ctrl)
        if r is None:
            rows.append({"amp_dn": a_dn, "ratio": None, "detected": None})
            continue
        det = r["ratio"] > thr
        rows.append({"amp_dn": a_dn, "ratio": r["ratio"], "detected": bool(det)})
        if det:
            floor = a_dn
    return floor, rows


def run(sub, thr):
    path = os.path.join(rimaxis.SEAL_DIR, sub + "--SHIP-V4.tiff")
    a = tifffile.imread(path)
    g = rimaxis.lum_of(a)
    del a
    sites, meta, _amp = da.load_sites(g.shape)
    ctrl = da.controls(g.shape, sites)
    rec = {"subject": sub, "shape": list(g.shape), "n_sites": len(sites),
           "n_ctrl": len(ctrl)}

    null = da.arm(g, sites, ctrl)
    if null is None:
        rec["outcome"] = "REFUSED"
        rec["why"] = "too few sites inside the frame"
        return rec
    rec["null_ratio"] = null["ratio"]
    rec["null_control_med"] = null["control_med"]
    rec["null_defect_med"] = null["defect_med"]

    floor, rows = ladder_floor(g, sites, ctrl, thr)
    rec["ladder"] = rows
    rec["floor_dn"] = floor

    top = RUNGS[0]
    imp = da.arm(ndimage.median_filter(da.plant(g, sites, top), size=3), sites, ctrl)
    planted_top = next(r["ratio"] for r in rows if r["amp_dn"] == top)
    rec["improve"] = {"top_dn": top, "planted_ratio": planted_top,
                      "repaired_ratio": imp["ratio"] if imp else None}

    # An arm is only evidence if it moved the right way. These are the gates.
    rec["null_ok"] = bool(rec["null_ratio"] <= thr)
    rec["ladder_ok"] = bool(floor is not None)
    rec["improve_ok"] = bool(
        imp is not None and planted_top > thr
        and imp["ratio"] < planted_top
        and abs(imp["ratio"] - rec["null_ratio"]) < abs(planted_top - rec["null_ratio"]))
    rec["outcome"] = ("COMMISSIONED"
                      if (rec["null_ok"] and rec["ladder_ok"] and rec["improve_ok"])
                      else "UNCOMMISSIONED")
    return rec


ACCESS_RE = re.compile(r"""\[\s*['"]power['"]\s*\]"""            # v["power"]
                       r"""|\.get\(\s*['"]power['"]"""           # v.get("power")
                       r"""|['"]power['"]\s+in\b""")             # "power" in v


def consults_power(src):
    """Does this source ACCESS a 'power' field, as opposed to talking about one?

    TWO WRONG ANSWERS WERE MEASURED BEFORE THIS ONE. The first version asked
    `"power" in source` and got True from the PASS message "no trails at or
    above this axis's power limit" -- prose about a rule read as the rule. The
    second stripped every string literal first and got False even on a genuine
    `v["power"]`, because a dictionary key IS a string literal; that arm was
    caught by this script's own commissioning rather than by review.

    So the test is syntactic and narrow: subscript, .get(), or membership. It
    answers the only question that matters -- whether the verdict reads the arm
    -- and it is commissioned against one function of each kind below.
    """
    return bool(ACCESS_RE.search(src))


def commission_reads_power():
    """Two planted verdict functions: one that only talks about power, one that
    uses it. The detector must separate them, or its answer about the real
    function is worthless.

    This is the arm the first version of this script did not have, which is why
    it reported a string literal as a code reference and its conclusion silently
    declined to fire. It then failed its own second version, which is the arm
    doing its job.
    """
    prose_only = ('def dust_verdict(s, dust):\n'
                  '    return "PASS", "no trails at or above this axis\'s power limit"\n')
    real_access = ('def dust_verdict(s, dust):\n'
                   '    if v["power"][0]["ratio"] < 1.0:\n'
                   '        return "REFUSED", "below this axis\'s power limit"\n')
    real_get = ('def dust_verdict(s, dust):\n'
                '    p = v.get("power")\n'
                '    if p is None:\n'
                '        return "REFUSED", "no power arm"\n')
    a = consults_power(prose_only)
    b = consults_power(real_access)
    c = consults_power(real_get)
    if a or not b or not c:
        raise SystemExit("DETECTOR UNCOMMISSIONED: prose-only %s (want False), "
                         "subscript %s (want True), .get %s (want True)" % (a, b, c))
    return {"prose_only": a, "subscript": b, "dot_get": c}


def main():
    thr = float(da.DUST_MAX)
    det = commission_reads_power()
    claim_hit, claim_miss = parse_claimed_floor()
    real = parse_real_amplitude()
    dust = json.load(io.open(da.OUT, encoding="utf-8"))

    print("THE AXIS UNDER TEST")
    print("  module            %s" % os.path.relpath(da.__file__, ROOT))
    print("  pass threshold    DUST_MAX = %.4f   (parsed from the module)" % thr)
    print("  site map loaded   %s" % os.path.relpath(da.MAP, ROOT))
    print("  published claim   detects %.0f DN, misses %.0f DN  (parsed from printcert4.py)"
          % (claim_hit, claim_miss))
    print()
    print("WHAT THE DARKS SAY IS ACTUALLY PRESENT  (from the map the axis loads)")
    print("  darks used        %d" % real["n_darks"])
    print("  sites found       %d, of which kept in the map %d"
          % (real["n_sites_total"], real["n_sites_kept"]))
    print("  cut               %.4f DN  (MAD-based, kept a site at all)" % real["cut_dn"])
    print("  excess threshold  %.1f DN  (dustmap.py EXCESS_DN -- a SELECTION CUT,"
          % real["cut_excess_dn"])
    print("                             not the worst site; see parse_real_amplitude)")
    print("  worst site amp    %.3f DN   <- the largest real defect on this sensor"
          % real["amp_max"])
    print("  median site amp   %.3f DN   <- what a typical mapped site carries"
          % real["amp_med"])
    print("  map raw_shape     %s" % real["raw_shape"])
    print()

    order = sorted(dust, key=lambda s: dust[s].get(SPAN_KEY, 0.0))
    picks = [order[0], order[len(order) // 3], order[2 * len(order) // 3], order[-1]]
    only = sys.argv[1:]
    if only:
        picks = only
    print("SUBJECTS, chosen to span the measured range of %s in dust.json" % SPAN_KEY)
    for s in picks:
        print("  %-38s %s = %8.1f" % (s, SPAN_KEY, dust[s].get(SPAN_KEY, float("nan"))))
    print()

    recs = []
    for i, s in enumerate(picks, 1):
        print("[%d/%d] %s" % (i, len(picks), s), flush=True)
        r = run(s, thr)
        recs.append(r)
        if r["outcome"] == "REFUSED":
            print("        REFUSED %s" % r["why"], flush=True)
            continue
        print("        null ratio %.4f  (control med %.1f)"
              % (r["null_ratio"], r["null_control_med"]), flush=True)
        for row in r["ladder"]:
            print("        plant %7.1f DN -> ratio %s  %s"
                  % (row["amp_dn"],
                     "  n/a " if row["ratio"] is None else "%6.4f" % row["ratio"],
                     "" if row["detected"] is None
                     else ("DETECTED" if row["detected"] else "missed")), flush=True)
        print("        floor      %s"
              % ("UNRESOLVED-ABOVE-TOP" if r["floor_dn"] is None
                 else "%.1f DN" % r["floor_dn"]), flush=True)
        print("        improvement %.1f DN planted %.4f -> repaired %.4f  %s"
              % (r["improve"]["top_dn"], r["improve"]["planted_ratio"],
                 r["improve"]["repaired_ratio"],
                 "moved back toward null" if r["improve_ok"] else "DID NOT RECOVER"),
              flush=True)
        print("        %s  (null_ok %s, ladder_ok %s, improve_ok %s)"
              % (r["outcome"], r["null_ok"], r["ladder_ok"], r["improve_ok"]), flush=True)
        print(flush=True)

    print("=" * 78)
    print("COMMISSIONING PARTITION -- every subject examined lands in exactly one")
    buckets = ("COMMISSIONED", "UNCOMMISSIONED", "REFUSED")
    counts = {b: sum(1 for r in recs if r["outcome"] == b) for b in buckets}
    for b in buckets:
        print("  %-16s %3d" % (b, counts[b]))
    tot = sum(counts.values())
    print("  %-16s %3d   (must equal %d examined)" % ("TOTAL", tot, len(recs)))
    if tot != len(recs):
        raise SystemExit("PARTITION DOES NOT SUM")

    print()
    print("THE VERDICT THIS SCRIPT EXISTS TO REACH")
    floors = [r["floor_dn"] for r in recs if r.get("floor_dn") is not None]
    unres = [r["subject"] for r in recs
             if r.get("outcome") != "REFUSED" and r.get("floor_dn") is None]
    if floors:
        print("  measured floor    best %.1f DN, worst %.1f DN over %d subject(s)"
              % (min(floors), max(floors), len(floors)))
    if unres:
        print("  no rung cleared   %s" % ", ".join(unres))
    print("  largest real defect %.3f DN (worst mapped site over %d darks)"
          % (real["amp_max"], real["n_darks"]))
    print("  typical real defect %.3f DN (median mapped site -- and the axis's"
          % real["amp_med"])
    print("                              statistic is a MEDIAN over sites, so this")
    print("                              is the amplitude it must actually resolve)")
    if floors:
        worst = max(floors)
        best = min(floors)
        r_max = worst / real["amp_max"]
        r_med = worst / real["amp_med"]
        print("  worst floor / worst real defect  %.2f x" % r_max)
        print("  worst floor / median real defect %.2f x" % r_med)
        print("  best  floor / worst real defect  %.2f x" % (best / real["amp_max"]))
        if best > real["amp_max"]:
            print("  => THE AXIS CANNOT SEE THIS SENSOR'S DEFECTS. Even its BEST measured")
            print("     floor sits %.2f x above the largest excess the darks record, and on"
                  % (best / real["amp_max"]))
            print("     %d of %d subjects examined no planted rung cleared at all. A PASS on"
                  % (len(unres), len(recs)))
            print("     this axis is silence, not a clean bill. Under the axis's own")
            print("     docstring rule those subjects are REFUSED, not PASS.")
        elif worst > real["amp_max"]:
            print("  => the axis reaches below the largest real defect on some subjects but")
            print("     not on others; a PASS is informative only where the floor is lower.")
        else:
            print("  => the axis reaches below the largest real defect; a PASS is informative.")

    print()
    print("IS THE POWER RULE ACTUALLY ENFORCED?")
    print("  detector commissioned: prose-only -> %s, subscript -> %s, .get -> %s"
          % (det["prose_only"], det["subscript"], det["dot_get"]))
    npow = sum(1 for v in dust.values() if "power" in v)
    src4 = io.open(os.path.join(GATHER, "printcert4.py"), encoding="utf-8").read()
    verdict = src4[src4.index("def dust_verdict"):]
    verdict = verdict[:verdict.index("\ndef ")]
    logic = strip_string_literals(verdict)
    reads_power = consults_power(verdict)
    mentions_in_prose = ("power" in verdict) and not reads_power
    print("  dust.json records carrying a power arm : %d of %d" % (npow, len(dust)))
    print("  dust_verdict() ACCESSES a power field  : %s" % reads_power)
    print("  ... mentions it only in prose          : %s" % mentions_in_prose)
    if npow == 0 and not reads_power:
        print("  => the power rule is DISCLOSED IN PROSE AND ENFORCED NOWHERE. The axis")
        print("     docstring says a subject whose defects sit below the detection floor")
        print("     'is REFUSED rather than passed', but no record carries the arm and the")
        print("     verdict function never consults it. This is print-then-TEST: a value")
        print("     computed, published in a footnote, and conditioned on by nothing.")
        print("     dustaxis.main() calls run_subject(s) with commission defaulting to")
        print("     False, so the ladder that would have produced the arm never ran on the")
        print("     delivered path.")

    out = os.path.join(OUTDIR, "70-dustaxis-power.json")
    json.dump({"threshold": thr, "claim": [claim_hit, claim_miss], "real": real,
               "rungs": list(RUNGS), "subjects": recs,
               "detector": det, "prose_only_mention": mentions_in_prose,
               "power_records": npow, "verdict_reads_power": reads_power},
              io.open(out, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
