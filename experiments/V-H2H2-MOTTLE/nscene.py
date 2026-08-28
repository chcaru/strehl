"""The N-ladder: does merged SCENE content fall as the stack deepens?

ORCH's chain of evidence tonight is: the softness lane measured 63 frames softer
than 32 at matched range; the tone lane measured strehl retaining 6-18% of the
comparators' detail on a 299-frame subject. Both are single points. Neither
demonstrates that DEPTH is the variable, because each compares across a different
axis -- one across N at one subject, one across stackers at one N.

This is the one-subject experiment that puts N on the x-axis: four rungs on
bee-3-cpl at 18, 37, 74 and 149 frames, every rung spanning the SAME focus
bracket, every render from ONE binary with no exposure choice available to it. If
scene content falls monotonically down that ladder, depth is the variable and the
mechanism is demonstrated rather than inferred. If it does not, the two lanes'
findings need another explanation and I should say so.

WHY EACH RUNG IS A PAIR. A single render cannot be split into scene and noise.
Two renders of the same scene from disjoint frames can be, exactly. That is what
makes this self-contained -- no comparator, no reference stacker, no assumption
about the shape of the noise.

THE CONFOUND, STATED, AND IT RUNS AGAINST THE FINDING. A sparse rung samples the
focus travel coarsely and may leave depths where no frame is sharp. That costs
the SHALLOW arms detail. So the confound pushes scene UP with N, and any fall
measured here is measured against it.

THE PREDICTION THAT CAN REFUTE THE WHOLE STORY. If the merge is averaging
properly, the noise term must fall roughly as 1/sqrt(N) -- a factor of 2.87 from
rung 18 to rung 149. If instead noise is flat or rising while scene falls, the
merge is not averaging, it is selecting, and it is selecting on noise. Both terms
are reported at every rung so this can be read off rather than argued.
"""
import json
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402
import decomplib  # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\ladder2\out"
RUNGS = [18, 37, 74, 149]
REF_RUNG = 149              # the arm the display gain and the sites both come from
SITE = 384                  # px, on the 7032x4688 output grid
MARGIN = 600                # keep sites clear of the alignment-eroded border
PAD = 64                    # integer-shift search half-width; +-24 saturated between rungs
NSITE = 3
BANDS = [("5-15", 5, 15), ("20-60", 20, 60), ("40-120", 40, 120)]


def path(rung, arm):
    return os.path.join(OUT, "n%d%s.tiff" % (rung, arm))


def green(img16, expo):
    """Display codes on the green plane. ONE gain for every arm, from ONE
    reference: deriving a gain per arm is the exposure mismatch this project has
    hit repeatedly, reintroduced by the back door."""
    return bandlib.display(img16[..., 1].astype(np.float64), expo)


def pick_sites(g):
    """Highest- and lowest-detail non-overlapping sites, scored on the reference."""
    h, w = g.shape
    step = SITE
    cands = []
    for y in range(MARGIN, h - MARGIN - SITE, step):
        for x in range(MARGIN, w - MARGIN - SITE, step):
            t = g[y:y + SITE, x:x + SITE]
            d = float(np.std(bandlib.boxblur(t, 2) - bandlib.boxblur(t, 7)))
            cands.append((d, y, x))
    cands.sort()
    flat = [(y, x) for _, y, x in cands[:NSITE]]
    detail = [(y, x) for _, y, x in cands[-NSITE:]]
    return {"flat": flat, "detail": detail}, cands


