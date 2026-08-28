"""Commission headscore.py's classifier before any of its verdicts are believed.

headscore.py reuses flatexp's measurement core, which is commissioned 8/8 in
commission_flatexp.py. But `classify()` and the BAND constant are NEW CODE with a
NEW ORIENTATION -- blotch and grain improve DOWNWARD, sharpness improves UPWARD --
and a sign error there inverts the conclusion silently. A new classifier is a new
instrument regardless of how well-tested the ruler underneath it is.

FIVE ARMS. The pair this project insists on, plus a band-matched plant per floor
axis:

  null      exact copy               -- all three axes UNCHANGED. Proves the
                                        instrument is quiet. Already shown at
                                        corpus scale: 26/26 UNCHANGED, every
                                        ratio exactly 1.0000.
  blur      gaussian, sigma 1.2      -- sharp REGRESSED, and grain must NOT be
                                        allowed to read the blur as a clean-up.
                                        This is the trade `focus-stack` already
                                        took: 0.077 fine grain and 0.260 mid-band,
                                        10-25x below both other arms, because it
                                        is a blurred image and not a clean one.
                                        The arm exists to prove the gauge SEES
                                        the sharpness price of a noise win.
  noise     white, sigma 90/65535    -- grain REGRESSED.
  mottle    bandpassed to 21-61 px   -- blotch REGRESSED.
  improve   fine-scale shrinkage     -- grain IMPROVED while sharp is HELD. THE
                                        LOAD-BEARING ARM. A suite that plants only
                                        degradations cannot distinguish a metric
                                        that is BLIND to an improvement from one
                                        that is PERVERSE on it, and this project
                                        has shipped a statistic bounded below by
                                        zero that could never charge for the
                                        artifact it was built to catch.

WHY THERE ARE TWO SEPARATE NOISE ARMS, and it is the first thing this suite
taught me. The first version planted white noise and required the BLOTCH axis --
the 21-61 px mottle band -- to read REGRESSED. It read UNCHANGED at 1.0001 and
0.9999, and I recorded it as a gauge failure. It was not. White noise has almost
no power at 21-61 px, so a band-selective statistic is CORRECT to ignore it, and
band selectivity is the entire reason that axis exists. A plant must be matched
to the band it is meant to move, or the commissioning is testing the plant.

THE IMPROVE ARM WAS ALSO MINE TO FIX. Its first version smoothed with weight
exp(-(g/p75)^2) where p75 is the 75th percentile of the subject's own gradient.
On `flat-on-ruler-cpl`, a mostly-flat subject, that weight stays high over real
detail and the arm cost 1.9% of sharpness -- so the gauge scored it REGRESSED and
was RIGHT to. It refused to certify my "improvement" as free. The arm now shrinks
only the fine-scale residual (x - gaussian(x, 1.0)), which lives at <=3 px by
construction and cannot touch the 5-13 px structure band the sharpness axis
reads. That is a targeted denoise rather than a smoother I merely hoped was
edge-preserving.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

HERE = Path(__file__).resolve().parent
SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
WORK = Path(r"C:\dev\strehl-out\BUILD-RECERT\commission-head")
SUBJECTS = ["coffee-bubbles", "flat-on-ruler-cpl"]
MAX = 65535

# arm -> {axis: required verdict}. "*" means unconstrained.
EXPECT = {
    "null":    {"blotch": "UNCHANGED", "sharp": "UNCHANGED", "grain": "UNCHANGED"},
    "blur":    {"blotch": "*",         "sharp": "REGRESSED", "grain": "*"},
    "noise":   {"blotch": "*",         "sharp": "*",         "grain": "REGRESSED"},
    "mottle":  {"blotch": "REGRESSED", "sharp": "*",         "grain": "*"},
    "improve": {"blotch": "*",         "sharp": "UNCHANGED", "grain": "IMPROVED"},
}


def make(arm, a):
    if arm == "null":
        return a.copy()
    x = a.astype(np.float32)
    if arm == "blur":
        for c in range(x.shape[2]):
            x[..., c] = gaussian_filter(x[..., c], 1.2)
    elif arm == "noise":
        rng = np.random.default_rng(20260827)
        x = x + rng.normal(0.0, 90.0, size=x.shape).astype(np.float32)
    elif arm == "mottle":
        # Band-limited to the 21-61 px mottle band the blotch axis reads. A
        # difference of gaussians is a bandpass; sigma 12 and 35 put the
        # passband over that range. White noise does NOT move this axis and
        # should not -- see the module docstring.
        rng = np.random.default_rng(20260828)
        for c in range(x.shape[2]):
            w = rng.normal(0.0, 1.0, size=x.shape[:2]).astype(np.float32)
            band = gaussian_filter(w, 12.0) - gaussian_filter(w, 35.0)
            s = float(band.std())
            if s <= 0:
                raise SystemExit("mottle plant produced a constant field")
            # Amplitude, not chosen by taste. At 250 the plant raised the blotch
            # ratio to only 1.0026 / 1.0054 -- the right DIRECTION but inside the
            # 1% band, so it read UNCHANGED. A plant that moves a statistic by
            # less than the statistic's own resolution has not commissioned it.
            x[..., c] = x[..., c] + band * (2500.0 / s)
    elif arm == "improve":
        # Shrink ONLY frequencies above the structure band, with a BRICK WALL.
        #
        # Two gaussian versions of this arm were rejected by the gauge before
        # this one, and both times the gauge was right:
        #   sigma 1.0 -> sharp 0.9252 / 0.9266   (7.4% of structure)
        #   sigma 0.5 -> sharp 0.9863 / 0.9869   (1.35% of structure)
        # The reason is that a gaussian is not a band separator. Its MTF is
        # exp(-2 pi^2 sigma^2 f^2), which at sigma 0.5 still passes 82% of the
        # amplitude at f = 0.20 cyc/px (lambda 5 px) -- the fine end of the
        # 5-13 px structure band. Halving "the fine residual" therefore removes
        # ~9% of the real amplitude at 5 px. There is no gaussian that denoises
        # the grain band without leaking into the band next to it.
        #
        # An FFT brick wall does separate them. The structure band the sharpness
        # axis reads is 0.077-0.20 cyc/px; the grain band is <= 3 px, i.e. above
        # 0.33 cyc/px. Attenuating only f > 0.30 cyc/px cannot alter a single
        # sample of struct-band content -- that is exact, not approximate, and it
        # is what makes this a genuine improvement rather than a small blur.
        h, w = x.shape[:2]
        fy = np.fft.fftfreq(h).astype(np.float32)[:, None]
        fx = np.fft.rfftfreq(w).astype(np.float32)[None, :]
        keep = np.hypot(fy, fx) > 0.30
        mask = np.where(keep, np.float32(0.5), np.float32(1.0))
        del fy, fx, keep
        for c in range(x.shape[2]):
            sp = np.fft.rfft2(x[..., c])
            sp *= mask
            x[..., c] = np.fft.irfft2(sp, s=(h, w)).astype(np.float32)
            del sp
        del mask
    return np.clip(x, 0, MAX).astype(np.uint16)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    src = {s: SHIP / f"{s}--SHIP-V4.tiff" for s in SUBJECTS}
    for s, p in src.items():
        if not p.exists():
            raise SystemExit(f"missing {p}")

    results = {}
    for arm in EXPECT:
        d = WORK / arm
        d.mkdir(exist_ok=True)
        for s in SUBJECTS:
            dst = d / f"{s}--COMM.tiff"
            if not dst.exists():
                a = tifffile.imread(src[s])
                b = make(arm, a)
                if arm != "null" and np.array_equal(a, b):
                    raise SystemExit(
                        f"PLANT DID NOT LAND: arm {arm!r} on {s} is bit-identical "
                        f"to its source. An inert plant reads exactly like a "
                        f"metric that is blind to it.")
                tifffile.imwrite(dst, b)
                del a, b
        out = WORK / f"{arm}.json"
        p = subprocess.run(
            [sys.executable, str(HERE / "headscore.py"),
             "--cand", str(d), "--cand-tag", "COMM", "--json", str(out)],
            capture_output=True, text=True)
        if p.returncode != 0:
            print(p.stdout[-2000:], p.stderr[-2000:])
            raise SystemExit(f"headscore failed on arm {arm}")
        import json
        rows = json.loads(out.read_text(encoding="utf-8"))
        results[arm] = {r["subject"]: r for r in rows}

    print(f"{'arm':<10}{'subject':<20}{'blotch':>9}{'sharp':>9}{'grain':>9}  verdicts")
    print("-" * 92)
    passes = fails = 0
    for arm, want in EXPECT.items():
        for s in SUBJECTS:
            r = results[arm].get(s)
            if not r or r.get("state") != "SCORED":
                print(f"{arm:<10}{s:<20}  NOT SCORED"); fails += 1; continue
            got = {"blotch": r["blotch_verdict"], "sharp": r["sharp_verdict"],
                   "grain": r["grain_verdict"]}
            ok = all(want[k] == "*" or got[k] == want[k] for k in want)
            passes += ok
            fails += not ok
            print(f"{arm:<10}{s:<20}{r['blotch_corr']:>9.4f}{r['sharp']:>9.4f}"
                  f"{r['grain_corr']:>9.4f}  "
                  f"b={got['blotch']:<10}s={got['sharp']:<10}g={got['grain']:<10}"
                  f"{'PASS' if ok else 'FAIL want ' + str(want)}")

    n = len(EXPECT) * len(SUBJECTS)
    print(f"\n{passes}/{n} commissioning cells PASS  "
          f"{'GREEN' if fails == 0 else 'RED'}")
    shutil.rmtree(WORK, ignore_errors=True)   # ~1 GB; ten lanes share this disk
    print(f"cleaned {WORK}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
