r"""Print certification of the 26 delivered masters, on gauges that support it.

WHAT WAS WRONG WITH THE PREVIOUS CERTIFICATION, and why this is not just a
re-run with a different flag.

  1 THE BASELINE WAS THE WORST FRAME. The rule frozen at
    experiments/V-REVIEW/vr_baseline.json:7 is "max over registered source
    frames". For blotch and chroma, LOW IS GOOD, so the max is the WORST frame
    available. Nine subjects were acquitted for being cleaner than the worst
    frame in their own stack. That is nearly free.

  2 THE RATIO WAS TAKEN ACROSS TWO DIFFERENT TONE CURVES. --srgb fits black and
    white points from EACH IMAGE'S OWN luminance percentiles
    (crates/strehl-cli/src/image_out.rs:165-176). A 123-frame master and a
    single source frame therefore sit on two different content-derived nonlinear
    curves. blotch = band/mean survives a linear gain; it does not survive a
    fitted curve. Forcing --exposure does not defend it: measured, --exposure 6
    commands 64x and changes 0 of 98,898,048 samples, delivered gain 1.0000000,
    because both percentiles are linear in the data so the normalised result is
    invariant. There is no gain that could have survived it.

  3 THE BANDING TERM IS PINNED AT ITS OWN FLOOR (found here). banding() returns
    median(diff(indices where rounded luma changes)), which is bounded below by
    1 by construction. All 26 masters read run = 1.0px against BAND_RUN_MIN 4.0.
    The FAIL path needs run >= 4 AND step >= 4; run can never reach 4, so the
    conjunction can never fire and the only live FAIL term is clip > 0.1%.
    A gate term that cannot fire is not a lenient gate, it is an absent one.

THE DESIGN THAT FIXES IT: TWO QUESTIONS, TWO GAUGES, ON PURPOSE.

  IS IT VISIBLE?  Absolute, measured on the DELIVERED sRGB file. This is not
  defect 2 repeated. Defect 2 is a defect in RATIOS -- two images on two curves.
  A single absolute reading on the file the printer actually receives is
  display-referred by definition, and no other gauge answers "will a person see
  this". Thresholds keep their original calibration BECAUSE THE GAUGE DID NOT
  MOVE: they were calibrated on --srgb and are applied to --srgb. That is
  re-justification, not re-derivation, and it is stated as such.

  DID THE MERGE CAUSE IT?  A ratio on a MATCHED --linear-srgb --demosaic pair,
  master against the best source frame, both rendered by the same sealed binary
  in the same run. The decision point is 1.0, which requires no calibration on
  any gauge -- only that numerator and denominator share one. This is why the
  linear gauge does not need thresholds ported onto it.

  A PRINT DEFECT IS VISIBLE **AND** ATTRIBUTABLE. Mottling the sources carry
  just as strongly is the subject's own texture -- it is the photograph. That
  distinction is what the previous gate intended and then computed against the
  wrong frame.

THE BASELINE IS FOCUS-QUALIFIED, and that is not decoration. Blur removes
mid-scale band energy, so a plain argmin over a focus stack tends to elect the
most defocused frame and the denominator becomes defocus. certcommission.py
demonstrates it: a planted blurred frame wins the plain argmin at EVERY blur
radius tested, down to r=1. Measured on real subjects the confound is small,
because the window is chosen as the flattest region and flat regions are
focus-insensitive -- but that is a measurement reported below, not an assumption.
"""
import io
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# The rule is a STRING and every operator-facing label is DERIVED FROM IT. The
# previous gate printed "master/best-source" beside a rule that said "max",
# because the label was typed by hand next to a rule that later changed.
BEST_RULE = "min over focus-qualified registered source frames"
WORST_RULE = "max over registered source frames"
FOCUS_FLOOR = 0.50
SEAL_DIR = r"C:\dev\strehl-out\acceptance\SHIP-V4"

# Calibrated on --srgb by the original gate; applied here to --srgb. Re-justified
# by gauge identity, NOT re-derived. Raising them would be my judgement standing
# in for the owner's eyes, so they are left where he last accepted them.
VIS_BLOTCH = 0.02
VIS_CHROMA = 0.015
CLIP_MAX = 0.001


def label_for(rule):
    """Derive the operator label from the rule. Never typed."""
    r = rule.strip().lower()
    if r.startswith("min"):
        return "master/best-source"
    if r.startswith("max"):
        return "master/worst-source"
    raise SystemExit("cannot derive a label from rule %r -- refusing to guess" % rule)