def integer_align(ref, arm_padded, search):
    """Integer-only shift that best matches `arm_padded` to `ref`.

    `ref` is an (S, S) window; `arm_padded` is the SAME window from the other
    arm, grown by `search` px on every side so the shift has somewhere to move.
    Asserting the shape relation rather than trusting it: the first version took
    two same-sized arrays and cropped both, and passing it a padded arm compared
    a 384 px window against a 336 px one.

    Integer only, deliberately: sub-pixel resampling adds blur to the very
    quantity being measured.

    A SEARCH THAT SATURATES REPORTS THE WRONG ANSWER AS CONFIDENTLY AS A SEARCH
    THAT FINDS ONE. An earlier +-8 search returned +-8, and widening it to +-12
    returned +12 -- it had been pinned at its own boundary and I read the pin as
    a measurement. The caller gets the boundary flag and asserts on it. Widening
    it again to +-24 pinned again at (2,-24) between rungs 18 and 149, which is
    why the search is now coarse-to-fine: a brute force over +-64 is 16641
    positions per site, and the two-stage version evaluates about 1200 for the
    same answer. Both stages are integer, at full resolution, with no
    downsampling anywhere -- the speedup is in the sampling of the search, not in
    the precision of the match.
    """
    s = ref.shape[0]
    want = (s + 2 * search, s + 2 * search)
    if arm_padded.shape != want:
        raise ValueError("arm window is %s, expected %s (ref %s, search %d)"
                         % (arm_padded.shape, want, ref.shape, search))

    def err(dy, dx):
        a = arm_padded[search + dy:search + dy + s, search + dx:search + dx + s]
        return float(np.mean(np.abs(a - ref)))

    step = 4 if search > 16 else 1
    best, bo = None, (0, 0)
    for dy in range(-search, search + 1, step):
        for dx in range(-search, search + 1, step):
            e = err(dy, dx)
            if best is None or e < best:
                best, bo = e, (dy, dx)
    if step > 1:
        cy, cx = bo
        for dy in range(max(-search, cy - step), min(search, cy + step) + 1):
            for dx in range(max(-search, cx - step), min(search, cx + step) + 1):
                e = err(dy, dx)
                if e < best:
                    best, bo = e, (dy, dx)
    at_edge = abs(bo[0]) == search or abs(bo[1]) == search
    return bo, best, at_edge



def shifted(g, y, x, dy, dx, size):
    """Crop at (y,x) displaced by an integer offset. No resampling anywhere."""
    return g[y + dy:y + dy + size, x + dx:x + dx + size]



