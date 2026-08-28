"""Per-subject band qualification across the corpus.

ORCH's question: three lanes are now applying V-LINEAR2's 29-tile result --
measured on ONE subject (113MSDCF) -- to THEIR subjects.  That is the transfer
this project has been burned by before (fact 52: a scalar fitted on one scene
and used on another).  Does the 0.25 cyc/px signal/noise boundary hold
corpus-wide, or does it move per subject?

WHY THIS FILE EXISTS RATHER THAN AN EDIT TO bandsignal.py.  `bandsignal.py` is
frozen: three lanes cite it and V-LINEAR2/PREREGISTRATION.md sec.2 fixes its
decision rule.  It is also hardcoded to one directory, 63 frames and one
filename pattern.  So this driver IMPORTS it and reuses `ratio_ci`, `verdict`,
`BANDS`, `FINE`, `SEL_LO`, `SEL_HI`, `T`, `MARGIN` unchanged.  The decision rule
and the band edges therefore CANNOT drift from the pre-registered instrument --
if they ever change there, they change here, and this file has no opinion of
its own about what passes.

TWO CONFOUNDS THIS DRIVER MUST HANDLE THAT THE SINGLE-SUBJECT VERSION DID NOT.

1. STACK DEPTH.  `far` is an index offset, and the corpus spans 19 to 299
   frames.  A fixed far=20 is a third of a 63-frame stack but a fifteenth of a
   299-frame one, where the "defocused" reference may still be nearly in focus.
   That biases deep stacks toward R~1, i.e. toward FALSELY reading as noise.
   So far scales with depth, `far = max(20, round(N/6))`, is REPORTED per
   subject, and the headline population is CONFIRMED (below), which requires
   the lens to have demonstrably moved.

2. READ COST.  Scanning 299 full frames per subject is the whole runtime.
   Frames are subsampled by `step` so roughly 60-100 are read, and `far` is
   converted into sampled units.  step is REPORTED per subject.  Subsampling
   changes which frames are examined, never the frequency axis -- no binning,
   no resampling, so cyc/px means the same thing on every subject.

THE HEADLINE.  Per subject, the boundary is the highest-frequency band that
PASSes (R >= 2.0 and CI low >= 1.5).  A subject where no band above 0.10 cyc/px
passes is flagged: no sharpness claim of any kind may be made on it.

    python bandsweep.py [key ...]        # default: every subject with develops
    python bandsweep.py --far 20 [key ...]   # MATCHED-DEFOCUS CONTROL
    python bandsweep.py --report FILE.json   # re-derive the report, no reads

OUTPUT FILENAMES ENCODE THE SUBJECT SUBSET, AND THAT IS NOT COSMETIC.  A
single-subject run once overwrote the full-corpus far=20 result with one row,
under the same name, and the file gave no sign it was partial.  A partial run
must not be able to masquerade as a complete one, so the subset is in the name.

TWO PROPERTIES OF `bandsignal.RNG` THAT AFFECT REPRODUCTION.  It is module-level,
stateful, and seeded once (`default_rng(20260827)`).  Consequently R is exactly
reproducible run-to-run -- measured 0.000e+00 over 12/12 bands -- but a bootstrap
CI depends on HOW MANY SUBJECTS WERE SWEPT BEFORE IT.  Leaf swept alone versus
swept as one of five moved the CI low on 12/12 bands, verdicts identical on all
12.  Judge that PER BAND against that band's OWN jitter: the worst movement
across all bands is 0.1486, but it belongs to a coarse band whose CI low is of
order 80, and comparing it to a fine band's margin raises a false alarm.  Per
band the tightest margin-to-jitter ratio is 59.8x and nothing is within 10x of
flipping.  Quote the subject list alongside any CI from this tool.

THE CONTROL THAT DECIDES WHETHER THE HEADLINE IS REAL.  `far` is chosen per
subject above, so a boundary that moves between subjects could be moving
because `far` moved, not because the subject differs.  `--far N` forces the
same real-frame offset on every subject.  If the spread survives at matched
far, it is the subjects; if it collapses, it was the parameter.  Run both and
report both -- the unmatched table alone is not evidence.
"""
import os
import sys
import json

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-LINEAR2"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
from h2h2b import band_power                                     # noqa: E402
import bandsignal                                                # noqa: E402

# reused unchanged from the frozen instrument
BANDS = bandsignal.BANDS
FINE = bandsignal.FINE
SEL_LO, SEL_HI = bandsignal.SEL_LO, bandsignal.SEL_HI
T, MARGIN = bandsignal.T, bandsignal.MARGIN
ratio_ci, verdict = bandsignal.ratio_ci, bandsignal.verdict

