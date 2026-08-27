"""Commission the acquittal wiring in orch_printready.py -- BOTH directions.

WHY THIS FILE EXISTS

`orch_printready.py` now carries adjudicated acquittals: nine subjects that read
high on a subject-dependent statistic were measured against their own source
frames by an independent lane, found no worse, and are recorded ACQUIT. The gate
consults that record and downgrades REVIEW to ACQUIT.

That is a mechanism for turning a flag into a pass, which is exactly the shape of
thing that quietly disables a gate. Nine of twenty-six masters now clear on a
stored opinion rather than on today's measurement. If the expiry does not
actually fire, this project has switched off a third of its own gate and would
not be able to tell.

    THE GREEN RUN OF A GATE WITH NINE STORED ACQUITTALS IS NOT EVIDENCE THE
    MASTERS ARE CLEAN. IT IS EVIDENCE THE LOOKUP SUCCEEDED. Those are different
    claims and only one of them was tested by running the gate.

So this commissions the acquittal logic directly, against synthetic measurements
derived from the real baseline, in both directions:

  - a movement the acquittal MUST NOT survive (the defect arm), and
  - a movement it MUST survive (the improvement-class arm).

The second arm is the one that is easy to skip and the one that matters. A check
that expires on everything passes every defect arm ever written and is useless,
because it converts the acquittal into a permanent REVIEW. This project has
already caught two instruments that were bounded in one direction -- one whose
error could not go below zero, one that scored a planted ring as a gain -- and
both passed their degradation arms perfectly.

WHAT THIS DOES NOT TEST. It does not test that the nine adjudications are
CORRECT. That was the other lane's work and rests on its source-frame
registration. This file tests only that the gate faithfully applies them and
faithfully stops applying them.
"""
import json
import sys

from orch_printready import (ACQUIT_TOL, ACQUIT_WINDOW_TOL, BLOTCH_REVIEW,
                             check_acquittal, load_baseline)

SUBJECT = "coffee-bubbles"   # tripped BOTH statistics, so both paths are live


def arm(name, must_acquit, subs, meas, why):
    applies, note = check_acquittal(SUBJECT, meas, subs)
    ok = (applies == must_acquit)
    print("%-4s %-22s want=%-7s got=%-7s  %s"
          % ("PASS" if ok else "FAIL", name,
             "ACQUIT" if must_acquit else "EXPIRE",
             "ACQUIT" if applies else "EXPIRE", why))
    if not ok:
        print("       note: %s" % note)
    return ok


def main():
    subs, prov = load_baseline()
    if SUBJECT not in subs:
        raise SystemExit("commissioning cannot run: %r absent from baseline (%s).\n"
                         "This is a HARD ERROR, not a skip -- a commissioning that\n"
                         "silently finds nothing to test reports the same green as\n"
                         "one that tested everything." % (SUBJECT, prov))
    base = subs[SUBJECT]["master"]
    b0, c0 = base["blotch"], base["chroma"]
    w0 = base["blotch_window_yx"]
    print("baseline %s: blotch %.5f  chroma %.5f  window %s" % (SUBJECT, b0, c0, w0))
    print("tolerances: value %.0f%%  window %d px\n" % (ACQUIT_TOL * 100, ACQUIT_WINDOW_TOL))

    def meas(b=None, c=None, w=None):
        return {"blotch": b if b is not None else b0,
                "chroma": c if c is not None else c0,
                "blotch_window_yx": list(w if w is not None else w0)}

    res = []
    # --- DEFECT ARMS: the acquittal must NOT survive these -------------------
    res.append(arm("blotch +12%", False, subs, meas(b=b0 * 1.12),
                   "render moved the statistic well past tolerance"))
    res.append(arm("blotch -12%", False, subs, meas(b=b0 * 0.88),
                   "movement toward BETTER still expires: nobody adjudicated it"))
    res.append(arm("chroma +30%", False, subs, meas(c=c0 * 1.30),
                   "the other tripped statistic must expire independently"))
    res.append(arm("window +40 px", False, subs, meas(w=[w0[0] + 40, w0[1]]),
                   "measured somewhere else; the values are not comparable"))

    # --- HOLD ARMS: the acquittal MUST survive these -------------------------
    # Without these, a check that expires unconditionally scores a perfect run.
    res.append(arm("blotch +2%", True, subs, meas(b=b0 * 1.02),
                   "inside the gate's own +/-2-3%% irreproducible scatter"))
    res.append(arm("window +4 px", True, subs, meas(w=[w0[0] + 4, w0[1] + 4]),
                   "flattest() tie-break jitter, not a different measurement"))
    res.append(arm("unchanged", True, subs, meas(),
                   "the adjudicated numbers themselves must still acquit"))
    # A statistic that drifted hard but now sits BELOW its review threshold is
    # not tripping the gate at all, so its adjudication is not load-bearing.
    res.append(arm("blotch below thresh", True, subs, meas(b=BLOTCH_REVIEW * 0.5),
                   "no longer trips review, so its drift cannot expire anything"))

    # --- RECORD ARMS ---------------------------------------------------------
    bad = dict(subs)
    bad[SUBJECT] = dict(subs[SUBJECT], verdict="CONVICT")
    res.append(arm("verdict CONVICT", False, bad, meas(),
                   "only ACQUIT acquits; any other recorded verdict must not"))
    res.append(arm("no record", False, {}, meas(),
                   "an unknown subject is never acquitted by default"))

    n_ok = sum(res)
    print("\n%d/%d arms pass (%d defect-direction, %d hold-direction)"
          % (n_ok, len(res), 6, 4))
    if n_ok != len(res):
        print("COMMISSIONING FAILED. The acquittal wiring must not be trusted and\n"
              "the nine ACQUIT verdicts in the gate mean nothing until it passes.")
        return 1
    print("Commissioned: the acquittal expires on real movement in EITHER\n"
          "direction and survives the gate's own known scatter. The nine ACQUIT\n"
          "rows are therefore statements about today's numbers, not stored opinions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
