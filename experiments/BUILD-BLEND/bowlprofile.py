"""BUILD-BLEND: the mean_coarse ladder against ORCH's four pre-registered criteria.

WHY THIS EXISTS AND IS NOT JUST `rimprofile.py` IN A LOOP
---------------------------------------------------------
rimprofile.py is ORCH's instrument and its criteria are stated in its units, so
this script reproduces its arithmetic exactly -- same bin edges, same luma, same
largest-component mask, same far-field reference, same sRGB encode. What it adds
is three fixes without which a ladder cannot be read:

1. THE MASK IS PER-IMAGE. rimprofile derives `subject` from a p5/p95 threshold on
   the very image it is profiling. Two arms therefore get two different masks and
   two different distance fields, so a row labelled "d=2" is not the same set of
   pixels between arms. This script builds the mask ONCE from a named reference
   and applies that one distance field to every image.

2. THE ENCODE WHITE IS ALSO PER-IMAGE. `white = percentile(lum, 99.9)` is taken
   from the image being profiled, so the /255 column is scaled by a per-image
   quantity too. This script takes `white` once from the same reference.

   Both drifts are reported per image rather than silently corrected, so their
   size is visible instead of assumed small.

3. THE UNITS DO NOT TRANSFER, AND THIS IS THE BIG ONE.

   ORCH's registered bars (d=2 >= -41.56, d=90 <= -4.5, |d>=300| <= 1.0, all "of
   255") were measured on ca-ctrl/ca-blend-*.tiff. Those two files declare, in
   their own ImageDescription:

       "sRGB (IEC 61966-2-1) ... sRGB transfer curve. For viewing."
       Tone rendering: black 0.011119 / 0.000000, white 0.306019 / 0.319798

   They are already sRGB-encoded and already tone-mapped. rimprofile.py then
   applies srgb() AGAIN -- its own docstring says "Measures on the LINEAR 16-bit
   render only". So those numbers are a double encode of a per-image tone curve.

   That is not a rounding difference. The encode's slope depends on where you
   sit on it. ORCH's far field was 59630 DN = 248.1 of 255, which pins
   white = 63466 DN and gives d(enc)/d(DN) = 0.001832 of 255 per DN. An untoned
   linear render of the same subject has its far field near 14509 DN and sits far
   lower on the curve, where the same curve is roughly 4x steeper. An identical
   physical deficit therefore prints a much larger "of 255" number on a linear
   file than on ORCH's toned pair.

   Reporting my rungs against ORCH's literal bars would be comparing two
   different rulers and would make this arm look worse than it is, which is the
   mirror image of the error that would make it look better. Neither is
   acceptable, so this script does BOTH of the following and never just one:

     - reports absolute DN, which is what ORCH required and which is
       unit-invariant;
     - restates each bar in the parity form ORCH themselves wrote it in
       ("Control is -0.50 and -0.79; that is the parity bar"), evaluated against
       the control measured through this identical path.

   Criterion (b) is restated as a RETAINED FRACTION of the mid-field win, which
   is scale-free and so transfers between encodes exactly:
       ORCH: control -7.69, mc0 blend -4.09, bar -4.5
       => the bar permits losing 0.41 of a 3.60 win, i.e. retain >= 88.6%.

EVERY BIN IS COUNTED. The summary partitions all bins into pass/fail/skipped and
the three must sum to the number of bins examined, so a bin that was never
measured cannot read as a bin that passed.

Usage:
    python bowlprofile.py --ref <control.tiff> <img.tiff> [<img.tiff> ...]
"""
import sys
import numpy as np
import tifffile
from scipy import ndimage

EDGES = [0, 4, 8, 12, 16, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150,
         200, 250, 300, 400, 500, 600]

# ORCH's operating point, pinned by the two numbers they published together:
# "control far field 59630 DN = 248.1/255".
ORCH_REF_DN = 59630.0
ORCH_REF_ENC = 248.1
# Retained fraction of the d=90 win that ORCH's bar permits: (-4.5 - -7.69) / (-4.09 - -7.69)
ORCH_WIN_KEEP = (-4.5 - -7.69) / (-4.09 - -7.69)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def luma(path):
    img = tifffile.imread(path)
    assert img.dtype == np.uint16, f"{path}: expected uint16, got {img.dtype}"
    return img.astype(np.float32).mean(axis=2)


def mask_and_white(lum):
    """rimprofile.py's own mask construction, reproduced exactly."""
    lo, hi = np.percentile(lum, [5, 95])
    thr = 0.5 * (lo + hi)
    subject = lum < thr
    lab, n = ndimage.label(subject)
    if n > 1:
        sizes = ndimage.sum(subject, lab, range(1, n + 1))
        subject = lab == (1 + int(np.argmax(sizes)))
    white = float(np.percentile(lum, 99.9))
    return subject, white, thr, n