# Every subject that already has linear develops on disk.  Developing the whole
# corpus would be ~950 GB and is not affordable; these five cost nothing and
# already span 33-299 frames and four subject types.
SUBJECTS = [
    ("113MSDCF",             r"C:\dev\strehl-out\V-LINEAR\lintiff"),
    ("119MSDCF",             r"C:\dev\strehl-out\V-NOISE2\119\lintiff"),
    ("bee-1-cpl",            r"C:\dev\strehl-out\V-NOISE2\bee\lintiff"),
    ("flower-bud-alone-cpl", r"C:\dev\strehl-out\V-NOISE2\fba\lintiff"),
    ("leaf-2-cpl",           r"C:\dev\strehl-out\V-NOISE2\leaf\lintiff"),
]

NY, NX = 5, 6
TARGET_READS = 80


def frames_of(d):
    return sorted(f for f in os.listdir(d) if f.lower().endswith(".tif"))


def sweep(key, d, far_force=None):
    files = frames_of(d)
    n_real = len(files)
    if n_real < 12:
        return None
    far_real = far_force if far_force else max(20, round(n_real / 6))
    step = max(1, round(n_real / TARGET_READS))
    idx = list(range(0, n_real, step))
    far = max(2, round(far_real / step))
    n = len(idx)
    if n - 2 * far < 6:
        far = max(2, (n - 6) // 2)

    allb = BANDS + FINE + [(SEL_LO, SEL_HI)]
    lo = np.array([b[0] for b in allb])
    hi = np.array([b[1] for b in allb])
    nsel = len(allb) - 1

    m0 = tifffile.memmap(os.path.join(d, files[0]), mode="r")
    H, W = m0.shape[0], m0.shape[1]
    del m0
    ys = np.linspace(MARGIN, H - MARGIN - T, NY).astype(int)
    xs = np.linspace(MARGIN, W - MARGIN - T, NX).astype(int)
    pos = [(int(y), int(x)) for y in ys for x in xs]
    ntile = len(pos)

    power = np.zeros((n, ntile, len(allb)))
    for a, f in enumerate(idx):
        mm = tifffile.memmap(os.path.join(d, files[f]), mode="r")
        for i, (y, x) in enumerate(pos):
            crop = h2.luma709(np.asarray(mm[y:y + T, x:x + T, :3], np.float64))
            bp = band_power(crop, lo, hi)
            power[a, i] = np.nan if bp is None else bp
        del mm
        sys.stderr.write(f"\r  {key}: frame {a + 1}/{n}   ")
    sys.stderr.write("\n")

    sel = power[:, :, nsel]
    best = np.nanargmax(sel, axis=0)

    keep, pf, pd, selr = [], [], [], []
    for i in range(ntile):
        b = int(best[i])
        if b < far // 4 + 1 or b > n - far // 4 - 2:
            continue
        ref = [r for r in (b - far, b + far) if 0 <= r < n]
        if not ref:
            continue
        keep.append(i)
        pf.append(power[b, i])
        pd.append(power[ref, i].mean(0))
        selr.append(power[b, i, nsel] / power[ref, i, nsel].mean())

    if len(keep) < 4:
        return {"key": key, "n_real": n_real, "step": step,
                "far_real": far_real, "kept": len(keep), "bands": {},
                "note": "too few tiles with an interior selection maximum"}

    pf, pd, selr = np.array(pf), np.array(pd), np.array(selr)
    conf = selr >= 2.0

    out = {"key": key, "n_real": n_real, "step": step, "far_real": far_real,
           "tiles": ntile, "kept": len(keep), "confirmed": int(conf.sum()),
           "bands": {}}
    pop = conf if conf.sum() >= 4 else np.ones(len(keep), bool)
    out["population"] = "CONFIRMED" if conf.sum() >= 4 else "ALL"
    for j, (a, b) in enumerate(allb):
        if j == nsel:
            continue
        r, cl, ch = ratio_ci(pf[pop, j], pd[pop, j])
        out["bands"][f"{a:.2f}-{b:.2f}"] = {
            "R": float(r), "lo": float(cl), "hi": float(ch),
            "verdict": verdict(r, cl), "f_lo": a, "f_hi": b,
            # IN-FOCUS power, kept so a SUBJECT PROPERTY can be separated from
            # the in/out ratio.  R says how much sharper focus is than defocus;
            # it says nothing about whether the subject HAS fine structure.  A
            # smooth subject and a textured one can share an R.  The fine/coarse
            # ratio of these numbers is scale-free and exposure-free, so it can
            # be compared across subjects where R's magnitude cannot.
            "pf": float(np.median(pf[pop, j])),
            # DEFOCUSED power, the DENOMINATOR of R.  Saved because R can be
            # driven either by a sharp numerator or by a collapsing denominator,
            # and those are different claims about a subject: "resolves finer"
            # versus "is isolated against an empty background".  R alone cannot
            # tell them apart, so both terms are recorded.
            "pd": float(np.median(pd[pop, j]))}
    return out


def boundary(rec):
    """Highest-frequency PASSing band edge; 0.0 if nothing above 0.10 passes.

    RESTRICTED TO THE `FINE` PARTITION, AND THIS IS LOAD-BEARING.  `rec["bands"]`
    also carries `BANDS`, which is coarser at the low end and contains the WIDE
    band 0.10-0.20.  Scanning every key lets a wide band certify its own top
    edge using content an octave below it: on flower-bud-alone-cpl, 0.10-0.20
    PASSes at R=4.731 while its top slice 0.17-0.20 is only MARGINAL at 2.015,
    so the unrestricted scan reported a 0.20 boundary the subject does not have.
    A band verdict may only be attributed to the frequencies inside that band,
    so the boundary is read off the finest non-overlapping partition available.
    """
    edges = _fine_partition()
    best = 0.0
    for a, b in edges:
        v = rec["bands"].get(f"{a:.2f}-{b:.2f}")
        if v and v["verdict"] == "PASS" and a >= 0.10:
            best = max(best, b)
    return best


def _fine_partition():
    """`FINE`, checked to actually BE a partition before anything relies on it.

    If bandsignal.FINE ever stops being contiguous and non-overlapping, the
    boundary definition above is meaningless -- so fail loudly rather than
    report a number derived from an assumption that has quietly expired.
    """
    e = sorted(FINE)
    for (a0, b0), (a1, b1) in zip(e, e[1:]):
        if abs(b0 - a1) > 1e-9:
            raise AssertionError(
                f"bandsignal.FINE is not a partition: {b0} -> {a1}")
    return e


def main():
    argv = sys.argv[1:]
    far_force = None
    if "--far" in argv:
        i = argv.index("--far")
        far_force = int(argv[i + 1])
        del argv[i:i + 2]
    if "--report" in argv:
        i = argv.index("--report")
        path = argv[i + 1]
        with open(path) as fh:
            report(json.load(fh), path)
        return 0
    want = argv
    subs = [s for s in SUBJECTS if not want or s[0] in want]
    recs = []
    for key, d in subs:
        if not os.path.isdir(d):
            print(f"SKIP {key}: {d} missing")
            continue
        r = sweep(key, d, far_force)
        if r:
            recs.append(r)

    out = os.path.join(
        _HERE, f"bandsweep{'-far%d' % far_force if far_force else ''}"
               f"{'-' + '+'.join(sorted(want)) if want else ''}.json")
    with open(out, "w") as fh:
        json.dump(recs, fh, indent=1)
    report(recs, out)
    print(f"\nwrote {out}")
    return 0


def report(recs, tag=""):
    keys = [f"{a:.2f}-{b:.2f}" for a, b in
            [(0.17, 0.20), (0.20, 0.25), (0.25, 0.30), (0.30, 0.40),
             (0.40, 0.48)]]
    print("\n" + "=" * 100)
    print(f"PER-SUBJECT BAND QUALIFICATION   {os.path.basename(tag)}")
    print("population: CONFIRMED where >=4 tiles, else ALL")
    print("rule: PASS = R>=2.0 and CI low>=1.5 | MARGINAL = 1.3<=R<2.0 | "
          "FAIL = R<1.3   (bandsignal.verdict)")
    print("=" * 100)
    hdr = f"{'subject':22} {'N':>4} {'st':>3} {'far':>4} {'pop':>9} {'kept':>4}"
    for k in keys:
        hdr += f" {k:>16}"
    print(hdr)
    for r in recs:
        line = (f"{r['key']:22} {r['n_real']:4d} {r['step']:3d} "
                f"{r['far_real']:4d} {r.get('population','-'):>9} "
                f"{r['kept']:4d}")
        for k in keys:
            b = r["bands"].get(k)
            line += (f" {b['R']:7.3f} {b['verdict'][:8]:>8}" if b
                     else f" {'-':>16}")
        print(line)

    print("\n" + "-" * 100)
    print("HEADLINE -- does the 0.25 cyc/px boundary hold corpus-wide?")
    print("(boundary read off the FINE partition only -- see boundary())")
    print("-" * 100)
    bs, dead = [], []
    for r in recs:
        b = boundary(r)
        bs.append((r["key"], b))
        if b == 0.0:
            dead.append(r["key"])
        print(f"  {r['key']:22} highest PASSing band edge = "
              f"{b:.2f} cyc/px" + ("   <== NO BAND QUALIFIES" if b == 0 else ""))
    vals = [b for _, b in bs]
    if vals:
        print(f"\n  range across subjects: {min(vals):.2f} - {max(vals):.2f} "
              f"cyc/px")
        print("  VERDICT: " + ("BOUNDARY MOVES BY SUBJECT -- no lane may use a "
                               "fixed band" if max(vals) != min(vals) else
                               "boundary is constant across the sampled "
                               "subjects"))
    if dead:
        print(f"\n  NO SHARPNESS CLAIM MAY BE MADE ON: {', '.join(dead)}")


if __name__ == "__main__":
    sys.exit(main())
