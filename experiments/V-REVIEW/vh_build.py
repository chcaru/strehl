"""Rewrite halo_profile.py's measurement core. Run once; edits the file in place.

Anchored on unique full lines and hard-errors if an anchor does not land, so a
mutation that silently fails to apply cannot produce a green that means nothing.
"""
import io, os, sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\halo_profile.py"
src = io.open(PATH, encoding="utf-8").read()

NEW_DOC = '''
WHAT THE SKIP TAXONOMY FOUND, AND WHAT CHANGED (V-REVIEW)
---------------------------------------------------------
Run over the 26 delivered masters this instrument measured 11 and skipped 15.
Diagnosing all guards independently rather than reporting only the first to
fire showed the 15 were not one problem but four, and that BOTH regime guards
were inert on the exact subjects they were written for:

  * REGIME GUARD 1 was written to catch `tweezers-cpl`, whose two arms are
    separate components. On these masters the tweezers segment as ONE component
    (largest share 100%, 10 components), so the guard never fires and the
    subject is measured and flagged anyway.
  * REGIME GUARD 2 was written to catch `flat-on-ruler-cpl`. It requires both
    far annuli to hold >200 px, and it splits them at a FIXED 650 px. That
    subject reaches only 599 px, so the outer annulus is EMPTY and the guard
    does not apply. It was inert on 7 of 26 subjects, including that one.

A guard that cannot apply reads exactly like a guard that passed. Both are
fixed below, and the fix for guard 2 is to split the far field at its own
MEDIAN distance so that both halves are populated whenever the far field is.

The component guard is replaced rather than loosened. Its stated concern --
that walking outward from a union of parts crosses the gaps between them -- is
answered directly by restricting every band to the DOMINANT COMPONENT'S OWN
VORONOI CELL: background whose nearest subject pixel belongs to the dominant
part. Inside that cell "outward from the silhouette" is well defined no matter
how many other parts exist, because the walk stops at the cell boundary instead
of crossing into another part's territory. This is what lets 862-component
`couch-fibers-cpl` be measured without relaxing anything.

AN ADAPTIVE FAR FIELD WAS TESTED AND REJECTED, WITH THE CALIBRATION
------------------------------------------------------------------
`112MSDCF` and `113MSDCF` have a real background -- 24% of frame -- that never
lies more than 167 and 181 px from the subject, so the fixed 400-900 px window
is unreachable and they cannot be measured. The obvious fix is a nearer far
field. It was calibrated on the 17 subjects where BOTH windows exist, by
measuring overshoot at 400-900 and again at 130-180:

    median absolute error 3318 DN, worst 13023 DN, against a 200 DN threshold.

It is not a small bias and it is not one-signed. It flips verdicts in BOTH
directions -- `dry-erase-marker-head-cpl` +236.7 -> -535.1 (HALO would become
clean) and `119MSDCF` -284.1 -> +240.5 (clean would become HALO). A far field
inside the penumbra is not a far field. Those two subjects are therefore
reported UNMEASURABLE with that reason, and the honest answer is that measuring
them needs a capture with more clearance around the subject, not a better
statistic.

MAX_SUBJ WAS A PROXY FOR TESTS THAT ARE ALREADY PRESENT
--------------------------------------------------------
"Subject is more than 80% of frame" was standing in for "there is no usable
background". That is tested directly and better by the backdrop fraction, the
far-field population and the near-band population, all of which already exist.
`coffee-bubbles` and `foam` fail those direct tests anyway (far field 0 px) and
are still UNMEASURABLE. `highly-angled-ruler-mm-cpl` fails only the proxy: it
has 106,153 far-field px and 7 populated near bands, and is now measured.
'''

anchor = "This measurement is only defined where there IS a bright backdrop and a dark"
if anchor not in src:
    raise SystemExit("ANCHOR NOT FOUND: docstring tail")
src = src.replace('"""\n\nimport argparse',
                  NEW_DOC + '"""\n\nimport argparse', 1)
if NEW_DOC not in src:
    raise SystemExit("ANCHOR NOT FOUND: docstring close")

old_imports = ("from scipy.ndimage import (binary_closing, binary_opening,\n"
               "                           distance_transform_edt, label)")
if old_imports not in src:
    raise SystemExit("ANCHOR NOT FOUND: imports")

old_const = "MIN_LARGEST = 0.70    # largest connected component share of subject mass"
if old_const not in src:
    raise SystemExit("ANCHOR NOT FOUND: MIN_LARGEST")
src = src.replace(old_const,
                  "MIN_LARGEST = 0.70    # RETIRED: replaced by the Voronoi restriction\n"
                  "MIN_DOM_FRAME = 0.02  # dominant part must be >=2% of FRAME to have a\n"
                  "                      # perimeter long enough to carry a measurable rim\n"
                  "MIN_BANDPX = 200      # px needed in a band before its median is used", 1)

