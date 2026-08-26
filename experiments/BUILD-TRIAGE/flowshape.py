"""Through-focus SHAPE summary: did the detail exist in the frames, or not?

THE QUESTION THIS ANSWERS
-------------------------
ORCH measured that the softest tiles in the corpus are almost all pale flowers
(four of the six worst; every flower in the bottom seven, by in-tile mean
|laplacian| in linear DN) and handed over three candidate explanations to be
falsified rather than adopted:

  1. capture/motion    -- flowers droop during a long bracket   (BUILD-GHOST's
                          instrument; not tested here)
  2. focus-measure blindness on low-contrast pale subjects -- the election
                          picks near-randomly and the merge averages defocus
  3. genuinely low subject contrast, correctly reproduced

ORCH also stated, unprompted, the limitation that makes candidate 3 impossible
to settle with an amplitude statistic: in-tile |laplacian| "conflates
*contrast* with *sharpness* -- it cannot separate them ... A subject can be
perfectly stacked and still score low here."

That is exactly right, and it is why the discriminator is the SHAPE of the
through-focus curve, not its height:

    resolved interior peak  -> some frame WAS in focus there.  The detail
                               existed and was captured.  If the merge is soft
                               there anyway, that is a merge defect.
    flat curve              -> NO frame was ever in focus there.  The detail
                               never existed.  No merge can invent it.

`peak_over_floor` is that shape statistic.  It is a ratio of the curve to its
own noise floor, so it is scale-free: a subject with one tenth the contrast
still shows a large peak_over_floor if it was properly focused.  `hf_max_rel`
is the contrast, and reporting both side by side is what separates the two
things ORCH's single number could not.

CALIBRATION
-----------
Read against `bee-3-cpl`, which ORCH nominates as the reference for print-worthy
output and which this project has confirmed at 1:1.  Its sites give the scale
for what "properly focused, high contrast" looks like on this rig.
"""
import glob
import json
import os

SCAN = r"C:\dev\strehl-out\BUILD-TRIAGE\sitescan"

# subject -> ORCH's rank and in-tile mean |laplacian|, from detailgallery.py
from orchsites import ORCH_DETAIL


def main():
    rows = []
    for p in sorted(glob.glob(os.path.join(SCAN, "*.flow.json"))):
        d = json.load(open(p))
        subj = d["subject"]
        rank, dn, _, _ = ORCH_DETAIL.get(subj, (0, 0, 0, 0))
        for s in d["sites"]:
            rows.append((rank, dn, subj, s))

    print("THROUGH-FOCUS SHAPE  --  did the detail exist in the source frames?")
    print("  contrast = hf_max_rel (height, what ORCH's DN measures)")
    print("  shape    = peak_over_floor (scale-free; large = clearly focused somewhere)\n")
    hdr = (f"{'ORCH#':>5} {'ORCHdn':>6} {'subject':<36} {'site':<16} "
           f"{'contrast':>8} {'shape':>7} {'bestfrm':>9} {'fall L/R':>11} {'verdict':<28}")
    print(hdr)
    print("-" * len(hdr))
    for rank, dn, subj, s in sorted(rows, key=lambda r: (r[0], r[3]["label"])):
        n = s.get("n_frames")
        bf = f"{s['best_frame']}"
        res = s["peak_resolved_inside_bracket"]
        climb = s["still_climbing"]
        if climb:
            v = f"GAP: still climbing at {s['at_end']}"
        elif res:
            v = "detail EXISTED (interior peak)"
        else:
            v = "flat/low: no frame in focus"
        print(f"{rank:>5} {dn:>6} {subj:<36} {s['label']:<16} "
              f"{s['hf_max_rel']:>8.4f} {s['peak_over_floor']:>7.1f} {bf:>9} "
              f"{s['fall_to_first']:>5.2f}/{s['fall_to_last']:<5.2f} {v:<28}")

    print("\nREADING:")
    ref = [r for r in rows if r[2] == "bee-3-cpl"]
    if ref:
        rc = [r[3]["hf_max_rel"] for r in ref]
        rs = [r[3]["peak_over_floor"] for r in ref]
        print(f"  reference bee-3-cpl : contrast {min(rc):.4f}-{max(rc):.4f}, "
              f"shape x{min(rs):.1f}-x{max(rs):.1f}")
    flow = [r for r in rows if r[2] != "bee-3-cpl" and "BOKEH" not in r[3]["label"]
            and "NULL" not in r[3]["label"]]
    if flow:
        fc = [r[3]["hf_max_rel"] for r in flow]
        nres = sum(1 for r in flow if r[3]["peak_resolved_inside_bracket"])
        print(f"  flower detail sites : contrast {min(fc):.4f}-{max(fc):.4f}, "
              f"i.e. the WORST flower site carries {max(rc)/min(fc):.1f}x less "
              f"contrast than the reference's best")
        print(f"  of {len(flow)} flower DETAIL sites, {nres} show a resolved "
              f"interior peak -> the detail existed in the frames")
    print("\n  A flat curve would mean 'no frame ever had it' (capture-limited).")
    print("  An interior peak means SOME FRAME HAD IT. That alone does NOT")
    print("  convict the merge: this tool reads the SOURCE FRAMES ONLY (raw CFA")
    print("  green, no demosaic, no alignment, no merge). Whether the merge kept")
    print("  the detail is a separate measurement -- compare.py at the same site.")
    print("  Both halves are required before any verdict.")
    print("\n  SELECTION EFFECT, stated because it bounds the claim: these probe")
    print("  sites were placed where structure is VISIBLE in the 1:1 tile. So")
    print("  '9/9 resolved' means 'where there is structure, the frames captured")
    print("  it' -- NOT 'the whole subject is well covered'. A subject can be")
    print("  sound at every site examined and still be mostly bokeh, which is")
    print("  precisely `flowers-cpl` (see its BOKEH-BG row: flat, no frame in")
    print("  focus). Per-region, never per-subject.")


if __name__ == "__main__":
    raise SystemExit(main())
