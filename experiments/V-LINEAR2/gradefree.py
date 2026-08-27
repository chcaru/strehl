"""THE ACCEPTANCE GATE, re-run against the free field on linear inputs.

This is the test the V-LINEAR brief names as decisive, and PREREGISTRATION.md
sec.4 item 3 fixes its threshold: the 4x4-block tone fit must explain LESS THAN
50% of the measured fine-scale gap, or the comparison is a tone measurement
again and no band number may be reported.

WHAT COLLAPSE LOOKS LIKE, pre-registered before this was run.  Against Zerene on
Lightroom-developed TIFFs, V-HEADTOHEAD2 sec.4.5 measured a block-average tone
fit reproducing the comparator's fine bands from strehl's own pixels to 0.02%,
accounting for 100.0% of the gap at 0.25-0.30, 89.1% at 0.20-0.25 and 212% at
0.30-0.40, on a fitted log-log slope of median 0.177 (1.000 == identical tone).
Here both arms are fed strehl's OWN linear develops, so if the develops really
did remove the confound:
    * the fitted slope must sit near 1.000, not 0.177;
    * the fraction of gap explained must fall well under 50%;
    * ideally there is no gap at the coarse bands at all to explain.
If the slope is still far from 1, the arms are still tonally different and
nothing downstream is a resolution measurement.

NOTHING IN gradetest.py IS MODIFIED.  It reads its comparator config out of
h2h2b.COMP, and `from h2h2b import COMP` binds the same dict object, so
registering entries here is visible to it.  That is deliberate reuse of the
prior lane's committed instrument, which is what the brief asked for.

INVOCATION (rule 47).  Reads:
    strehl      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-full-g1.tiff
    comparator  C:\\dev\\strehl-out\\V-LINEAR2\\out\\*.tif  (run_free.ps1)
Writes nothing.  Prints only.

    python gradefree.py <tag> [nroi=48]     tag in {enfuse, fs15, fsfork}
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2h2b                                                     # noqa: E402
import gradetest                                                 # noqa: E402
from h2free import FREE                                          # noqa: E402


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in FREE:
        print(f"usage: python gradefree.py <{'|'.join(FREE)}> [nroi]")
        return 2
    tag = sys.argv[1]
    cfg = FREE[tag]
    if cfg["scale"] is None:
        print(f"scale for {tag} not measured yet -- run `python geomfree.py "
              f"{tag}` and paste the interior maximum into h2free.FREE.")
        return 2
    if not os.path.exists(cfg["path"]):
        print(f"comparator output missing: {cfg['path']}")
        return 2

    # gradetest derives BOTH the comparator config key and the strehl render
    # tag from its single argv[1], so the key must be the frame-set tag "113"
    # in order to load 113-full-g1.tiff.  Registering there is an IN-MEMORY
    # rebind in this driver process only; experiments/V-HEADTOHEAD2/h2h2b.py is
    # not touched on disk and still points at the Zerene TIFF for anyone else.
    #
    # The standing warning is that h2h2b.COMP["113"] must never be repointed
    # and the result then reported as if it were the Zerene comparison.  That
    # is why both paths are printed here, unmissably, before any number.
    print("=" * 104)
    print("COMPARATOR REBIND -- in memory, this process only")
    print(f"  strehl arm      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-full-g1.tiff")
    print(f"  comparator arm  {cfg['path']}")
    print(f"                  {cfg['label']}")
    print(f"  NOT the Zerene TIFF at {h2h2b.COMP['113']['path']}")
    print(f"  scale {cfg['scale']:.4f} measured by geomfree.py")
    print("=" * 104)
    h2h2b.COMP["113"] = cfg
    sys.argv = [sys.argv[0], "113"] + sys.argv[2:]
    rc = gradetest.main()

    print("\n=== PRE-REGISTERED GATE (PREREGISTRATION.md sec.4 item 3) ===")
    print("  PASS  = the 4x4-block tone fit explains < 50% of the gap at the")
    print("          pre-registered band 0.20-0.25 cyc/px, AND the fitted")
    print("          log-log slope sits near 1.000.")
    print("  FAIL  = tone still explains most of the gap; the comparison is a")
    print("          tone measurement and NO band number may be reported.")
    print("  Baseline to beat (V-HEADTOHEAD2 sec.4.5, Lightroom-developed")
    print("  comparator input): slope 0.177, gap explained 89.1% at 0.20-0.25,")
    print("  100.0% at 0.25-0.30, 212% at 0.30-0.40.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
