r"""dcnull.py -- planted DC-offset and pure-gain nulls on the instrument that
actually produced the published merge-vs-best-frame band ratios.

WHY THIS EXISTS.  V-H2H2 measured that `experiments/ORCH-drift-check/contrast_ms.py`
returns 0.9696 on an arm whose true answer is exactly 1.000, because it rescales B's
pixels by a median ratio that a DC offset moves.  The published softness numbers
(1.0997 / 1.1936 / 1.1345 / 0.9426 / 0.7314 / 0.6063 / 0.5942 on `113MSDCF`) were NOT
produced by that file, so the question is whether the instrument that DID produce them
carries the same class of defect: a band power divided by a statistic that a DC offset
moves.

WHICH INSTRUMENT.  `docs/research/V-SOFTCHECK-bandqual.md:406` sources the seven
numbers to `V-SOFTCHECK-nyquist.md`, whose "N hypothesis" table has columns
merge-of-63 / merge-of-32 / difference over the seven bands 0.05-0.40 and a diagnostic
column `max63/max32` that "read exactly 1.0000 at all seven bands".  Exactly one script
in the tree prints that table: `experiments/V-SOFTCHECK/ncommon.py`.  Its scoring
function is `rings()`; the ratio is `median_t( rings(master)_b / max_k rings(frame_k)_b )`.
`ntest.py` carries a byte-identical `rings()` and is checked for that here.

NO RE-RUN ON REAL PIXELS IS POSSIBLE.  `C:\dev\strehl-out\V-SOFTCHECK` no longer
exists, so the seven numbers cannot be recomputed from their own inputs.  A planted
null needs no photographs: it needs a scene, a plant whose true answer is known in
advance, and the real scoring code.

WHAT IS RUN
  P0  potency of the probe            blur plant must move the score
  P1  potency of the probe on DC      a deliberately mean-normalised scorer, the
                                      vulnerability class under test, must move
  Q1  DC-offset null on ncommon       true answer 1.0000 at every band
  Q2  pure-gain null on ncommon       report what it does; gain is NOT normalised here
  Q3  DC and gain nulls on bandqual   the qualifier that chose the 0.20-0.25 band

Every extraction is anchored on a unique string and hard-errors if it does not land.
"""
import os, sys
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SOFT = os.path.abspath(os.path.join(HERE, "..", "V-SOFTCHECK"))
sys.path.insert(0, SOFT)


def die(msg):
    sys.exit("ABORT: " + msg)


def anchored(src, start, end, where):
    """Slice src from a UNIQUE start anchor to a UNIQUE end anchor. Hard-error
    if either anchor is absent or ambiguous -- an extraction that silently
    misses reads exactly like one that landed."""
    for a in (start, end):
        n = src.count(a)
        if n != 1:
            die("anchor %r occurs %d times in %s -- extraction did not land" % (a, n, where))
    i = src.index(start)
    j = src.index(end, i) + len(end)
    if j <= i:
        die("anchors out of order in %s" % where)
    return src[i:j]


# ------------------------------------------------------------------ producer
NCOMMON = os.path.join(SOFT, "ncommon.py")
NTEST = os.path.join(SOFT, "ntest.py")
with open(NCOMMON, encoding="utf-8") as fh:
    NSRC = fh.read()
with open(NTEST, encoding="utf-8") as fh:
    TSRC = fh.read()

CONST = anchored(NSRC, "T=256; NT=300",
                 'masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]', "ncommon.py consts")
RINGS = anchored(NSRC, "def rings(img,yy,xx):",
                 "return np.stack([P[:,m].mean(1) for m in masks],axis=1)", "ncommon.py rings")
RINGS_T = anchored(TSRC, "def rings(img,yy,xx):",
                   "return np.stack([P[:,m].mean(1) for m in masks],axis=1)", "ntest.py rings")
with open(os.path.join(SOFT, "ncurve.py"), encoding="utf-8") as fh:
    CSRC = fh.read()
RINGS_C = anchored(CSRC, "def rings(img,yy,xx):",
                   "return np.stack([P[:,m].mean(1) for m in masks],axis=1)", "ncurve.py rings")
SAME_RINGS = (RINGS == RINGS_T == RINGS_C)

NS = {"np": np}
exec(CONST, NS)
exec(RINGS, NS)
rings = NS["rings"]
T = NS["T"]
EDGES = NS["EDGES"]
MASKS = NS["masks"]
NB = len(MASKS)
if T != 256 or NB != 7:
    die("extracted constants are not the published ones: T=%r NB=%r" % (T, NB))


def bname(b):
    return "%.2f-%.2f" % (EDGES[b], EDGES[b + 1])


