"""Does the SHIPPED bee-2-cpl master carry frame 46, or is the rogue frame a
fact about my own registration bundle?

Section 9.25 convicted one source frame on my own merge. That is a claim about
my model until it is shown on the deliverable. This asks the question on the
shipped SHIP-V4 master.

THE STATISTIC, AND WHY IT IS THIS ONE.

Band RMS divided by the L1 band RMS OF THE SAME IMAGE. A ratio taken inside one
image cancels any per-image gain exactly, because the Laplacian pyramid is
linear. That matters more here than anywhere: this project has twice reported a
statistic that turned out to be linear in exposure, once after the number had
been sent upward. `--linear-srgb` renders differ in gain from frame to frame and
from master to master, so no cross-image absolute amplitude is admissible. G1
below turns the invariance into a check that can fail rather than an assertion.

THE ARMS. Four, and the third is the one that makes the reading mean anything.

  A  my merge, all 287 registered frames
  B  my merge, minus frame 46                 -- the plant: must move
  C  my merge, minus an ordinary frame        -- the null: must not move
  S  the shipped SHIP-V4 master, same window, same pyramid

Without C, arm B only shows that dropping A frame changes the picture. C drops a
different frame from the same stack, so what separates B from C is frame 46's
identity and nothing else.

WHAT WOULD MAKE THIS UNINFORMATIVE, stated before the run. The shipping merge
differs from my model in alignment, CA correction, per-frame variance, and it
uses 299 frames where I admit 287. If S falls outside the [B, A] bracket the
bracket cannot locate it, and the honest answer is that this instrument cannot
decide the question -- not a number pushed to the nearer end.
"""
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_gbundle as GB  # noqa: E402
import vn_lib as L  # noqa: E402
import vn_pyr as VP  # noqa: E402
import vn_subgate as SG  # noqa: E402

NB = SG.NB
NORM = 1          # the band every other band is expressed against
ROGUE = 46        # the convicted source index
ORDINARY = 100    # the null arm's dropped frame: no claim attaches to it
COARSE = 3        # bands >= this are the ones section 9.25 convicted


def recompose(lap, base):
    """Collapse a Laplacian pyramid back to an image."""
    out = base
    for k in range(len(lap) - 1, -1, -1):
        out = VP.expand(out, lap[k].shape) + lap[k]
    return out


def shape(img):
    """Band RMS normalised by band NORM of the same image."""
    lap, _ = VP.lap_pyr(np.asarray(img, dtype=np.float64), NB)
    r = [float(np.sqrt((b ** 2).mean())) for b in lap]
    d = r[NORM]
    if d <= 0.0:
        raise SystemExit("REFUSED: band %d is identically zero" % NORM)
    return [x / d for x in r], r


def merge(frames, varp, skip=None, extra=None):
    """The shipping reconstruction from pyramid.rs, as in vn_rogue_img."""
    wl = [None] * NB
    sw = [None] * NB
    sl = [None] * NB
    base = None
    m = 0
    seq = [f for j, f in enumerate(frames) if j != skip]
    if extra is not None:
        seq = seq + [extra]
    for f in seq:
        m += 1
        lap, b = VP.lap_pyr(np.asarray(f, dtype=np.float64), NB)
        base = b if base is None else base + b
        for k in range(NB):
            floor = np.maximum(SG.GATE * SG.BETA[k]
                               * np.maximum(varp[k], 0.0), 1.0)
            ex = VP.smooth5(lap[k] ** 2) - floor
            r = np.where(ex > 0.0, ex / floor / VP.SNR_REF, 0.0)
            w = np.where(ex > 0.0, r ** SG.EXPO[k], 0.0)
            wl[k] = w * lap[k] if wl[k] is None else wl[k] + w * lap[k]
            sw[k] = w.copy() if sw[k] is None else sw[k] + w
            sl[k] = lap[k].copy() if sl[k] is None else sl[k] + lap[k]
    out = base / m
    for k in range(NB - 1, -1, -1):
        g = np.where(sw[k] > 0.0, wl[k] / np.where(sw[k] > 0.0, sw[k], 1.0),
                     sl[k] / m)
        out = VP.expand(out, g.shape) + g
    return out