COVERAGE_MIN = 0.60


def coverage(v):
    """How much of the bracket does the surviving candidate set actually span?

    Source frames are emitted in their own geometry, so the master's window has
    to be re-found in each one by an integer shift; where focus breathing has
    carried that content off the sensor there is no data and the frame is
    refused. Those refusals are not uniform. Measured: coffee-bubbles keeps
    frames 0-4 of 19, leaf-2-cpl keeps 0-65 of 182, and couch-fibers-cpl keeps
    162-270 of 299 -- each a single focus regime rather than the stack.

    A minimum over five frames from one end of a bracket is not "the best source
    frame", it is the best frame of one focus regime, and it sits systematically
    HIGH because a minimum over a smaller set can only be larger. That inflates
    the ratio exactly where coverage is worst, and coverage is worst on the
    deepest stacks -- which is why the ratio still tracked stack depth at
    rho +0.87 after registration. Refuse those rather than report them.
    """
    src = [x for x in v.get("sources", []) if "blotch" in x]
    sampled = max(1, len(v.get("sampled", [])))
    if not src:
        return 0.0, 0.0, 0, sampled
    ks = [x["k"] for x in src]
    span = (max(ks) - min(ks)) / max(1, v["n_frames"] - 1)
    return len(src) / sampled, span, len(src), sampled


def best_index(blotch, focus):
    hi = max(focus)
    keep = [i for i in range(len(blotch)) if focus[i] >= FOCUS_FLOOR * hi]
    if not keep:
        return None, 0
    return min(keep, key=lambda i: blotch[i]), len(keep)


def price_sampling_bias(cert):
    """min-over-K >= min-over-N, so subsampling FLATTERS the master.

    Priced, not assumed, from the subjects measured exhaustively: take the true
    min over all frames and the min over a 12-point linspace subsample of the
    same frames, and report the worst inflation seen. That number becomes the
    margin, so the margin is measured rather than chosen.
    """
    worst, rows = 1.0, []
    for s, v in cert.items():
        if not v.get("done") or not v.get("exhaustive"):
            continue
        src = [x for x in v["sources"] if "blotch" in x]
        if len(src) < 14:
            continue
        b = [x["blotch"] for x in src]
        f = [x["focus_win"] for x in src]
        i_all, _ = best_index(b, f)
        idx = sorted(set(np.linspace(0, len(src) - 1, 12).astype(int).tolist()))
        i_sub, _ = best_index([b[i] for i in idx], [f[i] for i in idx])
        infl = b[idx[i_sub]] / b[i_all]
        rows.append((s, len(src), infl))
        worst = max(worst, infl)
    return worst, rows


