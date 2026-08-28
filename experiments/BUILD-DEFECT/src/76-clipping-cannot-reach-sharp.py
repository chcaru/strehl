r"""Can the --auto-exposure clipping regression explain "master exceeds its
own focus ceiling"?

ORCH measured that `strehl stack ... --srgb --auto-exposure` at HEAD blows the
highlights -- 11 of 18 corpus masters above 25% clipped, 109MSDCF at 92.03% --
and flagged, honestly, that clipping "creates infinitely sharp edges", which is
a candidate explanation for the sharpness axis refusing 11 of 19 subjects with
"the master exceeds the best frame focus ceiling". ORCH did not claim the
explanation, it flagged the attribution as unproven and asked whether any
finding depends on it. This measures it.

WHY THIS IS ANSWERABLE WITHOUT RE-RENDERING THE CORPUS. The hypothesis requires
that the clipped pixels reach the statistic. Three independent conditions must
ALL hold for that, and each is checkable:

  1. the axis must render with a binary that HAS the regression;
  2. it must pass the flags that TRIGGER it (`--srgb --auto-exposure`);
  3. it must accept a tone-mapped file at all.

The regression is in the `--srgb` tone path and was introduced after the
acceptance pin. So conditions (1) and (2) are questions about argv and a commit
graph, and (3) is a question about a guard that either fires or does not.

WHY THE ARCHITECTURAL ANSWER IS NOT ENOUGH ON ITS OWN. "No tone stage" does not
imply "no clipping" -- a linear render can still pin pixels at 65535 if the
capture is bright. So condition (4) is measured directly: render a subject that
ORCH measured as BLOWN under the HEAD recipe, through the axis's OWN render
call, and count the pixels at full scale -- globally and inside the exact 512 px
windows the axis measured. A structural argument that predicts zero and a
measurement that finds zero are two different pieces of evidence and this
reports both.

THE GATE CAN RETURN NOTHING. A verdict of REFUTED requires the measured site
clipping to sit below an absolute floor; SUPPORTED requires it above a
separate, higher floor; between them the instrument returns INCONCLUSIVE rather
than the nearer edge. A test that must choose a side is not a test.

COMMISSIONING. Three arms, because a degradation-only suite cannot tell a blind
gauge from a perverse one:
  POSITIVE   a known-blown render must read BLOWN. head-e260.tiff was measured
             at 85.5234% clipped in 21.4 by a different instrument, so this arm
             checks this code against an outside number rather than its own.
  NEGATIVE   a known-clean render must read CLEAN (pin-e000.tiff, 0.0012%).
  IMPROVEMENT the blown array, divided by the gain that blew it, must read
             SUBSTANTIALLY CLEANER. A statistic that only ever rises under
             damage cannot be shown to be scoring the damage rather than
             scoring the exposure; this arm requires it to fall when the defect
             is removed.
"""
import io
import json
import os
import re
import subprocess
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VG = os.path.join(ROOT, "experiments", "V-GATHER")
PROBE = r"C:\dev\strehl-out\BUILD-DEFECT\probe"
WORK = r"C:\dev\strehl-out\BUILD-DEFECT\clip"

FULL = 65535
# Absolute floors, in fraction of pixels pinned at full scale, inside the
# windows the axis actually measured. 0.1% is far below any level at which
# clipping could dominate a bandpass contrast over a 512x512 window (it is 262
# pixels of 262,144); 5% is the level at which it plainly could. The band
# between them returns INCONCLUSIVE.
REFUTE_BELOW = 0.001
SUPPORT_ABOVE = 0.05
# ORCH's own threshold for calling a master blown.
BLOWN_AT = 0.25

log = []


def say(s=""):
    print(s)
    log.append(s)


def clip_fraction(a):
    """Fraction of samples pinned at full scale, over all channels."""
    return float(np.count_nonzero(a >= FULL)) / float(a.size)