def main():
    frames, kept, meta = GB.load("bee-2-cpl", rule="registered")
    n = len(frames)
    hit = [j for j in range(n) if int(kept[j]) == ROGUE]
    if len(hit) != 1:
        raise SystemExit("REFUSED: source frame %d appears %d times in the "
                         "admitted set" % (ROGUE, len(hit)))
    j46 = hit[0]
    hit = [j for j in range(n) if int(kept[j]) == ORDINARY]
    if len(hit) != 1:
        raise SystemExit("REFUSED: null frame %d appears %d times"
                         % (ORDINARY, len(hit)))
    jord = hit[0]
    varp = VP.gauss_pyr(VP.fit_variance(frames[0])[0], NB)

    print("bee-2-cpl: %d admitted frames; rogue at index %d, null at %d"
          % (n, j46, jord))
    imgA = merge(frames, varp)
    imgB = merge(frames, varp, skip=j46)
    imgC = merge(frames, varp, skip=jord)
    shA, rawA = shape(imgA)
    shB, _ = shape(imgB)
    shC, _ = shape(imgC)

    # --- commissioning, both directions, before any verdict ---------------
    fails = []
    shG, _ = shape(imgA * 1.7)
    g1 = max(abs(shG[k] - shA[k]) for k in range(NB))
    if g1 > 1e-9:
        fails.append("G1 gain invariance: 1.7x gain moved a band ratio by "
                     "%.3g, want < 1e-9" % g1)
    g2 = shA[5] / shB[5]
    if g2 < 2.0:
        fails.append("G2 the plant must move it: L5 shape ratio A/B = %.4f, "
                     "want > 2" % g2)
    g3 = shA[5] / shC[5]
    if not (1 / 1.1 < g3 < 1.1):
        fails.append("G3 the null must not move it: dropping an ordinary "
                     "frame gave A/C = %.4f, want within 1.1x" % g3)
    # G4/G5 dissect the CAUSE from a CORRELATE, and the first design of this
    # control was wrong in a way worth recording. Frame 46 is two stops dark
    # AND holds 60x the median coarse-band energy. My first plant scaled an
    # ordinary frame to 0.249x level -- which reproduces the darkness and
    # reproduces none of the effect (measured: 0.9998x, no movement at all),
    # because scaling a frame down scales its band energy DOWN with it. That
    # plant tested the correlate. Darkness alone does not do this.
    # So swap the coarse bands instead, both ways round:
    #   G4 sufficiency -- an ORDINARY frame wearing frame 46's coarse bands
    #                     must reproduce the capture.
    #   G5 necessity   -- FRAME 46 wearing ordinary coarse bands must not.
    # Together they say the coarse bands are the cause and nothing else about
    # frame 46 is.
    lap46, b46 = VP.lap_pyr(np.asarray(frames[j46], dtype=np.float64), NB)
    lapo, bo = VP.lap_pyr(np.asarray(frames[jord], dtype=np.float64), NB)
    suff = recompose([lap46[k] if k >= COARSE else lapo[k]
                      for k in range(NB)], bo)
    nec = recompose([lapo[k] if k >= COARSE else lap46[k]
                     for k in range(NB)], b46)
    shD, _ = shape(merge(frames, varp, skip=j46, extra=suff))
    shE, _ = shape(merge(frames, varp, skip=j46, extra=nec))
    g4 = shD[5] / shB[5]
    g5 = shE[5] / shB[5]
    if g4 < 1.5:
        fails.append("G4 sufficiency: an ordinary frame wearing frame 46's "
                     "coarse bands moved L5 only %.4fx, want > 1.5" % g4)
    if not (1 / 1.25 < g5 < 1.25):
        fails.append("G5 necessity: frame 46 wearing ordinary coarse bands "
                     "still moved L5 by %.4fx, want within 1.25" % g5)
    print("commissioning")
    print("  G1 gain invariance      max band-ratio drift %.3g" % g1)
    print("  G2 plant moves L5       A/B = %.4f" % g2)
    print("  G3 null does not        A/C = %.4f" % g3)
    print("  G4 sufficiency (bands)  D/B = %.4f" % g4)
    print("  G5 necessity   (bands)  E/B = %.4f" % g5)
    if fails:
        print("REFUSED -- instrument not commissioned:")
        for f in fails:
            print("   " + f)
        return 2
    print("  all five pass")

    # --- the shipped master, same window, same pyramid --------------------
    mp = L.ensure_linear_master("bee-2-cpl")
    mrgb = L.read_rgb(mp)
    bw, _cw = L.choose_windows(mrgb)
    win = mrgb[bw[0]:bw[0] + L.BWIN, bw[1]:bw[1] + L.BWIN, 1]
    if win.shape != np.asarray(frames[0]).shape:
        raise SystemExit("REFUSED: master window %s does not match the bundle "
                         "grid %s; the band indices are not comparable"
                         % (win.shape, np.asarray(frames[0]).shape))
    shS, rawS = shape(win)

    rows = []
    for k in range(NB):
        span = shA[k] - shB[k]
        t = (shS[k] - shB[k]) / span if abs(span) > 1e-12 else None
        rows.append(dict(band=k, A=shA[k], B=shB[k], C=shC[k], S=shS[k],
                         plant_span=span, t=t,
                         inside=(t is not None and -0.25 <= t <= 1.25)))
    print("\n band   A all     B -rogue  C -ordinary  S shipped   t in [B,A]")
    for x in rows:
        print("  L%d %9.4f %9.4f %10.4f %11.4f %10s"
              % (x["band"], x["A"], x["B"], x["C"], x["S"],
                 ("%.3f" % x["t"]) if x["t"] is not None else "n/a"))

    live = [x for x in rows if x["t"] is not None and abs(x["plant_span"])
            > 0.05 * max(x["A"], x["B"])]
    inside = [x for x in live if x["inside"]]
    verdict = "UNDECIDED"
    if not live:
        verdict = "UNDECIDED: no band has a plant span large enough to locate S"
    elif len(inside) < len(live):
        verdict = ("UNDECIDED: S falls outside the [B, A] bracket at %d of %d "
                   "discriminating bands; the shipping merge differs from this "
                   "model by more than the plant does"
                   % (len(live) - len(inside), len(live)))
    else:
        tm = float(np.median([x["t"] for x in inside]))
        verdict = ("CARRIES IT (median t = %.3f)" % tm if tm > 0.5
                   else "DOES NOT CARRY IT (median t = %.3f)" % tm)
    print("\nbands that discriminate: %d of %d; S inside the bracket at %d"
          % (len(live), NB, len(inside)))
    print("VERDICT: %s" % verdict)

    res = dict(subject="bee-2-cpl", n_admitted=n, rogue_source_index=ROGUE,
               null_source_index=ORDINARY, norm_band=NORM,
               commission=dict(g1_gain_drift=g1, g2_plant=g2, g3_null=g3,
                               g4_sufficiency=g4, g5_necessity=g5,
                               g4_first_design_scaled_dark=0.9998,
                               passed=True),
               master=os.path.basename(mp), window=[int(bw[0]), int(bw[1])],
               raw_rms_A=rawA, raw_rms_S=rawS, rows=rows,
               n_discriminating=len(live), n_inside=len(inside),
               verdict=verdict)
    p = os.path.join(SG.OUT, "shipped46.json")
    json.dump(res, io.open(p, "w", encoding="utf-8"), default=float, indent=1)
    print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