start = src.index("def profile(y, sub=4):")
end = src.index("def main():")
NEWFN = '''def segment(y):
    t = otsu(y.ravel())
    subj = binary_opening(y < t, np.ones((3, 3)))
    subj = binary_closing(subj, np.ones((5, 5)))
    return t, subj


def profile(y, sub=4):
    """Returns (verdict, overshoot, bump, penumbra, farlevel, bands, why)."""
    y = y[::sub, ::sub]
    t, subj = segment(y)
    frac = float(subj.mean())
    if frac < MIN_SUBJ:
        return ("UNMEASURABLE", None, None, None, None, None,
                "no dark subject (%.1f%% of frame)" % (frac * 100))
    if float((y > t).mean()) < 0.05:
        return ("UNMEASURABLE", None, None, None, None, None,
                "backdrop too small (%.1f%% of frame)" % (float((y > t).mean()) * 100))

    lab, nlab = label(subj)
    if nlab < 1:
        return ("UNMEASURABLE", None, None, None, None, None, "no subject component")
    sizes = np.bincount(lab.ravel())[1:]
    dom = int(np.argmax(sizes)) + 1
    dom_frame = float(sizes[dom - 1]) / float(subj.size)
    if dom_frame < MIN_DOM_FRAME:
        return ("UNMEASURABLE", None, None, None, None, None,
                "no dominant silhouette: largest of %d parts is %.1f%% of frame "
                "(need %.0f%%)" % (nlab, dom_frame * 100, MIN_DOM_FRAME * 100))

    # THE VORONOI RESTRICTION. `ind` gives, for every background pixel, the
    # coordinates of its nearest subject pixel; the label there says which part
    # owns it. Restricting to the dominant part's cell means the outward walk
    # never crosses a gap into another part, which is precisely what REGIME
    # GUARD 1 existed to prevent -- now prevented by construction instead of by
    # refusing to measure.
    d, ind = distance_transform_edt(~subj, return_indices=True)
    d = d * sub
    own = (lab[ind[0], ind[1]] == dom) & (~subj)

    far = own & (d >= FAR[0]) & (d < FAR[1])
    nfar = int(far.sum())
    if nfar < MIN_FARPX // (sub * sub):
        return ("UNMEASURABLE", None, None, None, None, None,
                "far field only %d px within the dominant part's cell, need %d "
                "(subject reaches %.0f px)"
                % (nfar, MIN_FARPX // (sub * sub), float(d.max())))
    farlevel = float(np.median(y[far]))

    # REGIME GUARD 2, ALWAYS APPLICABLE. Split the far field at its OWN median
    # distance, so both halves are populated whenever the far field is. The
    # previous fixed 650 px split left the outer half empty on 7 of 26 subjects
    # -- including `flat-on-ruler-cpl`, the subject the guard was written for.
    dv = d[far]
    dmed = float(np.median(dv))
    A = far & (d < dmed)
    B = far & (d >= dmed)
    spread = None
    if int(A.sum()) > MIN_BANDPX and int(B.sum()) > MIN_BANDPX:
        spread = abs(float(np.median(y[A])) - float(np.median(y[B])))
        if spread > BG_UNIFORM:
            return ("UNMEASURABLE", None, None, None, None, None,
                    "background not uniform: far field's own halves differ by "
                    "%.0f DN (limit %d)" % (spread, BG_UNIFORM))
    else:
        return ("UNMEASURABLE", None, None, None, None, None,
                "far field cannot be split to test uniformity (%d/%d px)"
                % (int(A.sum()), int(B.sum())))

    bands = []
    for lo, hi in NEAR:
        m = own & (d >= lo) & (d < hi)
        n = int(m.sum())
        bands.append((lo, hi, n,
                      float(np.median(y[m])) - farlevel if n > MIN_BANDPX else None))
    vals = [b[3] for b in bands if b[3] is not None]
    if not vals:
        return ("UNMEASURABLE", None, None, None, None, None, "no populated near band")
    over = max(vals)
    bump = 0.0
    for i in range(len(vals) - 1):
        bump = max(bump, vals[i] - vals[i + 1])
    penumbra = min(vals)
    return ("MEASURED", over, bump, penumbra, farlevel, bands, "")


'''
src = src[:start] + NEWFN + src[end:]

for a, b in [
    ('    clean = halo = skipped = 0', '    clean = halo = unmeas = 0'),
    ('        if v == "SKIPPED":\n            skipped += 1\n'
     '            print("%-36s %10s %8s %10s %9s  SKIPPED -- %s"',
     '        if v == "UNMEASURABLE":\n            unmeas += 1\n'
     '            print("%-36s %10s %8s %10s %9s  UNMEASURABLE -- %s"'),
    ('    total = clean + halo + skipped',
     '    total = clean + halo + unmeas'),
    ('    print("partition: %d clean, %d HALO, %d skipped, %d total (found %d)"\n'
     '          % (clean, halo, skipped, total, len(files)))',
     '    print("partition: %d clean, %d HALO, %d UNMEASURABLE, %d total (found %d)"\n'
     '          % (clean, halo, unmeas, total, len(files)))'),
    ('    print("A SKIPPED subject is not a clean subject. It is one where the")',
     '    print("An UNMEASURABLE subject is not a clean subject. It is one where the")'),
]:
    if a not in src:
        raise SystemExit("ANCHOR NOT FOUND: %r" % a[:60])
    src = src.replace(a, b, 1)

with io.open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(src)
print("rewrote", PATH)
print("bytes", len(src.encode("utf-8")))