# ------- the mean-normalised scorer: the DEFECT CLASS, present here on purpose.
# This is NOT ncommon.py. It is the counterfactual instrument the orchestrator
# asked about -- band power divided by a level statistic a DC offset moves. It
# exists so that "DC did not move ncommon" can be shown to be a real null and not
# a dead probe.
def rings_meannorm(img, yy, xx):
    H, W = img.shape
    yy = np.clip(yy, 0, H - T)
    xx = np.clip(xx, 0, W - T)
    tl = np.stack([img[y:y + T, x:x + T] for y, x in zip(yy, xx)]).astype(np.float32)
    mu = tl.mean(axis=(1, 2))
    tl = (tl - mu[:, None, None]) * NS["WIN"]
    P = np.abs(np.fft.fft2(tl)) ** 2
    out = np.stack([P[:, m].mean(1) for m in MASKS], axis=1)
    return out / (mu[:, None] ** 2)


# ------------------------------------------------------------------ scene
def scene(H=1024, W=1024, seed=11):
    r = np.random.default_rng(seed)
    n = r.standard_normal((H, W))
    fy = np.fft.fftfreq(H); fx = np.fft.fftfreq(W)
    rr = np.hypot(*np.meshgrid(fy, fx, indexing="ij"))
    F = np.fft.fft2(n) / np.maximum(rr, 1.0 / max(H, W)) ** 0.8
    x = np.real(np.fft.ifft2(F))
    x /= x.std()
    for _ in range(40):                      # hard edges: broadband content
        y0 = int(r.integers(0, H - 80)); x0 = int(r.integers(0, W - 80))
        h = int(r.integers(6, 70)); w = int(r.integers(6, 70))
        x[y0:y0 + h, x0:x0 + w] += float(r.uniform(1.5, 4.0))
    return (1200.0 + 260.0 * x).astype(np.float32)