def main():
    for rung in RUNGS:
        for arm in "ab":
            if not os.path.exists(path(rung, arm)):
                sys.exit("missing render: %s" % path(rung, arm))

    ref16 = tifffile.imread(path(REF_RUNG, "a"))
    p999 = float(np.percentile(ref16.astype(np.float64) / 65535.0, 99.9))
    expo = 0.90 / max(p999, 1e-9)
    print("reference n%da: shape %s, 99.9th pct %.5f -> display gain %.4f "
          "(applied to every arm)" % (REF_RUNG, ref16.shape, p999, expo))
    gref = green(ref16, expo)
    sites, cands = pick_sites(gref)
    print("sites: %d flat, %d detail, %dpx, scored on the reference only" %
          (len(sites["flat"]), len(sites["detail"]), SITE))
    print("  detail-score range across %d candidates: %.4f .. %.4f"
          % (len(cands), cands[0][0], cands[-1][0]))
    for kind in ("flat", "detail"):
        print("  %-6s %s" % (kind, sites[kind]))

    # The coarse-to-fine search is a shortcut, and a shortcut that agrees with the
    # thing it replaces only on the cases you tried is not a shortcut, it is a
    # guess. So on one real site it is checked against the exhaustive search at a
    # width where exhaustive is affordable, and the run stops if they disagree.
    (sy, sx) = sites["detail"][0]
    gchk = green(tifffile.imread(path(RUNGS[0], "a")), expo)
    ref_win = gref[sy:sy + SITE, sx:sx + SITE]
    arm_win = gchk[sy - 24:sy + SITE + 24, sx - 24:sx + SITE + 24]
    fast, fe, _ = integer_align(ref_win, arm_win, 24)
    brute, be = None, None
    for dy in range(-24, 25):
        for dx in range(-24, 25):
            e = float(np.mean(np.abs(arm_win[24 + dy:24 + dy + SITE,
                                             24 + dx:24 + dx + SITE] - ref_win)))
            if be is None or e < be:
                brute, be = (dy, dx), e
    del gchk
    print("  search self-check at +-24: coarse-to-fine %s (%.4f) vs exhaustive %s "
          "(%.4f)" % (fast, fe, brute, be))
    if fast != brute:
        sys.exit("the coarse-to-fine search disagrees with the exhaustive one; the "
                 "step is too large for this error surface")

    # Registration, MEASURED at every rung rather than assumed once. There is no
    # flag to pin the alignment reference, so the merged output's pixel grid is a
    # function of which frames were in the stack: measured offsets of up to
    # (-5,+12) px between the two arms of a rung under the first staging. Every
    # crop below is taken through an integer-only shift, and the search is wide
    # enough that a saturated result is caught rather than reported.
    rows = []
    aligns = {}
    ref16 = tifffile.imread(path(REF_RUNG, "a"))
    gref = green(ref16, expo)
    del ref16
    for rung in RUNGS:
        a16, b16 = tifffile.imread(path(rung, "a")), tifffile.imread(path(rung, "b"))
        if a16.shape != b16.shape:
            sys.exit("rung %d arms differ in shape" % rung)
        ga, gb = green(a16, expo), green(b16, expo)
        del a16, b16
        # THE GAIN CHECK IS A PAIR-LEVEL, WHOLE-FRAME CALL, made once here before
        # any site is cut. Measured: the same statistic on a 384 px site has an sd
        # of 4.30% and would refuse 52% of sites on arms that cannot differ in
        # gain at all, against 0.19% on the whole frame. A global property tested
        # locally is a coin.
        try:
            tok = decomplib.check_pair_levels(ga, gb)
        except decomplib.Degenerate as e:
            sys.exit("rung %d arms failed the gain check: %s" % (rung, e))
        print("  rung %3d  %s" % (rung, tok))
        # ALIGNMENT IS PER SITE, not one global offset. Measured on the first
        # staging: an offset of (-3,+17) fitted at one detail site improved a
        # second site from +2.48% to +0.16% and made a third WORSE, from +2.23%
        # to +4.46%. The two renders therefore differ by more than a translation
        # -- a field-dependent residual, not a global shift -- so a single offset
        # cannot register them and fitting one at one site and believing it
        # everywhere is how a registration error becomes a band measurement.
        rec = {"n": rung}
        offs = {}
        for kind in ("flat", "detail"):
            for (y, x) in sites[kind]:
                oa, ea, e1 = integer_align(gref[y:y + SITE, x:x + SITE],
                                           ga[y - PAD:y + SITE + PAD,
                                              x - PAD:x + SITE + PAD], PAD)
                ob, eb, e2 = integer_align(shifted(ga, y, x, *oa, SITE),
                                           gb[y - PAD:y + SITE + PAD,
                                              x - PAD:x + SITE + PAD], PAD)
                if e1 or e2:
                    sys.exit("rung %d site (%d,%d): alignment saturated at +-%d px "
                             "(%s, %s); widen PAD" % (rung, y, x, PAD, oa, ob))
                offs[(y, x)] = (oa, ob, ea, eb)
        print("  rung %3d  a->ref %s   b->a %s   residual %.2f-%.2f codes"
              % (rung, sorted({o[0] for o in offs.values()}),
                 sorted({o[1] for o in offs.values()}),
                 min(o[3] for o in offs.values()), max(o[3] for o in offs.values())))
        # The size of the confound, printed beside the measurement it corrupts.
        # These two arms are not on a common grid: the b->a offset is a FIELD, not
        # a shift, and its spread is what a difference statistic carries.
        ob = np.array([o[1] for o in offs.values()], dtype=np.float64)
        fld = float(np.sqrt(np.mean((ob - ob.mean(axis=0)) ** 2)))
        rec["field_rms"] = fld
        print("            b->a displacement field: rms %.2f px about its own mean "
              "-- no single integer shift removes this" % fld)

        for kind in ("flat", "detail"):
            for label, lo, hi in BANDS:
                sc, ns, bias = [], [], []
                for (y, x) in sites[kind]:
                    oa, ob, _, _ = offs[(y, x)]
                    ca = shifted(ga, y, x, *oa, SITE)
                    cb = shifted(gb, y, x, oa[0] + ob[0], oa[1] + ob[1], SITE)
                    s, n = decomplib.decompose(ca, cb, lo, hi, tok)
                    sc.append(s)
                    ns.append(n)
                    bias.append(decomplib.noise_bias(tok, s, n))
                rec["%s.%s.scene" % (kind, label)] = float(np.median(sc))
                rec["%s.%s.noise" % (kind, label)] = float(np.median(ns))
                rec["%s.%s.nbias" % (kind, label)] = float(np.max(bias))
            sh = []
            for (y, x) in sites[kind]:
                oa, ob, _, _ = offs[(y, x)]
                sh.append(decomplib.sharpness(
                    shifted(ga, y, x, *oa, SITE),
                    shifted(gb, y, x, oa[0] + ob[0], oa[1] + ob[1], SITE)))
            rec["%s.sharp" % kind] = float(np.median(sh))
        rec["align"] = {"%d,%d" % k: [list(v[0]), list(v[1]), v[2], v[3]]
                        for k, v in offs.items()}
        rows.append(rec)
        del ga, gb



    base = rows[0]
    for kind in ("flat", "detail"):
        print("\n=== %s sites, ratio to n%d ===" % (kind.upper(), RUNGS[0]))
        hdr = "  %-5s" % "N" + "".join("%22s" % ("%s scene/noise" % l)
                                       for l, _, _ in BANDS) + "%12s" % "sharpness"
        print(hdr)
        for r in rows:
            line = "  %-5d" % r["n"]
            for label, _, _ in BANDS:
                bs = base["%s.%s.scene" % (kind, label)]
                bn = base["%s.%s.noise" % (kind, label)]
                if bs <= 0.0 or bn <= 0.0:
                    line += "%22s" % "refused"
                    continue
                s = r["%s.%s.scene" % (kind, label)] / bs
                n = r["%s.%s.noise" % (kind, label)] / bn
                line += "%22s" % ("%.4f / %.4f" % (s, n))
            line += "%12.4f" % (r["%s.sharp" % kind] / base["%s.sharp" % kind])
            print(line)
        zero = [(r["n"], label) for r in rows for label, _, _ in BANDS
                if r["%s.%s.scene" % (kind, label)] <= 0.0]
        if zero:
            print("  scene clamped to zero (half-difference variance met or exceeded the "
                  "half-sum) at: %s" % ", ".join("n%d %s" % z for z in zero))
        # Every noise ratio above carries an unstated assumption: that the two
        # arms' gains match. They match only to the level guard's measured floor,
        # and what that residual could do to a noise number depends on the site's
        # own scene/noise ratio. Printed, because a noise number without it is a
        # number quoted to more precision than the instrument has.
        wb = max(r["%s.%s.nbias" % (kind, label)] for r in rows
                 for label, _, _ in BANDS)
        print("  worst-case bias on any noise number above, from the gain the level "
              "guard could not rule out: %.2f%%" % (100 * wb))
        # 1/sqrt(N) is what a merge that averages must deliver. Printed beside the
        # measurement so the reader compares against a prediction, not a feeling.
        print("  %-5s" % "1/vN" + "".join("%22s" % ("  --   / %.4f"
              % np.sqrt(RUNGS[0] / r["n"])) for r in [rows[-1]] * len(BANDS)
              ) + "%12s" % "(at N=%d)" % RUNGS[-1])

    print("\n=== monotonicity: does scene fall as N rises? ===")
    verdicts = {}
    for kind in ("flat", "detail"):
        for label, _, _ in BANDS:
            v = [r["%s.%s.scene" % (kind, label)] for r in rows]
            if min(v) <= 0.0:
                print("  %-6s %-8s %s  REFUSED: the decomposition returned a scene of "
                      "zero at %d of %d rungs -- see the displacement field above"
                      % (kind, label, " ".join("%8.4f" % t for t in v),
                         sum(1 for t in v if t <= 0.0), len(v)))
                continue
            down = all(v[i + 1] <= v[i] for i in range(len(v) - 1))
            up = all(v[i + 1] >= v[i] for i in range(len(v) - 1))
            span = v[-1] / v[0]
            verdicts["%s.%s" % (kind, label)] = span
            print("  %-6s %-8s %s  n%d->n%d x%.4f   %s"
                  % (kind, label, " ".join("%8.4f" % t for t in v),
                     RUNGS[0], RUNGS[-1], span,
                     "MONOTONE DOWN" if down else "MONOTONE UP" if up else "not monotone"))

    with open(os.path.join(OUT, "ladder.json"), "w") as f:
        json.dump({"rows": rows, "sites": sites, "expo": expo}, f, indent=1)
    print("\nwrote %s" % os.path.join(OUT, "ladder.json"))


if __name__ == "__main__":
    main()