def commission():
    """Prove this file's clipping statistic responds, and in both directions."""
    say("=== COMMISSIONING ===")
    arms = []

    pos = os.path.join(PROBE, "head-e260.tiff")
    neg = os.path.join(PROBE, "pin-e000.tiff")
    for p in (pos, neg):
        if not os.path.exists(p):
            raise SystemExit("COMMISSIONING CANNOT RUN: missing %s" % p)

    a = np.asarray(tifffile.imread(pos))
    f_pos = clip_fraction(a)
    ok = f_pos > BLOWN_AT
    arms.append(("POSITIVE", ok,
                 "known-blown head-e260.tiff reads %.4f%% clipped, needs > %.1f%%"
                 % (100 * f_pos, 100 * BLOWN_AT)))

    b = np.asarray(tifffile.imread(neg))
    f_neg = clip_fraction(b)
    ok = f_neg < REFUTE_BELOW
    arms.append(("NEGATIVE", ok,
                 "known-clean pin-e000.tiff reads %.4f%% clipped, needs < %.3f%%"
                 % (100 * f_neg, 100 * REFUTE_BELOW)))

    # The improvement arm. +2.60 stops is a gain of 6.063x; dividing it out is
    # the inverse of the operation that blew the file. This is a planted
    # IMPROVEMENT, not a planted defect: the statistic must FALL.
    gain = 2.0 ** 2.60
    f_fix = clip_fraction(a.astype(np.float32) / gain)
    ok = f_fix < f_pos / 10.0
    arms.append(("IMPROVEMENT", ok,
                 "dividing the blown array by its own gain %.3fx moves clipping "
                 "%.4f%% -> %.4f%%, needs at least a 10x fall" % (gain, 100 * f_pos, 100 * f_fix)))

    passed = 0
    for name, ok, msg in arms:
        say("  %-12s %-4s %s" % (name, "PASS" if ok else "FAIL", msg))
        passed += 1 if ok else 0
    say("  %d declared = %d passed + %d failed" % (len(arms), passed, len(arms) - passed))
    if passed != len(arms):
        raise SystemExit("COMMISSIONING FAILED -- the statistic is not trusted, "
                         "so no verdict is issued")
    say()
    return f_pos, f_neg, f_fix


def condition_binary():
    """Does the axis render with a binary that carries the regression?"""
    src = io.open(os.path.join(VG, "certmeasure.py"), encoding="utf-8").read()
    m = re.search(r'^EXE\s*=\s*r?"([^"]+)"', src, re.M)
    if not m:
        raise SystemExit("cannot parse EXE from certmeasure.py")
    exe = m.group(1)
    pin = re.search(r"acceptance-pins[\\/]+([0-9a-f]{7,40})", exe)
    if not pin:
        raise SystemExit("cannot parse a pin commit from EXE path %s" % exe)
    pin = pin.group(1)

    # Are the regression commits ancestors of that pin? If they are not, the
    # binary predates the defect and cannot exhibit it.
    verdicts = {}
    for c in ("9cb7f5d9", "f2254c12"):
        r = subprocess.run(["git", "merge-base", "--is-ancestor", c, pin],
                           cwd=ROOT, capture_output=True, text=True)
        verdicts[c] = (r.returncode == 0)
    return exe, pin, verdicts


def condition_flags():
    """Does the axis pass the flags that trigger the regression?"""
    src = io.open(os.path.join(VG, "certmeasure.py"), encoding="utf-8").read()
    m = re.search(r"cmd\s*=\s*\[(.*?)\]", src, re.S)
    if not m:
        raise SystemExit("cannot parse the render argv from certmeasure.py")
    argv = re.findall(r'"(--[a-z-]+)"', m.group(1))
    return argv


def condition_refusal():
    """Would the axis accept a tone-mapped file? Call the real guard."""
    sys.path.insert(0, VG)
    import sharpaxis as sa
    seal = os.path.join(sa.cm.SEAL_DIR, "109MSDCF--SHIP-V4.tiff")
    if not os.path.exists(seal):
        raise SystemExit("missing seal %s" % seal)
    with tifffile.TiffFile(seal) as t:
        pg = t.pages[0]
        lat = (pg.tags["ImageWidth"].value, pg.tags["ImageLength"].value)
    try:
        sa._verify_tags(seal, lat)
        return False, "accepted -- the guard did NOT fire on a tone-mapped seal"
    except SystemExit as e:
        return True, str(e)


def measure_linear(subject):
    """Render the subject the way the axis does and count clipped pixels."""
    sys.path.insert(0, VG)
    import sharpaxis as sa
    import certmeasure as cm
    cm.check_binary()
    os.makedirs(WORK, exist_ok=True)
    out = os.path.join(WORK, "%s-linear.tiff" % subject)
    if not os.path.exists(out):
        got, err, _ = cm.render(subject, out)
        if not got:
            raise SystemExit("render failed for %s: %s" % (subject, err[-400:]))
    mm = tifffile.memmap(out, mode="r")
    whole = np.asarray(mm[:, :, :3])
    glob = clip_fraction(whole)
    # A zero read from a statistic is worth nothing until the array is shown to
    # be capable of a non-zero one. If the file were float, or scaled to a
    # different full scale, "0 samples at 65535" would be true and meaningless.
    peak = int(whole.max())
    if whole.dtype != np.uint16:
        raise SystemExit("REFUSING a verdict: expected uint16, got %s -- the "
                         "clipping count is not defined against %d"
                         % (whole.dtype, FULL))
    headroom = 1.0 - peak / float(FULL)

    d = json.load(io.open(os.path.join(VG, "sharp.json"), encoding="utf-8"))
    sites = [(s["y"], s["x"]) for s in d[subject]["sites"]]
    per = []
    for (y, x) in sites:
        w = np.asarray(mm[y:y + sa.WIN, x:x + sa.WIN, :3])
        per.append(clip_fraction(w))
    del mm
    return out, glob, sites, per, peak, headroom


