"""The rogue frame through the SHIPPING BINARY, not through my model.

Section 9.25 convicted source frame 46 of bee-2-cpl inside my own offline
reimplementation of the pyramid merge. `vn_shipped.py` then tried to locate the
shipped master between a with-rogue and a without-rogue arm of that model and
returned UNDECIDED: the model-to-shipping systematic is the same order as the
plant at some bands, so the bracket cannot place it. That is the right answer
for that instrument and it is not an answer to the question.

This removes the model. `--limit N` stacks the first N frames in filename
order, and `vn_lib.frames_of` is `sorted(...)` over the same directory, so the
frame my bundle calls source index 46 is the 47th file. Therefore:

    --limit 46   frames 0..45   the rogue is ABSENT
    --limit 47   frames 0..46   the rogue is PRESENT

Two renders through the pinned binary, on the real stack, with real alignment,
real CA correction and the real merge, differing by EXACTLY ONE FRAME.

THE NULLS ARE THE EXPERIMENT. `--limit 44 -> 45` and `--limit 45 -> 46` also add
exactly one frame each, and those frames are ordinary. If adding any frame to a
stack this size moves the statistic, the 46->47 step proves nothing. Two nulls,
not one, because a single null that happens to sit near a plant is not a null.

GAUGE. Renders use MEASURE_FLAGS (`--linear-srgb --demosaic`) -- no tone curve,
no auto-exposure -- and the statistic is a ratio taken inside one image, so any
per-image gain cancels exactly. Both belts are deliberate: this project has
twice shipped a statistic that was linear in exposure.

FIELD OF VIEW is the confound to watch. The merge aligns by default and crops to
the common field, so a different frame set can mean a different crop and the
fixed window would then cover different scene content. The nulls control for it
-- they change the frame set too -- and the log's own "field of view scaled to"
is recorded for every arm so the crop can be inspected rather than assumed.
"""
import io
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L  # noqa: E402
import vn_pyr as VP  # noqa: E402
import vn_subgate as SG  # noqa: E402

NB = SG.NB
NORM = 1
SUBJ = "bee-2-cpl"
ROGUE = 46
LIMITS = [44, 45, 46, 47]
SCRATCH = os.path.join(SG.OUT, "shipfr")
_NFR = re.compile(r"frames\s*:\s*(\d+) from")


def shape_at(rgb, bw):
    win = rgb[bw[0]:bw[0] + L.BWIN, bw[1]:bw[1] + L.BWIN, 1]
    lap, _ = VP.lap_pyr(np.asarray(win, dtype=np.float64), NB)
    r = [float(np.sqrt((b ** 2).mean())) for b in lap]
    return [x / r[NORM] for x in r], r


def main():
    sha = L.check_pin()
    os.makedirs(SCRATCH, exist_ok=True)
    names = L.frames_of(SUBJ)
    print("pin %s" % sha[:16])
    print("%s: %d frames; the rogue is file index %d = %s"
          % (SUBJ, len(names), ROGUE, names[ROGUE]))
    print("  --limit 46 stops at %s (rogue absent)" % names[45])
    print("  --limit 47 stops at %s (rogue present)" % names[46])

    arms = {}
    for n in LIMITS:
        tif = os.path.join(SCRATCH, "%s--L%d.tiff" % (SUBJ, n))
        lg = tif[:-5] + ".log"
        if not (os.path.exists(tif) and os.path.exists(lg)):
            log = L.render(SUBJ, tif, extra=["--limit", str(n)])
            io.open(lg, "w", encoding="utf-8").write(log)
        log = io.open(lg, encoding="utf-8").read()
        m = _NFR.search(log)
        got = int(m.group(1)) if m else None
        # A flag that parses and does nothing is indistinguishable from one
        # that works. The CLI's own help says so. Make it prove it.
        if got != n:
            raise SystemExit("REFUSED: --limit %d produced a log claiming %r "
                             "frames; the flag did not do what it says" %
                             (n, got))
        cov = L._COVER.search(log)
        arms[n] = dict(tiff=tif, n=got,
                       cover=float(cov.group(1)) if cov else None)
        print("  rendered --limit %-3d frames=%d cover=%s"
              % (n, got, arms[n]["cover"]))

    # One window, chosen on the arm WITHOUT the rogue, applied to every arm.
    base = L.read_rgb(arms[46]["tiff"])
    bw, _cw = L.choose_windows(base)
    print("window %s from the --limit 46 arm, applied to all arms" % (bw,))
    shp = {}
    for n in LIMITS:
        rgb = base if n == 46 else L.read_rgb(arms[n]["tiff"])
        if rgb.shape != base.shape:
            raise SystemExit("REFUSED: --limit %d rendered %s against %s for "
                             "--limit 46; a fixed window is not the same scene"
                             % (n, rgb.shape, base.shape))
        shp[n], raw = shape_at(rgb, bw)
        arms[n]["shape"] = shp[n]
        arms[n]["raw_rms"] = raw

    steps = [(44, 45, "null"), (45, 46, "null"), (46, 47, "ROGUE")]
    print("\n            step             kind      L3     L4     L5     L6")
    rows = []
    for a, b, kind in steps:
        r = [shp[b][k] / shp[a][k] if shp[a][k] else None for k in range(NB)]
        rows.append(dict(frm=a, to=b, kind=kind, ratio=r))
        print("  +1 frame %2d -> %2d   %8s  %6.3f %6.3f %6.3f %6.3f"
              % (a, b, kind, r[3], r[4], r[5], r[6]))

    nulls = [x for x in rows if x["kind"] == "null"]
    plant = [x for x in rows if x["kind"] == "ROGUE"][0]
    band = 5
    nmax = max(max(x["ratio"][band], 1.0 / x["ratio"][band]) for x in nulls)
    p = plant["ratio"][band]
    sep = p / nmax
    print("\n  worst null at L%d      %.4fx" % (band, nmax))
    print("  the rogue step at L%d  %.4fx" % (band, p))
    print("  separation            %.2fx" % sep)

    if nmax > 1.25:
        verdict = ("UNDECIDED: adding an ordinary frame already moves L%d by "
                   "%.3fx, so this stack size cannot isolate one frame"
                   % (band, nmax))
    elif p > 1.5 * nmax:
        verdict = ("THE SHIPPING BINARY CARRIES IT: adding frame %d multiplies "
                   "the L%d band shape by %.3fx where adding an ordinary frame "
                   "moves it at most %.3fx" % (ROGUE, band, p, nmax))
    else:
        verdict = ("NOT REPRODUCED IN THE SHIPPING BINARY: adding frame %d "
                   "moves L%d by %.3fx against a worst null of %.3fx"
                   % (ROGUE, band, p, nmax))
    print("\nVERDICT: %s" % verdict)

    res = dict(subject=SUBJ, pin=sha, rogue_source_index=ROGUE,
               rogue_file=names[ROGUE], norm_band=NORM,
               arms={str(n): dict(n=arms[n]["n"], cover=arms[n]["cover"],
                                  shape=arms[n]["shape"],
                                  raw_rms=arms[n]["raw_rms"])
                     for n in LIMITS},
               window=[int(bw[0]), int(bw[1])], steps=rows,
               worst_null=nmax, rogue_step=p, separation=sep,
               verdict=verdict)
    out = os.path.join(SG.OUT, "shipfr.json")
    json.dump(res, io.open(out, "w", encoding="utf-8"), default=float, indent=1)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