def focus_stack(base, K=9, seed=3):
    """K frames, four depth zones, each zone in focus at a different frame."""
    r = np.random.default_rng(seed)
    H = base.shape[0]
    zones = [(0, H // 4), (H // 4, H // 2), (H // 2, 3 * H // 4), (3 * H // 4, H)]
    kpk = [1, 3, 5, 7]
    frames = []
    for k in range(K):
        f = np.empty_like(base)
        for (a, b), kp in zip(zones, kpk):
            s = 0.42 * abs(k - kp)
            seg = base[a:b]
            f[a:b] = seg if s < 1e-6 else ndimage.gaussian_filter(seg, s, mode="reflect")
        f = f + (2.6 * r.standard_normal(base.shape)).astype(np.float32)
        frames.append(f.astype(np.float32))
    return frames


def merge_of(base, frames, extra_blur=0.55):
    """A plausible focus merge: per-zone pick of the sharpest frame, then a small
    residual softening so the baseline ratio is not trivially 1."""
    H = base.shape[0]
    zones = [(0, H // 4), (H // 4, H // 2), (H // 2, 3 * H // 4), (3 * H // 4, H)]
    kpk = [1, 3, 5, 7]
    m = np.empty_like(base)
    for (a, b), kp in zip(zones, kpk):
        m[a:b] = frames[kp][a:b]
    return ndimage.gaussian_filter(m, extra_blur, mode="reflect").astype(np.float32)


def grid(H, W, step=128):
    ys = np.arange(0, H - T + 1, step)
    xs = np.arange(0, W - T + 1, step)
    gy, gx = np.meshgrid(ys, xs, indexing="ij")
    return gy.ravel(), gx.ravel()


def band_ratios(M, frames, oy, ox, score=rings):
    """ncommon.py's arithmetic, verbatim: per-site max over frames as the
    denominator, median over tiles of the per-tile ratio."""
    MAr = score(M, oy, ox)
    Fr = np.stack([score(f, oy, ox) for f in frames])
    den = np.maximum(Fr.max(0), 1e-30)
    return np.array([float(np.median(MAr[:, b] / den[:, b])) for b in range(NB)])


# ------------------------------------------------------------------ plants
def plant_dc(x, c):
    y = (x + np.float32(c)).astype(np.float32)
    d = (y.astype(np.float64) - x.astype(np.float64))
    err = float(np.max(np.abs(d - c)))
    if err > 1e-3 * abs(c):
        die("DC plant did not land: max|delta - c| = %.6g for c = %g" % (err, c))
    if float(np.min(np.abs(d))) == 0.0 and c != 0:
        die("DC plant inert on at least one pixel")
    return y


def plant_gain(x, g):
    y = (x * np.float32(g)).astype(np.float32)
    ref = x.astype(np.float64) * g
    err = float(np.max(np.abs(y.astype(np.float64) - ref)))
    tol = 1e-5 * float(np.max(np.abs(ref)))
    if err > tol:
        die("gain plant did not land: max abs err %.6g > tol %.6g" % (err, tol))
    if g != 1.0 and np.array_equal(y, x):
        die("gain plant inert -- image unchanged")
    return y


def plant_blur(x, s):
    y = ndimage.gaussian_filter(x, s, mode="reflect").astype(np.float32)
    if np.array_equal(y, x):
        die("blur plant inert -- image unchanged")
    return y


def row(tag, r, base=None):
    cells = " ".join("%8.4f" % v for v in r)
    line = "  %-34s %s" % (tag, cells)
    if base is not None:
        dev = np.max(np.abs(r / base - 1.0))
        line += "   maxdev %.3e" % dev
    print(line)


def header():
    print("  %-34s %s" % ("", " ".join("%8s" % bname(b) for b in range(NB))))


def main():
    print("V-DCNULL -- planted nulls on the producer of the published band ratios\n")
    print("  producer      experiments/V-SOFTCHECK/ncommon.py :: rings()")
    print("  extraction    anchored, landed; ntest/ncurve rings() byte-identical: %s" % SAME_RINGS)
    print("  bands         %s" % ", ".join(bname(b) for b in range(NB)))
    if not SAME_RINGS:
        die("ncommon/ntest/ncurve rings() differ -- scope of this report is wrong")

    base = scene()
    frames = focus_stack(base)
    M = merge_of(base, frames)
    oy, ox = grid(*base.shape)
    lvl = float(np.median(M))
    print("  scene         1024x1024, %d tiles of %d, %d frames, median level %.1f DN\n"
          % (len(oy), T, len(frames), lvl))

    r0 = band_ratios(M, frames, oy, ox)
    header()
    row("BASELINE  merge/max-over-frames", r0)

    # ---------------- P0: the probe must move when something really differs
    print("\nP0 POTENCY -- a real blur on the master must reduce the score")
    for s in (0.5, 1.0):
        rb = band_ratios(plant_blur(M, s), frames, oy, ox)
        row("blur sigma %.1f on master" % s, rb, r0)
    print("     if these do not fall, nothing below certifies anything")

    # ---------------- P1: the probe must move when a DC offset really does bite
    print("\nP1 POTENCY OF THE DC PROBE -- same plant, mean-normalised scorer")
    print("     rings_meannorm divides band power by the tile mean squared. It is the")
    print("     defect class under test and is NOT ncommon.py.")
    rm0 = band_ratios(M, frames, oy, ox, score=rings_meannorm)
    row("meannorm BASELINE", rm0)
    for c in (250.0, 1000.0):
        rmc = band_ratios(plant_dc(M, c), frames, oy, ox, score=rings_meannorm)
        row("meannorm + DC %+.0f DN on master" % c, rmc, rm0)

    # ---------------- Q1: the DC null on the real producer
    print("\nQ1 DC-OFFSET NULL on ncommon.py rings()   true answer 1.0000 every band")
    for c in (250.0, 1000.0, -250.0):
        rc = band_ratios(plant_dc(M, c), frames, oy, ox)
        row("DC %+.0f DN on master only" % c, rc, r0)
    rc = band_ratios(M, [plant_dc(f, 250.0) for f in frames], oy, ox)
    row("DC +250 DN on all frames only", rc, r0)
    rc = band_ratios(plant_dc(M, 250.0), [plant_dc(f, 250.0) for f in frames], oy, ox)
    row("DC +250 DN on both sides", rc, r0)
    rc = band_ratios(M, [plant_dc(f, 250.0) if k % 2 == 0 else f
                         for k, f in enumerate(frames)], oy, ox)
    row("DC +250 DN on even frames only", rc, r0)

    # ---------------- Q2: the pure-gain null on the real producer
    print("\nQ2 PURE-GAIN NULL on ncommon.py rings()   a gain-normalising instrument")
    print("   would return 1.0000; ncommon.py does not normalise gain.")
    for g in (1.15, 1.0327):
        rg = band_ratios(plant_gain(M, g), frames, oy, ox)
        row("gain x%.4f on master only" % g, rg, r0)
        obs = float(np.median(rg / r0))
        print("     observed rg/r0 median %.6f   predicted g^2 %.6f   rel err %.2e"
              % (obs, g * g, abs(obs - g * g) / (g * g)))
    rg = band_ratios(plant_gain(M, 1.15), [plant_gain(f, 1.15) for f in frames], oy, ox)
    row("gain x1.1500 on BOTH sides", rg, r0)

    # ---------------- Q3: the qualifier
    print("\nQ3 THE QUALIFIER -- bandqual.py, which chose 0.20-0.25 as the highest")
    print("   band carrying real detail (R = 3.32). Its statistic is gain-normalised.")
    import dmeasure as DM
    import bandqual as BQ
    if DM.T != T:
        die("bandqual tile size %d != producer tile size %d" % (DM.T, T))
    if "P / (g[:, None, None] ** 2)" not in open(os.path.join(SOFT, "bandqual.py"),
                                                 encoding="utf-8").read():
        die("bandqual.gnorm no longer divides by g^2 -- this report describes stale code")

    def bq_R(fs):
        Ps, gs = [], []
        for f in fs:
            a, mu = DM.bandpow(f, oy, ox)
            Ps.append(a); gs.append(float(np.nanmedian(mu)))
        P = BQ.gnorm(np.stack(Ps), np.array(gs))
        return np.array([float(BQ.ratio(P, np.arange(len(oy)), BQ.SEL, b)[0]) for b in range(NB)])

    R0 = bq_R(frames)
    header()
    row("bandqual BASELINE R", R0)
    RD = bq_R([plant_dc(f, 250.0) for f in frames])
    row("bandqual DC +250 DN on all frames", RD, R0)
    RD2 = bq_R([plant_dc(f, 250.0) if k % 2 == 0 else f for k, f in enumerate(frames)])
    row("bandqual DC +250 DN on even frames", RD2, R0)
    RG = bq_R([plant_gain(f, 1.15) for f in frames])
    row("bandqual gain x1.15 all frames", RG, R0)
    rj = np.random.default_rng(9)
    jit = 1.0 + 0.05 * rj.standard_normal(len(frames))
    RJ = bq_R([plant_gain(f, jit[k]) for k, f in enumerate(frames)])
    row("bandqual per-frame gain jitter 5%", RJ, R0)

    # The uniform-DC arm above is degenerate on a stack whose frames share a mean:
    # gnorm divides frame k by g_k^2 and a common offset cancels between the two
    # frames entering the ratio. Real probes do NOT share a mean -- bandqual.py
    # prints their spread as `rel sd`. So: give the stack a real level spread first,
    # THEN apply the same uniform DC offset. The true answer is still 1.0000.
    print("\nQ3b bandqual on a stack with a REAL per-frame level spread, then uniform DC")
    lev = [plant_gain(f, jit[k]) for k, f in enumerate(frames)]
    gk = np.array([float(np.nanmedian(DM.bandpow(f, oy[:1], ox[:1])[1])) for f in lev])
    print("     per-frame level %.1f .. %.1f DN, rel sd %.4f (%.3fx spread)"
          % (gk.min(), gk.max(), gk.std() / gk.mean(), gk.max() / gk.min()))
    RL0 = bq_R(lev)
    header()
    row("bandqual spread BASELINE", RL0)
    for c in (250.0, 1000.0):
        RLc = bq_R([plant_dc(f, c) for f in lev])
        row("bandqual spread + uniform DC %+.0f DN" % c, RLc, RL0)

    # How much master-vs-frame GAIN mismatch would be needed to manufacture the
    # published 0.9426 out of a true 1.0000, given the measured g^2 law?
    print("\nQ2b what the measured g^2 law costs the published number")
    pub = 0.9426
    print("     r_obs = r_true * (g_master/g_frame)^2  [measured to 1.5e-07 above]")
    print("     a true 1.0000 reads %.4f if g_master/g_frame = %.6f  (%.2f%% level mismatch)"
          % (pub, np.sqrt(pub), 100 * (1 - np.sqrt(pub))))
    print("     a 1%% master under-gain alone moves the reading by %.4f" % (1 - 0.99 ** 2))

    # Can the worst DC bias measured on the qualifier move the published band
    # selection? Real-data readings, quoted from V-SOFTCHECK-bandqual.md:167.
    print("\nQ3c does the qualifier's DC bias move the published band selection?")
    worst = float(np.max(np.abs(bq_R([plant_dc(f, 250.0) if k % 2 == 0 else f
                                      for k, f in enumerate(frames)]) / R0 - 1.0)))
    R_pub, CI_pub, PASS_R, PASS_LO = 3.3235, 2.9495, BQ.PASS_R, BQ.PASS_LO
    print("     worst DC bias measured on R here: %.4f (differential DC across frames)" % worst)
    print("     published 0.20-0.25 on 113MSDCF: R = %.4f, CI low = %.4f" % (R_pub, CI_pub))
    print("     deflated by that bias:           R = %.4f, CI low = %.4f  (bars %.2f / %.2f)"
          % (R_pub / (1 + worst), CI_pub / (1 + worst), PASS_R, PASS_LO))
    print("     PASS survives deflation: %s"
          % (R_pub / (1 + worst) >= PASS_R and CI_pub / (1 + worst) > PASS_LO))

    print("\nDONE")


if __name__ == "__main__":
    main()