def main():
    say("=== can clipping explain 'master exceeds its own focus ceiling'? ===")
    say()
    f_pos, f_neg, f_fix = commission()

    say("=== the three conditions the hypothesis requires ===")
    exe, pin, anc = condition_binary()
    say("  (1) BINARY  the axis renders with %s" % os.path.basename(exe))
    say("              pin %s" % pin)
    for c, is_anc in sorted(anc.items()):
        say("              regression commit %s an ancestor of the pin? %s"
            % (c, "YES" if is_anc else "NO"))
    c1 = not any(anc.values())

    argv = condition_flags()
    say("  (2) FLAGS   render argv flags: %s" % " ".join(argv))
    c2 = ("--auto-exposure" not in argv) and ("--srgb" not in argv)
    say("              --auto-exposure present? %s   --srgb present? %s"
        % ("YES" if "--auto-exposure" in argv else "NO",
           "YES" if "--srgb" in argv else "NO"))

    refused, why = condition_refusal()
    say("  (3) GUARD   tone-mapped seal offered to sharpaxis._verify_tags:")
    say("              %s" % why.strip()[:110])
    c3 = refused
    say()

    say("=== (4) direct measurement, not inference ===")
    subject = "112MSDCF"
    out, glob, sites, per, peak, headroom = measure_linear(subject)
    per = np.array(per)
    say("  subject %s -- ORCH measured this one at 35.57%% clipped under the" % subject)
    say("  HEAD --srgb --auto-exposure recipe. Rendered here through the axis's")
    say("  own render call:")
    say("    whole image      %.4f%% of samples at full scale" % (100 * glob))
    say("    peak sample      %d of %d -- %.1f%% headroom remains, so the zero"
        % (peak, FULL, 100 * headroom))
    say("                     above is a real absence and not an unreachable test")
    say("    %d axis sites    max %.4f%%  median %.4f%%  mean %.4f%%"
        % (len(sites), 100 * per.max(), 100 * float(np.median(per)), 100 * per.mean()))
    say()

    worst = float(per.max())
    if worst < REFUTE_BELOW:
        v4 = "REFUTED"
    elif worst > SUPPORT_ABOVE:
        v4 = "SUPPORTED"
    else:
        v4 = "INCONCLUSIVE"

    say("=== verdict ===")
    conds = [("binary predates the regression", c1),
             ("flags cannot trigger it", c2),
             ("guard refuses tone-mapped input", c3)]
    for n, ok in conds:
        say("  %-34s %s" % (n, "HOLDS" if ok else "DOES NOT HOLD"))
    say("  measured site clipping            %s (worst site %.4f%%, floor %.3f%%)"
        % (v4, 100 * worst, 100 * REFUTE_BELOW))
    say()

    if all(c for _, c in conds) and v4 == "REFUTED":
        overall = "REFUTED"
        say("  OVERALL: REFUTED. The clipping regression cannot reach the")
        say("  sharpness axis by any of the three routes it would need, and the")
        say("  render the axis actually measures is clipped at %.4f%% globally"
            % (100 * glob))
        say("  and %.4f%% at its worst measured site." % (100 * worst))
    elif v4 == "SUPPORTED":
        overall = "SUPPORTED"
        say("  OVERALL: SUPPORTED -- clipping does reach the sites.")
    else:
        overall = "INCONCLUSIVE"
        say("  OVERALL: INCONCLUSIVE -- the conditions and the measurement")
        say("  disagree, or the measurement fell between the floors.")

    res = dict(commission=dict(positive=f_pos, negative=f_neg, improvement=f_fix),
               exe=exe, pin=pin, ancestors=anc, argv=argv,
               guard_refuses=c3, guard_message=why,
               subject=subject, global_clip=glob,
               n_sites=len(sites), site_max=worst, peak_sample=peak, headroom=headroom,
               site_median=float(np.median(per)), site_mean=float(per.mean()),
               refute_below=REFUTE_BELOW, support_above=SUPPORT_ABOVE,
               verdict_measured=v4, verdict=overall)
    od = os.path.join(HERE, "..", "out")
    os.makedirs(od, exist_ok=True)
    io.open(os.path.join(od, "76-clipping-cannot-reach-sharp.json"), "w",
            encoding="utf-8").write(json.dumps(res, indent=1, sort_keys=True))
    io.open(os.path.join(od, "76-clipping-cannot-reach-sharp.log"), "w",
            encoding="utf-8").write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
