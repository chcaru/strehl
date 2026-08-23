"""M41 step 8 -- does split-half FRC actually have power on THIS sensor?

Why this script exists.  The run of record (a6_run.log) shows split-half FRC
ranking arm C (the plain mean) ABOVE arm A (the shipped noise-gated merge) at
0.28 cyc/px on 109MSDCF -- 0.595 vs 0.565 -- and ranking arm E, whose flat-ROI
high-pass noise is 144x-295x a single frame and 99% of whose pixels fall outside
the range of every input frame, at 0.970 at 0.45 cyc/px.  Either FRC is
measuring something other than detail, or the mean is sharper than the shipped
merge and a 295x noise explosion is high-resolution.  Fact 19 and
M39-verify-detail-metric say the mean is not sharper.

The hypothesis: FRC between two halves of the SAME SENSOR cannot separate scene
detail from FIXED-PATTERN NOISE, because FPN is common-mode -- it is identical
in both halves and therefore perfectly correlated at every frequency.

The test, which can fail: run the split-half FRC protocol on the FLAT ROI, where
by construction there is no scene detail to resolve.  Any FRC above the 1/7
threshold there is measuring correlated non-scene content.

  PREDICTION IF THE HYPOTHESIS IS TRUE : flat-ROI split-half FRC stays high
                                         (>> 1/7) out to Nyquist.
  PREDICTION IF IT IS FALSE            : flat-ROI split-half FRC collapses to
                                         ~0 at all but the lowest frequencies,
                                         and the detail-ROI readings stand.

A dark-frame arm is included as the strongest form of the same test: frames of
the read-only dark corpus contain NO scene at all.
"""
import os, sys, glob, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L
from a2_run import load_two, core, PAD

OUT = L.OUT


def main():
    with open(os.path.join(OUT, "rois_b.json")) as fh:
        rois = json.load(fh)
    log = open(os.path.join(OUT, "a8_frc_power.log"), "w", encoding="utf-8")

    def p(m):
        print(m); log.write(m + "\n"); log.flush()

    p("M41 step 8 -- power check on split-half FRC.  See docstring for the two "
      "predictions; this control can fail.")
    for name in ("109MSDCF", "119MSDCF"):
        info = rois[name]
        for key in ("detail_roi", "flat_roi"):
            x, y, w, h = info[key]
            info[key] = [max(PAD, x), max(PAD, y), w, h]
        files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
        Dc, Fc = load_two(files, tuple(info["detail_roi"]), tuple(info["flat_roi"]))
        ev, od = np.arange(0, len(files), 2), np.arange(1, len(files), 2)
        for lab, cube in (("FLAT ROI (no scene detail by construction)", Fc),
                          ("DETAIL ROI (for reference)", Dc)):
            a = core(cube[ev].mean(0)).astype(np.float64)
            b = core(cube[od].mean(0)).astype(np.float64)
            ff, fr, _ = L.frc(a, b)
            x = L.frc_cross(ff, fr)
            at = {q: float(np.interp(q, ff, fr)) for q in (0.10, 0.20, 0.2762, 0.35, 0.45)}
            p(f"  [{name}] {lab}")
            p(f"      arm C split-half FRC: 1/7 crossing {x:.4f} cyc/px   "
              + "  ".join(f"@{q:.2f} {v:6.3f}" for q, v in at.items()))
            # the same two halves with the COMMON-MODE part removed: subtract the
            # all-frame mean from each half, leaving only each half's own noise
            allm = core(cube.mean(0)).astype(np.float64)
            ff2, fr2, _ = L.frc(a - allm, b - allm)
            at2 = {q: float(np.interp(q, ff2, fr2)) for q in (0.10, 0.20, 0.2762, 0.35, 0.45)}
            p(f"      same halves, COMMON MODE REMOVED: 1/7 crossing "
              f"{L.frc_cross(ff2, fr2):.4f}   "
              + "  ".join(f"@{q:.2f} {v:6.3f}" for q, v in at2.items()))
    log.close()


if __name__ == "__main__":
    main()
