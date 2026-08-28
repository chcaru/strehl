"""Truncate the outward walk where the dominant part's Voronoi cell pinches off.

MEASURED MECHANISM.  On `leaf-2-cpl` the profile is a clean monotone ramp out
to d=32-50 and then spikes +5721 DN at d=50-80 and falls back -4524 at 80-120.
Band populations over the same walk collapse 42924 -> 7994.  The cell has
narrowed to a directional sliver, so the outer band medians are not the
background level at that distance -- they are the level in whichever direction
happened to survive.  That is a sampling artifact of the Voronoi restriction and
it manufactured HALO verdicts on `leaf-2-cpl` and `lead-1-cpl`.

THE DISCRIMINATOR IS DENSITY, NOT POPULATION.  The bands are 4,6,8,12,18,30,40
px wide, so raw counts are not comparable.  Per-unit-width density, normalised
to the innermost band, was measured on all 26 subjects.  A well-formed cell
holds 0.2-0.6; the pinching ones fall to 0.02.

The walk therefore STOPS at the first band whose density falls below 10% of the
innermost band's, rather than the subject being skipped.  A halo lives close to
the silhouette, so the truncated bands are not where one would hide -- and this
is commissioned, not asserted: see vh_commission.py for the detection floor.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\halo_profile.py"
src = io.open(PATH, encoding="utf-8").read()

A = ("MIN_BANDPX = 200      # px needed in a band before its median is used")
if A not in src:
    raise SystemExit("ANCHOR NOT FOUND: MIN_BANDPX")
src = src.replace(A, A + "\nMIN_CELL_DENS = 0.10  # stop the walk when the dominant part's cell has\n"
                        "                      # narrowed to <10% of its innermost density", 1)

B = """    bands = []
    for lo, hi in NEAR:
        m = own & (d >= lo) & (d < hi)
        n = int(m.sum())
        bands.append((lo, hi, n,
                      float(np.median(y[m])) - farlevel if n > MIN_BANDPX else None))
    vals = [b[3] for b in bands if b[3] is not None]
    if not vals:
        return ("UNMEASURABLE", None, None, None, None, None, "no populated near band")"""
if B not in src:
    raise SystemExit("ANCHOR NOT FOUND: band loop")
NEW = """    bands = []
    dens0 = None
    for lo, hi in NEAR:
        m = own & (d >= lo) & (d < hi)
        n = int(m.sum())
        dens = n / float(hi - lo)
        if dens0 is None:
            dens0 = dens
        # CELL-PINCH TRUNCATION. Stop rather than skip: the surviving pixels
        # this far out are a directional sliver, and their median is not the
        # background level at that distance.
        if dens0 > 0 and dens / dens0 < MIN_CELL_DENS:
            bands.append((lo, hi, n, None))
            continue
        bands.append((lo, hi, n,
                      float(np.median(y[m])) - farlevel if n > MIN_BANDPX else None))
    vals = []
    for b in bands:
        if b[3] is None:
            break
        vals.append(b[3])
    if len(vals) < 3:
        return ("UNMEASURABLE", None, None, None, None, None,
                "only %d usable near band(s): dominant part's cell pinches off "
                "before a profile can be walked" % len(vals))"""
src = src.replace(B, NEW, 1)

with io.open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(src)
print("patched cell-pinch truncation")