def main():
    deliv = json.load(io.open(os.path.join(HERE, "delivered.json"), encoding="utf-8"))
    population = sorted(f[:-len("--SHIP-V4.tiff")] for f in os.listdir(SEAL_DIR)
                        if f.endswith("--SHIP-V4.tiff"))
    if not population:
        raise SystemExit("no sealed masters found -- refusing to certify nothing")
    # CROSS-CHECK THE POPULATION AGAINST AN INDEPENDENT COUNT. "running ==
    # len(population)" is self-consistent and therefore proves nothing: a
    # population truncated to twenty would sum to twenty and read as complete.
    # The .ok seals are written per master by the acceptance harness, so they are
    # a second, independently produced census of the same set.
    seals = [f for f in os.listdir(SEAL_DIR) if f.endswith(".tiff.ok")]
    if len(seals) != len(population):
        raise SystemExit("POPULATION DISAGREES WITH SEALS: %d masters, %d seals"
                         % (len(population), len(seals)))
    cert = {}
    cp = os.path.join(HERE, "cert.json")
    if os.path.exists(cp):
        cert = json.load(io.open(cp, encoding="utf-8"))

    margin, bias_rows = price_sampling_bias(cert)
    print("SAMPLING BIAS -- priced from exhaustively measured subjects")
    if bias_rows:
        for s, n, infl in bias_rows:
            print("  %-24s n=%-3d min-over-12 / min-over-all = %.4f" % (s, n, infl))
    else:
        print("  none available yet")
    print("  margin adopted: ratio must exceed %.4f to be called attributable\n" % margin)

    buckets = {"PASS": [], "FAIL": [], "SUBJECT": [], "REFUSED": [], "NOT EXAMINED": []}
    lab_best, lab_worst = label_for(BEST_RULE), label_for(WORST_RULE)

    print("%-24s %8s %8s %7s  %9s %9s  %s"
          % ("subject", "blotch", "chroma", "clip%", lab_worst, lab_best, "verdict"))
    print("-" * 108)

    # The population is the SEAL DIRECTORY, not the results file. Iterating the
    # results would make a subject that was never measured disappear from the
    # denominator instead of appearing as NOT EXAMINED -- the exact ambiguity
    # this partition exists to remove.
    for s in sorted(population):
        if s not in deliv:
            buckets["NOT EXAMINED"].append((s, "no delivered-file measurement"))
            print("%-24s %8s %8s %7s  %9s %9s  %s"
                  % (s, "-", "-", "-", "-", "-", "NOT EXAMINED"))
            continue
        d = deliv[s]
        vis = []
        if d["blotch"] > VIS_BLOTCH:
            vis.append("blotch %.4f > %.3f" % (d["blotch"], VIS_BLOTCH))
        if d["chroma"] > VIS_CHROMA:
            vis.append("chroma %.4f > %.3f" % (d["chroma"], VIS_CHROMA))
        if d["clip"] > CLIP_MAX:
            vis.append("clip %.4f%% > %.2f%%" % (d["clip"] * 100, CLIP_MAX * 100))

        rw = rb = None
        cov_note = None
        v = cert.get(s)
        if v and v.get("done"):
            uf, sf, used, samp = coverage(v)
            if uf < COVERAGE_MIN or sf < COVERAGE_MIN:
                cov_note = ("candidate set covers %.0f%% of sampled frames and "
                            "%.0f%% of the bracket (%d of %d usable) -- below %.0f%%"
                            % (100 * uf, 100 * sf, used, samp, 100 * COVERAGE_MIN))
                v = None
        if v and v.get("done"):
            src = [x for x in v["sources"] if "blotch" in x]
            if src:
                b = [x["blotch"] for x in src]
                f = [x["focus_win"] for x in src]
                mb = v["master"]["blotch"]
                i_b, _ = best_index(b, f)
                rw, rb = mb / max(b), (mb / b[i_b] if i_b is not None else None)

        if not vis:
            bucket, why = "PASS", "below visibility on the delivered file"
        elif rb is None:
            bucket, why = "REFUSED", "visible (%s) but %s" % (
                "; ".join(vis),
                cov_note or "no matched-gauge attribution measured")
        elif rb > margin:
            bucket, why = "FAIL", "visible (%s) and %s = %.3f > %.3f" % ("; ".join(vis), lab_best, rb, margin)
        else:
            bucket, why = "SUBJECT", "visible (%s) but %s = %.3f -- the sources carry it" % ("; ".join(vis), lab_best, rb)

        buckets[bucket].append((s, why))
        print("%-24s %8.5f %8.5f %7.4f  %9s %9s  %s"
              % (s, d["blotch"], d["chroma"], d["clip"] * 100,
                 "%.4f" % rw if rw is not None else "-",
                 "%.4f" % rb if rb is not None else "-", bucket))

    total = len(population)
    print("\nPARTITION -- every delivered master lands in exactly one bucket")
    running = 0
    for k in ("PASS", "FAIL", "SUBJECT", "REFUSED", "NOT EXAMINED"):
        running += len(buckets[k])
        print("  %-14s %3d" % (k, len(buckets[k])))
    print("  %-14s %3d  (must equal %d)" % ("TOTAL", running, total))
    if running != total:
        raise SystemExit("PARTITION DOES NOT SUM: %d != %d" % (running, total))

    for k in ("FAIL", "REFUSED", "SUBJECT", "NOT EXAMINED"):
        if buckets[k]:
            print("\n%s" % k)
            for s, why in buckets[k]:
                print("  %-24s %s" % (s, why))

    print("""
NOT CERTIFIED BY THIS INSTRUMENT -- applies to all 26, not to a subset.
  This measures mid-scale luminance mottling, chroma mottling and clipping.
  It does NOT measure: halos or ringing at edges (the owner's single loudest
  complaint about this tool), sharpness or resolution, sensor dust (known,
  located and unfixed), or structure finer than 50px or coarser than 400px.
  A PASS here is silence on those, not a clean bill. Anyone reading these
  counts as "print-ready" is reading roughly a third of what ruins a print.""")


if __name__ == "__main__":
    main()
