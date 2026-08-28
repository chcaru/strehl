"""Render a FOCUS LADDER of single-frame probes on 113MSDCF, for band qualification.

ORCH: a resolution claim must be measured in a band SHOWN to contain signal.  My
operating band is 0.30-0.35 cyc/OUTPUT px and my develop path is `--srgb --exposure`
on merged masters.  V-LINEAR's failing measurement is `--linear-srgb --demosaic` on
single frames, and that lane states the property is develop-dependent (1.004 linear
vs ~3.0 Lightroom on the same frames).  So the qualification has to be re-run on MY
develop path and MY grid or it answers a different question.

STREHL_ONLY_FRAME puts one bracket frame through the identical pipeline with NO
election, so probes land on the same output grid as the merges and carry the same
tone curve and the same explicit gain (+2.33 stops, 5.028x) as N032/N063.  That is
the matched gauge; --auto-exposure is forbidden here as everywhere in this lane.

Step 2 over 63 frames.  A probe ladder coarser than the true focus step means a
tile's "in focus" probe is slightly off-peak, which UNDERSTATES the focus response
and biases the qualification toward FAIL.  That is the safe direction to be wrong in.
"""
import drender as D

SUBJ = "113MSDCF"; EXPO = "2.33"

if __name__ == "__main__":
    h = D.pin(); print("pin sha256 %s...\n" % h[:16])
    src, allf = D.frames(SUBJ); NF = len(allf)
    assert NF == 63, "expected 63 frames, got %d" % NF
    ks = list(range(0, NF, 2))
    assert ks[0] == 0 and ks[-1] == 62, ks[:3]
    print("%s: %d frames, %d probes at exposure +%s (matches N032/N063)\n"
          % (SUBJ, NF, len(ks), EXPO))
    for k in ks:
        D.probe(SUBJ, k, EXPO)
    print("\ndone: %d probes" % len(ks))