def orch_sensitivity():
    """d(enc)/d(DN) of 255 per DN at ORCH's operating point, derived not guessed."""
    # Invert enc = 255*srgb(ref/white) for white, given ORCH's published pair.
    y = ORCH_REF_ENC / 255.0
    x = ((y + 0.055) / 1.055) ** 2.4          # = ref/white
    white = ORCH_REF_DN / x
    dsrgb = 1.055 * (1 / 2.4) * x ** (1 / 2.4 - 1)
    return 255.0 * dsrgb / white, white, x


def profile(lum, signed, white):
    ds, vals, npx = [], [], []
    for i in range(len(EDGES) - 1):
        m = (signed >= EDGES[i]) & (signed < EDGES[i + 1])
        if m.sum() < 500:
            continue
        ds.append(0.5 * (EDGES[i] + EDGES[i + 1]))
        vals.append(float(np.median(lum[m])))
        npx.append(int(m.sum()))
    vals = np.array(vals)
    far = (signed > 600) & (signed < 1400)
    ref = float(np.median(lum[far]))
    enc = srgb(vals / white) * 255.0
    enc_ref = float(srgb(np.array([ref / white]))[0] * 255.0)
    return np.array(ds), vals, ref, enc, enc_ref, npx


def main():
    argv = sys.argv[1:]
    if "--ref" not in argv:
        print(__doc__)
        sys.exit(2)
    i = argv.index("--ref")
    refpath = argv[i + 1]
    targets = argv[:i] + argv[i + 2:]
    if not targets:
        print("no targets given"); sys.exit(2)

    sens, orch_white, orch_x = orch_sensitivity()
    print("=" * 78)
    print("ORCH's operating point, derived from their published pair")
    print("=" * 78)
    print(f"  far field {ORCH_REF_DN:.0f} DN printed as {ORCH_REF_ENC} of 255")
    print(f"  => implied encode white   = {orch_white:.0f} DN  (ref/white = {orch_x:.5f})")
    print(f"  => slope at that point    = {sens:.6f} of 255 per DN")
    print(f"  => their 1.0-of-255 bar   = {1.0/sens:.0f} DN = "
          f"{100.0/sens/ORCH_REF_DN:.3f}% of far field")
    print(f"  => their d=90 bar keeps   = {ORCH_WIN_KEEP*100:.1f}% of the mid-field win")
    print()

    print("=" * 78)
    print(f"SHARED MASK AND WHITE, both taken once from: {refpath}")
    print("=" * 78)
    lum_ref = luma(refpath)
    subject, white, thr, ncomp = mask_and_white(lum_ref)
    print(f"  threshold {thr:.0f} DN, {ncomp} components, "
          f"subject = {subject.mean()*100:.2f}% of frame")
    print(f"  encode white (p99.9)     = {white:.0f} DN")
    signed = (ndimage.distance_transform_edt(~subject)
              - ndimage.distance_transform_edt(subject))
    print()

    print("=" * 78)
    print("PER-IMAGE DRIFT (reported, not corrected -- so its size is visible)")
    print("=" * 78)
    print(f"  {'image':<28} {'own subj %':>11} {'own white DN':>13} {'own thr DN':>11}")
    lums = {}
    for t in [refpath] + targets:
        lum = luma(t)
        lums[t] = lum
        s2, w2, t2, _ = mask_and_white(lum)
        name = t.split("\\")[-1]
        print(f"  {name:<28} {s2.mean()*100:>11.2f} {w2:>13.0f} {t2:>11.0f}")
    print()

    results = {}
    for t in [refpath] + targets:
        ds, vals, ref, enc, enc_ref, npx = profile(lums[t], signed, white)
        results[t] = (ds, vals, ref, enc, enc_ref, npx)

    ds = results[refpath][0]
    print("=" * 78)
    print("ABSOLUTE MEDIAN DN PER BIN (ORCH's hard requirement: levels, not ratios)")
    print("=" * 78)
    names = [t.split("\\")[-1].replace(".tiff", "") for t in [refpath] + targets]
    print("  d (px) " + "".join(f"{n[-22:]:>23}" for n in names))
    for j, d in enumerate(ds):
        row = f"  {d:6.0f} "
        for t in [refpath] + targets:
            row += f"{results[t][1][j]:>23.0f}"
        print(row)
    row = "  farfld "
    for t in [refpath] + targets:
        row += f"{results[t][2]:>23.0f}"
    print(row)
    print()

    print("=" * 78)
    print("DEFICIT vs EACH IMAGE'S OWN FAR FIELD, in DN")
    print("(each arm against its own zero, so a global level shift divides out)")
    print("=" * 78)
    print("  d (px) " + "".join(f"{n[-22:]:>23}" for n in names))
    for j, d in enumerate(ds):
        row = f"  {d:6.0f} "
        for t in [refpath] + targets:
            row += f"{results[t][1][j] - results[t][2]:>23.0f}"
        print(row)
    print()

    print("=" * 78)
    print("THE SAME ROWS IN 'of 255', SHARED WHITE")
    print("NOTE: this operating point is NOT ORCH's. Their bars were measured on a")
    print("      toned+sRGB file at 248.1/255; these are linear files far lower on")
    print("      the curve, where it is steeper. Compare COLUMN TO COLUMN here, and")
    print("      use the parity verdict below -- never these against ORCH's numbers.")
    print("=" * 78)
    print("  d (px) " + "".join(f"{n[-22:]:>23}" for n in names))
    for j, d in enumerate(ds):
        row = f"  {d:6.0f} "
        for t in [refpath] + targets:
            _, _, _, enc, enc_ref, _ = results[t]
            row += f"{enc[j] - enc_ref:>23.2f}"
        print(row)
    print()

    # ---- ORCH's criteria, in the parity form they wrote them in ----
    def at(t, d):
        dsx, vals, ref, enc, enc_ref, _ = results[t]
        j = int(np.argmin(np.abs(dsx - d)))
        return enc[j] - enc_ref, vals[j] - ref, dsx[j]

    print("=" * 78)
    print("ORCH'S PRE-REGISTERED CRITERIA, evaluated as parity against the control")
    print("=" * 78)
    ctrl = refpath
    mc0 = targets[0]
    verdicts = {}
    for t in targets:
        pas = fail = skip = 0
        lines = []

        # (a) the bowl must close: control parity at d >= 300.
        #     ORCH's bar was |D| <= 1.0 of 255 against a control at -0.50/-0.79,
        #     i.e. control's own depth plus whatever headroom 1.0 left over it.
        #     That headroom is what transfers between encodes, so carry it in DN.
        for d in [dd for dd in ds if dd >= 300]:
            _, rdn, _ = at(t, d)
            _, cdn, _ = at(ctrl, d)
            tol_dn = max(1.0 / sens - abs(cdn), 0.0)   # ORCH's headroom, in DN
            ok = abs(rdn) <= abs(cdn) + tol_dn
            lines.append(f"    (a) d={d:>4.0f}  rung {rdn:+8.0f} DN vs control "
                         f"{cdn:+8.0f} DN, headroom {tol_dn:+7.0f} DN  "
                         f"{'PASS' if ok else 'FAIL'}")
            pas, fail = (pas + 1, fail) if ok else (pas, fail + 1)

        # (b) the win must survive: retained fraction of the d=90 win
        _, r90, dd90 = at(t, 90)
        _, c90, _ = at(ctrl, 90)
        _, m90, _ = at(mc0, 90)
        win = m90 - c90
        if abs(win) < 1e-6:
            lines.append("    (b) SKIPPED: mc0 shows no win at d=90 to retain")
            skip += 1
        else:
            keep = (r90 - c90) / win
            ok = keep >= ORCH_WIN_KEEP
            lines.append(f"    (b) d={dd90:>4.0f}  rung {r90:+8.0f} DN, control {c90:+8.0f}, "
                         f"mc0 {m90:+8.0f} -> retains {keep*100:6.1f}% "
                         f"(bar {ORCH_WIN_KEEP*100:.1f}%)  {'PASS' if ok else 'FAIL'}")
            pas, fail = (pas + 1, fail) if ok else (pas, fail + 1)

        # (c) no new silhouette cost vs control
        _, r2, dd2 = at(t, 2)
        _, c2, _ = at(ctrl, 2)
        ok = r2 >= c2
        lines.append(f"    (c) d={dd2:>4.0f}  rung {r2:+8.0f} DN vs control {c2:+8.0f} DN  "
                     f"{'PASS' if ok else 'FAIL'}")
        pas, fail = (pas + 1, fail) if ok else (pas, fail + 1)

        name = t.split("\\")[-1]
        print(f"  {name}")
        for L in lines:
            print(L)
        total = pas + fail + skip
        print(f"    -> {pas} pass + {fail} fail + {skip} skipped = {total} checks")
        verdicts[t] = (pas, fail, skip)
        print()

    print("=" * 78)
    print("SUMMARY  (criterion (d), the lavendar morphology, is visual and separate)")
    print("=" * 78)
    for t, (p, f, s) in verdicts.items():
        v = "ALL PASS" if f == 0 and s == 0 else ("FAIL" if f else "INCOMPLETE")
        print(f"  {t.split(chr(92))[-1]:<44} {p} pass {f} fail {s} skip   {v}")


if __name__ == "__main__":
    main()
